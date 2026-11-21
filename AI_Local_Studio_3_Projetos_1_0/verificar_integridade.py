"""Read-only integrity verification of the distributed project files."""
from pathlib import Path
import hashlib
import json
import sys


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root/'MANIFESTO_SHA256.json').read_text(encoding='utf-8'))
    errors = []
    checked = 0
    for entry in manifest['files']:
        path = (root/entry['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            errors.append('Ausente ou caminho inválido: '+entry['path'])
            continue
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024),b''):
                digest.update(block)
        if path.stat().st_size != entry['size'] or digest.hexdigest() != entry['sha256']:
            errors.append('Alterado: '+entry['path'])
        checked += 1
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'OK: {checked} arquivos conferidos por tamanho e SHA-256.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
