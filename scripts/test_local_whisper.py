"""Opt-in real local Whisper test, using Windows offline SAPI synthetic speech."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.cache import Cache
from core.media import ROOT,ffmpeg,probe
from core.process import Runner
from core.settings import DEFAULTS
from core.transcription import transcribe


def main():
    import tkinter as tk
    from tkinter import filedialog
    window=tk.Tk();window.withdraw();window.attributes('-topmost',True)
    model=filedialog.askdirectory(title='Modelo Faster-Whisper local contendo model.bin')
    window.destroy()
    if not model:raise SystemExit('Teste cancelado.')
    if not (Path(model)/'model.bin').is_file():raise ValueError('Pasta de modelo inválida.')
    parent=ROOT/'.local'/'whisper-test';parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='test-',dir=parent) as temporary:
        folder=Path(temporary);wav=folder/'speech.wav';video=folder/'speech.mp4'
        environment=dict(os.environ,STUDIO_TEST_WAV=str(wav))
        code="$stream=New-Object -ComObject SAPI.SpFileStream; $stream.Open($env:STUDIO_TEST_WAV,3,$false); $voice=New-Object -ComObject SAPI.SpVoice; $voice.AudioOutputStream=$stream; $null=$voice.Speak('This is a local transcription test. One two three.'); $stream.Close()"
        subprocess.run(['powershell.exe','-NoProfile','-Command',code],env=environment,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        Runner().run(ffmpeg()+['-f','lavfi','-i','color=s=640x360:r=10','-i',str(wav),'-shortest','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(video)])
        info=probe(video)
        cfg={**DEFAULTS,'transcribe':True,'model_path':model,'language':'en','transcription_device':'auto'}
        cache=Cache(folder/'cache',video)
        rows,device=transcribe(info,cache,Runner(report=lambda stage,done,total,message:print(f'{stage}: {done:.1f}/{total:.1f}s {message}',flush=True)),cfg)
        text=' '.join(row['text'] for row in rows)
        if len(text.split())<2:raise RuntimeError('Modelo executou, mas não reconheceu fala suficiente no áudio sintético.')
        print('Transcrição real executada em:',device,'\nTexto:',text)
        rows2,device2=transcribe(info,cache,Runner(),cfg)
        assert rows==rows2
        print('Cache de transcrição: aprovado. Nenhum download ou gravação particular utilizado.')


if __name__=='__main__':
    try:main()
    except Exception as exc:print('Falha no teste local:',exc);raise SystemExit(1)
