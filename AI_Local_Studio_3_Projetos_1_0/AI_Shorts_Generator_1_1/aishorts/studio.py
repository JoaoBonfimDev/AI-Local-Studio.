"""Local-only, dependency-free browser control panel for four Short exports."""
import json
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .config import ROOT, load, lock, run_directory
from .media import save

ASSET = ROOT / 'assets' / 'studio.html'
STAGES = (
    ('prepare', 'Preparação', 2),
    ('audio', 'Transcrição de áudio', 45),
    ('visual', 'Análise dos frames', 22),
    ('rank', 'Seleção dos momentos', 4),
    ('render', 'Renderização dos Shorts', 23),
    ('verify', 'Verificação dos MP4', 3),
    ('export', 'Exportação local', 1),
)
WEIGHTS = {name: weight for name, _label, weight in STAGES}
BEFORE = {}
total = 0
for name, _label, weight in STAGES:
    BEFORE[name] = total
    total += weight


class Studio:
    def __init__(self, config_path=None):
        self.config_path = Path(config_path or ROOT / 'config.local.json').resolve()
        self.lock = threading.RLock()
        self.config = load(self.config_path)
        self.phase = 'idle'
        self.stage = 'prepare'
        self.stage_pct = 0
        self.percent = 0
        self.message = 'Escolha sua gravação para começar.'
        self.started = None
        self.updated = None
        self.outputs = []
        self.output_details = []
        self.rendered_shorts = 0
        self.logs = []
        self.error = None
        self.run_folder = None

    def snapshot(self):
        with self.lock:
            elapsed = time.monotonic() - self.started if self.started else 0
            eta = None
            if self.phase == 'running' and self.stage_pct >= 5 and self.updated:
                stage_elapsed = max(0, time.monotonic() - self.updated)
                if stage_elapsed > 1:
                    eta = round(stage_elapsed * (100 - self.stage_pct) / self.stage_pct)
            return {
                'phase': self.phase,
                'stage': self.stage,
                'stage_percent': round(self.stage_pct, 1),
                'percent': round(self.percent, 1),
                'message': self.message,
                'elapsed': round(elapsed),
                'eta_stage': eta,
                'error': self.error,
                'outputs': [{'name': p.name, 'path': str(p),
                             'category':self.output_details[i].get('category',''),
                             'reason':self.output_details[i].get('reason',''),
                             'quote':self.output_details[i].get('quote',''),
                             'start':self.output_details[i].get('start',0),
                             'score':self.output_details[i].get('score',0)}
                            for i,p in enumerate(self.outputs)],
                'rendered_shorts': self.rendered_shorts,
                'logs': list(self.logs[-14:]),
                'run_folder': str(self.run_folder) if self.run_folder else None,
                'stages': [{'id': name, 'label': label} for name, label, _ in STAGES],
                'config': {key: self.config.get(key, '') for key in
                           ('input','export_directory','model_path','encoder',
                           'transcription_device','quality','selection_style',
                            'minimum_score','duration_seconds','label')},
                'audio_options':{'analysis':self.config.get('audio_track',0),
                                 'render':self.config.get('render_audio_track',0)},
            }

    def event(self, stage, pct, message):
        with self.lock:
            if stage == 'done':
                self.percent = self.stage_pct = 100
                self.stage = 'done'
            elif stage in WEIGHTS:
                pct = min(100, max(0, float(pct)))
                if self.stage != stage:
                    self.updated = time.monotonic()
                self.stage = stage
                self.stage_pct = pct
                self.percent = max(self.percent, BEFORE[stage] + WEIGHTS[stage] * pct / 100)
                if stage == 'render':
                    self.rendered_shorts = max(self.rendered_shorts, min(4, int(pct / 25)))
                elif stage in ('verify','export'):
                    self.rendered_shorts = 4
            self.message = message
            if not self.logs or self.logs[-1]['message'] != message:
                self.logs.append({'stage': stage, 'message': message})
                self.logs = self.logs[-45:]

    def start(self, payload):
        with self.lock:
            if self.phase == 'running':
                raise ValueError('Já existe uma geração em andamento.')
            allowed = {'input','export_directory','model_path','encoder','quality','selection_style',
                       'audio_track','render_audio_track',
                       'transcription_device','minimum_score','duration_seconds','label'}
            if not isinstance(payload, dict) or set(payload) - allowed:
                raise ValueError('Opções de geração inválidas.')
            cfg = dict(self.config)
            for field in allowed:
                if field in payload:
                    cfg[field] = payload[field]
            for field in ('input','export_directory','model_path'):
                value = str(cfg.get(field) or '').strip()
                cfg[field] = str(Path(value).expanduser().resolve()) if value else ''
            if not cfg['input'] or not Path(cfg['input']).is_file():
                raise ValueError('Selecione o arquivo de vídeo original existente.')
            if not cfg['export_directory'] or not Path(cfg['export_directory']).is_absolute():
                raise ValueError('Selecione uma pasta de saída válida.')
            if cfg['encoder'] not in ('auto','h264_nvenc','libx264'):
                raise ValueError('Encoder inválido.')
            if cfg['quality'] not in ('balanced','high','ultra'):
                raise ValueError('Qualidade inválida.')
            if cfg['selection_style'] not in ('balanced','action','commentary','observation'):
                raise ValueError('Perfil de seleção inválido.')
            if cfg['transcription_device'] not in ('auto','cuda','cpu'):
                raise ValueError('Dispositivo Whisper inválido.')
            cfg['duration_seconds'] = int(cfg['duration_seconds'])
            cfg['minimum_score'] = int(cfg['minimum_score'])
            for name in ('audio_track','render_audio_track'):
                cfg[name]=int(cfg[name])
                if cfg[name]<0 or cfg[name]>31:raise ValueError('Índice da faixa de áudio inválido.')
            if not 30 <= cfg['duration_seconds'] <= 60:
                raise ValueError('Os Shorts devem durar entre 30 e 60 segundos.')
            if not 0 <= cfg['minimum_score'] <= 100:
                raise ValueError('A nota mínima deve estar entre 0 e 100.')
            cfg['label'] = str(cfg['label']).strip()[:35] or 'GAMEPLAY'
            cfg['shorts'] = 4
            cfg['paid_api_enabled'] = False
            self.config = cfg
            self.phase = 'running'
            self.stage = 'prepare'
            self.stage_pct = self.percent = 0
            self.message = 'Validando vídeo e modelo local...'
            self.started = time.monotonic()
            self.updated = self.started
            self.outputs = []
            self.output_details = []
            self.rendered_shorts = 0
            self.logs = []
            self.error = None
            self.run_folder = None
            worker = threading.Thread(target=self._work, args=(cfg,), name='shorts-pipeline', daemon=True)
            worker.start()

    def _work(self, cfg):
        try:
            from .pipeline import execute
            from .scan import model_location
            model_location(cfg)  # Fail early, before extracting a huge WAV.
            save(self.config_path, cfg)
            folder = run_directory(cfg)
            with self.lock:
                self.run_folder = folder
            with lock(folder):
                exported = execute(cfg, folder, 'run', progress=self.event, require_four=True)
            files = [Path(item['file']) for item in exported]
            if len(files) != 4 or not all(p.is_file() for p in files):
                raise RuntimeError('A exportação não confirmou os quatro arquivos.')
            with self.lock:
                self.outputs = files
                self.output_details = exported
                self.rendered_shorts = 4
                self.phase = 'done'
                self.percent = self.stage_pct = 100
                self.stage = 'done'
                self.message = '4 Shorts prontos! Assista no painel ou abra a pasta de saída.'
        except Exception as error:
            with self.lock:
                self.phase = 'error'
                self.error = f'{type(error).__name__}: {error}'
                self.message = 'A execução foi interrompida. Seus arquivos anteriores foram preservados.'


def _file_dialog(kind):
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as error:
        raise RuntimeError('Seletor nativo indisponível: informe o caminho manualmente.') from error
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    try:
        if kind == 'video':
            return filedialog.askopenfilename(parent=root,title='Escolha a gravação',
                   filetypes=[('Vídeos','*.mp4 *.mkv *.mov *.avi *.webm'),('Todos','*.*')])
        if kind in ('output','model'):
            return filedialog.askdirectory(parent=root,title='Escolha a pasta')
        raise ValueError('Seletor inválido.')
    finally:
        root.destroy()


def create_server(studio):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'AIShortsLocal/1.0'

        def log_message(self, _format, *_args):
            pass

        def _headers(self, code, content_type, length=None, extra=None):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; media-src 'self'; connect-src 'self'; img-src 'self' data:")
            if length is not None:self.send_header('Content-Length', str(length))
            if extra:
                for key,value in extra.items():self.send_header(key,value)
            self.end_headers()

        def _json(self, code, data):
            content = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self._headers(code, 'application/json; charset=utf-8', len(content))
            self.wfile.write(content)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/':
                page = ASSET.read_text(encoding='utf-8').replace('__LOCAL_TOKEN__', token)
                body = page.encode('utf-8')
                self._headers(200,'text/html; charset=utf-8',len(body))
                self.wfile.write(body)
            elif path == '/api/status':
                self._json(200, studio.snapshot())
            elif path.startswith('/api/video/'):
                try:
                    from urllib.parse import parse_qs
                    if parse_qs(urlsplit(self.path).query).get('token') != [token]:
                        return self._json(403,{'error':'Token do vídeo inválido.'})
                    idx = int(path.rsplit('/',1)[1]) - 1
                    with studio.lock:
                        file = studio.outputs[idx] if studio.phase == 'done' and 0 <= idx < 4 else None
                    if file is None or not file.is_file():raise FileNotFoundError()
                    self._video(file)
                except (FileNotFoundError,ValueError):
                    self._json(404,{'error':'Short indisponível.'})
            else:
                self._json(404,{'error':'Página desconhecida.'})

        def _video(self, file):
            size = file.stat().st_size
            start,end = 0,size-1
            header = self.headers.get('Range','')
            if header:
                import re
                match = re.fullmatch(r'bytes=(\d*)-(\d*)',header)
                if not match: return self._headers(416,'text/plain',0,{'Content-Range':f'bytes */{size}'})
                a,b = match.groups()
                if not a and b:
                    start = max(0,size-int(b))
                else:
                    start = int(a or 0)
                    end = min(size-1,int(b)) if b else size-1
                if start>=size or end<start:
                    return self._headers(416,'text/plain',0,{'Content-Range':f'bytes */{size}'})
            length = end-start+1
            extra = {'Accept-Ranges':'bytes'}
            if header:extra['Content-Range']=f'bytes {start}-{end}/{size}'
            self._headers(206 if header else 200,'video/mp4',length,extra)
            with file.open('rb') as stream:
                stream.seek(start)
                while length > 0:
                    block = stream.read(min(length,256*1024))
                    if not block:break
                    try:self.wfile.write(block)
                    except (BrokenPipeError,ConnectionResetError):break
                    length -= len(block)

        def do_POST(self):
            expected_origin = f'http://127.0.0.1:{self.server.server_port}'
            if (self.headers.get('Origin') not in (None,expected_origin)
                    or self.headers.get('X-Local-Token') != token):
                return self._json(403,{'error':'Acesso local não autorizado.'})
            try:
                size = int(self.headers.get('Content-Length','0'))
                if not 0 <= size <= 16384:raise ValueError('Formulário muito grande.')
                data = json.loads(self.rfile.read(size) or b'{}')
                path = urlsplit(self.path).path
                if path == '/api/start':
                    studio.start(data)
                    return self._json(200,{'ok':True})
                if path == '/api/pick':
                    if studio.snapshot()['phase'] == 'running':raise ValueError('Aguarde a execução terminar.')
                    kind = data.get('kind')
                    return self._json(200,{'path':_file_dialog(kind)})
                if path == '/api/inspect-audio':
                    from .media import inspect
                    file=Path(str(data.get('input') or '')).expanduser()
                    if not file.is_file():raise ValueError('Selecione um vídeo existente antes de verificar as faixas.')
                    details=inspect(file)
                    streams=[s for s in details['streams'] if s['type']=='audio']
                    return self._json(200,{'tracks':[
                        {'index':i,'label':f'Faixa {i} · {s["codec"]} · {s["metadata"].get("title") or s["metadata"].get("handler_name") or "áudio"}'}
                        for i,s in enumerate(streams)]})
                if path == '/api/open-output':
                    if studio.snapshot()['phase'] != 'done':raise ValueError('A saída ainda não está pronta.')
                    directory = Path(studio.config['export_directory'])
                    if os.name == 'nt':os.startfile(str(directory))
                    else:
                        import subprocess
                        subprocess.Popen(['xdg-open',str(directory)])
                    return self._json(200,{'ok':True})
                raise ValueError('Ação desconhecida.')
            except Exception as error:
                return self._json(400,{'error':str(error)})

    return ThreadingHTTPServer(('127.0.0.1',0), Handler)


def launch(config_path=None, open_browser=True):
    studio = Studio(config_path)
    server = create_server(studio)
    address = f'http://127.0.0.1:{server.server_port}/'
    print(f'AI Shorts Local Studio: {address}', flush=True)
    print('Mantenha esta janela aberta durante a geração. Para encerrar: Ctrl+C.', flush=True)
    if open_browser:
        threading.Timer(0.7, lambda: webbrowser.open(address)).start()
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:print('\nPainel encerrado.',flush=True)
    finally:server.server_close()

