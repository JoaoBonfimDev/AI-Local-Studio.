"""Adapted from Shorts scan.audio: bounded windows, local model, checkpoint resume."""
import gc
import json
from pathlib import Path
import sys
import tempfile
import wave
from .media import ffmpeg, probe
from .process import Runner, save_json, load_json


def execute(source, folder, cfg):
    from .gpu import configure_cuda
    configure_cuda()
    import numpy as np
    from faster_whisper import WhisperModel, BatchedInferencePipeline
    folder = Path(folder)
    info = probe(source)
    duration = info['duration']
    runner = Runner()
    def progress(done, message):
        save_json(folder/'progress.json', dict(stage='Transcrição local', done=done, total=duration, message=message))
    def load(device):
        return WhisperModel(cfg['model_path'], device=device, compute_type=cfg['compute_type'] if device=='cuda' else 'int8', cpu_threads=6, num_workers=1, local_files_only=True)
    using = 'cpu' if cfg['transcription_device']=='cpu' else 'cuda'
    progress(0, 'Carregando um modelo local; esta etapa não tem percentual mensurável.')
    try:
        model = load(using)
    except (RuntimeError, ValueError, OSError):
        if cfg['transcription_device']=='cuda': raise
        using='cpu'; model=load('cpu')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='als-whisper-') as tmp:
        wav = Path(tmp)/'part.wav'
        for start in range(0, __import__('math').ceil(duration), 30):
            end=min(duration,start+30)
            checkpoint=folder/f'{start:08}.json'
            if checkpoint.exists():
                rows.extend(load_json(checkpoint));progress(end,'Checkpoint de fala recuperado');continue
            runner.run(ffmpeg()+['-ss',str(start),'-i',source,'-t',str(end-start),'-map',f"0:a:{cfg['audio_track']}",'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',str(wav)])
            with wave.open(str(wav)) as audio:
                signal=np.frombuffer(audio.readframes(audio.getnframes()),np.int16).astype(np.float32)/32768
            def decode():
                args=dict(language=cfg['language'] or None, beam_size=3, word_timestamps=True, vad_filter=cfg['vad'], condition_on_previous_text=False)
                if cfg['batch_size']>1:
                    pipeline=BatchedInferencePipeline(model=model)
                    return pipeline.transcribe(signal,batch_size=cfg['batch_size'],**args)
                return model.transcribe(signal,**args)
            try:
                segments, details=decode(); decoded=list(segments)
            except (RuntimeError, ValueError, OSError):
                if using!='cuda' or cfg['transcription_device']=='cuda': raise
                # Release the GPU model before loading the fallback.
                del model;gc.collect();using='cpu';model=load('cpu')
                segments, details=decode();decoded=list(segments)
            part=[dict(start=s.start+start,end=s.end+start,text=s.text,language=details.language,
                       avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob,
                       words=[dict(start=w.start+start,end=w.end+start,text=w.word) for w in s.words or []]) for s in decoded]
            save_json(checkpoint,part);rows.extend(part)
            progress(end,'Transcrição '+using+'; voz e jogo podem estar misturados')
    save_json(folder/'complete.json',dict(segments=rows,device=using))


if __name__=='__main__':
    execute(sys.argv[1],sys.argv[2],json.loads(sys.argv[3]))
