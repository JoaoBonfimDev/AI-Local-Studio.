"""Bounded-memory audiovisual scoring and chronological, disjoint episodes."""
import math
from pathlib import Path
import tempfile
import numpy as np
from .media import Cancelled, ffmpeg

BLOCK = 60.0
FPS = 2
WIDTH, HEIGHT = 160, 90


def normalized(values):
    a = np.asarray(values, dtype=float)
    if not len(a):
        return a
    low, high = np.percentile(a, [10, 90])
    return np.clip((a - low) / max(high - low, 1e-8), 0, 1)


def analyze(source, info, runner, progress, mode='auto'):
    duration = info['duration']
    progress(.01, 'Analisando movimento em cópia reduzida; a saída mantém o original.')
    with tempfile.TemporaryDirectory(prefix='highlights_analysis_') as tmp:
        tmp = Path(tmp)
        frames = tmp/'frames.gray'
        decoder, scaler = 'CPU', 'CPU'
        base = ffmpeg()
        args = ['-i', str(source), '-map', f"0:{info['video']['index']}", '-an', '-sn', '-dn',
                '-vf', f'fps={FPS},scale={WIDTH}:{HEIGHT},format=gray',
                '-f', 'rawvideo', str(frames)]
        if mode != 'cpu':
            try:
                gpu_args = args.copy()
                gpu_args[gpu_args.index('-vf')+1] = f'fps={FPS},scale_cuda={WIDTH}:{HEIGHT}:format=yuv420p,hwdownload,format=yuv420p,format=gray'
                runner.run(base + ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'] + gpu_args)
                decoder = 'NVDEC'
                scaler = 'CUDA'
            except RuntimeError as exc:
                runner.log('Scale CUDA indisponível: ' + str(exc))
                try:
                    runner.run(base + ['-hwaccel', 'cuda'] + args)
                    decoder = 'NVDEC'
                except RuntimeError as exc:
                    runner.log('Análise NVDEC indisponível; CPU: ' + str(exc))
                    runner.run(base + args)
        else:
            runner.run(base + args)
        if frames.stat().st_size < WIDTH * HEIGHT * 2:
            raise ValueError('Vídeo sem quadros suficientes para análise.')
        progress(.55, f'Movimento decodificado com {decoder}. Analisando áudio.')
        audio_path = tmp/'audio.f32'
        # Only scoring is mixed to mono. Export keeps every original audio track separately.
        audio = None
        if info['audio']:
            runner.run(base + ['-i', str(source), '-map', f"0:{info['audio'][0]['index']}",
                               '-vn', '-ac', '1', '-ar', '8000', '-f', 'f32le', str(audio_path)])
            if audio_path.stat().st_size:
                audio = np.memmap(audio_path, dtype='<f4', mode='r')
        frame_count = frames.stat().st_size // (HEIGHT * WIDTH)
        data = np.memmap(frames, dtype=np.uint8, mode='r', shape=(frame_count, HEIGHT, WIDTH))
        torch = None
        scorer = 'NumPy CPU'
        if mode != 'cpu':
            try:
                import torch as candidate
                if candidate.cuda.is_available():
                    candidate.zeros(1, device='cuda')
                    torch = candidate
                    scorer = 'PyTorch CUDA'
            except (ImportError, RuntimeError, OSError) as exc:
                runner.log('CUDA para pontuação indisponível: ' + str(exc))
        blocks = []
        try:
            for i in range(int(duration // BLOCK)):
                if runner.cancel.is_set():
                    raise Cancelled('Análise cancelada.')
                start, end = i * BLOCK, (i+1) * BLOCK
                part = np.asarray(data[int(start*FPS):int(end*FPS)], dtype=np.float32)
                if len(part) < 2:
                    break
                if torch is not None:
                    try:
                        tensor = torch.from_numpy(part).to('cuda')
                        diffs = (tensor[1:] - tensor[:-1]).abs().mean(dim=(1, 2)) / 255
                        motion = float(torch.quantile(diffs, .75).item())
                        del tensor, diffs
                    except RuntimeError as exc:
                        runner.log('Falha CUDA; retomando pontuação CPU: ' + str(exc))
                        torch = None
                        scorer = 'NumPy CPU (fallback)'
                        motion = float(np.percentile(np.abs(np.diff(part, axis=0)).mean(axis=(1, 2))/255, 75))
                else:
                    motion = float(np.percentile(np.abs(np.diff(part, axis=0)).mean(axis=(1, 2))/255, 75))
                energy = 0.
                if audio is not None:
                    samples = np.asarray(audio[int(start*8000):int(end*8000)])
                    if len(samples):
                        energy = float(np.sqrt(np.mean(samples.astype(np.float64)**2)))
                blocks.append(dict(start=start, end=end, motion=motion, audio=energy))
                progress(.65 + .34 * (i+1)/max(1, int(duration//BLOCK)), f'Pontuando minuto {i+1} com {scorer}')
        finally:
            # Windows cannot delete files while memory maps remain open.
            data._mmap.close()
            del data
            if audio is not None:
                audio._mmap.close()
                del audio
        motions = normalized([b['motion'] for b in blocks])
        energies = normalized([b['audio'] for b in blocks])
        for i, block in enumerate(blocks):
            block['score'] = float(.8 * motions[i] + .2 * energies[i])
        progress(1, 'Análise concluída.')
        return dict(blocks=blocks, decoder=decoder, scaler=scaler, scorer=scorer,
                    method='80% movimento + 20% energia do áudio; blocos de contexto de 60 s')


def validate(plan, duration):
    episodes = plan.get('episodes', [])
    if not 1 <= len(episodes) <= 10:
        raise ValueError('O plano precisa conter de 1 a 10 episódios.')
    previous = -1.
    for number, e in enumerate(episodes, 1):
        total = 0.
        if not isinstance(e, dict) or not isinstance(e.get('segments'), list) or not e['segments']:
            raise ValueError('Episódio vazio.')
        for s in e['segments']:
            try:
                start, end = float(s['start']), float(s['end'])
            except (KeyError, TypeError, ValueError):
                raise ValueError('Cada trecho precisa conter start e end numéricos.') from None
            if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= duration + 1e-6):
                raise ValueError('Trecho fora dos limites da fonte.')
            if start < previous - 1e-6:
                raise ValueError('Trechos repetidos, sobrepostos ou fora de ordem.')
            total += end-start
            previous = end
            s.update(start=start, end=end)
        if not 600 <= total <= 900:
            raise ValueError('Cada episódio precisa durar de 600 a 900 segundos.')
        e.update(number=number, duration=total)
    return plan


def select(blocks, duration, max_episodes=10, target_minutes=12, keep_fraction=.6):
    if not isinstance(max_episodes, int) or not 1 <= max_episodes <= 10:
        raise ValueError('Escolha de 1 a 10 episódios.')
    if target_minutes not in (11, 12, 13, 14):
        raise ValueError('Duração alvo: 11, 12, 13 ou 14 minutos.')
    if not .1 <= keep_fraction <= 1:
        raise ValueError('Fração de seleção inválida.')
    # Remove truly static/silent blocks; relative ranking alone would select loading screens.
    eligible = [dict(b) for b in blocks if b['motion'] >= .003 or b['audio'] >= .01]
    eligible.sort(key=lambda b: (-b['score'], b['start']))
    budget = min(len(eligible), max(10, int(len(eligible) * keep_fraction)))
    n = min(max_episodes, budget // target_minutes)
    if n == 0 and budget >= 10:
        n = 1
    if not n:
        raise ValueError('Menos de 10 minutos de material elegível. Não serão criados episódios curtos ou repetidos.')
    per_episode = min(target_minutes, budget // n)
    chosen = sorted(eligible[:n * per_episode], key=lambda b: b['start'])
    episodes = []
    for i in range(n):
        group = chosen[i*per_episode:(i+1)*per_episode]
        segments = []
        for b in group:
            if segments and abs(segments[-1]['end'] - b['start']) < 1e-6:
                segments[-1]['end'] = b['end']
            else:
                segments.append(dict(start=b['start'], end=b['end']))
        episodes.append(dict(number=i+1, duration=sum(s['end']-s['start'] for s in segments),
                             segments=segments))
    return validate(dict(version='1.0', episodes=episodes, eligible_minutes=len(eligible),
                         selected_minutes=n*per_episode,
                         note='Seleção heurística; revise os trechos antes de renderizar.'), duration)
