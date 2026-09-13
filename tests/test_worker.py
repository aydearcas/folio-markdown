import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from folio import worker


class WorkerTests(unittest.TestCase):
    def run_job(self, job, converter):
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(job) + "\n")), contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()), patch("folio.worker.convert_file", side_effect=converter):
            status = worker.main()
        events = [json.loads(line[len(worker.PREFIX):]) for line in output.getvalue().splitlines()]
        return status, events

    def test_batch_continues_after_error(self):
        calls = []
        def convert(source, dest, options, emit, cache):
            calls.append(str(source))
            if source.name == "bad.pdf":
                raise RuntimeError("broken")
            return {"engine": "liteparse", "markdown": "out/document.md", "pages": 1}
        status, events = self.run_job({"files": ["bad.pdf", "good.pdf"], "destination": "out", "options": {}}, convert)
        self.assertEqual(status, 0)
        self.assertEqual(calls, ["bad.pdf", "good.pdf"])
        self.assertEqual([e["event"] for e in events], ["started", "error", "started", "done", "batch_finished"])

    def test_malformed_job(self):
        status, events = self.run_job({"files": 123}, lambda: None)
        self.assertEqual(status, 2)
        self.assertEqual(events[0]["event"], "fatal")

    def test_killed_process_does_not_publish_partial_output(self):
        # A real child process with a deliberately blocking fake adapter.
        # No GUI, parser download or actual PDF conversion is involved.
        script = """
import sys, time
from pathlib import Path
import folio.core as core
import folio.engines as engines
core.select_engine = lambda source, options: ('liteparse', [])
def blocking(source, stage, options, emit, cache):
    print('BLOCKING_ADAPTER', flush=True)
    time.sleep(30)
engines.run_liteparse = blocking
core.convert_file(Path(sys.argv[1]), Path(sys.argv[2]), core.Options())
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            original = b"%PDF-1.7\nsynthetic"
            source.write_bytes(original)
            process = subprocess.Popen([sys.executable, "-u", "-c", script, str(source), str(root / "out")],
                                       cwd=Path(__file__).resolve().parents[1],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    process.communicate(timeout=1)
            finally:
                process.kill()
                output, errors = process.communicate(timeout=5)
            self.assertIn("BLOCKING_ADAPTER", output, errors)
            self.assertEqual(source.read_bytes(), original)
            children = list((root / "out").iterdir())
            self.assertEqual(len(children), 1)
            self.assertTrue(children[0].name.startswith(".partial"))
            report = json.loads((children[0] / "conversion.json").read_text())
            self.assertEqual(report["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
