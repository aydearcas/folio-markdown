"""Contract tests with explicit fake backends. These are NOT real conversion tests."""
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from folio.core import Options, ConversionError, select_engine
from folio.engines import run_liteparse, run_docling


class FakeLiteParse:
    calls = []
    needs_ocr = False
    error_pages = []

    def __init__(self, *, output_format="json", ocr_enabled=True, ocr_language="eng",
                 keep_headers_footers=False, preserve_very_small_text=False, quiet=False,
                 image_mode="off", max_pages=1000, tessdata_path=None, extract_images=False,
                 image_output_dir=None, target_pages=None):
        self.kwargs = {k: v for k, v in locals().items() if k != "self"}
        self.__class__.calls.append(self.kwargs)

    def close(self):
        pass

    def is_complex(self, source):
        return [SimpleNamespace(needs_ocr=self.needs_ocr)]

    def parse(self, source):
        target = self.kwargs["target_pages"]
        pages = [int(target)] if target else [1, 2]
        images = []
        if self.kwargs["extract_images"]:
            path = Path(self.kwargs["image_output_dir"]) / "img_p1.png"
            path.write_bytes(b"mock image")
            images = [SimpleNamespace(name="img_p1.png", path=str(path))]
        text = "\n".join(f"## Page {p}\nSynthetic paragraph on page {p}." for p in pages)
        if images:
            text += "\n![](img_p1.png)"
        return SimpleNamespace(text=text, total_pages=2, page_errors=self.error_pages,
                               pages=[SimpleNamespace(page_num=p, text_items=[SimpleNamespace(text="x", x=1, y=2)]) for p in pages],
                               images=images)


def lite_module():
    module = ModuleType("liteparse")
    module.LiteParse = FakeLiteParse
    return module


class LiteParseTests(unittest.TestCase):
    def setUp(self):
        FakeLiteParse.calls = []
        FakeLiteParse.error_pages = []
        FakeLiteParse.needs_ocr = False

    def test_markdown_json_images_and_page_copy(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("sys.modules", {"liteparse": lite_module()}):
            stage = Path(tmp)
            result = run_liteparse(Path("test.pdf"), stage, Options(images=True, page_copy=True), lambda _: None, {})
            self.assertEqual(result["pages"], 2)
            self.assertIn("<images/img_p1.png>", (stage / "document.md").read_text())
            self.assertNotIn(tmp, (stage / "document.md").read_text())
            structure = json.loads((stage / "structure.json").read_text())
            self.assertEqual(structure["data"]["pages"][0]["text_items"][0]["x"], 1)
            page_text = (stage / "document.pages.md").read_text()
            self.assertIn("<!-- PDF page: 2 -->", page_text)
            self.assertNotIn("img_p1", page_text)
            self.assertTrue(FakeLiteParse.calls[0]["preserve_very_small_text"])
            self.assertEqual([c["target_pages"] for c in FakeLiteParse.calls], [None, "1", "2"])

    def test_partial_parse_is_failure(self):
        FakeLiteParse.error_pages = ["page 2 failed"]
        with tempfile.TemporaryDirectory() as tmp, patch.dict("sys.modules", {"liteparse": lite_module()}):
            with self.assertRaises(ConversionError):
                run_liteparse(Path("test.pdf"), Path(tmp), Options(), lambda _: None, {})

    def test_auto_ocr_selects_docling(self):
        FakeLiteParse.needs_ocr = True
        with patch.dict("sys.modules", {"liteparse": lite_module()}), patch("folio.core.available", return_value=True):
            engine, warnings = select_engine(Path("a.pdf"), Options(engine="auto"))
            self.assertEqual(engine, "docling")
            self.assertEqual(warnings[0]["code"], "auto_ocr")

    def test_auto_native_selects_liteparse(self):
        with patch.dict("sys.modules", {"liteparse": lite_module()}), patch("folio.core.available", return_value=True):
            engine, warnings = select_engine(Path("a.pdf"), Options(engine="auto"))
            self.assertEqual(engine, "liteparse")
            self.assertEqual(warnings[0]["code"], "auto_native")

    def test_auto_missing_docling_is_visible(self):
        FakeLiteParse.needs_ocr = True
        with patch.dict("sys.modules", {"liteparse": lite_module()}), patch("folio.core.available", side_effect=lambda n: n == "liteparse"):
            engine, warnings = select_engine(Path("a.pdf"), Options(engine="auto"))
            self.assertEqual(engine, "liteparse")
            self.assertEqual(warnings[0]["code"], "auto_no_docling")


class FakeDocument:
    pages = {1: None, 2: None}
    layers = None

    def save_as_markdown(self, filename, *, artifacts_dir, image_mode, image_placeholder, included_content_layers):
        self.layers = included_content_layers
        Path(filename).write_text("# Document\n\nSynthetic paragraph", encoding="utf-8")

    def save_as_json(self, filename, *, image_mode):
        Path(filename).write_text('{"pages":{"1":{},"2":{}}}')

    def export_to_markdown(self, *, page_no, image_mode, image_placeholder, included_content_layers):
        return f"# Page {page_no}"


class FakePipeline:
    def __init__(self):
        self.table_structure_options = SimpleNamespace()


class FakeConverter:
    options = None
    status = "success"
    doc = None

    def __init__(self, *, format_options):
        self.__class__.options = format_options["pdf"].pipeline_options
        self.__class__.backend = getattr(format_options["pdf"], "backend", None)

    def convert(self, source, *, raises_on_error):
        self.__class__.doc = FakeDocument()
        return SimpleNamespace(status=self.status, document=self.doc)


def docling_modules():
    def module(name, **attributes):
        result = ModuleType(name)
        result.__dict__.update(attributes)
        return result
    return {
        "docling.backend": module("docling.backend"),
        "docling.backend.pypdfium2_backend": module("pypdfium2_backend", PyPdfiumDocumentBackend=FakePdfiumBackend),
        "docling": module("docling"), "docling.datamodel": module("docling.datamodel"),
        "docling.datamodel.base_models": module("base_models", InputFormat=SimpleNamespace(PDF="pdf"), ConversionStatus=SimpleNamespace(SUCCESS="success")),
        "docling.datamodel.pipeline_options": module("pipeline_options", PdfPipelineOptions=FakePipeline, EasyOcrOptions=SimpleNamespace, TableFormerMode=SimpleNamespace(ACCURATE="accurate")),
        "docling.datamodel.accelerator_options": module("accelerator_options", AcceleratorOptions=SimpleNamespace, AcceleratorDevice=SimpleNamespace(CPU="cpu")),
        "docling.document_converter": module("document_converter", DocumentConverter=FakeConverter, PdfFormatOption=SimpleNamespace),
        "docling_core": module("docling_core"), "docling_core.types": module("docling_core.types"),
        "docling_core.types.doc": module("doc", ImageRefMode=SimpleNamespace(REFERENCED="ref", PLACEHOLDER="placeholder"), ContentLayer=SimpleNamespace(BODY="body", FURNITURE="furniture")),
    }


class FakePdfiumBackend:
    pass


class DoclingTests(unittest.TestCase):
    def setUp(self):
        FakeConverter.status = "success"

    def test_pdfium_is_default_and_original_has_separate_converter_cache(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("sys.modules", docling_modules()):
            cache, events = {}, []
            run_docling(Path("doc.pdf"), Path(tmp), Options(engine="docling", ocr=False), events.append, cache)
            self.assertIs(FakeConverter.backend, FakePdfiumBackend)
            run_docling(Path("doc.pdf"), Path(tmp), Options(engine="docling", ocr=False, docling_pdfium=False), events.append, cache)
            self.assertIsNone(FakeConverter.backend)
            self.assertEqual(len(cache), 2)
            self.assertTrue(any(e.get("detail") == "PDFium" for e in events))

    def test_pdfium_setting_must_be_boolean(self):
        self.assertTrue(Options.from_dict({}).docling_pdfium)
        with self.assertRaises(ConversionError):
            Options(docling_pdfium="false")

    def test_settings_export_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("sys.modules", docling_modules()):
            stage = Path(tmp)
            result = run_docling(Path("doc.pdf"), stage, Options(engine="docling", ocr_language="spa", page_copy=True, keep_headers=True), lambda _: None, {})
            pipeline = FakeConverter.options
            self.assertFalse(pipeline.enable_remote_services)
            self.assertEqual(pipeline.ocr_options.lang, ["es"])
            self.assertFalse(pipeline.ocr_options.use_gpu)
            self.assertEqual(pipeline.accelerator_options.device, "cpu")
            self.assertEqual(pipeline.table_structure_options.mode, "accurate")
            self.assertEqual(FakeConverter.doc.layers, {"body", "furniture"})
            self.assertEqual(result["pages"], 2)
            self.assertIn("<!-- PDF page: 2 -->", (stage / "document.pages.md").read_text())
            self.assertTrue((stage / "structure.json").is_file())

    def test_incomplete_docling_result_rejected(self):
        FakeConverter.status = "partial_success"
        with tempfile.TemporaryDirectory() as tmp, patch.dict("sys.modules", docling_modules()):
            with self.assertRaises(ConversionError):
                run_docling(Path("doc.pdf"), Path(tmp), Options(engine="docling"), lambda _: None, {})

    def test_converter_reused_within_batch(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("sys.modules", docling_modules()):
            cache = {}
            for _ in range(2):
                run_docling(Path("doc.pdf"), Path(tmp), Options(engine="docling", ocr=False), lambda _: None, cache)
            self.assertEqual(len(cache), 1)


if __name__ == "__main__":
    unittest.main()
