"""Render Folio context menus while the application inherits a dark palette."""
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QSettings, QPoint
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication
from folio.app import MainWindow


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    dark = QPalette()
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base, QPalette.ColorRole.Button):
        dark.setColor(role, QColor("#202020"))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        dark.setColor(role, QColor("#ffffff"))
    app.setPalette(dark)
    with tempfile.TemporaryDirectory() as tmp:
        window = MainWindow(QSettings(str(Path(tmp) / "preview.ini"), QSettings.Format.IniFormat))
        window.source.setPlainText("Folio · text to copy\nDiagnostic log: exit status, engine versions and tracebacks.")
        window.tabs.setCurrentIndex(1)
        window.source.selectAll()
        window.show()
        app.processEvents()
        folder = ROOT / "screenshots"
        folder.mkdir(exist_ok=True)
        for name, target in (("context_menu_dark_system.png", window.source), ("context_input_dark_system.png", window.destination)):
            menu = target.createStandardContextMenu()
            menu.popup(window.mapToGlobal(QPoint(500, 300)))
            app.processEvents()
            enabled = [a for a in menu.actions() if a.isEnabled() and not a.isSeparator()]
            if enabled:
                menu.setActiveAction(enabled[0])
            app.processEvents()
            menu.grab().save(str(folder / name))
            menu.close()
            menu.deleteLater()
        window.grab().save(str(folder / "interface_021.png"))
        window.close()


if __name__ == "__main__":
    main()
