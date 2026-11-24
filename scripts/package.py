"""Source-only distributable, with per-file hashes and ZIP CRC verification."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.venv','.local','.git','__pycache__','tools','.render','.studio'}
SUFFIXES={'.mp4','.mkv','.mov','.wav','.raw','.nut','.f32','.bin','.safetensors','.pyc','.zip','.log'}


def build(destination):
    files=[p for p in ROOT.rglob('*') if p.is_file() and not EXCLUDED.intersection(p.relative_to(ROOT).parts) and p.suffix.lower() not in SUFFIXES and p.name!='MANIFESTO_SHA256.json']
    records=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(files)]
    manifest=ROOT/'MANIFESTO_SHA256.json'
    manifest.write_text(json.dumps({'version':'2.0.2','files':records},ensure_ascii=False,indent=2),encoding='utf-8')
    files.append(manifest)
    destination=Path(destination).resolve();destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as bundle:
        for p in sorted(files):bundle.write(p,'AI-Local-Studio/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(destination) as bundle:
        if bundle.testzip() is not None:raise RuntimeError('ZIP CRC failure')
        for record in records:
            if hashlib.sha256(bundle.read('AI-Local-Studio/'+record['path'])).hexdigest()!=record['sha256']:raise RuntimeError('Hash mismatch')
    result=dict(path=str(destination),files=len(files),bytes=destination.stat().st_size,sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
    print(json.dumps(result,indent=2));return result


if __name__=='__main__':
    import sys
    build(sys.argv[1] if len(sys.argv)>1 else ROOT.parent/'AI_Local_Studio_2_0_2.zip')
