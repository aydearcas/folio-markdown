"""Conversion orchestration. No GUI or heavy parser imports at module load time."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata, util
from pathlib import Path
from typing import Any, Callable
import json
import os
import re
import tempfile
import time
import uuid

from . import __version__


class ConversionError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code, self.detail = code, detail


@dataclass(frozen=True)
class Options:
    engine: str = "auto"
    document_type: str = "auto"
    ocr: bool = True
    ocr_language: str = "eng"
    images: bool = False
    structured_json: bool = True
    page_copy: bool = False
    keep_headers: bool = False
    tessdata_path: str = ""
    artifacts_path: str = ""
    docling_pdfium: bool = True

    def __post_init__(self):
        if self.document_type not in {"auto", "pdf", "text"}:
            raise ConversionError("invalid_options", self.document_type)
        if self.engine not in {"liteparse", "docling", "auto"}:
            raise ConversionError("invalid_options", self.engine)
        if self.ocr_language not in {"eng", "spa", "fra", "deu", "ita", "por"}:
            raise ConversionError("invalid_options", self.ocr_language)
        for name in ("ocr", "images", "structured_json", "page_copy", "keep_headers", "docling_pdfium"):
            if not isinstance(getattr(self, name), bool):
                raise ConversionError("invalid_options", name)
        for name in ("tessdata_path", "artifacts_path"):
            if not isinstance(getattr(self, name), str):
                raise ConversionError("invalid_options", name)

    @classmethod
    def from_dict(cls, data: dict):
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


def installed_versions() -> dict[str, str | None]:
    result = {}
    for name in ("PySide6", "liteparse", "docling", "docling-core", "easyocr", "python-docx"):
        try:
            result[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            result[name] = None
    return result


def available(engine: str) -> bool:
    try:
        return util.find_spec(engine) is not None
    except (ImportError, ValueError):
        return False


def safe_stem(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")[:100]
    if not value:
        value = "document"
    if value.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}:
        value = "_" + value
    return value


def write_json(path: Path, data: Any):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def source_hash(path: Path) -> str:
    with path.open("rb") as handle:
        return sha256_stream(handle)


def sha256_stream(handle) -> str:
    digest = sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def quality_warnings(markdown: str, page_count: int | None) -> list[dict]:
    """Signals only, deliberately NOT an accuracy or completeness score."""
    warnings = []
    visible = re.sub(r"<!--.*?-->", "", markdown, flags=re.S).strip()
    if not visible:
        raise ConversionError("empty_text")
    if page_count is not None and len(visible) / max(page_count, 1) < 80:
        warnings.append({"code": "sparse_text"})
    if visible.count("\ufffd") > 3:
        warnings.append({"code": "replacement_chars"})
    return warnings


def select_engine(source: Path, options: Options) -> tuple[str, list[dict]]:
    if options.engine != "auto":
        if not available(options.engine):
            raise ConversionError("missing_engine", options.engine)
        return options.engine, []
    if not available("liteparse"):
        if available("docling"):
            return "docling", [{"code": "auto_no_liteparse"}]
        raise ConversionError("missing_engine", "LiteParse / Docling")
    from liteparse import LiteParse
    try:
        parser = LiteParse(ocr_enabled=False)
        try:
            checks = parser.is_complex(str(source))
        finally:
            close = getattr(parser, "close", None)
            if callable(close):
                close()
        needs_ocr = any(bool(p.needs_ocr) for p in checks)
    except Exception as exc:
        # A failed diagnostic is not a conversion failure; make this visible.
        return "liteparse", [{"code": "auto_probe_failed", "detail": str(exc)}]
    if needs_ocr and available("docling"):
        return "docling", [{"code": "auto_ocr"}]
    if needs_ocr:
        return "liteparse", [{"code": "auto_no_docling"}]
    return "liteparse", [{"code": "auto_native"}]


def convert_file(source: Path, destination: Path, options: Options,
                 emit: Callable[[dict], None] = lambda event: None,
                 cache: dict | None = None) -> dict:
    """Never overwrite originals/results. Publish only a completed directory.

    Partial folders deliberately remain on cancellation/failure for recovery;
    their report has status=incomplete/failed and they are not reported as done.
    """
    from .engines import run_docling, run_liteparse
    from .formats import detect_format
    from .text_engines import run_text
    source = Path(source).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    file_format = detect_format(source)
    family = "pdf" if file_format == "pdf" else "text"
    if options.document_type not in ("auto", family):
        raise ConversionError("type_mismatch", f"{source.name} ({file_format.upper()})")
    if family == "pdf":
        for value in (options.tessdata_path, options.artifacts_path):
            if value and not Path(value).expanduser().is_dir():
                raise ConversionError("invalid_directory", value)
        engine, routing = select_engine(source, options)
    else:
        engine, routing = ("python-docx" if file_format == "docx" else "text"), []
    destination.mkdir(parents=True, exist_ok=True)
    stem = safe_stem(source.stem)
    run_id = uuid.uuid4().hex[:12]
    final = destination / f"{stem}__{engine}__{run_id}"
    stage = Path(tempfile.mkdtemp(prefix=f".partial_{stem[:35]}_", dir=destination))
    emit({"event": "stage", "path": str(stage), "engine": engine})
    start = time.monotonic()
    report = {
        "schema": "folio.conversion.v1", "app_version": __version__,
        "status": "incomplete", "source_file": source.name,
        "source_sha256": source_hash(source), "source_bytes": source.stat().st_size,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "engine": engine, "format": file_format, "document_type": family,
        "versions": installed_versions(), "options": asdict(options),
        "warnings": routing,
        "notice": "Verify tables, values and references against the original document. Text documents have no physical page mapping.",
    }
    # Paths to local model caches are unnecessary in a portable/shared report.
    for key in ("tessdata_path", "artifacts_path"):
        report["options"][key] = bool(report["options"][key])
    write_json(stage / "conversion.json", report)
    try:
        if family == "pdf":
            adapter = run_liteparse if engine == "liteparse" else run_docling
            details = adapter(source, stage, options, emit, cache if cache is not None else {})
        else:
            details = run_text(source, stage, options, file_format, emit)
        markdown_path = stage / "document.md"
        markdown = markdown_path.read_text(encoding="utf-8")
        report.update(details)
        report["warnings"] = routing + details.get("warnings", []) + quality_warnings(markdown, details["pages"])
        report["elapsed_seconds"] = round(time.monotonic() - start, 2)
        report["status"] = "completed"
        report["outputs"] = sorted(p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file())
        write_json(stage / "conversion.json", report)
        # UUID and an exclusive reservation prevent concurrent runs colliding.
        lock = destination / f".reserve_{run_id}"
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            if final.exists():
                raise FileExistsError(str(final))
            stage.rename(final)
        finally:
            lock.unlink(missing_ok=True)
        return {"output": str(final), "markdown": str(final / "document.md"),
                "engine": engine, "format": file_format, "pages": details["pages"],
                "warnings": report["warnings"], "elapsed": report["elapsed_seconds"]}
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = {"type": type(exc).__name__, "detail": str(exc)}
        try:
            write_json(stage / "conversion.json", report)
        except OSError:
            pass
        raise
