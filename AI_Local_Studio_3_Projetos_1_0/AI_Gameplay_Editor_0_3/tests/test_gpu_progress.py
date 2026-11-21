import unittest
from pathlib import Path
from unittest import mock

from gameplay_editor.media import MediaError, MediaInfo, scan_motion
from gameplay_editor.progress import Progress, format_seconds


class TestGpuFallback(unittest.TestCase):
    def setUp(self):
        self.info = MediaInfo(Path("/nao-existe.mp4"), 10, 320, 180, "30/1", True, 1, 1)

    def test_auto_falls_back_to_cpu(self):
        with mock.patch("gameplay_editor.media._cuda_decodes", return_value=False):
            with mock.patch("gameplay_editor.media._scan_motion_once", return_value=[.1] * 10) as cpu:
                result = scan_motion(self.info, decode="auto")
        self.assertEqual(result, [.1] * 10)
        cpu.assert_called_once_with(self.info, 3, gpu=False)

    def test_forced_gpu_reports_missing_hardware(self):
        with mock.patch("gameplay_editor.media._cuda_decodes", return_value=False):
            with self.assertRaisesRegex(MediaError, "NVDEC/CUDA indisponível"):
                scan_motion(self.info, decode="gpu")

    def test_auto_recovers_from_runtime_gpu_failure(self):
        def decode(_, __, *, gpu):
            if gpu:
                raise MediaError("GPU falhou")
            return [.2] * 10

        with mock.patch("gameplay_editor.media._cuda_decodes", return_value=True):
            with mock.patch("gameplay_editor.media._scan_motion_once", side_effect=decode):
                self.assertEqual(scan_motion(self.info, decode="auto"), [.2] * 10)


class TestProgress(unittest.TestCase):
    def test_elapsed_formats(self):
        self.assertEqual(format_seconds(17572.7), "04:52:53")
        self.assertEqual(format_seconds(61), "00:01:01")

    def test_progress_percent_and_finish(self):
        with mock.patch("builtins.print") as printer:
            progress = Progress("scan", 100, interval=0)
            progress.update(40)
            progress.done()
        self.assertTrue(any("100.0%" in str(call) for call in printer.call_args_list))


if __name__ == "__main__":
    unittest.main()
