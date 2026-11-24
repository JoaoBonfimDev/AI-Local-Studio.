"""Single loopback server, CSRF token/Host/Origin checks, scoped range media."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
from urllib.parse import urlsplit,parse_qs

from core.jobs import Manager
from core.media import ROOT
from core.gpu import diagnose,telemetry


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass

    def allowed(self):
        return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}' and self.headers.get('Sec-Fetch-Site')!='cross-site'

    def authenticated(self):
        supplied=self.headers.get('X-Local-Token') or parse_qs(urlsplit(self.path).query).get('token',[''])[0]
        return secrets.compare_digest(supplied,self.server.token)

    def reply(self,data,code=200,kind='application/json; charset=utf-8'):
        body=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False,allow_nan=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers();self.wfile.write(body)

    def stream_media(self,path):
        if not path or not Path(path).is_file():return self.reply({'error':'Mídia indisponível.'},404)
        path=Path(path);length=path.stat().st_size;start=0;end=length-1
        header=self.headers.get('Range')
        if header:
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',header)
            if not match or not any(match.groups()):return self.reply({'error':'Range inválido'},416)
            if not match[1]:start=max(0,length-int(match[2]))
            else:start=int(match[1]);end=min(end,int(match[2])) if match[2] else end
            if start>end or start>=length:return self.reply({'error':'Range fora dos limites'},416)
        self.send_response(206 if header else 200)
        self.send_header('Content-Type','video/mp4' if path.suffix.lower()=='.mp4' else 'application/octet-stream')
        self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1))
        self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Content-Type-Options','nosniff')
        if header:self.send_header('Content-Range',f'bytes {start}-{end}/{length}')
        self.end_headers()
        try:
            with path.open('rb') as stream:
                stream.seek(start);remaining=end-start+1
                while remaining:
                    block=stream.read(min(1024*1024,remaining))
                    if not block:break
                    self.wfile.write(block);remaining-=len(block)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass

    def do_GET(self):
        if not self.allowed():return self.reply({'error':'Host recusado'},403)
        path=urlsplit(self.path).path
        if path=='/':
            html=(ROOT/'web/assets/index.html').read_text(encoding='utf-8').replace('__TOKEN__',self.server.token)
            return self.reply(html.encode('utf-8'),kind='text/html; charset=utf-8')
        if path in {'/app.js','/style.css'}:
            file=ROOT/'web/assets'/path[1:]
            return self.reply(file.read_bytes(),kind='text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8')
        if not self.authenticated():return self.reply({'error':'Token local obrigatório'},403)
        manager=self.server.manager
        if path=='/api/status':return self.reply(manager.snapshot())
        if path=='/api/diagnostics':return self.reply(self.server.diagnostics)
        if path=='/api/media/preview':return self.stream_media(manager.preview)
        if path=='/api/media/source':return self.stream_media(manager.source)
        if path.startswith('/api/media/result/'):
            try:return self.stream_media(manager.state['files'][int(path.rsplit('/',1)[1])]['file'])
            except (IndexError,ValueError,KeyError):return self.reply({'error':'Saída desconhecida'},404)
        return self.reply({'error':'Não encontrado'},404)

    def do_POST(self):
        expected=f'http://127.0.0.1:{self.server.server_port}'
        if not self.allowed() or not self.authenticated() or self.headers.get('Origin') not in {None,expected}:
            return self.reply({'error':'Solicitação local recusada'},403)
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<=2*1024*1024:raise ValueError('Corpo da solicitação inválido.')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError('Esperado um objeto JSON.')
            manager=self.server.manager
            path=urlsplit(self.path).path
            if path=='/api/analyze':manager.analyze(data)
            elif path=='/api/render':manager.begin_render(data)
            elif path=='/api/cancel':manager.cancel.set()
            elif path=='/api/resume':manager.resume()
            elif path=='/api/restore':manager.restore()
            elif path=='/api/preview':manager.make_preview(data)
            elif path=='/api/model':manager.download_model(data)
            elif path=='/api/open':
                target=manager.export_folder
                if target and target.is_dir() and os.name=='nt':os.startfile(str(target))
            elif path=='/api/browse':
                if manager.busy():raise ValueError('Aguarde a operação atual.')
                kind='folder' if data.get('kind')=='folder' else 'file'
                p=subprocess.run([sys.executable,'-X','utf8','-m','web.dialog',kind],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if p.returncode:raise ValueError('Seletor indisponível. Cole o caminho no campo.')
                return self.reply({'path':p.stdout.strip()})
            else:return self.reply({'error':'Não encontrado'},404)
            return self.reply({'ok':True})
        except (ValueError,TypeError,KeyError,OSError) as exc:
            return self.reply({'error':str(exc)},400)


def make_server(port=8765,data_root=None,diagnostics=True):
    manager=Manager(data_root or ROOT/'.local')
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.daemon_threads=True;server.token=secrets.token_urlsafe(32);server.manager=manager
    server.diagnostics={'message':'Diagnóstico em andamento'}
    stop=threading.Event();server.stop=stop
    def monitor():
        if diagnostics:
            try:server.diagnostics=diagnose()
            except Exception as exc:server.diagnostics={'error':str(exc)}
        while not stop.is_set():
            manager.telemetry=telemetry()
            stop.wait(2)
    threading.Thread(target=monitor,daemon=True).start()
    return server
