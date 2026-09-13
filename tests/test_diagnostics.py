import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from folio.diagnostics import environment_report, qt_exit_detail, native_exception_marker, probe_status
from tools.diagnose_docling import run_probe, main


class DiagnosticsTests(unittest.TestCase):
    def test_cli_pdfium_default_and_explicit_experimental_reader(self):
        for flags, expected in (([], True), (["--pdfium"], True), (["--original-reader"], False)):
            with self.subTest(flags=flags), patch("sys.argv", ["diagnose_docling.py", *flags]), \
                 patch("tools.diagnose_docling.run_probe", return_value=(Path("unused"), {"status": "completed"})) as probe:
                self.assertEqual(main(), 0)
                self.assertEqual(probe.call_args.kwargs["pdfium"], expected)
    def test_completed_process_with_native_dump_is_not_clean_success(self):
        marker = native_exception_marker("Windows fatal exception: access violation\n")
        self.assertIsNotNone(marker)
        self.assertEqual(probe_status(0, True, True, [], [marker]), "completed_with_native_notices")
        self.assertEqual(probe_status(0, True, True, [], []), "completed")
        self.assertEqual(probe_status(0, True, False, [], [marker]), "failed")
        self.assertEqual(probe_status(3221225477, False, False, [], [marker]), "failed")
        self.assertEqual(probe_status(0, False, True, [{"code": "bad_pdf"}], []), "failed")

    def test_native_markers_exclude_routine_warnings(self):
        self.assertIsNone(native_exception_marker("UserWarning: deprecated field"))
        self.assertIsNone(native_exception_marker('FOLIO_EVENT:{"text":"Windows fatal exception:"}'))
        self.assertIsNotNone(native_exception_marker("Fatal Python error: Segmentation fault"))

    def test_versions_do_not_include_environment_secrets(self):
        report = environment_report()
        self.assertIn("torch", report["packages"])
        self.assertIn("python", report)
        self.assertNotIn("HF_TOKEN", json.dumps(report))
        self.assertNotIn("environment_variables", report)

    def test_qt_crash_raw_code_not_interpreted_as_cause(self):
        value = qt_exit_detail(-1073741819, "CrashExit")
        self.assertIn("0xC0000005", value)
        self.assertIn("exitCode_valid=false", value)
        self.assertNotIn("memory", value.lower())
        self.assertIn("exitCode_valid=true", qt_exit_detail(2, "NormalExit"))

    def test_runner_actual_process_success_and_per_file_error(self):
        # Text routing exercises the real subprocess/report path without
        # requiring Docling or downloading model weights.
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            source = Path(tmp) / "sample.txt"
            source.write_text("Diagnostic control 9281", encoding="utf-8")
            folder, info = run_probe(source, Path(tmp) / "out")
            self.assertEqual(info["status"], "completed")
            self.assertTrue(info["conversion_done"])
            self.assertTrue(info["batch_finished"])
            self.assertTrue(info["options"]["docling_pdfium"])
            self.assertEqual(info["returncode"], 0)
            self.assertIn("FOLIO_EVENT:", (folder / "worker.log").read_text())
            self.assertEqual(json.loads((folder / "diagnostic.json").read_text())["status"], "completed")
            source.write_bytes(b"\x00binary")
            _, failure = run_probe(source, Path(tmp) / "out")
            # Worker processes per-file errors and exits 0; protocol, not just
            # the process exit code, determines whether conversion succeeded.
            self.assertEqual(failure["returncode"], 0)
            self.assertEqual(failure["status"], "failed")
            self.assertFalse(failure["conversion_done"])
            self.assertEqual(failure["errors"][0]["code"], "binary_text")
