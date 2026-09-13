"""Small diagnostics helpers. Importing this module loads no ML backend."""
from importlib import metadata
import platform
import sys


def environment_report():
    versions = {}
    for name in ("PySide6", "docling", "docling-slim", "docling-core", "docling-ibm-models", "docling-parse", "pypdfium2",
                 "torch", "torchvision", "transformers", "easyocr", "huggingface-hub",
                 "numpy", "opencv-python-headless", "liteparse", "python-docx"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return {"python": platform.python_version(), "os": platform.platform(),
            "machine": platform.machine(), "python_bits": 64 if sys.maxsize > 2**32 else 32,
            "packages": versions}


def qt_exit_detail(code: int, state: str) -> str:
    # Qt documents exitCode as valid only for NormalExit. Never interpret a
    # CrashExit's raw value as a diagnosed NTSTATUS; use the standalone runner.
    raw = f"{code} (0x{code & 0xffffffff:08X})"
    valid = state == "NormalExit"
    return f"Qt={state}; raw exit={raw}; exitCode_valid={str(valid).lower()}"


def native_exception_marker(line: str) -> str | None:
    """Detect native diagnostic headers, not a confirmed process termination.

    On Windows an exception dump may precede recovery and a normal exit.
    """
    for prefix in ("Windows fatal exception:", "Fatal Python error:"):
        if line.lstrip().startswith(prefix):
            return line.strip()[:300]
    return None


def probe_status(returncode, done, finished, errors, native_exceptions):
    if returncode != 0 or not done or not finished or errors:
        return "failed"
    return "completed_with_native_notices" if native_exceptions else "completed"
