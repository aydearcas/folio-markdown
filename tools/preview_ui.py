"""Capture the actual interface after a mixed-file conversion. Requires LiteParse.

QT_QPA_PLATFORM=offscreen python tools/preview_ui.py
Uses isolated settings; does not change the user's preferences.
"""
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication
from folio.app import MainWindow


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    with tempfile.TemporaryDirectory() as temp:
        window = MainWindow(QSettings(str(Path(temp) / "preview.ini"), QSettings.Format.IniFormat))
        window.resize(1280, 960)
        window.destination.setText(str(ROOT / "smoke-results"))
        window.ocr.setChecked(False)
        window.add_files([str(ROOT / "examples" / name) for name in
                          ("synthetic_article.pdf", "sample_document.docx", "sample_notes.txt", "sample_data.csv")])
        window.show()
        window.start()
        shots = ROOT / "screenshots"
        shots.mkdir(exist_ok=True)
        failure = []

        def check():
            if window.process is not None:
                return
            timer.stop()
            if any(e.state not in ("done", "warning") for e in window.entries):
                failure.append(window.log.toPlainText())
                app.quit()
                return
            window.table.selectRow(1)
            window.selection_changed()
            app.processEvents()
            window.grab().save(str(shots / "interface_es.png"))
            window.language_combo.setCurrentIndex(1)
            app.processEvents()
            window.grab().save(str(shots / "interface_en.png"))
            window.resize(980, 700)
            app.processEvents()
            window.grab().save(str(shots / "interface_compact.png"))
            print(window.log.toPlainText())
            print("Screenshots:", shots)
            app.quit()

        def timeout():
            if window.process:
                window.process.kill()
            failure.append("Mixed-file conversion timed out")
            app.quit()

        timer = QTimer()
        timer.timeout.connect(check)
        timer.start(100)
        QTimer.singleShot(45000, timeout)
        app.exec()
        window.close()
        if failure:
            raise RuntimeError("\n".join(failure))


if __name__ == "__main__":
    main()
