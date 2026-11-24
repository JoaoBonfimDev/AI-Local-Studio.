import os
from pathlib import Path
import tempfile
import threading
import unittest
from highlights.media import Runner, Cancelled, ffmpeg, probe, render_args, render, check_properties
from highlights.selection import analyze, select, validate


def frame_hashes(runner, path, start=None, length=None):
    args = ffmpeg()
    if start is not None:
        args += ['-ss', str(start)]
    args += ['-i', str(path)]
    if length is not None:
        args += ['-t',str(length)]
    data = runner.run(args+['-map','0:v:0','-an','-fps_mode','passthrough','-f','framemd5','-'])
    return [line.rsplit(b',',1)[-1].strip() for line in data.splitlines() if line and not line.startswith(b'#')]


@unittest.skipUnless(os.environ.get('RUN_MEDIA_TESTS') == '1', 'Defina RUN_MEDIA_TESTS=1 para integração com FFmpeg.')
class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='highlights_tests_')
        cls.root = Path(cls.tmp.name)
        cls.runner = Runner()
        cls.source = cls.root/'gravação original.mkv'
        cls.runner.run(ffmpeg()+['-f','lavfi','-i','testsrc2=size=160x90:rate=12:duration=780',
                                '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=780',
                                '-f','lavfi','-i','sine=frequency=880:sample_rate=44100:duration=780',
                                '-map','0:v','-map','1:a','-map','2:a',
                                '-c:v','libx264','-preset','ultrafast','-crf','18',
                                '-c:a','pcm_s16le',str(cls.source)])
        cls.info = probe(cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def plan(self):
        return dict(episodes=[dict(number=1, segments=[dict(start=0,end=300),dict(start=360,end=780)])])

    def test_analyze_and_select_real_video_cpu(self):
        result = analyze(self.source,self.info,self.runner,lambda *x:None,'cpu')
        self.assertEqual(len(result['blocks']),13)
        self.assertEqual(result['decoder'],'CPU')
        plan = select(result['blocks'],780,10,12,1.)
        validate(plan,780)
        self.assertEqual(plan['episodes'][0]['duration'],720)

    def verify_render(self, mode):
        folder = self.root/mode
        result = render(self.source,self.plan(),self.info,folder,mode,self.runner,lambda *x:None)
        dest = Path(result['files'][0])
        out_info = probe(dest)
        check_properties(self.info,out_info)
        self.assertAlmostEqual(out_info['duration'],720,places=2)
        expected = frame_hashes(self.runner,self.source,0,300)+frame_hashes(self.runner,self.source,360,420)
        self.assertEqual(expected,frame_hashes(self.runner,dest))
        # Compare decoded PCM samples for every audio track across the cuts.
        for track in (0,1):
            def samples(path,start=None,length=None):
                cmd=ffmpeg()
                if start is not None: cmd += ['-ss',str(start)]
                cmd += ['-i',str(path)]
                if length is not None: cmd += ['-t',str(length)]
                return self.runner.run(cmd+['-map',f'0:a:{track}','-vn','-c:a','pcm_s16le','-f','s16le','-'])
            self.assertEqual(samples(self.source,0,300)+samples(self.source,360,420),samples(dest))
        return result

    def test_cpu_full_episode_pixels_audio_duration(self):
        self.verify_render('cpu')

    @unittest.skipUnless(os.environ.get('RUN_GPU_TESTS') == '1','Defina RUN_GPU_TESTS=1 para testar a GPU real.')
    def test_nvdec_nvenc_full_episode(self):
        result = self.verify_render('auto')
        self.assertEqual(result['decoder'],'NVDEC')
        self.assertEqual(result['encoder'],'h264_nvenc')

    def test_short_fractional_cut_preserves_frames(self):
        dest=self.root/'fracionado.mkv'
        segment=dict(start=65.25,end=69.75)
        self.runner.run(render_args(self.source,segment,dest,self.info,'ffv1',False))
        self.assertEqual(frame_hashes(self.runner,self.source,65.25,4.5),frame_hashes(self.runner,dest))

    def test_ten_bit_and_no_audio(self):
        source = self.root/'dez_bits.mkv'
        dest = self.root/'dez_bits_corte.mkv'
        self.runner.run(ffmpeg()+['-f','lavfi','-i','testsrc2=size=160x90:rate=30000/1001:duration=6',
                                  '-pix_fmt','yuv420p10le','-c:v','ffv1',str(source)])
        info=probe(source)
        self.runner.run(render_args(source,dict(start=1,end=5),dest,info,'ffv1',False))
        check_properties(info,probe(dest))
        self.assertEqual(frame_hashes(self.runner,source,1,4),frame_hashes(self.runner,dest))
        self.assertEqual(probe(dest)['audio'],[])

    def test_vfr_preserves_frame_sequence_and_cadence(self):
        import json
        from highlights.media import binary
        source=self.root/'vfr.mkv'
        dest=self.root/'vfr_corte.mkv'
        self.runner.run(ffmpeg()+['-f','lavfi','-i','testsrc2=size=160x90:rate=30:duration=6',
                                  '-vf',"select=not(mod(n\\,3))+not(mod(n\\,5))",'-fps_mode','vfr',
                                  '-c:v','ffv1',str(source)])
        info=probe(source)
        self.runner.run(render_args(source,dict(start=0,end=6),dest,info,'ffv1',False))
        self.assertEqual(frame_hashes(self.runner,source),frame_hashes(self.runner,dest))
        def timestamps(path):
            data=json.loads(self.runner.run([binary('ffprobe'),'-v','error','-select_streams','v:0',
                                             '-show_entries','frame=best_effort_timestamp_time','-of','json',str(path)]))
            return [float(f['best_effort_timestamp_time']) for f in data['frames']]
        original=timestamps(source)
        output=timestamps(dest)
        self.assertEqual(len(original),len(output))
        for a,b in zip(original,output): self.assertAlmostEqual(a,b,places=3)

    def test_analysis_nvdec(self):
        if os.environ.get('RUN_GPU_TESTS') != '1':
            self.skipTest('GPU opcional')
        result=analyze(self.source,self.info,self.runner,lambda *x:None,'auto')
        self.assertEqual(result['decoder'],'NVDEC')
        self.assertEqual(result['scaler'],'CUDA')


class CancellationTests(unittest.TestCase):
    def test_cancel_before_start(self):
        event=threading.Event()
        event.set()
        with self.assertRaises(Cancelled):
            Runner(event).run(['nonexistent-program'])
