"""FFmpeg process control. No shell, no remote media, no original writes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading


class Cancelled(Exception):
    pass


class Runner:
    def __init__(self, cancel=None, log=None):
        self.cancel = cancel or threading.Event()
        self.log = log or (lambda message: None)

    def run(self, args, timeout=None, cwd=None):
        if self.cancel.is_set():
            raise Cancelled('Operação cancelada.')
        self.log(' '.join(map(str, args)))
        # Disk-backed stderr/stdout avoids pipe deadlocks and unbounded RAM.
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            p = subprocess.Popen(list(map(str, args)), stdout=out, stderr=err,
                                 stdin=subprocess.DEVNULL,
                                 cwd=cwd,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            import time
            start = time.monotonic()
            while p.poll() is None:
                if self.cancel.wait(.15):
                    p.kill()
                    p.wait()
                    raise Cancelled('Operação cancelada.')
                if timeout and time.monotonic() - start > timeout:
                    p.kill()
                    p.wait()
                    raise RuntimeError('Tempo limite excedido: ' + str(args[0]))
            out.seek(0)
            if p.returncode:
                err.seek(0, 2)
                err.seek(max(0, err.tell() - 6000))
                raise RuntimeError(err.read().decode('utf-8', 'replace'))
            return out.read()


def binary(name):
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f'{name} não encontrado no PATH. Leia INSTALACAO_WINDOWS.md.')
    return found


def ffmpeg():
    return [binary('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y']


def local_file(value):
    if not isinstance(value, str) or not value.strip() or '://' in value:
        raise ValueError('Informe o caminho de um vídeo local.')
    p = Path(value.strip().strip('"')).expanduser().resolve()
    if not p.is_file():
        raise ValueError('Vídeo não encontrado: ' + str(p))
    if p.suffix.lower() not in {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v', '.ts'}:
        raise ValueError('Extensão de vídeo não suportada.')
    return p


def probe(path, runner=None):
    runner = runner or Runner()
    data = json.loads(runner.run([binary('ffprobe'), '-v', 'error', '-show_streams',
                                  '-show_format', '-of', 'json', str(path)], timeout=60))
    videos = [s for s in data['streams'] if s['codec_type'] == 'video'
              and not s.get('disposition', {}).get('attached_pic')]
    if len(videos) != 1:
        raise ValueError('A versão 1.0 exige exatamente uma faixa de vídeo.')
    v = videos[0]
    duration = float(data.get('format', {}).get('duration', v.get('duration', 0)))
    if duration <= 0:
        raise ValueError('Não foi possível determinar a duração do vídeo.')
    # Refuse metadata which cannot be preserved reliably by this pipeline.
    side = json.dumps(v.get('side_data_list', []))
    if v.get('color_transfer') in {'smpte2084', 'arib-std-b67'} or any(s in side.lower() for s in ('dovi', 'dolby', 'dynamic hdr', 'mastering display', 'content light')):
        raise ValueError('Metadados HDR especiais detectados. A versão 1.0 não os preserva com segurança.')
    if any(float(s.get('rotation', 0)) != 0 for s in v.get('side_data_list', []) if 'rotation' in s):
        raise ValueError('Vídeo com rotação: normalize a orientação antes de usar esta versão.')
    return dict(duration=duration, video=v,
                audio=[s for s in data['streams'] if s['codec_type'] == 'audio'],
                size=int(data.get('format', {}).get('size', 0)))


def pcm_codec(stream):
    fmt = stream.get('sample_fmt', '')
    return {'u8': 'pcm_u8', 's16': 'pcm_s16le', 's32': 'pcm_s32le',
            's64': 'pcm_s64le', 'flt': 'pcm_f32le', 'dbl': 'pcm_f64le'}.get(fmt.removesuffix('p'))


def render_args(source, segment, dest, info, encoder, nvdec):
    v = info['video']
    args = ffmpeg() + ['-noautorotate', '-ss', f"{segment['start']:.9f}"]
    if nvdec:
        args += ['-hwaccel', 'cuda']
    args += ['-i', str(source), '-t', f"{segment['end'] - segment['start']:.9f}",
             '-map', f"0:{v['index']}"]
    for audio in info['audio']:
        args += ['-map', f"0:{audio['index']}"]
    args += ['-map_metadata', '0', '-map_chapters', '-1', '-sn', '-dn',
             '-c:v', encoder, '-pix_fmt', '+' + v['pix_fmt'],
             '-fps_mode', 'passthrough', '-enc_time_base:v', v.get('time_base', '1/1000')]
    if encoder == 'ffv1':
        args += ['-level', '3', '-coder', '1', '-context', '1', '-g', '1', '-threads', '4']
    else:
        args += ['-preset', 'p4', '-tune', 'lossless', '-rc', 'constqp', '-qp', '0']
    if nvdec:
        # NVDEC outputs packed NV12/P010; explicitly repack at identical dimensions.
        # No chroma/depth change is allowed by +pix_fmt, and the preflight checks pixels.
        args += ['-vf', 'scale=iw:ih:flags=neighbor']
    color_options = {'color_range': 'color_range', 'color_space': 'colorspace',
                     'color_transfer': 'color_trc', 'color_primaries': 'color_primaries'}
    for tag, option in color_options.items():
        value = v.get(tag)
        if value and value not in ('unknown', 'unspecified', 'reserved'):
            args += ['-' + option + ':v:0', value]
    for i, audio in enumerate(info['audio']):
        codec = pcm_codec(audio)
        if not codec:
            raise ValueError('Formato de áudio não suportado sem perdas: ' + str(audio.get('sample_fmt')))
        args += [f'-c:a:{i}', codec]
    return args + [str(dest)]


def check_properties(source_info, output_info):
    for key in ('width', 'height', 'pix_fmt', 'sample_aspect_ratio'):
        if source_info['video'].get(key, '1:1') != output_info['video'].get(key, '1:1'):
            raise RuntimeError('Propriedade de vídeo alterada: ' + key)
    for key in ('color_range', 'color_space', 'color_transfer', 'color_primaries'):
        original = source_info['video'].get(key)
        if original and original not in ('unknown', 'unspecified') and original != output_info['video'].get(key):
            raise RuntimeError('Metadado de cor alterado: ' + key)
    if len(source_info['audio']) != len(output_info['audio']):
        raise RuntimeError('Número de faixas de áudio alterado.')
    for a, b in zip(source_info['audio'], output_info['audio']):
        for key in ('channels', 'sample_rate'):
            if a.get(key) != b.get(key):
                raise RuntimeError('Propriedade de áudio alterada: ' + key)


def render(source, plan, info, folder, mode, runner, progress):
    """Atomic outputs, one encoder for all segments, tested on actual source."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    count = sum(len(e['segments']) for e in plan['episodes'])
    with tempfile.TemporaryDirectory(prefix='render_', dir=folder) as temp:
        temp = Path(temp)
        sample = plan['episodes'][0]['segments'][0]
        sample = dict(start=sample['start'], end=min(sample['end'], sample['start'] + 1))
        def sample_hashes(path, original=False):
            cmd = ffmpeg()
            if original:
                cmd += ['-ss', str(sample['start'])]
            cmd += ['-i', str(path)]
            if original:
                cmd += ['-t', str(sample['end']-sample['start'])]
            data = runner.run(cmd + ['-map', '0:v:0', '-an', '-fps_mode', 'passthrough', '-f', 'framemd5', '-'])
            return [line.rsplit(b',',1)[-1].strip() for line in data.splitlines() if line and not line.startswith(b'#')]
        reference_hashes = sample_hashes(source, True) if mode != 'cpu' else None
        encoder, nvdec = 'ffv1', False
        if mode != 'cpu':
            try:
                runner.run(render_args(source, sample, temp/'decode.mkv', info, 'ffv1', True), timeout=90)
                if reference_hashes != sample_hashes(temp/'decode.mkv'):
                    raise RuntimeError('NVDEC não preservou os pixels na amostra.')
                nvdec = True
            except RuntimeError as exc:
                runner.log('NVDEC indisponível para a fonte; CPU: ' + str(exc))
            # NVENC lossless does not accept every chroma/depth. Never convert pixel formats.
            if info['video']['pix_fmt'] in {'yuv420p', 'yuv444p'}:
                try:
                    testfile = temp/'encode.mkv'
                    runner.run(render_args(source, sample, testfile, info, 'h264_nvenc', nvdec), timeout=90)
                    check_properties(info, probe(testfile, runner))
                    # Compare decoded video pixels before enabling lossless NVENC.
                    if reference_hashes != sample_hashes(testfile):
                        raise RuntimeError('NVENC não preservou os pixels na amostra.')
                    encoder = 'h264_nvenc'
                except RuntimeError as exc:
                    runner.log('NVENC sem perdas incompatível; FFV1: ' + str(exc))
        progress(0, f'Render: {encoder}; decodificação: {"NVDEC" if nvdec else "CPU"}')
        done = 0
        outputs = []
        for episode in plan['episodes']:
            parts = []
            for index, segment in enumerate(episode['segments']):
                part = temp / f'part_{episode["number"]:02}_{index:04}.mkv'
                runner.run(render_args(source, segment, part, info, encoder, nvdec))
                parts.append(part)
                done += 1
                progress(done / count * .95, f'Episódio {episode["number"]}: trecho {index + 1}')
            listing = temp / 'concat.txt'
            # Generated simple basenames avoid ffconcat quoting ambiguity.
            listing.write_text(''.join(f"file '{p.name}'\n" for p in parts), encoding='utf-8')
            pending = temp / f'episodio_{episode["number"]:02}.mkv'
            runner.run(ffmpeg() + ['-f', 'concat', '-safe', '1', '-i', listing.name,
                                   '-map', '0', '-c', 'copy', '-map_metadata', '0', str(pending)], cwd=temp)
            output_info = probe(pending, runner)
            check_properties(info, output_info)
            if not 600 - .1 <= output_info['duration'] <= 900 + .1:
                raise RuntimeError('Duração renderizada fora de 10 a 15 minutos.')
            final = folder / pending.name
            if final.exists():
                raise RuntimeError('Saída já existe; não será sobrescrita: ' + str(final))
            pending.rename(final)
            outputs.append(str(final))
            for part in parts:
                part.unlink()
        progress(1, 'Renderização concluída.')
        return dict(files=outputs, encoder=encoder, decoder='NVDEC' if nvdec else 'CPU')
