"""Streaming-in-blocks adaptation of Gameplay media scans and Shorts visual signals."""
from array import array
import math
from pathlib import Path
import sys
import tempfile
from .media import ffmpeg
from .process import save_json
from legacy.gameplay_editor.media import build_activity

BLOCK = 60
WIDTH, HEIGHT = 160, 90


def _samples(raw):
    values = array('h'); values.frombytes(raw[:len(raw)//2*2])
    if sys.byteorder != 'little': values.byteswap()
    return values


def analyze(info, cache, runner, *, sample_seconds=2, decode='auto', audio_track=0):
    duration = info['duration']
    total = math.ceil(duration)
    audio = []
    visual = []
    audio_folder = cache.stage('audio', {'track': audio_track, 'rate': 8000})
    visual_folder = cache.stage('visual', {'step': sample_seconds, 'size': [WIDTH, HEIGHT]})
    decoder = 'CPU'
    hardware = None
    previous = None
    with tempfile.TemporaryDirectory(prefix='als-scan-') as tmp:
        tmp = Path(tmp)
        for start in range(0, math.ceil(duration), BLOCK):
            runner.check()
            end = min(duration, start + BLOCK)
            name = f'{start:08}.json'
            part = cache.get(audio_folder / name)
            if part is None:
                values = []
                if info['audio']:
                    rawpath = tmp / 'audio.raw'
                    runner.run(ffmpeg() + ['-ss', str(start), '-i', info['path'], '-t', str(end-start), '-map', f'0:a:{audio_track}', '-vn', '-ac', '1', '-ar', '8000', '-f', 's16le', str(rawpath)], total=end-start, stage=f'Áudio {start}s–{end:g}s')
                    samples = _samples(rawpath.read_bytes())
                    for i in range(0, len(samples), 8000):
                        block = samples[i:i+8000]
                        values.append(round(math.sqrt(sum(int(x)*int(x) for x in block)/len(block))/32768, 6))
                part = (values + [0.] * math.ceil(end-start))[:math.ceil(end-start)]
                save_json(audio_folder / name, part)
            else:
                runner.report('Áudio em cache', end, duration, f'{end:g}s recuperados')
            audio.extend(part)
        for start in range(0, math.ceil(duration), BLOCK):
            runner.check()
            end = min(duration, start+BLOCK)
            name = f'{start:08}.json'
            part = cache.get(visual_folder / name)
            if part is None:
                rawpath = tmp / 'frames.raw'
                vf = f'fps=1/{sample_seconds},scale={WIDTH}:{HEIGHT},format=gray'
                base = ffmpeg() + ['-ss', str(start)]
                tail = ['-i', info['path'], '-t', str(end-start), '-an', '-sn', '-dn', '-vf', vf, '-pix_fmt', 'gray', '-f', 'rawvideo', str(rawpath)]
                if decode != 'cpu' and hardware is not False:
                    try:
                        gpu_tail = list(tail)
                        gpu_tail[gpu_tail.index('-vf')+1] = f'fps=1/{sample_seconds},scale_cuda={WIDTH}:{HEIGHT}:format=yuv420p,hwdownload,format=yuv420p,format=gray'
                        runner.run(base + ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'] + gpu_tail, total=end-start, stage=f'Visual NVDEC {start}s–{end:g}s')
                        hardware = True; decoder = 'NVDEC + scale CUDA'
                    except RuntimeError:
                        hardware = False
                        runner.report('Fallback CPU', 0, end-start, 'NVDEC/scale CUDA indisponível para a fonte; usando CPU.')
                if decode == 'cpu' or hardware is False:
                    runner.run(base + tail, total=end-start, stage=f'Visual CPU {start}s–{end:g}s')
                raw = rawpath.read_bytes()
                size = WIDTH*HEIGHT
                if len(raw) % size: raise RuntimeError('Quadro parcial na análise visual.')
                part = []
                for i in range(0, len(raw), size):
                    frame = raw[i:i+size]
                    difference = sum(abs(a-b) for a,b in zip(previous, frame))/size if previous is not None else 0.
                    part.append(dict(seconds_approx=round(start+i//size*sample_seconds, 4), difference=difference, brightness=sum(frame)/size))
                    previous = frame
                # Store final frame to correctly continue an interrupted scan.
                save_json(visual_folder/name, {'rows': part, 'last_frame': list(previous or b''), 'decoder': decoder})
            else:
                previous = bytes(part.get('last_frame', [])) or None
                decoder = part.get('decoder', decoder)
                runner.report('Visual em cache', end, duration, f'{end:g}s recuperados')
                part = part['rows']
            visual.extend(part)
    motion = [0.] * total
    for row in visual:
        first = int(row['seconds_approx'])
        for i in range(first, min(total, first+sample_seconds)):
            motion[i] = min(1., row['difference']/48)
    audio = (audio+[0.]*total)[:total]
    return dict(audio=audio, visual=visual, motion=motion, activity=build_activity(audio, motion), decoder=decoder,
        cache_hits=cache.hits, cache_misses=cache.misses)
