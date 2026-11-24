"""AI Local Studio 2.0.2: one server, one job, shared local processing."""
import argparse
import json
import threading
import webbrowser
from core.gpu import diagnose


def main():
    parser=argparse.ArgumentParser(description='AI Local Studio 2.0.2 — 100% local')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--doctor',action='store_true')
    args=parser.parse_args()
    if args.doctor:
        print(json.dumps(diagnose(),ensure_ascii=False,indent=2));return
    from web.server import make_server
    try:server=make_server(args.port)
    except OSError as exc:
        raise SystemExit(f'Não foi possível abrir o servidor local: {exc}. Verifique se o Studio já está aberto ou se o Windows bloqueou sockets locais.')
    url=f'http://127.0.0.1:{server.server_port}/'
    print('AI Local Studio 2.0.2\n'+url+'\nMantenha esta janela aberta. Ctrl+C para encerrar.',flush=True)
    if not args.no_browser:threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:
        server.manager.cancel.set();server.stop.set()
        if server.manager.worker:server.manager.worker.join(timeout=10)
        server.server_close()


if __name__=='__main__':main()
