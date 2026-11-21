"""Análise integral em blocos, adaptada de editorial_scan.py e review_current.py."""
import json,math,subprocess,wave
from pathlib import Path
import numpy as np
from . import media

def model_location(cfg):
    path=Path(cfg['model_path']) if cfg['model_path'] else Path(cfg['data_directory'])/'models'/cfg['model']
    if not (path/'model.bin').is_file():
        raise FileNotFoundError('Modelo local ausente. Configure model_path ou execute prepare-model --allow-download.')
    return path

def _notify(callback,stage,percent,message):
    if callback:callback(stage,percent,message)

def _extract_audio(cfg,wav,part,duration,callback):
    cmd=[media.ffmpeg(),'-hide_banner','-loglevel','error','-nostdin','-y',
         '-i',cfg['input'],'-map',f"0:a:{cfg['audio_track']}",'-ac','1','-ar','16000',
         '-c:a','pcm_s16le','-progress','pipe:1','-nostats',str(part)]
    recent=[]
    with subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                          text=True,encoding='utf-8',errors='replace') as proc:
        for line in proc.stdout:
            line=line.strip();recent.append(line);recent=recent[-12:]
            if line.startswith('out_time='):
                try:
                    t=line.split('=',1)[1];hours,minutes,seconds=t.split(':')
                    elapsed=int(hours)*3600+int(minutes)*60+float(seconds)
                    _notify(callback,'audio',min(9.5,elapsed/max(duration,.1)*10),'Extraindo áudio da gravação')
                except (ValueError,OverflowError):pass
        code=proc.wait()
    if code:raise RuntimeError('FFmpeg não conseguiu extrair áudio: '+' | '.join(recent[-5:]))
    part.replace(wav)

def _whisper(cfg,callback):
    from faster_whisper import WhisperModel
    device=cfg.get('transcription_device','auto')
    if device in ('auto','cuda'):
        try:
            _notify(callback,'audio',10,'Tentando Whisper na GPU')
            return WhisperModel(str(model_location(cfg)),device='cuda',compute_type='float16',local_files_only=True), True
        except (RuntimeError,OSError,ValueError) as error:
            if device=='cuda':raise RuntimeError(f'Whisper na GPU indisponível: {error}') from error
            _notify(callback,'audio',10,'GPU para transcrição indisponível; usando CPU')
    return WhisperModel(str(model_location(cfg)),device='cpu',compute_type='int8',cpu_threads=6,local_files_only=True), False

def audio(cfg,folder,callback=None):
    complete=folder/'coverage_audio.json'
    if complete.exists():
        _notify(callback,'audio',100,'Transcrição encontrada no cache');return
    model_location(cfg)
    duration=media.inspect(Path(cfg['input']))['duration'];wav=folder/'audio.wav'
    if not wav.exists():
        part=folder/'audio.partial.wav'
        _extract_audio(cfg,wav,part,duration,callback)
    model,using_cuda=_whisper(cfg,callback)
    rows=[];energy=[];chunk=cfg['chunk_seconds']
    with wave.open(str(wav)) as w:
        for index,start in enumerate(range(0,math.ceil(duration),chunk)):
            end=min(duration,start+chunk);cached=folder/f'transcript_{index:04}.json'
            if cached.exists():data=json.loads(cached.read_text(encoding='utf-8'))
            else:
                w.setpos(start*16000)
                signal=np.frombuffer(w.readframes(round((end-start)*16000)),np.int16).astype(np.float32)/32768
                energy_chunk=[float(np.sqrt(np.mean(signal[i:i+16000]**2))) for i in range(0,len(signal),16000)]
                # Short local windows reduce forced translation of mixed game/creator speech.
                segments=[]
                for offset in range(0,len(signal),30*16000):
                    base=start+offset/16000
                    args=dict(language=cfg['language'],beam_size=3,word_timestamps=True,vad_filter=True,
                              condition_on_previous_text=False,repetition_penalty=1.1,no_repeat_ngram_size=4)
                    try:
                        segs,info=model.transcribe(signal[offset:offset+30*16000],**args)
                        decoded=list(segs)
                    except (RuntimeError,OSError,ValueError):
                        if cfg.get('transcription_device','auto')!='auto' or not using_cuda:raise
                        _notify(callback,'audio',10+90*base/max(duration,.1),'CUDA falhou no áudio; retomando na CPU')
                        from faster_whisper import WhisperModel
                        model=WhisperModel(str(model_location(cfg)),device='cpu',compute_type='int8',cpu_threads=6,local_files_only=True)
                        using_cuda=False
                        segs,info=model.transcribe(signal[offset:offset+30*16000],**args)
                        decoded=list(segs)
                    for s in decoded:
                        segments.append({'start':s.start+base,'end':s.end+base,'text':s.text,'language':info.language,'language_probability':info.language_probability,'avg_logprob':s.avg_logprob,'no_speech_prob':s.no_speech_prob,'words':[{'start':t.start+base,'end':t.end+base,'text':t.word} for t in s.words or []]})
                    _notify(callback,'audio',10+90*min(duration,base+30)/max(duration,.1),'Transcrevendo áudio localmente')
                data={'segments':segments,'energy':energy_chunk};media.save(cached,data)
            rows.extend(data['segments']);energy.extend(data['energy']);print(f'Áudio: {end/duration:.0%}',flush=True)
            _notify(callback,'audio',10+90*end/max(duration,.1),'Transcrição em andamento')
    media.save(folder/'transcript.json',rows);media.save(folder/'energy.json',energy)
    media.save(complete,{'completed':True,'seconds':duration,'api_cost_brl':0})

def visuals(cfg,folder,callback=None):
    if (folder/'coverage_visual.json').exists():
        _notify(callback,'visual',100,'Análise visual encontrada no cache');return
    import cv2
    step=cfg['sample_seconds'];frames=folder/'frames';frames.mkdir(exist_ok=True)
    cmd=[media.ffmpeg(),'-hide_banner','-loglevel','error','-nostdin','-i',cfg['input'],'-an','-vf',f'fps=1/{step},scale=384:216','-pix_fmt','bgr24','-f','rawvideo','pipe:1']
    rows=[];previous=None
    duration=media.inspect(Path(cfg['input']))['duration']
    with subprocess.Popen(cmd,stdout=subprocess.PIPE) as proc:
        while True:
            raw=proc.stdout.read(384*216*3)
            if not raw:break
            if len(raw)!=384*216*3:raise RuntimeError('Quadro incompleto.')
            frame=np.frombuffer(raw,np.uint8).reshape(216,384,3);gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY).astype(float)
            index=len(rows);difference=float(np.abs(gray-previous).mean()) if previous is not None else 0
            rows.append({'seconds_approx':index*step,'difference':difference,'brightness':float(gray.mean()),'detail':float(cv2.Laplacian(gray,cv2.CV_64F).var())})
            cv2.imwrite(str(frames/f'{index:05}.jpg'),frame);previous=gray
            if index%8==0:_notify(callback,'visual',min(99,(index+1)*step/max(duration,.1)*100),'Analisando frames')
        if proc.wait():raise RuntimeError('Falha no FFmpeg durante análise visual.')
    media.save(folder/'visual.json',rows)
    for page in range(math.ceil(len(rows)/24)):
        canvas=np.zeros((6*244,4*384,3),np.uint8)
        for j,row in enumerate(rows[page*24:(page+1)*24]):
            index=page*24+j;y,x=j//4*244,j%4*384
            canvas[y:y+216,x:x+384]=cv2.imread(str(frames/f'{index:05}.jpg'))
            t=int(row['seconds_approx']);cv2.putText(canvas,f'~{t//60}:{t%60:02}',(x+5,y+236),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),1)
        cv2.imwrite(str(folder/f'contact_{page:04}.jpg'),canvas)
    media.save(folder/'coverage_visual.json',{'completed':True,'samples':len(rows),'sample_seconds':step,'timestamps':'approximate'})
    _notify(callback,'visual',100,'Análise visual concluída')
