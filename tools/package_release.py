"""Create a source ZIP; exclude environments, caches and generated run results."""
from pathlib import Path
import argparse
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".venv", "__pycache__", "smoke-results", "diagnostics", ".git"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Output already exists; choose a new ZIP filename")
    # A source ZIP must never ship a missing/empty shortcut icon again.
    icon = (ROOT / "folio" / "assets" / "folio.ico").read_bytes()
    if len(icon) < 6 + 7 * 16 or icon[:6] != b"\x00\x00\x01\x00\x07\x00":
        parser.error("Invalid ICO: run tools/build_icon.py before packaging")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "x", compression=ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            rel = path.relative_to(ROOT)
            if not path.is_file() or path == output or any(part in EXCLUDED for part in rel.parts):
                continue
            if path.suffix in {".pyc", ".log", ".zip"} or path.name in {"installed-versions.txt", ".DS_Store"}:
                continue
            # Native CRLF line endings for Windows launchers, without editing source.
            if path.suffix.lower() == ".cmd":
                data = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\n", "\r\n")
                archive.writestr("Folio/" + rel.as_posix(), data.encode("utf-8"))
            else:
                archive.write(path, "Folio/" + rel.as_posix())
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        print(f"Verified {len(archive.namelist())} files; {output.stat().st_size} bytes: {output}")


if __name__ == "__main__":
    main()
