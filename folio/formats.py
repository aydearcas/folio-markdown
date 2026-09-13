"""Local file detection and loss-aware text decoding (no parser downloads)."""
from pathlib import Path
import codecs
import zipfile

from .core import ConversionError

TEXT_SUFFIXES = {".txt", ".text", ".log", ".md", ".markdown", ".csv", ".tsv"}
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | {".pdf", ".docx"}


def detect_format(path: Path) -> str:
    path = Path(path)
    if not path.is_file():
        raise ConversionError("file_missing", str(path))
    with path.open("rb") as handle:
        header = handle.read(1024)
    suffix = path.suffix.lower()
    if header.startswith(b"%PDF-") or (suffix == ".pdf" and b"%PDF-" in header):
        return "pdf"
    if header.startswith(b"PK"):
        try:
            with zipfile.ZipFile(path) as archive:
                if {"[Content_Types].xml", "word/document.xml"}.issubset(archive.namelist()):
                    return "docx"
        except zipfile.BadZipFile:
            pass
        raise ConversionError("invalid_docx" if suffix == ".docx" else "unsupported_format", path.name)
    if suffix == ".pdf":
        raise ConversionError("invalid_pdf", str(path))
    if suffix == ".docx":
        raise ConversionError("invalid_docx", path.name)
    if suffix in TEXT_SUFFIXES:
        return {".markdown": "md", ".text": "txt", ".log": "txt"}.get(suffix, suffix[1:])
    raise ConversionError("unsupported_format", path.name)


def read_text(path: Path, limit: int | None = None) -> tuple[str, str, list[dict]]:
    with path.open("rb") as handle:
        raw = handle.read() if limit is None else handle.read(limit)
    notices = []
    # UTF-32 BOM starts with UTF-16 BOM bytes; check the wider encoding first.
    if raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        encoding = "utf-32"
    elif raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        encoding = "utf-16"
    else:
        encoding = "utf-8-sig"
    try:
        decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
        value = decoder.decode(raw, final=limit is None)
    except UnicodeDecodeError as exc:
        if encoding != "utf-8-sig":
            raise ConversionError("invalid_encoding", str(exc)) from exc
        try:
            value = raw.decode("cp1252")
        except UnicodeDecodeError as fallback:
            raise ConversionError("invalid_encoding", str(fallback)) from fallback
        encoding = "cp1252"
        notices.append({"code": "encoding_fallback", "detail": encoding})
    # Fail rather than silently export a binary file renamed to .txt.
    if any(ord(c) < 32 and c not in "\n\r\t\f" for c in value):
        raise ConversionError("binary_text", path.name)
    return value.replace("\r\n", "\n").replace("\r", "\n"), encoding, notices
