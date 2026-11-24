"""Real synthetic-media integration tests. No private recordings or model downloads."""
import copy
from fractions import Fraction
import hashlib
import http.client
from io import BytesIO
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from core.cache import Cache,fingerprint
from core.gpu import nvenc_available
from core.jobs import Manager
from core.media import ffmpeg,probe
from core.process import Runner,Cancelled,load_json,save_json
from core.scanner import analyze
from core.settings import DEFAULTS,validate as validate_settings
from modes.plan import create,validate
from modes import highlights,gameplay
from render.video import render,encoder_args
from render.validation import validate as validate_output
from web.server import make_server,Handler
from core.naming import game_name,mode_folder,video_stem,unique_video


class CoreTests(unittest.TestCase):
    def test_safe_windows_game_names_and_mode_folders(self):
        self.assertEqual(game_name('  GTA 6  '),'GTA 6')
        self.assertEqual(game_name('Final Fantasy VII: Remake'),'Final Fantasy VII Remake')
        self.assertNotIn('/',game_name('../../GTA 6'))
        self.assertNotIn('\\',game_name(r'GTA\6'))
        self.assertEqual(game_name('CON'),'_CON')
        self.assertEqual(game_name('NUL.txt'),'_NUL.txt')
        self.assertLessEqual(len(game_name('a'*200)),48)
        with self.assertRaises(ValueError):validate_settings({'game_name':7})
        self.assertEqual(validate_settings({'game_name':'   '})['game_name'],'')
        s={**DEFAULTS,'game_name':'GTA 6'}
        self.assertEqual(video_stem(s,1),'GTA 6 - Shorts 01')
        self.assertEqual(mode_folder(s),'Shorts')
        self.assertEqual(video_stem({**s,'mode':'gameplay','gameplay_mode':'best'},1),'GTA 6 - Gameplay longa - Melhores momentos')
        self.assertEqual(video_stem({**s,'mode':'highlights'},3),'GTA 6 - Highlights - Episodio 03')

    def test_settings_reject_nonfinite_and_wrong_enums(self):
        for payload in [{'episodes':11},{'encoder':'cmd.exe'},{'episode_minutes':float('nan')},{'episodes':1.5},{'transcribe':'yes'},{'mode':'gameplay','captions':True}]:
            with self.subTest(payload=payload),self.assertRaises(ValueError):validate_settings(payload)

    def test_plan_chronology_uniqueness_and_bounds(self):
        plan={'episodes':[{'segments':[{'start':1,'end':4}]},{'segments':[{'start':3,'end':6}]}]}
        with self.assertRaises(ValueError):validate(plan,100,'highlights')
        for pair in [(0,float('nan')),(-1,5),(1,101),(4,3)]:
            with self.assertRaises(ValueError):validate({'episodes':[{'segments':[dict(zip(['start','end'],pair))]}]},100,'gameplay')

    def test_quality_flags_are_encoder_specific(self):
        self.assertNotIn('-cq',encoder_args('libx264','ultra'))
        self.assertNotIn('-crf',encoder_args('h264_nvenc','ultra'))

    def test_highlights_variable_duration_disjoint_no_padding(self):
        a=dict(audio=[.1]*2400,motion=[.6]*2400,activity=[.9]*2400)
        for minutes in [10,12,16]:
            s={**DEFAULTS,'mode':'highlights','episode_minutes':minutes,'episodes':10,'sensitivity':100}
            eps=highlights.select(a,[],dict(duration=2400),s)
            validate({'episodes':eps},2400,'highlights')
            self.assertLess(len(eps),10)
            self.assertAlmostEqual(sum(sum(r['end']-r['start'] for r in e['segments']) for e in eps),2400)
        a=dict(audio=[0]*100,motion=[0]*100,activity=[0]*100)
        self.assertEqual(highlights.select(a,[],dict(duration=100),{**DEFAULTS,'mode':'highlights'}),[])

    def test_gameplay_no_artificial_duration_cap(self):
        a=dict(audio=[.1]*7200,motion=[.3]*7200,activity=[.9]*7200)
        eps=gameplay.select(a,[],dict(duration=7200),{**DEFAULTS,'mode':'gameplay'})
        self.assertEqual(eps[0]['segments'][0]['end'],7200)

    def test_cancel_running_process_promptly(self):
        cancel=threading.Event();runner=Runner(cancel)
        timer=threading.Timer(.2,cancel.set);timer.start()
        try:
            with self.assertRaises(Cancelled):runner.run([__import__('sys').executable,'-c','import time;time.sleep(20)'])
        finally:timer.cancel()


class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch=Path(__file__).resolve().parents[1]/'.local'/'tests';scratch.mkdir(parents=True,exist_ok=True)
        cls.temp=tempfile.TemporaryDirectory(prefix='media-',dir=scratch);cls.root=Path(cls.temp.name)
        cls.source=cls.root/'synthetic gameplay with spaces.mkv'
        Runner().run(ffmpeg()+['-f','lavfi','-i','testsrc2=size=320x180:rate=10',
            '-f','lavfi','-i','sine=frequency=440:sample_rate=48000',
            '-f','lavfi','-i','sine=frequency=880:sample_rate=44100',
            '-t','300','-map','0:v','-map','1:a','-map','2:a','-c:v','libx264','-preset','ultrafast','-crf','25','-c:a','pcm_s16le',str(cls.source)])
        cls.info=probe(cls.source);cls.original_hash=fingerprint(cls.source)
        cls.nvenc=nvenc_available()

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def folder(self,name):
        folder=self.root/(hashlib.sha256((self._testMethodName+'-'+name).encode()).hexdigest()[:8]);folder.mkdir(exist_ok=True);return folder

    def settings(self,mode='gameplay',encoder='cpu'):
        return {**DEFAULTS,'mode':mode,'encoder':encoder,'quality':'balanced','source_identity':self.original_hash}

    def test_import_scan_and_shared_cache(self):
        root=self.folder('cache');cache=Cache(root,self.source)
        reports=[];runner=Runner(report=lambda *r:reports.append(r))
        result=analyze(self.info,cache,runner,sample_seconds=2,decode='cpu')
        self.assertEqual(len(result['audio']),300);self.assertEqual(len(result['motion']),300)
        self.assertGreater(max(result['motion']),0)
        second=Cache(root,self.source)
        with patch.object(Runner,'run',side_effect=AssertionError('A cache hit must not decode again')):
            reused=analyze(self.info,second,Runner(),sample_seconds=2,decode='cpu')
        self.assertEqual(result['visual'],reused['visual']);self.assertEqual(second.hits,10)
        self.assertTrue(any(0<r[1]<=r[2] for r in reports if r[2]))
        # A selection change leaves the same audio/visual stage identities intact.
        for mode in ['shorts','gameplay','highlights']:
            s=self.settings(mode);s.update(episode_minutes=.1,sensitivity=100,minimum_score=0)
            plan=create(result,[],self.info,s,self.folder(mode));validate(plan,300,mode)
        # Changing visual sampling recalculates only visual blocks, not audio.
        third=Cache(root,self.source)
        commands=[]
        original=Runner.run
        def track(r,args,**kwargs):commands.append(args);return original(r,args,**kwargs)
        with patch.object(Runner,'run',track):analyze(self.info,third,Runner(),sample_seconds=3,decode='cpu')
        self.assertFalse(any('s16le' in c for c in commands))

    def test_cpu_concat_audio_continuity_and_sync(self):
        plan={'episodes':[{'segments':[{'start':.3,'end':3.5},{'start':7.2,'end':10.4},{'start':15.1,'end':18.3}]}]}
        reports=[]
        files,encoder=render(self.source,self.info,plan,self.settings(),self.folder('cpu'),Runner(report=lambda *r:reports.append(r)))
        self.assertEqual(encoder,'libx264');self.assertTrue(files[0]['full_decode_passed'])
        output=probe(files[0]['file']);self.assertEqual(len(output['audio']),2)
        self.assertEqual((output['width'],output['height']),(320,180));self.assertEqual(output['fps'],'10/1')
        # Both synthetic tones must remain audible across every cut boundary.
        import array
        for track in [0,1]:
            raw=Runner().run(ffmpeg()+['-i',files[0]['file'],'-map',f'0:a:{track}','-ac','1','-ar','48000','-f','f32le','-'])
            audio=array.array('f');audio.frombytes(raw)
            for boundary in [3.2,6.4]:
                for shift in [-.04,0,.04]:
                    chunk=audio[round((boundary+shift)*48000):round((boundary+shift+.02)*48000)]
                    rms=math.sqrt(sum(x*x for x in chunk)/len(chunk))
                    self.assertGreater(rms,.04,'Unexpected silence at concatenation boundary')
        self.assertEqual(fingerprint(self.source),self.original_hash)
        self.assertTrue(any(r[0].startswith('Validação') for r in reports))
        self.assertTrue(files[0]['monotonic_dts']);self.assertEqual(files[0]['audio_packet_gaps'],0)
        self.assertAlmostEqual(float(output['video']['duration']),float(output['audio'][0]['duration']),delta=.1)

    def test_fractional_frame_alignment(self):
        plan={'episodes':[{'segments':[{'start':1.03,'end':2.17},{'start':5.07,'end':6.13}]}]}
        files,_=render(self.source,self.info,plan,self.settings(),self.folder('fractional'),Runner())
        self.assertAlmostEqual(files[0]['duration'],2.2,delta=.12)

    def test_full_range_source_all_three_modes_cpu_and_nvenc(self):
        folder=self.folder('fullrange');source=folder/'fullrange.mkv'
        Runner().run(ffmpeg()+['-i',str(self.source),'-t','32','-map','0:v:0','-map','0:a?',
            '-vf','scale=in_range=tv:out_range=pc','-color_range','pc','-c:v','libx264',
            '-preset','ultrafast','-pix_fmt','yuv420p','-c:a','copy',str(source)])
        info=probe(source)
        self.assertEqual(info['video']['pix_fmt'],'yuvj420p')
        self.assertEqual(info['video']['color_range'],'pc')
        identity=fingerprint(source)
        for mode in ['shorts','gameplay','highlights']:
            for encoder in ['cpu']+(['nvenc'] if self.nvenc else []):
                with self.subTest(mode=mode,encoder=encoder):
                    s=self.settings(mode,encoder);s['source_identity']=identity
                    spans=[dict(start=0,end=30)] if mode=='shorts' else [dict(start=.3,end=2.3),dict(start=5,end=7)]
                    plan={'episodes':[{'segments':spans}]}
                    files,_=render(source,info,plan,s,folder/(mode+'-'+encoder),Runner())
                    result=probe(files[0]['file'])
                    self.assertEqual(result['video']['codec_name'],'h264')
                    self.assertEqual(result['video']['pix_fmt'],'yuv420p')
                    # H.264 may omit the VUI range field for its limited-range
                    # default; FFprobe then omits color_range as well.
                    self.assertIn(result['video'].get('color_range'),[None,'tv','unknown','unspecified'])
                    self.assertEqual(len(result['audio']),1 if mode=='shorts' else 2)
                    self.assertTrue(files[0]['full_decode_passed'])
                    self.assertEqual(files[0]['audio_packet_gaps'],0)
        self.assertEqual(fingerprint(source),identity)

    def test_full_range_conversion_preserves_displayed_levels(self):
        folder=self.folder('levels');source=folder/'levels.mp4'
        Runner().run(ffmpeg()+['-f','lavfi','-i','color=c=black:s=320x180:r=10,drawbox=x=160:y=0:w=160:h=180:color=white:t=fill',
            '-t','3','-vf','scale=in_range=tv:out_range=pc','-color_range','pc','-c:v','libx264','-preset','ultrafast','-crf','0','-pix_fmt','yuv420p',str(source)])
        info=probe(source);s=self.settings();s['source_identity']=fingerprint(source)
        files,_=render(source,info,{'episodes':[{'segments':[dict(start=0,end=2)]}]},s,folder,Runner())
        def rgb(path):
            return Runner().run(ffmpeg()+['-ss','1','-i',str(path),'-frames:v','1','-vf','format=rgb24','-pix_fmt','rgb24','-f','rawvideo','-'])
        before,after=rgb(source),rgb(files[0]['file'])
        self.assertEqual(len(before),len(after))
        self.assertLess(sum(abs(a-b) for a,b in zip(before,after))/len(before),4)
        # Metadata-only relabeling would lift black towards 16 and crush white.
        pixel=lambda x:after[(90*320+x)*3:(90*320+x)*3+3]
        self.assertLess(max(pixel(40)),4);self.assertGreater(min(pixel(280)),250)

    def test_bad_pixel_format_diagnostic_includes_observed_values(self):
        folder=self.folder('failure-report');source=folder/'fullrange.mp4'
        Runner().run(ffmpeg()+['-f','lavfi','-i','color=s=320x180:r=10','-t','1',
            '-vf','scale=in_range=tv:out_range=pc','-color_range','pc','-c:v','libx264','-pix_fmt','yuv420p',str(source)])
        expected=dict(duration=1,dimensions=[320,180],audio_tracks=0,fps_float=10)
        with self.assertRaisesRegex(RuntimeError,'pixels=yuvj420p'):
            validate_output(source,expected,Runner())
        report=load_json(source.with_suffix('.failure.json'))
        self.assertEqual(report['observed']['color_range'],'pc')
        self.assertEqual(report['stage'],'output_validation')

    def test_flash_beep_sync_after_disjoint_cuts(self):
        folder=self.folder('sync');source=folder/'flash.mp4'
        Runner().run(ffmpeg()+['-f','lavfi','-i',"color=c=black:s=320x180:r=30,drawbox=color=white:t=fill:enable='between(mod(t,3),1,1.1)'",
            '-f','lavfi','-i',r'aevalsrc=0.5*sin(2*PI*880*t)*between(mod(t\,3)\,1\,1.1):s=48000',
            '-t','6','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(source)])
        s=self.settings();s['source_identity']=fingerprint(source)
        files,_=render(source,probe(source),{'episodes':[{'segments':[dict(start=.2,end=2.2),dict(start=3.2,end=5.2)]}]},s,folder,Runner())
        output=files[0]['file']
        video=Runner().run(ffmpeg()+['-i',output,'-an','-vf','fps=30,scale=8:8,format=gray','-pix_fmt','gray','-f','rawvideo','-'])
        audio=Runner().run(ffmpeg()+['-i',output,'-vn','-ac','1','-ar','48000','-f','f32le','-'])
        from array import array
        samples=array('f');samples.frombytes(audio)
        flash=[];beep=[]
        for i in range(len(video)//64):
            if sum(video[i*64:(i+1)*64])/64>100:flash.append(i/30)
            chunk=samples[i*1600:(i+1)*1600]
            if chunk and math.sqrt(sum(x*x for x in chunk)/len(chunk))>.15:beep.append(i/30)
        self.assertTrue(flash and beep)
        for target in [.8,2.8]:
            self.assertLessEqual(abs(min(flash,key=lambda t:abs(t-target))-target),1/30+.001)
            self.assertLessEqual(abs(min(beep,key=lambda t:abs(t-target))-target),1/30+.001)

    def test_optional_short_captions_use_original_grouping(self):
        if not self.nvenc:self.skipTest('NVENC required for practical 1080x1920 caption smoke test')
        s=self.settings('shorts','nvenc');s['captions']=True
        transcript=[dict(words=[dict(start=.5,end=1.5,text='Legenda local de teste')])]
        files,_=render(self.source,self.info,{'episodes':[{'segments':[dict(start=0,end=30)]}]},s,self.folder('captions'),Runner(),transcript)
        self.assertTrue(files[0]['full_decode_passed'])

    def test_manager_review_render_restore_and_cache_reuse(self):
        folder=self.folder('manager');manager=Manager(folder/'data')
        payload={**DEFAULTS,'game_name':'FF7','input':str(self.source),'output':str(folder/'output'),'mode':'gameplay','encoder':'cpu'}
        manager.analyze(payload);manager.worker.join(60)
        self.assertEqual(manager.snapshot()['status'],'review',manager.snapshot()['message'])
        with self.assertRaises(ValueError):
            manager.begin_render({'plan':{'episodes':[{'segments':[dict(start=-1,end=2)]}]}})
        manager.begin_render({'plan':{'episodes':[{'segments':[dict(start=0,end=2),dict(start=5,end=7)]}]}})
        manager.worker.join(60)
        self.assertEqual(manager.snapshot()['status'],'done',manager.snapshot()['message'])
        restored=Manager(folder/'data');restored.restore()
        self.assertEqual(restored.state['status'],'paused');self.assertEqual(len(restored.state['plan']['episodes'][0]['segments']),2)
        restored.resume();restored.worker.join(60)
        self.assertEqual(restored.state['status'],'done',restored.state['message'])
        manager.analyze({**payload,'mode':'highlights','episodes':2,'episode_minutes':.1});manager.worker.join(60)
        self.assertEqual(manager.state['status'],'review',manager.state['message'])
        self.assertGreater(manager.state['cache']['hits'],0)

    def test_named_folders_clean_videos_and_restore_export_directory(self):
        folder=self.folder('named-manager');manager=Manager(folder/'data')
        source=folder/'active.mp4'
        Runner().run(ffmpeg()+['-f','lavfi','-i','testsrc2=size=320x180:rate=10,noise=alls=80:allf=t',
            '-t','5','-c:v','libx264','-preset','ultrafast',str(source)])
        payload={**DEFAULTS,'game_name':'GTA 6','input':str(source),'output':str(folder/'out'),'mode':'gameplay','gameplay_mode':'best',
            'sensitivity':100,'speech_weight':0,'cue_weight':0,'encoder':'cpu'}
        manager.analyze(payload);manager.worker.join(60)
        self.assertEqual(manager.state['status'],'review',manager.state['message'])
        exports=folder/'out'/'GTA 6'/'Gameplay - Melhores momentos'
        self.assertEqual(manager.export_folder,exports)
        self.assertIn('.studio',manager.folder.parts)
        self.assertEqual(list(exports.iterdir()),[])
        manager.begin_render({'plan':{'episodes':[{'segments':[dict(start=0,end=2)]}]},'encoder':'cpu','quality':'balanced'})
        manager.worker.join(30)
        self.assertEqual(manager.state['status'],'done',manager.state['message'])
        final=exports/'GTA 6 - Gameplay longa - Melhores momentos.mp4'
        self.assertTrue(final.is_file())
        self.assertEqual([p.name for p in exports.iterdir()],[final.name])
        restored=Manager(folder/'data');restored.restore()
        self.assertEqual(restored.export_folder,exports);self.assertEqual(restored.settings['game_name'],'GTA 6')
        restored.resume();restored.worker.join(30)
        self.assertEqual(restored.state['status'],'done',restored.state['message'])
        self.assertEqual([p.name for p in exports.iterdir()],[final.name])

    def test_named_export_collision_never_overwrites_and_resume_keeps_name(self):
        folder=self.folder('collision');dest=folder/'videos';dest.mkdir()
        existing=dest/'GTA 6 - Gameplay longa - Completa.mp4'
        existing.write_bytes(b'Existing user file: preserve unchanged')
        s=self.settings();s.update(game_name='GTA 6',export_directory=str(dest))
        plan={'episodes':[{'segments':[dict(start=0,end=2)]}]}
        files,_=render(self.source,self.info,plan,s,folder/'session',Runner())
        self.assertEqual(Path(files[0]['file']).name,'GTA 6 - Gameplay longa - Completa (2).mp4')
        self.assertEqual(existing.read_bytes(),b'Existing user file: preserve unchanged')
        again,_=render(self.source,self.info,plan,s,folder/'session',Runner())
        self.assertEqual(files[0]['file'],again[0]['file'])
        self.assertEqual(len(list(dest.iterdir())),2)

    def test_gpu_can_be_selected_at_render_without_reanalyzing(self):
        if not self.nvenc:self.skipTest('RTX/NVENC not available')
        folder=self.folder('render-options');manager=Manager(folder/'data')
        manager.analyze({**DEFAULTS,'game_name':'FF7','input':str(self.source),'output':str(folder/'out'),'mode':'gameplay','encoder':'cpu'})
        manager.worker.join(60);self.assertEqual(manager.state['status'],'review',manager.state['message'])
        before=load_json(manager.folder/'analysis.json')
        with patch('core.scanner.analyze',side_effect=AssertionError('Render changes must not scan again')):
            manager.begin_render({'plan':{'episodes':[{'segments':[dict(start=0,end=3)]}]},'encoder':'nvenc','quality':'balanced'})
            manager.worker.join(30)
        self.assertEqual(manager.state['status'],'done',manager.state['message'])
        self.assertEqual(manager.state['encoder'],'h264_nvenc')
        self.assertEqual(manager.settings['encoder'],'nvenc')
        self.assertEqual(load_json(manager.folder/'analysis.json'),before)

    def test_forced_gpu_does_not_silently_fall_back_to_cpu(self):
        with patch('render.video.nvenc_available',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'NVENC'):
                render(self.source,self.info,{'episodes':[{'segments':[dict(start=0,end=2)]}]},self.settings(encoder='nvenc'),self.folder('gpu-required'),Runner())

    def test_runtime_nvenc_failure_restarts_cpu_without_mixing(self):
        folder=self.folder('runtime-fallback');original=Runner.run
        def fail_gpu(r,args,**kwargs):
            if 'h264_nvenc' in args:raise RuntimeError('Simulated runtime encoder failure')
            return original(r,args,**kwargs)
        with patch('render.video.nvenc_available',return_value=True),patch.object(Runner,'run',fail_gpu):
            files,encoder=render(self.source,self.info,{'episodes':[{'segments':[dict(start=0,end=2)]}]},self.settings(encoder='auto'),folder,Runner())
        self.assertEqual(encoder,'libx264');self.assertTrue(files[0]['full_decode_passed'])

    def test_four_vertical_shorts_no_audio_effects_required(self):
        plan={'episodes':[{'number':i+1,'segments':[{'start':i*70,'end':i*70+30}]} for i in range(4)]}
        s=self.settings('shorts','auto')
        files,_=render(self.source,self.info,plan,s,self.folder('shorts'),Runner())
        self.assertEqual(len(files),4)
        self.assertTrue(all(f['dimensions']==[1080,1920] and f['full_decode_passed'] for f in files))
        self.assertTrue(all(f['audio']=='aac' for f in files))

    def test_no_audio(self):
        source=self.folder('silent')/'silent.mp4'
        Runner().run(ffmpeg()+['-f','lavfi','-i','testsrc2=size=320x180:rate=10','-t','3','-c:v','libx264','-preset','ultrafast',str(source)])
        info=probe(source);s=self.settings();s['source_identity']=fingerprint(source)
        a=analyze(info,Cache(self.folder('silent-cache'),source),Runner(),decode='cpu')
        self.assertEqual(a['audio'],[0.,0.,0.])
        files,_=render(source,info,{'episodes':[{'segments':[dict(start=0,end=2)]}]},s,self.folder('silent-output'),Runner())
        self.assertIsNone(files[0]['audio']);self.assertEqual(probe(files[0]['file'])['audio'],[])

    def test_multiple_highlights_episodes(self):
        a=dict(audio=[.1]*300,motion=[.5]*300,activity=[.9]*300)
        s=self.settings('highlights');s.update(episodes=3,episode_minutes=.1,sensitivity=100)
        plan={'episodes':highlights.select(a,[],self.info,s)}
        files,_=render(self.source,self.info,plan,s,self.folder('episodes'),Runner())
        self.assertEqual(len(files),3);self.assertTrue(all(abs(f['duration']-6)<.12 for f in files))

    def test_default_twelve_minute_episode_real_media(self):
        folder=self.folder('long');source=folder/'long.mkv'
        Runner().run(ffmpeg()+['-f','lavfi','-i','testsrc2=size=320x180:rate=5',
            '-f','lavfi','-i','sine=frequency=660:sample_rate=48000','-t','780',
            '-c:v','libx264','-preset','ultrafast','-crf','28','-c:a','aac',str(source)])
        info=probe(source);s=self.settings('highlights','auto');s['source_identity']=fingerprint(source)
        plan={'episodes':[{'segments':[dict(start=0,end=360),dict(start=420,end=780)]}]}
        files,_=render(source,info,plan,s,folder,Runner())
        self.assertAlmostEqual(files[0]['duration'],720,delta=.2);self.assertTrue(files[0]['full_decode_passed'])

    def test_gpu_nvenc_and_nvdec_real(self):
        if not self.nvenc:self.skipTest('Actual NVENC probe failed')
        files,encoder=render(self.source,self.info,{'episodes':[{'segments':[dict(start=0,end=3),dict(start=8,end=11)]}]},self.settings(encoder='nvenc'),self.folder('gpu'),Runner())
        self.assertEqual(encoder,'h264_nvenc');self.assertTrue(files[0]['full_decode_passed'])
        # Three-second input avoids scanning the entire recording for a decoder smoke test.
        info=probe(files[0]['file']);a=analyze(info,Cache(self.folder('gpu-cache'),files[0]['file']),Runner(),decode='auto')
        self.assertIn('NVDEC',a['decoder'])

    def test_fallback_cpu(self):
        with patch('render.video.nvenc_available',return_value=False):
            files,encoder=render(self.source,self.info,{'episodes':[{'segments':[dict(start=0,end=2)]}]},self.settings(encoder='auto'),self.folder('fallback'),Runner())
        self.assertEqual(encoder,'libx264');self.assertTrue(files[0]['full_decode_passed'])

    def test_cancel_resume_and_modified_original_rejected(self):
        folder=self.folder('resume');plan={'episodes':[{'segments':[dict(start=0,end=2),dict(start=5,end=7)]}]}
        cancel=threading.Event()
        def report(stage,done,total,message):
            if stage.startswith('Episódio') and 'corte 2/' in stage:cancel.set()
        with self.assertRaises(Cancelled):render(self.source,self.info,plan,self.settings(),folder,Runner(cancel,report))
        self.assertTrue(list((folder/'.render').rglob('*.nut')))
        reports=[];files,_=render(self.source,self.info,plan,self.settings(),folder,Runner(report=lambda *r:reports.append(r)))
        self.assertTrue(any(r[0]=='Corte em checkpoint' for r in reports));self.assertTrue(files)
        s=self.settings();s['source_identity']={'wrong':True}
        with self.assertRaises(ValueError):render(self.source,self.info,plan,s,folder,Runner())

    def test_invalid_codec_and_corrupted_file_rejected(self):
        info=self.info
        expected=dict(duration=300,dimensions=[320,180],audio_tracks=2,fps_float=10)
        with self.assertRaises(RuntimeError):validate_output(self.source,expected,Runner())
        bad=self.folder('corrupt')/'bad.mp4';bad.write_bytes(b'not a video')
        with self.assertRaises((RuntimeError,ValueError)):validate_output(bad,expected,Runner())

    def test_original_not_overwritten_outputs_unique(self):
        plan={'episodes':[{'segments':[dict(start=0,end=1)]}]};folder=self.folder('unique')
        a,_=render(self.source,self.info,plan,self.settings(),folder,Runner())
        b,_=render(self.source,self.info,plan,self.settings(),folder,Runner())
        self.assertEqual(a[0]['sha256'],b[0]['sha256']);self.assertEqual(a[0]['file'],b[0]['file'])
        self.assertEqual(fingerprint(self.source),self.original_hash)


class HandlerTests(unittest.TestCase):
    """Same HTTP handlers tested in memory even if Windows blocks socket binding."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        from types import SimpleNamespace
        self.server=SimpleNamespace(server_port=8765,token='local-secret',manager=Manager(Path(self.temp.name)),diagnostics={'tested':True})

    def request(self,method,path,headers=None,data=b''):
        h=Handler.__new__(Handler)
        h.server=self.server;h.command=method;h.path=path;h.request_version='HTTP/1.1';h.requestline=method+' '+path+' HTTP/1.1'
        h.headers={'Host':'127.0.0.1:8765',**(headers or {})};h.rfile=BytesIO(data);h.wfile=BytesIO()
        getattr(h,'do_'+method)()
        return h.wfile.getvalue()

    def test_ui_and_token_protected_status(self):
        self.assertIn(b'AI Local Studio 2.0',self.request('GET','/'))
        self.assertIn(b'403',self.request('GET','/api/status').split(b'\r\n')[0])
        self.assertIn(b'200',self.request('GET','/api/status',{'X-Local-Token':'local-secret'}).split(b'\r\n')[0])

    def test_csrf_host_origin_and_invalid_paths_denied(self):
        for headers in [{'Host':'evil.test'},{'X-Local-Token':'local-secret','Origin':'https://evil.test'},{'X-Local-Token':'local-secret','Sec-Fetch-Site':'cross-site'}]:
            self.assertIn(b'403',self.request('POST','/api/cancel',headers,b'{}').split(b'\r\n')[0])
        body=json.dumps({'input':'https://bad.test/video.mp4','output':self.temp.name}).encode()
        self.assertIn(b'400',self.request('POST','/api/analyze',{'X-Local-Token':'local-secret','Content-Length':str(len(body))},body).split(b'\r\n')[0])
        self.assertIn(b'404',self.request('GET','/../../secret',{'X-Local-Token':'local-secret'}).split(b'\r\n')[0])

    def test_range_video_support(self):
        source=Path(self.temp.name)/'preview.mp4';source.write_bytes(b'0123456789');self.server.manager.preview=source
        r=self.request('GET','/api/media/preview?token=local-secret',{'Range':'bytes=2-5'})
        self.assertIn(b'206',r.split(b'\r\n')[0]);self.assertEqual(r.split(b'\r\n\r\n')[1],b'2345')
        self.assertIn(b'416',self.request('GET','/api/media/preview?token=local-secret',{'Range':'bytes=20-25'}).split(b'\r\n')[0])

    def test_loopback_server_socket(self):
        try:server=make_server(0,self.temp.name,diagnostics=False)
        except OSError as exc:
            if getattr(exc,'winerror',None)==10013:self.skipTest('Windows sandbox blocks loopback socket: '+str(exc))
            raise
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            try:
                conn.request('GET','/');response=conn.getresponse();body=response.read()
            except OSError as exc:
                if getattr(exc,'winerror',None)==10013:self.skipTest('Windows sandbox blocks loopback connections: '+str(exc))
                raise
            self.assertEqual(response.status,200);self.assertIn(b'AI LOCAL STUDIO',body)
            conn.request('GET','/api/status',headers={'X-Local-Token':server.token});response=conn.getresponse();self.assertEqual(response.status,200);self.assertEqual(json.loads(response.read())['status'],'idle')
            conn.close()
        finally:server.stop.set();server.shutdown();server.server_close();thread.join(3)


if __name__=='__main__':unittest.main(verbosity=2)
