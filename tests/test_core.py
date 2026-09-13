import ast
from dataclasses import asdict
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from folio.core import Options, ConversionError, safe_stem, quality_warnings, convert_file, source_hash, select_engine
from folio.engines import public_data, _relative_lite_images
from folio.i18n import TEXT, tr

ROOT = Path(__file__).resolve().parents[1]


class CoreTests(unittest.TestCase):
    def test_options_roundtrip(self):
        opts = Options(engine="docling", ocr_language="spa", images=True)
        self.assertEqual(opts, Options.from_dict(asdict(opts)))

    def test_invalid_engine(self):
        with self.assertRaises(ConversionError):
            Options(engine="remote")

    def test_invalid_language(self):
        with self.assertRaises(ConversionError):
            Options(ocr_language="auto")

    def test_invalid_bool(self):
        with self.assertRaises(ConversionError):
            Options(ocr="yes")

    def test_windows_names(self):
        for name in ("CON", "nul.txt", "COM1", "LPT9"):
            self.assertTrue(safe_stem(name).startswith("_"))
        self.assertEqual(safe_stem("a/b:c?d"), "a_b_c_d")
        self.assertEqual(safe_stem(" ."), "document")
        self.assertLessEqual(len(safe_stem("a" * 300)), 100)

    def test_unicode_name(self):
        self.assertEqual(safe_stem("ID23_García 2026"), "ID23_García 2026")

    def test_empty_is_failure(self):
        with self.assertRaises(ConversionError):
            quality_warnings("<!-- image -->\n", 1)

    def test_quality_is_only_a_signal(self):
        self.assertEqual(quality_warnings("A long sentence. " * 100, 2), [])
        self.assertIn({"code": "sparse_text"}, quality_warnings("Short", 2))
        self.assertIn({"code": "replacement_chars"}, quality_warnings("\ufffd" * 5, 1))

    def test_public_snapshot(self):
        value = SimpleNamespace(page_num=1, bbox=SimpleNamespace(x=2, y=3), raw=b"123")
        data = public_data(value)
        self.assertEqual(data["bbox"], {"x": 2, "y": 3})
        self.assertEqual(data["raw"], {"binary_bytes_omitted": 3})

    def test_unknown_not_silently_stringified(self):
        with self.assertRaises(TypeError):
            public_data(object())

    def test_nonfinite_serialization(self):
        self.assertIsNone(public_data(float("nan")))

    def test_i18n_complete(self):
        import string
        for key, pair in TEXT.items():
            self.assertEqual(len(pair), 2)
            self.assertTrue(all(pair))
            names = [{name for _, name, _, _ in string.Formatter().parse(value) if name} for value in pair]
            self.assertEqual(names[0], names[1], key)
        self.assertEqual(tr("eng", "es"), "Inglés")
        self.assertEqual(tr("count", "en", n=2), "2 documents")

    def test_static_translation_keys(self):
        tree = ast.parse((ROOT / "folio" / "app.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("t", "label", "button", "check", "message"):
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    self.assertIn(node.args[0].value, TEXT)

    def test_images_relative_existing_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            (stage / "images").mkdir()
            image = stage / "images" / "img_p1.png"
            image.write_bytes(b"fixture")
            result = SimpleNamespace(images=[SimpleNamespace(name="img_p1.png", path=str(image))])
            md = _relative_lite_images("![](img_p1.png)\n![](unknown.png)", result, stage)
            self.assertIn("<images/img_p1.png>", md)
            self.assertIn("![](unknown.png)", md)

    def fake_adapter(self, source, stage, options, emit, cache):
        (stage / "document.md").write_text("# Test\n\n" + "A real-looking sentence. " * 20, encoding="utf-8")
        return {"pages": 1, "warnings": []}

    def test_transaction_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "á test.pdf"
            source.write_bytes(b"%PDF-1.7\nfixture")
            original_hash = source_hash(source)
            with patch("folio.core.select_engine", return_value=("liteparse", [])), patch("folio.engines.run_liteparse", side_effect=self.fake_adapter):
                one = convert_file(source, root / "out", Options())
                two = convert_file(source, root / "out", Options())
            self.assertNotEqual(one["output"], two["output"])
            self.assertTrue(Path(one["markdown"]).is_file())
            self.assertEqual(original_hash, source_hash(source))
            report = json.loads((Path(one["output"]) / "conversion.json").read_text())
            self.assertEqual(report["source_sha256"], original_hash)
            self.assertEqual(report["status"], "completed")
            self.assertFalse(list((root / "out").glob(".partial*")))

    def test_failed_results_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "test.pdf"
            source.write_bytes(b"%PDF-1.7")
            with patch("folio.core.select_engine", return_value=("liteparse", [])), patch("folio.engines.run_liteparse", side_effect=RuntimeError("broken")):
                with self.assertRaises(RuntimeError):
                    convert_file(source, root / "out", Options())
            children = list((root / "out").iterdir())
            self.assertEqual(len(children), 1)
            self.assertTrue(children[0].name.startswith(".partial"))
            report = json.loads((children[0] / "conversion.json").read_text())
            self.assertEqual(report["status"], "failed")

    def test_bad_pdf_rejected_before_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.pdf"
            path.write_text("not a PDF")
            with self.assertRaises(ConversionError) as raised:
                convert_file(path, Path(tmp), Options())
            self.assertEqual(raised.exception.code, "invalid_pdf")

    def test_manual_never_silently_changes_engine(self):
        with patch("folio.core.available", return_value=False):
            with self.assertRaises(ConversionError) as raised:
                select_engine(Path("unused.pdf"), Options(engine="docling"))
            self.assertEqual(raised.exception.code, "missing_engine")

    def test_auto_no_engines(self):
        with patch("folio.core.available", return_value=False):
            with self.assertRaises(ConversionError):
                select_engine(Path("unused.pdf"), Options(engine="auto"))

    def test_auto_docling_only(self):
        with patch("folio.core.available", side_effect=lambda name: name == "docling"):
            engine, warnings = select_engine(Path("unused.pdf"), Options(engine="auto"))
            self.assertEqual(engine, "docling")
            self.assertEqual(warnings[0]["code"], "auto_no_liteparse")


if __name__ == "__main__":
    unittest.main()
