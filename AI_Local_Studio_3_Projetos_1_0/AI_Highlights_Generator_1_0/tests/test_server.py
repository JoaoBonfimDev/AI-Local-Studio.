import http.client
import io
from email.message import Message
import json
import os
import re
import threading
import unittest
from highlights.server import make_server


class HandlerTests(unittest.TestCase):
    """Exercise actual request handlers without a network connection."""
    def setUp(self):
        self.server = make_server(0)

    def tearDown(self):
        self.server.server_close()

    def request(self, method, path, body=None, headers=None):
        handler = object.__new__(self.server.RequestHandlerClass)
        handler.server = self.server
        handler.path = path
        handler.command = method
        handler.request_version = 'HTTP/1.1'
        handler.requestline = method+' '+path+' HTTP/1.1'
        handler.headers = Message()
        payload = json.dumps(body).encode() if body is not None else b''
        values = {'Host':f'127.0.0.1:{self.server.server_port}', 'Content-Length':str(len(payload))}
        values.update(headers or {})
        for k,v in values.items(): handler.headers[k]=v
        handler.rfile = io.BytesIO(payload)
        handler.wfile = io.BytesIO()
        getattr(handler, 'do_'+method)()
        result = handler.wfile.getvalue()
        head, content = result.split(b'\r\n\r\n',1)
        return int(head.split(b' ')[1]),content

    def token(self):
        code,html=self.request('GET','/')
        self.assertEqual(code,200)
        return re.search("const token='([^']+)'",html.decode())[1]

    def test_serves_ui_and_status(self):
        code,body=self.request('GET','/api/status',headers={'X-Local-Token':self.token()})
        self.assertEqual(code,200)
        self.assertEqual(json.loads(body)['status'],'idle')

    def test_rejects_cross_site_requests(self):
        token=self.token()
        code,_=self.request('POST','/api/cancel',{}, {'X-Local-Token':token,'Origin':'https://other.invalid'})
        self.assertEqual(code,403)
        code,_=self.request('POST','/api/cancel',{})
        self.assertEqual(code,403)

    def test_rejects_nonlocal_host(self):
        code,_=self.request('GET','/',headers={'Host':'remote.invalid'})
        self.assertEqual(code,403)

    def test_validates_input_before_starting_job(self):
        code,body=self.request('POST','/api/analyze',{'input':'https://example.org/video.mp4'}, {'X-Local-Token':self.token()})
        self.assertEqual(code,400)
        self.assertIn('local',json.loads(body)['error'])


@unittest.skipUnless(os.environ.get('RUN_HTTP_TESTS') == '1', 'Defina RUN_HTTP_TESTS=1 em ambiente com sockets locais liberados.')
class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = make_server(0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()

    def test_ui_and_authenticated_status(self):
        self.connection.request('GET', '/')
        r = self.connection.getresponse()
        self.assertEqual(r.status, 200)
        html = r.read().decode()
        token = re.search("const token='([^']+)'", html)[1]
        self.assertNotIn('__TOKEN__', html)
        self.connection.request('GET','/api/status',headers={'X-Local-Token': token})
        r = self.connection.getresponse()
        self.assertEqual(r.status, 200)
        self.assertEqual(json.loads(r.read())['status'],'idle')

    def test_mutation_without_token_is_denied(self):
        self.connection.request('POST','/api/analyze',body='{}')
        r = self.connection.getresponse()
        self.assertEqual(r.status,403)
        r.read()

    def test_cross_origin_and_bad_host_denied(self):
        self.connection.request('GET','/',headers={'Host':'evil.example'})
        r = self.connection.getresponse()
        self.assertEqual(r.status,403)
        r.read()
        self.connection.request('GET','/')
        r = self.connection.getresponse()
        token = re.search("const token='([^']+)'",r.read().decode())[1]
        self.connection.request('POST','/api/cancel',body='{}',headers={'X-Local-Token':token,'Origin':'http://evil.example'})
        r = self.connection.getresponse()
        self.assertEqual(r.status,403)
        r.read()
