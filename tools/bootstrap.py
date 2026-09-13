"""Explicit local setup, no administrator rights, no global package changes."""
from __future__ import annotations
from pathlib import Path
import argparse
import platform
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def run(command):
    print("\n> " + " ".join(str(p) for p in command), flush=True)
    subprocess.run([str(p) for p in command], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=("both", "liteparse", "docling", "text"))
    args = parser.parse_args()
    if not (3, 10) <= sys.version_info[:2] < (3, 14) or platform.architecture()[0] != "64bit":
        print("Instala / Install Python 3.12 64-bit (compatible: 3.10-3.13).")
        return 1
    mode = args.engine
    if mode is None:
        print("\n1. LiteParse + Docling (completo / full; descarga grande / large download)")
        print("2. Solo LiteParse / LiteParse only (mas ligero / lighter)")
        print("3. Solo Docling / Docling only")
        print("4. Solo documentos de texto / Text documents only (sin PDF / no PDF)")
        answer = input("Elige / Choose [1]: ").strip() or "1"
        mode = {"1": "both", "2": "liteparse", "3": "docling", "4": "text"}.get(answer)
        if not mode:
            print("Opcion no valida / Invalid option.")
            return 1
    env = ROOT / ".venv"
    python = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    print("\nSe instalaran paquetes de PyPI en .venv. No se modifican los PDF.")
    print("Packages will be installed from PyPI into .venv. PDFs are not modified.")
    if not python.exists():
        venv.EnvBuilder(with_pip=True, clear=False).create(env)
    req = "requirements.txt" if mode == "both" else "requirements-base.txt" if mode == "text" else f"requirements-{mode}.txt"
    try:
        run([python, "-m", "pip", "install", "-r", ROOT / req])
        run([python, "-m", "pip", "check"])
        versions = subprocess.check_output([str(python), "-m", "pip", "freeze"], text=True, cwd=ROOT)
        # Actual resolved environment, not a fabricated lockfile.
        (ROOT / "installed-versions.txt").write_text(versions, encoding="utf-8")
        run([python, "-m", "unittest", "discover", "-s", "tests", "-v"])
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"\nInstalacion o comprobacion incompleta / Setup or check incomplete:\n{exc}")
        print("No se ha borrado ningun archivo. Consulta la guia para continuar.")
        print("No files were deleted. See the guide to continue.")
        return 1
    print("\nListo / Ready: start_windows.cmd (Windows) or .venv/bin/python main.py")
    print("Primera conversion: los modelos/OCR pueden descargarse automaticamente.")
    print("First conversion: models/OCR data may download automatically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
