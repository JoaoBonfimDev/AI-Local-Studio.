"""Small end-to-end HTTP tests without downloading models or touching user videos."""
import http.client
import json
import re
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from aishorts.studio import Studio, create_server


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfgpath = self.root / 'config.local.json'
        self.source = self.root / 'demo.mp4'
        self.source.write_bytes(b'fake-video-for-pipeline-mock')
        self.model = self.root / 'model'
        self.model.mkdir()
        (self.model / 'model.bin').write_bytes(b'fake-model')
        self.export = self.root / 'export'
        self.studio = Studio(self.cfgpath)
        self.studio.config['data_directory'] = str(self.root / 'work')
        self.payload = dict(input=str(self.source),export_directory=str(self.export),
                            model_path=str(self.model),minimum_score='35',
                            duration_seconds='45',encoder='auto',transcription_device='cpu',label='TEST')

    def test_progress_and_four_outputs(self):
        def fake_execute(_cfg,folder,stage,progress,require_four):
            self.assertEqual(stage,'run')
            self.assertTrue(require_four)
            progress('prepare',100,'Fonte validada')
            progress('audio',50,'Transcrevendo')
            progress('visual',100,'Analisando')
            progress('render',100,'Render finalizado')
            self.export.mkdir(parents=True)
            outputs=[]
            for index in range(4):
                file = self.export / f'Short {index+1}.mp4'
                file.write_bytes(b'MOCK'*512)
                outputs.append({'file':str(file)})
            progress('done',100,'Concluído')
            return outputs
        with patch('aishorts.pipeline.execute',side_effect=fake_execute):
            self.studio.start(self.payload)
            for _ in range(100):
                if self.studio.snapshot()['phase']!='running':break
                time.sleep(.01)
        result = self.studio.snapshot()
        self.assertEqual(result['phase'],'done',result['error'])
        self.assertEqual(len(result['outputs']),4)
        self.assertEqual(result['percent'],100)
        self.assertTrue((self.root/'work'/'runs').is_dir())

        server=create_server(self.studio)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(),server.server_close(),thread.join(timeout=3)))
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
        conn.request('GET','/')
        response=conn.getresponse()
        html=response.read().decode('utf-8')
        self.assertEqual(response.status,200)
        self.assertIn('4 Shorts',html)
        token=re.search(r"const TOKEN='([^']+)'",html).group(1)
        conn.request('GET','/api/status')
        response=conn.getresponse()
        data=json.loads(response.read())
        self.assertEqual(len(data['outputs']),4)
        details={'streams':[{'type':'video','codec':'h264','metadata':{}},
                            {'type':'audio','codec':'aac','metadata':{'title':'Mixagem'}},
                            {'type':'audio','codec':'aac','metadata':{'title':'Microfone'}}]}
        with patch('aishorts.media.inspect',return_value=details):
            conn.request('POST','/api/inspect-audio',json.dumps({'input':str(self.source)}),
                         headers={'Content-Type':'application/json','X-Local-Token':token,
                                  'Origin':f'http://127.0.0.1:{server.server_port}'})
            response=conn.getresponse()
            self.assertEqual(response.status,200)
            tracks=json.loads(response.read())['tracks']
            self.assertEqual(len(tracks),2)
            self.assertIn('Microfone',tracks[1]['label'])
        conn.request('GET','/api/video/1?token='+token,headers={'Range':'bytes=0-9'})
        response=conn.getresponse()
        self.assertEqual(response.status,206)
        self.assertEqual(response.read(),b'MOCKMOCKMO')
        conn.request('POST','/api/start','{}',headers={'Content-Type':'application/json'})
        response=conn.getresponse()
        self.assertEqual(response.status,403)
        response.read()
        conn.request('POST','/api/start','{}',headers={'Content-Type':'application/json',
                     'Origin':'http://evil.invalid','X-Local-Token':token})
        response=conn.getresponse()
        self.assertEqual(response.status,403)
        response.read()
        conn.close()

    def test_rejects_missing_video_and_parallel_jobs(self):
        with self.assertRaisesRegex(ValueError,'vídeo'):
            self.studio.start({**self.payload,'input':str(self.root/'missing.mp4')})
        event=threading.Event()
        def block(_cfg,folder,stage,progress,require_four):
            event.wait(timeout=3)
            return []
        with patch('aishorts.pipeline.execute',side_effect=block):
            self.studio.start(self.payload)
            with self.assertRaisesRegex(ValueError,'andamento'):
                self.studio.start(self.payload)
            event.set()
            for _ in range(100):
                if self.studio.snapshot()['phase']!='running':break
                time.sleep(.01)
            self.assertEqual(self.studio.snapshot()['phase'],'error')


if __name__ == '__main__':unittest.main()
