"""Install into the project venv; never change the user's global Python packages."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import venv
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    if sys.version_info<(3,12):raise RuntimeError('Instale Python 3.13 ou 3.14; os módulos preservados exigem sintaxe de Python 3.12 ou superior.')
    environment=ROOT/'.venv'
    interpreter=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not interpreter.is_file():
        print('Criando ambiente virtual isolado...',flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    if '--offline' not in sys.argv:
        # A missing speech wheel must not prevent local video editing.
        result=subprocess.run([str(interpreter),'-m','pip','install','--only-binary=:all:','--timeout','15','--retries','1','-r',str(ROOT/'requirements.txt')],check=False)
        if result.returncode:
            print('Dependencias de fala indisponiveis. O motor audiovisual funciona; tente INSTALAR_IA.cmd depois.',flush=True)
    tools=ROOT/'tools';tools.mkdir(exist_ok=True)
    missing=[name for name in ['ffmpeg','ffprobe'] if not shutil.which(name) and not (tools/(name+'.exe')).is_file()]
    if missing:
        if '--offline' in sys.argv:raise RuntimeError('FFmpeg/FFprobe ausentes para instalacao offline.')
        print('Baixando FFmpeg/FFprobe por HTTPS para tools/ (sem instalacao global)...',flush=True)
        with tempfile.TemporaryDirectory(prefix='als-install-') as temporary:
            archive=Path(temporary)/'ffmpeg.zip'
            with urllib.request.urlopen('https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',timeout=90) as response,archive.open('wb') as output:
                shutil.copyfileobj(response,output,1024*1024)
            with zipfile.ZipFile(archive) as bundle:
                for name in missing:
                    matches=[n for n in bundle.namelist() if n.endswith('/bin/'+name+'.exe')]
                    if len(matches)!=1:raise RuntimeError('Pacote FFmpeg inesperado.')
                    with bundle.open(matches[0]) as source,(tools/(name+'.exe')).open('xb') as target:
                        shutil.copyfileobj(source,target,1024*1024)
    for name in ['ffmpeg','ffprobe']:
        executable=tools/(name+'.exe')
        subprocess.run([str(executable) if executable.is_file() else name,'-version'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run([str(interpreter),'-X','utf8','-m','compileall','-q','core','modes','render','web','main.py'],cwd=ROOT,check=True)
    print('Instalacao base concluida. INICIAR.cmd abre o Studio. INSTALAR_IA.cmd permite repetir a instalacao das dependencias de fala.',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as exc:print('Falha: '+str(exc),file=sys.stderr);raise SystemExit(1)
