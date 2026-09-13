"""Isolated batch worker: one JSON request on stdin, prefixed events on stdout."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import traceback

from .core import Options, ConversionError, convert_file

PREFIX = "FOLIO_EVENT:"


def emit(event):
    print(PREFIX + json.dumps(event, ensure_ascii=True), flush=True)


def main():
    try:
        job = json.loads(sys.stdin.readline())
        options = Options.from_dict(job["options"])
        output = Path(job["destination"])
        files = job["files"]
        if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
            raise ValueError("files must be a list of local paths")
    except Exception as exc:
        emit({"event": "fatal", "code": "invalid_job", "detail": str(exc)})
        return 2
    cache = {}
    for index, filename in enumerate(files):
        emit({"event": "started", "index": index, "file": filename})
        try:
            result = convert_file(Path(filename), output, options, emit, cache)
            emit({"event": "done", "index": index, **result})
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            emit({"event": "error", "index": index,
                  "code": exc.code if isinstance(exc, ConversionError) else "conversion_failed",
                  "detail": str(exc)})
    emit({"event": "batch_finished"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
