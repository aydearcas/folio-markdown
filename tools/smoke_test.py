"""Real backend smoke test; NOT mocked. May download models when explicitly run."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from folio.core import Options, convert_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=("liteparse", "docling", "text"), required=True)
    parser.add_argument("--ocr", action="store_true", help="Test the synthetic scan; may download OCR models")
    args = parser.parse_args()
    if args.engine == "text":
        if args.ocr:
            parser.error("OCR applies to PDFs only")
        try:
            for name in ("sample_document.docx", "sample_notes.txt", "sample_markdown.md", "sample_data.csv", "sample_data.tsv"):
                result = convert_file(ROOT / "examples" / name, ROOT / "smoke-results", Options(document_type="auto"))
                text = Path(result["markdown"]).read_text(encoding="utf-8")
                assert text.strip() and result["pages"] is None
                assert (Path(result["output"]) / "structure.json").is_file()
                print("PASS:", name, "->", result["output"])
            return 0
        except Exception as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
    source = ROOT / "examples" / ("synthetic_scan.pdf" if args.ocr else "synthetic_article.pdf")
    options = Options(engine=args.engine, ocr=args.ocr, page_copy=True, images=not args.ocr)
    try:
        result = convert_file(source, ROOT / "smoke-results", options, lambda e: print(json.dumps(e)))
        text = Path(result["markdown"]).read_text(encoding="utf-8")
        paginated = (Path(result["output"]) / "document.pages.md").read_text(encoding="utf-8")
        assert (Path(result["output"]) / "structure.json").is_file(), "JSON missing"
        assert "<!-- PDF page: 1 -->" in paginated, "Page marker missing"
        if args.ocr:
            assert "FOLIO" in text.upper() and "OCR" in text.upper(), "OCR text not recovered"
        else:
            assert result["pages"] == 2, f"Unexpected page count: {result['pages']}"
            assert "9281" in text, "Page-two marker not found"
            assert "Sample A" in text, "Table label not found"
            assert "<!-- PDF page: 2 -->" in paginated, "Page 2 missing"
        print("PASS: actual conversion, content, JSON and page markers.")
        print(result["output"])
        return 0
    except Exception as exc:
        print(f"FAIL: {getattr(exc, 'code', type(exc).__name__)}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
