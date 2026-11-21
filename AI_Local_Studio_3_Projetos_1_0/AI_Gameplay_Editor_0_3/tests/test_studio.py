import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from gameplay_editor.studio import RenderServer, RenderState


class TestDashboard(unittest.TestCase):
    def test_serves_local_html_progress_and_shutdown(self):
        timeline = {
            "source": {"path": "/video_original.mp4", "duration": 60, "width": 1920, "height": 1080},
            "clips": [{"start": 0, "end": 30}, {"start": 35, "end": 55}],
        }
        state = RenderState(timeline, "/resultado.mp4", "ultra")
        server = RenderServer(state)
        self.assertEqual(server.server_address[0], "127.0.0.1")
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urlopen(base + "/", timeout=3) as response:
                page = response.read().decode("utf-8")
                self.assertIn("AI GAMEPLAY EDITOR", page)
                self.assertIn("Progresso geral", page)
                self.assertIn("Qualidade em outro nível", page)

            state.update({"stage": "rendering", "percent": 43.5, "clip_index": 1, "message": "Testando"})
            with urlopen(base + "/api/status", timeout=3) as response:
                status = json.load(response)
            self.assertEqual(status["percent"], 43.5)
            self.assertEqual(status["quality_label"], "Qualidade máxima")
            self.assertEqual(status["clip_total"], 2)
            with self.assertRaises(HTTPError) as denied:
                urlopen(Request(base + "/api/close", data=b"", method="POST"), timeout=3)
            self.assertEqual(denied.exception.code, 409)
            state.update({"stage": "completed", "percent": 100})
            with urlopen(Request(base + "/api/close", data=b"", method="POST"), timeout=3) as response:
                self.assertEqual(response.status, 200)
            t.join(timeout=3)
            self.assertFalse(t.is_alive())
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
