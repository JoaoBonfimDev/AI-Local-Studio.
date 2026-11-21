import argparse
import threading
import webbrowser
from highlights.server import make_server

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AI Highlights Generator 1.0 — 100% local')
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    server = make_server(args.port)
    url = f'http://127.0.0.1:{server.server_port}'
    print('AI Highlights Generator 1.0\n' + url + '\nCtrl+C para encerrar.')
    if not args.no_browser:
        threading.Timer(.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.manager.cancel.set()
    finally:
        server.manager.cancel.set()
        if server.manager.worker is not None:
            server.manager.worker.join(timeout=5)
        server.server_close()
