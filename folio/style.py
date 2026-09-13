from pathlib import Path


def light_palette():
    """Folio has a light UI; do not mix it with dark native popup colors."""
    from PySide6.QtGui import QColor, QPalette
    palette = QPalette()
    colors = {
        "Window": "#f5f6f7", "WindowText": "#202e35", "Base": "#ffffff",
        "AlternateBase": "#f7f9fa", "Text": "#202e35", "Button": "#ffffff",
        "ButtonText": "#202e35", "ToolTipBase": "#ffffff", "ToolTipText": "#202e35",
        "Highlight": "#216b60", "HighlightedText": "#ffffff", "Link": "#216b60",
        "LinkVisited": "#535f82", "PlaceholderText": "#72848b",
    }
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        for role, color in colors.items():
            palette.setColor(group, getattr(QPalette.ColorRole, role), QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#83939a"))
    return palette


STYLESHEET = """
QMainWindow, QWidget#root { background: #f5f6f7; color: #202e35; }
QWidget { font-family: 'Segoe UI', 'Inter', 'Arial'; font-size: 13px; color: #202e35; }
QFrame#header { background: white; border-bottom: 1px solid #e1e6e8; }
QLabel#brand { font-size: 27px; font-weight: 650; letter-spacing: -1px; }
QLabel#subtitle, QLabel#muted { color: #657680; }
QLabel#section { color: #6b7c84; font-size: 10px; font-weight: 650; letter-spacing: 1.3px; }
QLabel#title { font-size: 22px; font-weight: 600; }
QLabel#emptyTitle { font-size: 21px; font-weight: 600; }
QLabel#badge { color: #226a5e; background: #edf5f2; padding: 6px 10px; border-radius: 10px; font-size: 10px; letter-spacing: .7px; }
QFrame#card { background: white; border: 1px solid #e1e6e8; border-radius: 12px; }
QFrame#sidebar, QScrollArea#sidebarScroll, QScrollArea#sidebarScroll > QWidget > QWidget { background: white; border: none; }
QFrame#drop { background: #fafbfc; border: 1px dashed #bccbd1; border-radius: 12px; }
QPushButton { background: white; border: 2px solid #d5dfe2; border-radius: 7px; padding: 7px 11px; min-height: 18px; font-weight: 550; }
QPushButton:enabled:hover { background: #f1f5f5; border-color: #9cafb5; }
QPushButton:enabled:pressed { background: #e6eeed; border-color: #216b60; }
QPushButton:enabled:focus { border-color: #428e80; }
QPushButton:disabled { color: #9aa8af; border-color: #e3e8eb; background: #f4f6f7; }
QPushButton#primary { background: #216b60; color: white; border-color: #216b60; padding: 11px 20px; font-weight: 600; }
QPushButton#primary:enabled:hover { background: #18584f; border-color: #18584f; }
QPushButton#primary:enabled:pressed { background: #10473f; border-color: #10473f; }
QPushButton#primary:enabled:focus { border-color: #8bc6b7; }
QPushButton#primary:disabled { background: #dce5e2; border-color: #dce5e2; color: #839992; }
QPushButton#quiet { border-color: transparent; background: transparent; color: #49636b; padding: 5px 7px; }
QPushButton#quiet:enabled:hover { background: #eef3f3; border-color: transparent; }
QPushButton#quiet:enabled:pressed { background: #dae9e5; }
QPushButton#quiet:enabled:focus { border-color: #428e80; }
QPushButton#quiet:disabled { color: #a8b4b9; background: transparent; border-color: transparent; }
QPushButton#iconButton { padding: 0; font-size: 19px; }
QPushButton#disclosure { text-align: left; border-color: transparent; background: #f5f8f8; }
QPushButton#disclosure:enabled:hover { background: #edf3f1; }
QPushButton#disclosure:enabled:focus { border-color: #428e80; }
QPushButton#disclosure:disabled { background: #f4f6f7; color: #a0aeb4; }
QLineEdit, QComboBox { background: white; border: 2px solid #d5dfe2; border-radius: 6px; padding: 7px; min-height: 18px; selection-background-color: #d6e9e4; selection-color: #202e35; }
QLineEdit:focus, QComboBox:focus { border-color: #428e80; }
QLineEdit:disabled, QComboBox:disabled { color: #a0aeb4; border-color: #e5e9eb; background: #f5f7f8; }
QComboBox { padding-right: 28px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; border: none; width: 26px; }
QComboBox::down-arrow { image: url("__ASSETS__/chevron.svg"); width: 16px; height: 16px; }
QComboBox QAbstractItemView { background: white; color: #202e35; selection-background-color: #e7f2ee; selection-color: #1c554b; outline: none; }
QMenu { background-color: #ffffff; color: #202e35; border: 1px solid #cbd7dc; padding: 5px; }
QMenu::item { background-color: transparent; color: #202e35; padding: 7px 28px 7px 22px; border: 1px solid transparent; }
QMenu::item:enabled:selected { background-color: #216b60; color: #ffffff; border-color: #216b60; }
QMenu::item:disabled { background-color: transparent; color: #83939a; }
QMenu::separator { height: 1px; background: #dce4e7; margin: 5px 8px; }
QMenu::indicator { width: 16px; height: 16px; }
QMenu::indicator:checked { background: #216b60; image: url("__ASSETS__/check.svg"); border-radius: 3px; }
QCheckBox { spacing: 9px; padding: 4px 0px; }
QCheckBox:disabled { color: #a0aeb4; }
QCheckBox::indicator { width: 16px; height: 16px; border: 2px solid #bdcdd1; border-radius: 4px; background: white; }
QCheckBox::indicator:checked { background: #216b60; border-color: #216b60; image: url("__ASSETS__/check.svg"); }
QCheckBox::indicator:unchecked:hover { border-color: #428e80; }
QCheckBox::indicator:checked:hover { background: #18584f; }
QCheckBox:focus::indicator { border-color: #72b3a4; }
QCheckBox::indicator:disabled { border-color: #d8e2e4; background: #edf2f3; }
QCheckBox::indicator:checked:disabled { border-color: #baccc7; background: #baccc7; }
QGroupBox { font-weight: 550; border: 1px solid #e1e6e8; border-radius: 7px; margin-top: 12px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QTableWidget { background: white; border: none; gridline-color: transparent; alternate-background-color: #fafbfc; selection-background-color: #e8f2ef; selection-color: #154f45; outline: none; }
QTableWidget::item { padding: 8px; border-bottom: 1px solid #eff2f3; }
QHeaderView::section { background: #f7f9fa; color: #6c7f88; border: none; padding: 10px; font-size: 11px; font-weight: 550; }
QTabWidget::pane { border: 1px solid #e2e8eb; border-radius: 6px; background: white; }
QTabBar::tab { padding: 10px 14px; color: #72848b; background: transparent; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #216b60; border-bottom: 2px solid #216b60; font-weight: 650; }
QTextBrowser, QPlainTextEdit { background: white; color: #202e35; border: none; padding: 10px; selection-background-color: #dcefe8; selection-color: #202e35; }
QProgressBar { background: #e5ecec; border: none; border-radius: 3px; height: 5px; max-height: 5px; }
QProgressBar::chunk { background: #398f7d; border-radius: 3px; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: #c7d1d6; border-radius: 3px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #edf0f2; }
QToolTip { color: #202e35; background: #ffffff; border: 1px solid #d3dee1; padding: 7px; }
""".replace("__ASSETS__", (Path(__file__).resolve().parent / "assets").as_posix())
