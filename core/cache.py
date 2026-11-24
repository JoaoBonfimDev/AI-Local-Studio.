"""Stage-specific persistent cache, independent of editing/render settings."""
import hashlib
import json
from pathlib import Path
from .process import load_json, save_json

VERSION = '2.0.0-analysis-3'


def fingerprint(path):
    path = Path(path).resolve()
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for position in sorted({0, max(0, stat.st_size // 2 - 524288), max(0, stat.st_size - 1048576)}):
            stream.seek(position); digest.update(stream.read(1048576))
    return dict(path=str(path), size=stat.st_size, mtime_ns=stat.st_mtime_ns, sampled_sha256=digest.hexdigest())


def key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:32]


class Cache:
    def __init__(self, root, source):
        self.identity = fingerprint(source)
        self.root = Path(root) / key(self.identity)
        self.root.mkdir(parents=True, exist_ok=True)
        save_json(self.root / 'source.json', self.identity)
        self.hits = 0
        self.misses = 0

    def stage(self, stage, settings):
        folder = self.root / (stage + '-' + key([VERSION, settings]))
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def get(self, path):
        try:
            result = load_json(path)
            self.hits += 1
            return result
        except (OSError, ValueError):
            self.misses += 1
            return None
