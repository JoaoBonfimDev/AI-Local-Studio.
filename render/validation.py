"""No success before stream checks, full decode, timestamps and A/V duration checks."""
import hashlib
import math
import struct
from pathlib import Path
from core.media import probe,ffmpeg,binary
from core.process import save_json


def faststart(path):
    boxes=[]
    with Path(path).open('rb') as stream:
        size=Path(path).stat().st_size
        while stream.tell()+8<=size:
            position=stream.tell();raw=stream.read(8)
            length,kind=struct.unpack('>I4s',raw)
            if length==1:
                length=struct.unpack('>Q',stream.read(8))[0]
            if length==0:length=size-position
            if length<8 or position+length>size:return False
            boxes.append(kind);stream.seek(position+length)
    return b'moov' in boxes and b'mdat' in boxes and boxes.index(b'moov')<boxes.index(b'mdat')


def validate(path,expected,runner):
    info=probe(path,runner)
    video=info['video'];audio=info['audio']
    tolerance=max(.12,2/expected['fps_float'])
    if video.get('codec_name')!='h264' or video.get('pix_fmt')!='yuv420p':
        diagnostic=Path(path).with_suffix('.failure.json')
        save_json(diagnostic,dict(stage='output_validation',file=str(path),expected=dict(codec='h264',pix_fmt='yuv420p'),
            observed={key:video.get(key) for key in ['codec_name','pix_fmt','color_range','profile','width','height']},
            note='Falha de formato na saída. Esta verificação não indica que a gravação original esteja corrompida.'))
        raise RuntimeError(f"Falha na validação da saída: codec={video.get('codec_name', 'desconhecido')}, pixels={video.get('pix_fmt', 'desconhecido')}, faixa={video.get('color_range', 'não informada')}. Esperado: H.264 yuv420p. Diagnóstico: {diagnostic}")
    if (info['width'],info['height'])!=tuple(expected['dimensions']):raise RuntimeError('Dimensões inesperadas na saída.')
    if len(audio)!=expected['audio_tracks'] or any(a.get('codec_name')!='aac' or a.get('profile')!='LC' for a in audio):raise RuntimeError('Áudio final precisa ser AAC-LC com as faixas esperadas.')
    if abs(info['duration']-expected['duration'])>tolerance:raise RuntimeError(f"Duração inválida: {info['duration']:.3f}s, esperado {expected['duration']:.3f}s")
    vduration=float(video.get('duration') or info['duration'])
    for stream in audio:
        if abs(float(stream.get('start_time') or 0)-float(video.get('start_time') or 0))>tolerance:raise RuntimeError('Início de áudio e vídeo dessincronizado.')
        if abs(float(stream.get('duration') or info['duration'])-vduration)>tolerance:raise RuntimeError('Duração do áudio e vídeo diverge.')
    if not faststart(path):raise RuntimeError('MP4 incompleto ou sem faststart.')
    runner.run(ffmpeg()+['-xerror','-err_detect','explode','-i',str(path),'-map','0:v:0','-map','0:a?','-f','null','-'],total=info['duration'],stage='Validação: decodificação completa')
    # Check DTS monotonicity and PCM packet gaps without loading packet lists in RAM.
    # FFprobe writes disk-backed output; scan individual lines afterwards.
    import tempfile
    import subprocess
    with tempfile.TemporaryDirectory(prefix='als-packets-') as tmp:
        packets=Path(tmp)/'packets.txt'
        runner.run([binary('ffprobe'),'-v','error','-show_packets','-show_entries','packet=stream_index,dts_time,pts_time,duration_time','-of','compact=p=0:nk=0','-o',str(packets),str(path)])
        previous={};gaps=0
        with packets.open('r',encoding='utf-8') as stream:
            for line in stream:
                runner.check()
                fields=dict(piece.split('=',1) for piece in line.strip().split('|') if '=' in piece)
                try:
                    index=int(fields['stream_index']);dts=float(fields['dts_time']);dur=float(fields.get('duration_time',0))
                except (KeyError,ValueError):continue
                if index in previous:
                    old,old_duration=previous[index]
                    if dts<old-1e-6:raise RuntimeError('DTS regressivo detectado na saída.')
                    if any(a['index']==index for a in audio) and dts-(old+old_duration)>.025:gaps+=1
                previous[index]=(dts,dur)
        if gaps:raise RuntimeError(f'{gaps} lacunas de pacotes de áudio na saída.')
    with Path(path).open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    return dict(file=str(path),duration=info['duration'],bytes=Path(path).stat().st_size,sha256=sha,
        codec='h264',audio='aac' if audio else None,full_decode_passed=True,monotonic_dts=True,audio_packet_gaps=0,faststart=True,
        dimensions=[info['width'],info['height']],expected=expected)
