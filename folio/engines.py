"""Small, lazy-loaded adapters for the documented LiteParse and Docling APIs."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
import math
import re

from .core import ConversionError, Options, write_json


def public_data(value, depth=0):
    """Serialize Python and PyO3 public data, omitting binary image payloads.

    This is an API snapshot, NOT a promise of lossless LiteParse serialization.
    All exposed scalar spatial fields are preserved without inventing a schema.
    """
    if depth > 30:
        raise ValueError("Maximum structured data nesting exceeded")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Enum):
        return public_data(value.value, depth + 1)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return {"binary_bytes_omitted": len(value)}
    if isinstance(value, dict):
        return {str(k): public_data(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [public_data(v, depth + 1) for v in value]
    if is_dataclass(value):
        return public_data(asdict(value), depth + 1)
    if hasattr(value, "model_dump"):
        return public_data(value.model_dump(mode="json"), depth + 1)
    data = {}
    for name in dir(value):
        if name.startswith("_"):
            continue
        attr = getattr(value, name)
        if not callable(attr):
            data[name] = public_data(attr, depth + 1)
    if not data:
        raise TypeError(f"No serializable public fields on {type(value).__name__}")
    return data


def _relative_lite_images(markdown: str, result, stage: Path) -> str:
    """Link only images that really exist; don't turn placeholders into claims."""
    known = {}
    for item in getattr(result, "images", []):
        name, path = getattr(item, "name", ""), getattr(item, "path", "")
        if not path:
            continue
        absolute = Path(path)
        if not absolute.is_absolute():
            # Engines may return a filename or a stage-relative path.
            candidates = [stage / absolute, stage / "images" / absolute.name]
            absolute = next((p for p in candidates if p.is_file()), candidates[0])
        try:
            rel = absolute.resolve().relative_to(stage.resolve()).as_posix()
        except ValueError:
            continue
        if absolute.is_file():
            known[str(path)] = rel
            if name:
                known[str(name)] = rel
            known[absolute.name] = rel
    def replace(match):
        target = match.group(2).strip("<>")
        relative = known.get(target) or known.get(Path(target).name)
        return f"![{match.group(1)}](<{relative}>)" if relative else match.group(0)
    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace, markdown)


def _portable_paths(value, stage: Path):
    """Prevent absolute staging paths becoming stale after publishing the folder."""
    if isinstance(value, str):
        return value.replace(str(stage) + "/", "").replace(str(stage) + "\\", "")
    if isinstance(value, list):
        return [_portable_paths(v, stage) for v in value]
    if isinstance(value, dict):
        return {k: _portable_paths(v, stage) for k, v in value.items()}
    return value


def run_liteparse(source: Path, stage: Path, options: Options, emit, cache) -> dict:
    from liteparse import LiteParse
    kwargs = dict(output_format="markdown", ocr_enabled=options.ocr,
                  ocr_language=options.ocr_language, keep_headers_footers=options.keep_headers,
                  preserve_very_small_text=True, quiet=True,
                  image_mode="embed" if options.images else "off", max_pages=100000)
    if options.tessdata_path:
        kwargs["tessdata_path"] = str(Path(options.tessdata_path).expanduser())
    if options.images:
        (stage / "images").mkdir()
        kwargs.update(extract_images=True, image_output_dir=str(stage / "images"))
    parser = LiteParse(**kwargs)
    try:
        emit({"event": "phase", "code": "parsing", "engine": "LiteParse"})
        result = parser.parse(str(source))
        errors = getattr(result, "page_errors", [])
        if errors:
            raise ConversionError("partial_result", str(errors))
        count = int(result.total_pages)
        if len(result.pages) != count:
            raise ConversionError("partial_result", f"{len(result.pages)}/{count}")
        markdown = str(result.text)
        if options.images:
            markdown = _relative_lite_images(markdown, result, stage)
        (stage / "document.md").write_text(markdown, encoding="utf-8")
        warnings = []
        if options.structured_json:
            data = _portable_paths(public_data(result), stage)
            write_json(stage / "structure.json", {
                "schema": "folio.liteparse.public-api.v1",
                "note": "Public API fields; binary payloads omitted; not a lossless native format.",
                "data": data,
            })
        if options.page_copy:
            # Reparse pages explicitly; result.page.text is spatial text, NOT Markdown.
            # Keep this additional copy separate so the main document keeps its flow.
            parts = []
            for page_no in range(1, count + 1):
                emit({"event": "phase", "code": "pages", "current": page_no, "total": count})
                page_options = {**kwargs, "target_pages": str(page_no),
                                "extract_images": False, "image_mode": "off"}
                page_options.pop("image_output_dir", None)
                page_parser = LiteParse(**page_options)
                try:
                    page = page_parser.parse(str(source))
                    if getattr(page, "page_errors", []):
                        raise ConversionError("partial_result", str(page.page_errors))
                    parts.append(f"<!-- PDF page: {page_no} -->\n\n{page.text}\n")
                finally:
                    close = getattr(page_parser, "close", None)
                    if callable(close):
                        close()
            (stage / "document.pages.md").write_text("\n".join(parts), encoding="utf-8")
        if options.images and not getattr(result, "images", []):
            warnings.append({"code": "no_images"})
        return {"pages": count, "warnings": warnings}
    finally:
        close = getattr(parser, "close", None)
        if callable(close):
            close()


def run_docling(source: Path, stage: Path, options: Options, emit, cache) -> dict:
    from docling.datamodel.base_models import InputFormat, ConversionStatus
    from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions, TableFormerMode
    from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.types.doc import ImageRefMode, ContentLayer

    key = ("docling", options.ocr, options.ocr_language, options.images, options.artifacts_path,
           options.docling_pdfium)
    if key not in cache:
        emit({"event": "phase", "code": "models", "engine": "Docling"})
        pipeline = PdfPipelineOptions()
        pipeline.enable_remote_services = False
        pipeline.do_ocr = options.ocr
        pipeline.do_table_structure = True
        pipeline.table_structure_options.mode = TableFormerMode.ACCURATE
        pipeline.generate_picture_images = options.images
        pipeline.generate_page_images = options.images
        pipeline.images_scale = 1.5
        # Stable CPU baseline. No GPU setup or remote model is required.
        pipeline.accelerator_options = AcceleratorOptions(num_threads=4, device=AcceleratorDevice.CPU)
        if options.ocr:
            lang = {"eng": "en", "spa": "es", "fra": "fr", "deu": "de", "ita": "it", "por": "pt"}[options.ocr_language]
            pipeline.ocr_options = EasyOcrOptions(lang=[lang], use_gpu=False)
        if options.artifacts_path:
            pipeline.artifacts_path = Path(options.artifacts_path).expanduser()
        format_kwargs = {"pipeline_options": pipeline}
        if options.docling_pdfium:
            # Explicit compatibility choice: same Docling ML pipeline, another
            # PDF reader. Do not silently retry with different extraction.
            from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
            format_kwargs["backend"] = PyPdfiumDocumentBackend
        cache[key] = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(**format_kwargs)})
    emit({"event": "notice", "code": "docling_reader",
          "detail": "PDFium" if options.docling_pdfium else "Docling original (experimental)"})
    emit({"event": "phase", "code": "parsing", "engine": "Docling"})
    result = cache[key].convert(source, raises_on_error=True)
    if result.status != ConversionStatus.SUCCESS:
        raise ConversionError("partial_result", str(result.status))
    doc = result.document
    layers = {ContentLayer.BODY}
    if options.keep_headers:
        layers.add(ContentLayer.FURNITURE)
    mode = ImageRefMode.REFERENCED if options.images else ImageRefMode.PLACEHOLDER
    doc.save_as_markdown(stage / "document.md", artifacts_dir=stage / "images",
                         image_mode=mode, image_placeholder="",
                         included_content_layers=layers)
    if options.structured_json:
        # Native Docling export preserves page provenance and table structure.
        doc.save_as_json(stage / "structure.json", image_mode=ImageRefMode.PLACEHOLDER)
    if options.page_copy:
        parts = []
        for page_no in sorted(doc.pages):
            text = doc.export_to_markdown(page_no=page_no, image_mode=ImageRefMode.PLACEHOLDER,
                                          image_placeholder="", included_content_layers=layers)
            parts.append(f"<!-- PDF page: {page_no} -->\n\n{text}\n")
        (stage / "document.pages.md").write_text("\n".join(parts), encoding="utf-8")
    warnings = []
    if options.images and not list((stage / "images").glob("*")):
        warnings.append({"code": "no_images"})
    return {"pages": len(doc.pages), "warnings": warnings}
