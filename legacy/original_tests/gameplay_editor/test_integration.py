import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg indisponível")
class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="age-tests-")
        cls.root = Path(cls.scratch.name)
        cls.source = cls.root / "gameplay curto com espaços.mkv"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=20",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
            "-t", "6", "-c:v", "mpeg4", "-q:v", "4", "-c:a", "aac",
            str(cls.source),
        ], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def command(self, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / "main.py"), *args],
            cwd=ROOT, text=True, capture_output=True,
        )

    def test_doctor(self):
        p = self.command("doctor")
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_run_full(self):
        directory = self.root / "completo"
        p = self.command(
            "run", "--input", str(self.source), "--output-dir", str(directory),
            "--mode", "completo", "--encoder", "cpu",
        )
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertIn("[sem cortes]", p.stdout)
        self.assertFalse((directory / "gameplay_full.mp4").exists())
        timeline = json.loads((directory / "timeline_full.json").read_text(encoding="utf-8"))
        self.assertGreater(timeline["summary"]["selected_seconds"], 0)

    def test_run_highlights_and_manual_render(self):
        directory = self.root / "melhores"
        p = self.command(
            "analyze", "--input", str(self.source), "--output-dir", str(directory),
            "--mode", "melhores", "--sensitivity", "100",
        )
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        timeline = directory / "timeline_highlights.json"
        self.assertTrue(json.loads(timeline.read_text(encoding="utf-8"))["clips"])
        p = self.command("render", "--timeline", str(timeline), "--output", str(directory / "final.mp4"), "--encoder", "cpu", "--terminal")
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertTrue((directory / "final.mp4").stat().st_size > 1000)

    def test_never_overwrite_original(self):
        directory = self.root / "isolado"
        p = self.command("analyze", "--input", str(self.source), "--output-dir", str(directory), "--mode", "completo")
        self.assertEqual(p.returncode, 0, p.stderr)
        p = self.command("render", "--timeline", str(directory / "timeline_full.json"), "--output", str(self.source), "--terminal")
        self.assertNotEqual(p.returncode, 0)

    def test_two_manually_reordered_clips(self):
        from gameplay_editor.media import probe
        from gameplay_editor.render import render_timeline

        directory = self.root / "dois-cortes"
        directory.mkdir()
        timeline = {
            "schema_version": 1,
            "source": probe(self.source).source_record(),
            "clips": [
                {"start": 4, "end": 5.5, "name": "Cena final"},
                {"start": .5, "end": 2.0, "name": "Cena inicial"},
            ],
        }
        output = render_timeline(timeline, directory / "reordenado.mp4", encoder="cpu")
        duration = probe(output).duration
        self.assertAlmostEqual(duration, 3, delta=.25)

    def test_ultra_quality_reports_live_stages(self):
        from gameplay_editor.media import probe
        from gameplay_editor.render import render_timeline

        directory = self.root / "alta-qualidade"
        directory.mkdir()
        timeline = {
            "schema_version": 1,
            "source": probe(self.source).source_record(),
            "clips": [{"start": 0, "end": 2, "name": "Cena de teste"}],
        }
        updates = []
        output = render_timeline(
            timeline, directory / "alta.mp4", encoder="cpu", quality="ultra",
            on_event=updates.append,
        )
        self.assertTrue(output.is_file())
        self.assertTrue(any(u["stage"] == "rendering" for u in updates))
        self.assertTrue(any(u["stage"] == "joining" for u in updates))
        self.assertEqual(updates[-1]["stage"], "completed")
        self.assertEqual(updates[-1]["percent"], 100)
        self.assertTrue(all(u["quality"] == "ultra" for u in updates))

    def test_no_audio_video_supported(self):
        source = self.root / "sem-audio.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=20",
            "-t", "4", "-c:v", "mpeg4", "-q:v", "4", str(source),
        ], check=True)
        directory = self.root / "sem-audio-resultados"
        p = self.command(
            "run", "--input", str(source), "--output-dir", str(directory),
            "--mode", "completo", "--encoder", "cpu",
        )
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        timeline = directory / "timeline_full.json"
        self.assertFalse(json.loads(timeline.read_text(encoding="utf-8"))["source"]["has_audio"])
        p = self.command("render", "--timeline", str(timeline), "--output", str(directory / "sem-audio-editado.mp4"), "--encoder", "cpu", "--terminal")
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertTrue((directory / "sem-audio-editado.mp4").is_file())

    def test_dashboard_renders_with_live_server(self):
        from gameplay_editor.media import probe
        from gameplay_editor.studio import render_with_dashboard

        directory = self.root / "studio-real"
        directory.mkdir()
        destination = directory / "studio.mp4"
        timeline = {
            "schema_version": 1,
            "source": probe(self.source).source_record(),
            "clips": [{"start": 0, "end": 2.5, "name": "Teste visual"}],
        }
        with mock.patch("gameplay_editor.studio.webbrowser.open", return_value=True) as opened:
            worker = threading.Thread(
                target=render_with_dashboard,
                args=(timeline, destination),
                kwargs={"encoder": "cpu", "quality": "high", "open_browser": True},
                daemon=True,
            )
            worker.start()
            deadline = time.monotonic() + 15
            while not opened.called and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(opened.called)
            base = opened.call_args.args[0].rstrip("/")
            status = {}
            while time.monotonic() < deadline:
                with urlopen(base + "/api/status", timeout=3) as response:
                    status = json.load(response)
                if status["stage"] in ("completed", "error"):
                    break
                time.sleep(.15)
            self.assertEqual(status.get("stage"), "completed", status)
            self.assertEqual(status["percent"], 100)
            self.assertTrue(destination.is_file())
            with urlopen(Request(base + "/api/close", data=b"", method="POST"), timeout=3) as response:
                self.assertEqual(response.status, 200)
            worker.join(timeout=3)
            self.assertFalse(worker.is_alive())


if __name__ == "__main__":
    unittest.main()
