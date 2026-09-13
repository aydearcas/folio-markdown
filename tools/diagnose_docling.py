"""Run the actual Folio worker outside Qt and retain the OS exit code.

Does not reinstall packages, modify the source PDF, clear caches, elevate
permissions, or upload diagnostic output. Model downloads may occur as usual.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from folio.core import Options, write_json
from folio.diagnostics import environment_report, native_exception_marker, probe_status
from folio.worker import PREFIX


def run_probe(source: Path, destination: Path, *, ocr: bool = False,
              language: str = "eng", artifacts_path: str = "", pdfium: bool = True) -> tuple[Path, dict]:
    destination.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="docling_", dir=destination))
    options = Options(engine="docling", ocr=ocr, ocr_language=language,
                      images=False, page_copy=False, artifacts_path=artifacts_path,
                      docling_pdfium=pdfium)
    info = {"schema": "folio.diagnostic.v2", "status": "running",
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "source_file": source.name, "options": asdict(options),
            "environment": environment_report(),
            "notice": "No document upload. Logs may include local paths, file names and library messages. Review before sharing."}
    info["options"]["artifacts_path"] = bool(artifacts_path)
    write_json(folder / "diagnostic.json", info)
    try:
        check = subprocess.run([sys.executable, "-m", "pip", "check"],
                               capture_output=True, text=True, errors="replace", timeout=30)
        info["pip_check"] = {"returncode": check.returncode, "output": check.stdout + check.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        info["pip_check"] = {"error": str(exc)}
    env = os.environ.copy()
    env.update(PYTHONFAULTHANDLER="1", PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1",
               HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1")
    request = {"files": [str(source.resolve())], "destination": str(folder / "results"), "options": asdict(options)}
    done = finished = False
    errors = []
    native_exceptions = []
    print("Diagnostic folder / Carpeta de diagnóstico:", folder, flush=True)
    print("Running the real converter. Model downloads may be needed; Ctrl+C cancels.\n"
          "Conversión real. Puede descargar modelos; Ctrl+C cancela.", flush=True)
    command = [sys.executable, "-X", "faulthandler", "-u", "-m", "folio.worker"]
    process = None
    try:
        with (folder / "worker.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding="utf-8", errors="replace")
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.close()
            for line in process.stdout:
                log.write(line)
                log.flush()
                marker = native_exception_marker(line)
                if marker:
                    native_exceptions.append(marker)
                # Native model libraries may print Unicode progress bars on Windows.
                try:
                    print(line, end="", flush=True)
                except UnicodeEncodeError:
                    print(line.encode("ascii", "replace").decode("ascii"), end="", flush=True)
                offset = line.find(PREFIX)
                if offset >= 0:
                    try:
                        event = json.loads(line[offset + len(PREFIX):])
                        done |= event.get("event") == "done"
                        finished |= event.get("event") == "batch_finished"
                        if event.get("event") in ("error", "fatal"):
                            errors.append(event)
                    except ValueError:
                        pass
            code = process.wait()
        info.update(returncode=code, batch_finished=finished, conversion_done=done, errors=errors)
        if sys.platform == "win32":
            info["windows_exit_hex"] = f"0x{code & 0xffffffff:08X}"
        elif code < 0:
            info["termination_signal"] = -code
        info["status"] = probe_status(code, done, finished, errors, native_exceptions)
    except KeyboardInterrupt:
        if process and process.poll() is None:
            process.kill()
            process.wait()
        info["status"] = "cancelled"
    except (OSError, ValueError) as exc:
        info.update(status="failed", runner_error=str(exc))
    finally:
        if process:
            if process.poll() is None:
                process.kill()
                process.wait()
            if process.stdout:
                process.stdout.close()
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
        info["native_exception_count"] = len(native_exceptions)
        info["native_exception_messages"] = sorted(set(native_exceptions))
        write_json(folder / "diagnostic.json", info)
    print("\nResult / Resultado:", info["status"], info.get("windows_exit_hex", info.get("returncode", "")))
    if native_exceptions:
        print("Native exception messages detected. Completion does not verify content.\n"
              "Se detectaron mensajes de excepciones nativas. Terminar no verifica el contenido.")
    print("Review before sharing / Revisar antes de compartir: worker.log + diagnostic.json")
    print(folder)
    return folder, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "examples" / "synthetic_article.pdf")
    parser.add_argument("--output", type=Path, default=ROOT / "diagnostics")
    parser.add_argument("--ocr", action="store_true", help="Enable EasyOCR. Default: disabled.")
    readers = parser.add_mutually_exclusive_group()
    readers.add_argument("--pdfium", dest="pdfium", action="store_true", help="Use PDFium (default).")
    readers.add_argument("--original-reader", dest="pdfium", action="store_false",
                         help="Experimental original reader; prone to errors in the tested Windows environment.")
    parser.set_defaults(pdfium=True)
    parser.add_argument("--language", choices=("eng", "spa", "fra", "deu", "ita", "por"), default="eng")
    parser.add_argument("--artifacts-path", default="", help="Optional prepared Docling model folder.")
    args = parser.parse_args()
    if not args.source.is_file():
        parser.error("Source file does not exist")
    _, info = run_probe(args.source, args.output, ocr=args.ocr, language=args.language,
                       artifacts_path=args.artifacts_path, pdfium=args.pdfium)
    return {"completed": 0, "completed_with_native_notices": 2}.get(info["status"], 1)


if __name__ == "__main__":
    raise SystemExit(main())
