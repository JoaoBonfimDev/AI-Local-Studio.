import json,tempfile,unittest
from pathlib import Path
from aishorts.config import load,identity,lock
from aishorts.media import save
from aishorts.ranking import generate,validate,LIMITS,selected,overlap
from aishorts.pipeline import captions
from aishorts.export import export_files,digest

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_root=Path(__file__).resolve().parents[1]/'.local/tests'
        self.temp_root.mkdir(parents=True,exist_ok=True)
    def test_cache_tracks_source_and_analysis_not_destination(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as tmp:
            p=Path(tmp)/'source.mp4';p.write_bytes(b'first');cfg=load();cfg['input']=str(p)
            first=identity(cfg);cfg['export_directory']=tmp;self.assertEqual(first,identity(cfg))
            cfg['audio_track']=1;self.assertNotEqual(first,identity(cfg));cfg['audio_track']=0
            p.write_bytes(b'changed');self.assertNotEqual(first,identity(cfg))

    def test_lock_prevents_parallel_runs(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as tmp:
            with lock(Path(tmp)):
                with self.assertRaises(RuntimeError):
                    with lock(Path(tmp)):pass
            self.assertFalse((Path(tmp)/'running.lock').exists())

    def test_no_candidates_for_silence_and_static_frames(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as tmp:
            f=Path(tmp);save(f/'transcript.json',[]);save(f/'energy.json',[0]*180)
            save(f/'visual.json',[{'seconds_approx':t,'difference':0,'brightness':0} for t in range(0,180,10)])
            self.assertEqual(generate(f,load(),180)['selected'],[])

    def test_whole_recording_and_limits(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as tmp:
            f=Path(tmp);save(f/'transcript.json',[{'start':170,'end':178,'text':'Nossa, consegui! Finalmente, caramba!', 'avg_logprob':-.1}])
            save(f/'energy.json',[.05]*180);save(f/'visual.json',[{'seconds_approx':t,'difference':20 if t>=140 else 0,'brightness':80} for t in range(0,180,10)])
            result=validate(generate(f,load(),180),180)
            self.assertTrue(selected(result));self.assertGreaterEqual(selected(result)[0]['start'],130)
            for c in result['clips']:
                self.assertEqual(c['score'],sum(c['scores'].values()))
                self.assertTrue(all(0<=v<=LIMITS[k] for k,v in c['scores'].items()))

    def test_diverse_selection_action_commentary_observation(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as tmp:
            folder=Path(tmp)
            duration=540
            phrases=[]
            def speech(at,phrase):
                for i in range(4):
                    phrases.append({'start':at+10*i,'end':at+10*i+8,
                                    'text':phrase,'avg_logprob':-.1,'no_speech_prob':0})
            speech(7,'Nossa, a polícia tá vindo, vai ter perseguição!')
            speech(112,'Eu acho que a gente deve voltar porque o jogo fica interessante nessa parte.')
            speech(205,'Olha isso! Que detalhe estranho, vocês viram esse lugar?')
            speech(315,'Caramba, uma explosão! Preciso fugir da polícia agora!')
            speech(423,'Eu pensei que essa missão era muito melhor, na minha opinião valeu a pena.')
            visual=[]
            for at in range(0,duration,10):
                movement=24 if (0<=at<80 or 300<=at<380) else 5
                visual.append({'seconds_approx':at,'difference':movement,'brightness':90})
            save(folder/'transcript.json',phrases)
            save(folder/'visual.json',visual)
            save(folder/'energy.json',[.06]*duration)
            cfg=load();cfg['duration_seconds']=45;cfg['minimum_score']=35
            result=validate(generate(folder,cfg,duration),duration)
            chosen=selected(result)
            self.assertEqual(len(chosen),4)
            self.assertEqual(result['composition'],{'acao':2,'comentario':1,'observacao':1})
            self.assertTrue(all(c['reason'] and c['quote'] for c in chosen))
            self.assertTrue(all(not overlap(a['parts'],b['parts']) for i,a in enumerate(chosen) for b in chosen[i+1:]))
            cfg['selection_style']='commentary'
            alternative=validate(generate(folder,cfg,duration),duration)
            self.assertEqual(alternative['composition'],{'acao':1,'comentario':2,'observacao':1})

    def test_commentary_without_action_is_eligible(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as tmp:
            folder=Path(tmp)
            sentences=[{'start':t,'end':t+8,'text':'Eu acho que o jogo poderia melhorar essa parte porque a história ficou diferente.',
                        'avg_logprob':-.1,'no_speech_prob':0} for t in range(10,42,10)]
            save(folder/'transcript.json',sentences)
            save(folder/'visual.json',[{'seconds_approx':i,'difference':5,'brightness':70} for i in range(0,90,10)])
            save(folder/'energy.json',[.04]*90)
            cfg=load();cfg['minimum_score']=30
            result=generate(folder,cfg,90)
            self.assertTrue(any('comentario' in c['eligible_categories'] for c in result['clips']))

    def test_action_can_be_found_when_microphone_track_is_silent(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as tmp:
            folder=Path(tmp)
            save(folder/'transcript.json',[])
            save(folder/'visual.json',[{'seconds_approx':i,'difference':27,'brightness':80}
                                      for i in range(0,100,10)])
            save(folder/'energy.json',[0]*100)
            cfg=load()
            result=generate(folder,cfg,100)
            self.assertTrue(any('acao' in c['eligible_categories'] for c in result['clips']))

    def test_caption_remap_and_low_confidence_exclusion(self):
        rows=[{'start':10,'end':11,'text':'Olá','language':'pt','avg_logprob':-.1,'no_speech_prob':0,'words':[{'start':10,'end':11,'text':'Olá'}]}, {'language':'en','words':[]}, {'language':'pt','avg_logprob':-2,'words':[]}]
        out=captions(rows,{'parts':[[0,2],[10,12]]})
        self.assertEqual(len(out),1);self.assertEqual(out[0]['words'][0]['start'],2)

    def test_export_no_overwrite_and_hash(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as tmp:
            f=Path(tmp);sources=[]
            for i in range(4):p=f/f'{i}.mp4';p.write_bytes(bytes([i])*1024);sources.append(p)
            a=export_files(sources,'Live.mkv',f/'dest');b=export_files(sources,'Live.mkv',f/'dest')
            self.assertEqual(len(list((f/'dest').glob('*.mp4'))),8)
            for src,x,y in zip(sources,a,b):
                self.assertNotEqual(x['file'],y['file']);self.assertEqual(digest(src),digest(Path(y['file'])))
            with self.assertRaises(ValueError):export_files(sources[:2],'Live.mkv',f/'missing')
            self.assertFalse((f/'missing').exists())

if __name__=='__main__':unittest.main()
