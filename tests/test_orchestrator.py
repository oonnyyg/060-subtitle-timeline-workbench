import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from subtitle_workbench import process_request


REPO_ROOT = Path(__file__).resolve().parents[1]


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _write(self, name, text, bom=False):
        path = self.tmp / name
        data = text.encode("utf-8")
        if bom:
            data = b"\xef\xbb\xbf" + data
        path.write_bytes(data)
        return str(path)

    def _request(self, **overrides):
        request = {
            "files": [
                {"path": self._write("a.srt", "1\n00:00:01,000 --> 00:00:03,000\nhello world\n", True)},
                {"path": self._write("b.srt", "2\n00:00:03,000 --> 00:00:05,000\nhello world\n", False), "offset_ms": 0},
            ],
            "output_dir": str(self.tmp / "out"),
            "speed_threshold": 100,
        }
        request.update(overrides)
        return request

    def test_success_writes_lf_utf8_and_merges(self):
        report = process_request(self._request())
        self.assertTrue(report["ok"])
        self.assertEqual(report["cue_count"], 1)
        raw = Path(report["output_file"]).read_bytes()
        self.assertNotIn(b"\r", raw)
        self.assertIn("00:00:01,000 --> 00:00:05,000", raw.decode("utf-8"))

    def test_dropped_and_clipped_counts(self):
        request = self._request(
            files=[
                {"path": self._write("c.srt", "1\n00:00:00,500 --> 00:00:01,000\nclip\n\n2\n00:00:00,100 --> 00:00:00,200\ndrop\n"), "offset_ms": -700}
            ]
        )
        report = process_request(request)
        self.assertTrue(report["ok"])
        self.assertEqual(report["clipped"], 1)
        self.assertEqual(report["dropped"], 1)

    def test_parse_error_aborts_without_output(self):
        bad = self._write("bad.srt", "1\nno timing here\n")
        request = {
            "files": [{"path": bad}],
            "output_dir": str(self.tmp / "out"),
        }
        report = process_request(request)
        self.assertFalse(report["ok"])
        self.assertEqual(report["errors"][0]["reason"], "missing_time_line")
        self.assertFalse((self.tmp / "out").exists())

    def test_speed_warning_threshold(self):
        path = self._write("fast.srt", "1\n00:00:00,000 --> 00:00:01,000\nabcdefghij\n")
        report = process_request(
            {"files": [{"path": path}], "output_dir": str(self.tmp / "out"), "speed_threshold": 5}
        )
        self.assertEqual(len(report["speed_warnings"]), 1)
        self.assertEqual(report["speed_warnings"][0]["speed"], 10.0)

    def test_source_files_unchanged(self):
        path = self._write("src.srt", "1\n00:00:00,000 --> 00:00:01,000\nkeep\n")
        original = Path(path).read_bytes()
        process_request(
            {"files": [{"path": path, "offset_ms": 5000}], "output_dir": str(self.tmp / "out")}
        )
        self.assertEqual(Path(path).read_bytes(), original)

    def test_cli_module_round_trip(self):
        request = self._request()
        proc = subprocess.run(
            [sys.executable, "-m", "subtitle_workbench"],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertTrue(report["ok"])


if __name__ == "__main__":
    unittest.main()
