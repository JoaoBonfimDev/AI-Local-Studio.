"""Cancellable, bounded-memory subprocess runner adapted from Highlights 1.0."""
import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from legacy.highlights.media import Cancelled


class Runner:
    def __init__(self, cancel=None, report=None):
        self.cancel = cancel or threading.Event()
        self.report = report or (lambda *args: None)

    def check(self):
        if self.cancel.is_set():
            raise Cancelled('Operação interrompida; checkpoints preservados.')

    def run(self, args, *, total=None, stage='processamento', cwd=None, timeout=None, external_progress=None):
        self.check()
        with tempfile.TemporaryDirectory(prefix='als-process-') as tmp:
            progress = Path(tmp) / 'progress.txt'
            command = [str(a) for a in args]
            if total is not None:
                command[1:1] = ['-progress', str(progress), '-stats_period', '0.25', '-nostats']
                self.report(stage, 0, total, 'Iniciando ' + stage)
            with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out,
                    stderr=err, cwd=cwd, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                started = time.monotonic()
                try:
                    while process.poll() is None:
                        self.check()
                        if timeout and time.monotonic() - started > timeout:
                            raise RuntimeError('Tempo limite excedido: ' + command[0])
                        if total is not None and progress.exists():
                            try:
                                # Only read the tail; progress files can grow during long exports.
                                with progress.open('rb') as stream:
                                    stream.seek(max(0, progress.stat().st_size - 4096))
                                    rows = stream.read().decode('ascii', 'ignore').splitlines()
                                values = [int(r.split('=', 1)[1]) / 1e6 for r in rows if r.startswith('out_time_us=') and r[12:].lstrip('-').isdigit()]
                                if values:
                                    self.report(stage, min(total, max(0, values[-1])), total, stage)
                            except (OSError, ValueError):
                                pass
                        if external_progress:
                            try:
                                state = json.loads(Path(external_progress).read_text(encoding='utf-8'))
                                self.report(state['stage'], state['done'], state['total'], state['message'])
                            except (OSError, ValueError, KeyError):
                                pass
                        self.cancel.wait(.1)
                    self.check()
                    if process.returncode:
                        err.seek(0, 2); err.seek(max(0, err.tell() - 6000))
                        raise RuntimeError(err.read().decode('utf-8', 'replace').strip())
                    if total is not None:
                        self.report(stage, total, total, stage + ' concluída')
                    out.seek(0)
                    return out.read()
                finally:
                    if process.poll() is None:
                        process.kill(); process.wait()


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.tmp')
    with pending.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.flush()
    pending.replace(path)


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))
