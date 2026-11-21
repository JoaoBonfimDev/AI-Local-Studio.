"""Loopback-only browser UI with CSRF protection and a single cancellable job."""
import copy
from datetime import datetime
import json
from pathlib import Path
import secrets
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .media import Cancelled, Runner, local_file, probe, render
from .selection import analyze, select, validate

ROOT = Path(__file__).resolve().parent.parent


class Manager:
    def __init__(self):
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.worker = None
        self.state = dict(status='idle', progress=0, message='Selecione uma gameplay local.', log=[])
        self.source = self.info = self.folder = self.fingerprint = None
        self.mode = 'auto'

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.state)

    def update(self, **fields):
        with self.lock:
            self.state.update(fields)

    def log(self, message):
        with self.lock:
            self.state['log'] = (self.state['log'] + [message])[-100:]

    def progress(self, amount, message):
        self.update(progress=round(amount*100, 1), message=message)

    def busy(self):
        return self.worker is not None and self.worker.is_alive()

    def start(self, operation):
        if self.busy():
            raise ValueError('Já existe uma operação em andamento.')
        self.cancel.clear()
        def work():
            try:
                operation()
            except Cancelled:
                self.update(status='cancelled', message='Cancelado. Episódios já concluídos permanecem na pasta.')
            except Exception as exc:
                self.log(str(exc))
                self.update(status='error', message=str(exc))
        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def begin_analysis(self, data):
        if self.busy():
            raise ValueError('Aguarde ou cancele a operação atual.')
        source = local_file(data.get('input'))
        output = data.get('output', '').strip().strip('"')
        if not output or '://' in output:
            raise ValueError('Informe uma pasta local de saída.')
        base = Path(output).expanduser().resolve()
        if base == source:
            raise ValueError('A saída precisa ser uma pasta.')
        mode = data.get('mode', 'auto')
        if mode not in ('auto', 'cpu'):
            raise ValueError('Modo inválido.')
        limit, target, fraction = int(data.get('episodes', 10)), int(data.get('minutes', 12)), float(data.get('fraction', .6))
        if not 1 <= limit <= 10 or target not in (11, 12, 13, 14) or not .1 <= fraction <= 1:
            raise ValueError('Parâmetros de seleção inválidos.')
        self.source, self.mode = source, mode
        self.info = None
        self.fingerprint = (source.stat().st_size, source.stat().st_mtime_ns)
        self.folder = base / ('Highlights_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + secrets.token_hex(3))
        self.folder.mkdir(parents=True, exist_ok=False)
        self.update(status='analyzing', progress=0, message='Lendo vídeo...', log=[], plan=None, files=[])
        def operation():
            runner = Runner(self.cancel, self.log)
            self.info = probe(source, runner)
            if self.info['duration'] < 600:
                raise ValueError('A fonte tem menos de 10 minutos. Não haverá repetição para completar episódios.')
            result = analyze(source, self.info, runner, self.progress, mode)
            plan = select(result['blocks'], self.info['duration'], limit, target, fraction)
            plan.update(input=str(source), fingerprint=list(self.fingerprint), analysis=result,
                        source_info=self.info)
            (self.folder/'plano.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
            self.update(status='review', progress=100, message='Revise o plano e clique em Renderizar.',
                        plan=plan, folder=str(self.folder), hardware=dict(decoder=result['decoder'], scaler=result['scaler'], scorer=result['scorer']))
        self.start(operation)

    def begin_render(self, data):
        if self.busy() or self.source is None or self.info is None:
            raise ValueError('Analise um vídeo primeiro e aguarde o plano.')
        if self.state['status'] != 'review' or not self.state.get('plan'):
            raise ValueError('O plano não está disponível para renderização.')
        if self.fingerprint != (self.source.stat().st_size, self.source.stat().st_mtime_ns):
            raise ValueError('A fonte mudou desde a análise. Analise novamente.')
        requested = data.get('plan')
        plan = dict(version='1.0', episodes=requested.get('episodes', []) if isinstance(requested, dict) else [])
        validate(plan, self.info['duration'])
        plan.update(input=str(self.source), fingerprint=list(self.fingerprint))
        # An edited plan is always validated and persisted before the render.
        (self.folder/'plano_render.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
        self.update(status='rendering', progress=0, message='Testando codecs na fonte...', plan=plan)
        def operation():
            runner = Runner(self.cancel, self.log)
            result = render(self.source, plan, self.info, self.folder, self.mode, runner, self.progress)
            (self.folder/'resultado.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            self.update(status='done', progress=100, message='Episódios concluídos.', **result)
        self.start(operation)


def make_server(port=8767):
    token = secrets.token_urlsafe(32)
    manager = Manager()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, data, code=200, kind='application/json; charset=utf-8'):
            body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.allowed():
                return self.reply({'error': 'Host recusado.'}, 403)
            if self.path == '/':
                html = (ROOT/'web'/'index.html').read_text(encoding='utf-8').replace('__TOKEN__', token)
                return self.reply(html.encode('utf-8'), kind='text/html; charset=utf-8')
            if self.path == '/api/status' and self.headers.get('X-Local-Token') == token:
                return self.reply(manager.snapshot())
            self.reply({'error': 'Não encontrado.'}, 404)

        def do_POST(self):
            origin = self.headers.get('Origin')
            expected = f'http://127.0.0.1:{self.server.server_port}'
            if not self.allowed() or self.headers.get('X-Local-Token') != token or origin not in (None, expected):
                return self.reply({'error': 'Solicitação local recusada.'}, 403)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 1024*1024:
                    raise ValueError('Corpo da solicitação inválido.')
                data = json.loads(self.rfile.read(length))
                if self.path == '/api/analyze':
                    manager.begin_analysis(data)
                elif self.path == '/api/render':
                    manager.begin_render(data)
                elif self.path == '/api/cancel':
                    manager.cancel.set()
                elif self.path == '/api/browse':
                    if manager.busy():
                        raise ValueError('Aguarde a operação atual.')
                    kind = 'folder' if data.get('kind') == 'folder' else 'file'
                    p = subprocess.run([sys.executable, '-m', 'highlights.dialog', kind],
                                       capture_output=True, text=True, encoding='utf-8', cwd=ROOT)
                    if p.returncode:
                        raise ValueError('Seletor indisponível. Cole o caminho no campo.')
                    return self.reply({'path': p.stdout.strip()})
                elif self.path == '/api/open':
                    import os
                    if manager.folder and manager.folder.is_dir() and sys.platform == 'win32':
                        os.startfile(manager.folder)
                else:
                    return self.reply({'error': 'Não encontrado.'}, 404)
                self.reply({'ok': True})
            except (ValueError, TypeError, OSError) as exc:
                self.reply({'error': str(exc)}, 400)
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.manager = manager
    return server
