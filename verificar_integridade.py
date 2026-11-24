"""Read-only verification of source files included in the release package."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    records=json.loads((ROOT/'MANIFESTO_SHA256.json').read_text(encoding='utf-8'))['files']
    errors=[]
    for record in records:
        path=(ROOT/record['path']).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():errors.append(record['path']);continue
        if path.stat().st_size!=record['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:errors.append(record['path'])
    if errors:raise SystemExit('Arquivos ausentes/alterados: '+', '.join(errors))
    print(f'OK: {len(records)} arquivos conferidos por tamanho e SHA-256.')


if __name__=='__main__':main()
