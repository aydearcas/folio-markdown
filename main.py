"""Run with the interpreter prepared by the included installer."""
import sys

if __name__ == "__main__":
    try:
        from folio.app import main
    except ImportError as exc:
        message = ("Folio: faltan dependencias / missing dependencies.\n"
                   "Ejecuta / Run install_windows.cmd, or:\n"
                   "python -m pip install -r requirements.txt\n\n" + str(exc))
        print(message, file=sys.stderr)
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, "Folio", 0x10)
        raise SystemExit(1)
    raise SystemExit(main())
