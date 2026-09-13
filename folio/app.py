from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
import sys

from PySide6.QtCore import Qt, QProcess, QProcessEnvironment, QSettings, QUrl, QStandardPaths, QTimer
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QImage, QTextDocument
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel,
    QPushButton, QComboBox, QCheckBox, QLineEdit, QVBoxLayout, QHBoxLayout,
    QScrollArea, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStackedWidget, QTextBrowser, QPlainTextEdit, QTabWidget,
    QProgressBar, QFileDialog, QMessageBox)

from .core import Options, ConversionError, installed_versions
from .formats import SUPPORTED_SUFFIXES, detect_format, read_text
from .i18n import tr
from .style import STYLESHEET, light_palette
from .diagnostics import qt_exit_detail, native_exception_marker
from .worker import PREFIX

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
except ImportError:
    QPdfDocument = QPdfView = None


@dataclass
class Entry:
    path: Path
    state: str = "waiting"
    result: dict = field(default_factory=dict)
    format: str = ""


class LocalMarkdown(QTextBrowser):
    """No remote loads, scripts, executable links, or arbitrary local resources."""
    def __init__(self):
        super().__init__()
        self.base = None
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.document().setDefaultStyleSheet("body {color:#25353d;} p {margin-top:6px; margin-bottom:8px;} h1,h2,h3 {color:#1e5a50; margin-top:14px; margin-bottom:8px;} table {border-collapse:collapse;} td,th {padding:6px; border:1px solid #ccd8dd;}")

    def loadResource(self, resource_type, url):
        if resource_type != QTextDocument.ResourceType.ImageResource or not self.base:
            return None
        if url.scheme() not in ("", "file"):
            return None
        candidate = Path(url.toLocalFile()) if url.isLocalFile() else self.base / url.path()
        try:
            candidate = candidate.resolve()
            candidate.relative_to(self.base.resolve())
            if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                return None
            if candidate.stat().st_size > 20 * 1024 * 1024:
                return None
            return QImage(str(candidate))
        except (OSError, ValueError):
            return None


class DropFrame(QFrame):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.callback([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])
        event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings("FolioLocal", "Folio")
        self.language = str(self.settings.value("language", "es"))
        if self.language not in ("es", "en"):
            self.language = "es"
        self.entries = []
        self.text_bindings = []
        self.combo_bindings = []
        self.batch_rows = []
        self.events = []
        self.process = None
        self.buffer = b""
        self.stderr_buffer = b""
        self.active_batch_index = None
        self.cancel_requested = False
        self.batch_finished = False
        self.closing = False
        self.summary = ("ready", {})
        self.versions = installed_versions()
        self.native_exception_count = 0
        self.setWindowTitle("Folio · Documents → Markdown")
        self.resize(1220, 840)
        self.setMinimumSize(980, 700)
        self.setAcceptDrops(True)
        self.setStyleSheet(STYLESHEET)
        self.setPalette(light_palette())
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "folio.png")))
        self.build_ui()
        self.restore_settings()
        self.retranslate()

    def t(self, key, **kwargs):
        return tr(key, self.language, **kwargs)

    @property
    def running(self):
        return self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning

    def label(self, key, name=None, wrap=False):
        widget = QLabel()
        widget.setTextFormat(Qt.TextFormat.PlainText)
        widget.setWordWrap(wrap)
        if name:
            widget.setObjectName(name)
        self.text_bindings.append((widget, key))
        return widget

    def button(self, key, callback, name=None):
        widget = QPushButton()
        widget.clicked.connect(callback)
        if name:
            widget.setObjectName(name)
        self.text_bindings.append((widget, key))
        return widget

    def check(self, key):
        widget = QCheckBox()
        self.text_bindings.append((widget, key))
        return widget

    def combo(self, keys):
        widget = QComboBox()
        for key in keys:
            widget.addItem("", key)
        self.combo_bindings.append((widget, keys))
        return widget

    def build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        header = QFrame()
        header.setObjectName("header")
        bar = QHBoxLayout(header)
        bar.setContentsMargins(26, 16, 26, 16)
        brand = QLabel("folio")
        brand.setObjectName("brand")
        bar.addWidget(brand)
        bar.addSpacing(16)
        bar.addWidget(self.label("tagline", "subtitle"))
        bar.addStretch()
        bar.addWidget(self.label("local", "badge"))
        bar.addSpacing(12)
        bar.addWidget(self.label("language", "muted"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("Español", "es")
        self.language_combo.addItem("English", "en")
        self.language_combo.setCurrentIndex(1 if self.language == "en" else 0)
        self.language_combo.currentIndexChanged.connect(self.change_language)
        bar.addWidget(self.language_combo)
        bar.addWidget(self.button("help", self.show_help, "quiet"))
        outer.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(24, 25, 24, 24)
        side.setSpacing(10)
        side.addWidget(self.label("settings", "section"))
        side.addWidget(self.label("document_type"))
        self.document_type = self.combo(["type_auto", "type_pdf", "type_text"])
        side.addWidget(self.document_type)
        self.format_hint = self.label("format_hint", "muted", True)
        side.addWidget(self.format_hint)
        side.addSpacing(5)
        side.addWidget(self.label("engine"))
        self.engine = self.combo(["liteparse", "docling", "auto"])
        self.engine.setCurrentIndex(2)
        self.engine.currentIndexChanged.connect(self.update_engine)
        side.addWidget(self.engine)
        self.engine_hint = QLabel()
        self.engine_hint.setObjectName("muted")
        self.engine_hint.setWordWrap(True)
        side.addWidget(self.engine_hint)
        self.engine_state = QLabel()
        self.engine_state.setObjectName("muted")
        self.engine_state.setWordWrap(True)
        side.addWidget(self.engine_state)
        side.addSpacing(8)
        self.ocr = self.check("ocr")
        self.ocr.setChecked(True)
        side.addWidget(self.ocr)
        side.addWidget(self.label("ocr_language", "muted"))
        self.ocr_language = self.combo(["eng", "spa", "fra", "deu", "ita", "por"])
        self.ocr.toggled.connect(self.update_format)
        side.addWidget(self.ocr_language)
        side.addSpacing(12)
        side.addWidget(self.label("destination", "section"))
        self.destination = QLineEdit()
        side.addWidget(self.destination)
        side.addWidget(self.button("browse", self.choose_destination))
        side.addSpacing(15)
        side.addWidget(self.label("outputs", "section"))
        side.addWidget(self.label("markdown_always", "muted"))
        self.json_option = self.check("json")
        self.json_option.setChecked(True)
        self.image_option = self.check("images")
        self.page_option = self.check("pages")
        for widget in (self.json_option, self.image_option, self.page_option):
            side.addWidget(widget)
        self.page_hint = self.label("pages_short", "muted", True)
        side.addWidget(self.page_hint)
        side.addSpacing(5)
        self.advanced = self.button("advanced", lambda: None, "disclosure")
        self.advanced.setCheckable(True)
        self.advanced.setChecked(False)
        self.advanced_panel = QWidget()
        adv = QVBoxLayout(self.advanced_panel)
        adv.setContentsMargins(4, 0, 4, 6)
        self.headers = self.check("headers")
        adv.addWidget(self.headers)
        adv.addWidget(self.label("docling_reader_label", "muted"))
        self.docling_original = self.check("docling_original")
        adv.addWidget(self.docling_original)
        self.pdfium_hint = self.label("pdfium_hint", "muted", True)
        adv.addWidget(self.pdfium_hint)
        self.tessdata = QLineEdit()
        self.artifacts = QLineEdit()
        self.model_buttons = []
        for key, field in (("tessdata", self.tessdata), ("artifacts", self.artifacts)):
            adv.addWidget(self.label(key, "muted"))
            row = QHBoxLayout()
            row.addWidget(field, 1)
            choose = QPushButton("…")
            choose.setObjectName("iconButton")
            choose.setFixedSize(38, 38)
            choose.setToolTip(self.t("browse"))
            choose.setAccessibleName(self.t(key))
            self.model_buttons.append((choose, key))
            choose.clicked.connect(lambda checked=False, target=field: self.choose_model_dir(target))
            row.addWidget(choose)
            adv.addLayout(row)
        self.advanced_panel.setVisible(False)
        self.advanced.toggled.connect(self.toggle_advanced)
        side.addWidget(self.advanced)
        side.addWidget(self.advanced_panel)
        side.addSpacing(12)
        side.addWidget(self.label("first_use", "muted", True))
        side.addStretch()
        self.side_scroll = QScrollArea()
        self.side_scroll.setObjectName("sidebarScroll")
        self.side_scroll.setWidgetResizable(True)
        self.side_scroll.setWidget(self.sidebar)
        self.side_scroll.setFixedWidth(332)
        body.addWidget(self.side_scroll)

        main = QWidget()
        workspace = QVBoxLayout(main)
        workspace.setContentsMargins(25, 24, 25, 20)
        workspace.setSpacing(14)
        titlebar = QHBoxLayout()
        titlebar.addWidget(self.label("files", "title"))
        titlebar.addStretch()
        self.count_label = QLabel()
        self.count_label.setObjectName("muted")
        titlebar.addWidget(self.count_label)
        self.add_button = self.button("add", self.choose_files)
        titlebar.addWidget(self.add_button)
        workspace.addLayout(titlebar)

        self.split = QSplitter(Qt.Orientation.Vertical)
        files_card = DropFrame(self.add_files)
        files_card.setObjectName("card")
        card = QVBoxLayout(files_card)
        card.setContentsMargins(12, 12, 12, 5)
        self.file_stack = QStackedWidget()
        empty = DropFrame(self.add_files)
        empty.setObjectName("drop")
        empty_layout = QVBoxLayout(empty)
        empty_layout.addStretch()
        mark = QLabel("PDF · DOCX · TXT  →  .md")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet("color:#428c7d; font-size:16px; font-weight:600; padding:8px;")
        empty_layout.addWidget(mark)
        for key, name in (("drop_title", "emptyTitle"), ("drop_text", "muted")):
            label = self.label(key, name, True)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(label)
        empty_layout.addStretch()
        self.file_stack.addWidget(empty)
        self.table = QTableWidget(0, 4)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(47)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.file_stack.addWidget(self.table)
        card.addWidget(self.file_stack, 1)
        actions = QHBoxLayout()
        self.remove_button = self.button("remove", self.remove_selected, "quiet")
        self.clear_button = self.button("clear", self.clear_files, "quiet")
        actions.addWidget(self.remove_button)
        actions.addWidget(self.clear_button)
        actions.addStretch()
        card.addLayout(actions)
        self.split.addWidget(files_card)

        preview_card = QFrame()
        preview_card.setObjectName("card")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(14, 13, 14, 12)
        preview_top = QHBoxLayout()
        preview_top.addWidget(self.label("preview", "section"))
        preview_top.addStretch()
        self.open_pdf_button = self.button("open_pdf", self.open_original, "quiet")
        self.open_md_button = self.button("open_md", self.open_markdown, "quiet")
        self.open_result_button = self.button("open_folder", self.open_result, "quiet")
        preview_top.addWidget(self.open_pdf_button)
        preview_top.addWidget(self.open_md_button)
        preview_top.addWidget(self.open_result_button)
        preview_layout.addLayout(preview_top)
        self.tabs = QTabWidget()
        self.rendered = LocalMarkdown()
        self.source = QPlainTextEdit()
        self.source.setReadOnly(True)
        self.source.setFont(QFont("Consolas", 10))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1500)
        self.log.setFont(QFont("Consolas", 9))
        self.tabs.addTab(self.rendered, "")
        self.tabs.addTab(self.source, "")
        self.original_stack = QStackedWidget()
        if QPdfDocument:
            self.pdf_doc = QPdfDocument(self)
            self.pdf_view = QPdfView()
            self.pdf_view.setDocument(self.pdf_doc)
            self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            self.original_stack.addWidget(self.pdf_view)
        else:
            self.pdf_doc = None
            self.original_stack.addWidget(self.label("pdf_fallback", "muted", True))
        self.original_text = QPlainTextEdit()
        self.original_text.setReadOnly(True)
        self.original_stack.addWidget(self.original_text)
        original_help = self.label("original_help", "muted", True)
        original_help.setAlignment(Qt.AlignmentFlag.AlignCenter)
        original_help.setContentsMargins(25, 25, 25, 25)
        self.original_stack.addWidget(original_help)
        self.original_stack.setCurrentIndex(2)
        self.tabs.addTab(self.original_stack, "")
        self.tabs.addTab(self.log, "")
        self.save_log_button = self.button("save_log", self.save_log, "quiet")
        self.tabs.setCornerWidget(self.save_log_button)
        preview_layout.addWidget(self.tabs, 1)
        self.split.addWidget(preview_card)
        self.split.setSizes([270, 330])
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 2)
        workspace.addWidget(self.split, 1)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        workspace.addWidget(self.progress)
        footer = QHBoxLayout()
        status_col = QVBoxLayout()
        self.status_label = QLabel()
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setWordWrap(True)
        status_col.addWidget(self.status_label)
        status_col.addWidget(self.label("review", "muted", True))
        footer.addLayout(status_col, 1)
        self.cancel_button = self.button("cancel", self.cancel)
        self.cancel_button.setEnabled(False)
        footer.addWidget(self.cancel_button)
        self.convert_button = self.button("convert", self.start, "primary")
        footer.addWidget(self.convert_button)
        workspace.addLayout(footer)
        body.addWidget(main, 1)
        outer.addLayout(body, 1)
        self.document_type.currentIndexChanged.connect(self.update_format)

    def restore_settings(self):
        for widget, key in ((self.engine, "engine"), (self.ocr_language, "ocr_language"), (self.document_type, "document_type")):
            index = widget.findData(self.settings.value(key, widget.currentData()))
            widget.setCurrentIndex(max(0, index))
        for widget, key, default in ((self.ocr,"ocr",True), (self.json_option,"json",True),
                                    (self.image_option,"images",False), (self.page_option,"pages",False),
                                    (self.headers,"headers",False)):
            widget.setChecked(str(self.settings.value(key, default)).lower() in ("true", "1"))
        # A new preference key migrates all pre-0.2.3 installations to PDFium.
        # Subsequent explicit choices of the experimental reader are retained.
        self.docling_original.setChecked(self.settings.value("docling_reader", "pdfium") == "original_experimental")
        documents = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        self.destination.setText(str(self.settings.value("destination", str(Path(documents or str(Path.home())) / "Folio"))))
        self.tessdata.setText(str(self.settings.value("tessdata", "")))
        self.artifacts.setText(str(self.settings.value("artifacts", "")))

    def save_settings(self):
        self.settings.setValue("language", self.language)
        self.settings.setValue("engine", self.engine.currentData())
        self.settings.setValue("document_type", self.document_type.currentData())
        self.settings.setValue("ocr_language", self.ocr_language.currentData())
        for widget, key in ((self.ocr,"ocr"), (self.json_option,"json"), (self.image_option,"images"),
                            (self.page_option,"pages"), (self.headers,"headers")):
            self.settings.setValue(key, widget.isChecked())
        self.settings.setValue("docling_reader", "original_experimental" if self.docling_original.isChecked() else "pdfium")
        for widget, key in ((self.destination,"destination"), (self.tessdata,"tessdata"), (self.artifacts,"artifacts")):
            self.settings.setValue(key, widget.text())
        self.settings.sync()

    def change_language(self):
        self.language = self.language_combo.currentData()
        self.settings.setValue("language", self.language)
        self.retranslate()

    def retranslate(self):
        for widget, key in self.text_bindings:
            widget.setText(self.t(key))
        for widget, keys in self.combo_bindings:
            for index, key in enumerate(keys):
                widget.setItemText(index, self.t(key))
        self.toggle_advanced(self.advanced.isChecked())
        self.tessdata.setPlaceholderText(self.t("cache_default"))
        self.artifacts.setPlaceholderText(self.t("cache_default"))
        self.page_option.setToolTip(self.t("pages_hint"))
        for button, key in self.model_buttons:
            button.setToolTip(self.t(key))
            button.setAccessibleName(self.t(key))
        self.table.setHorizontalHeaderLabels([self.t(k) for k in ("file", "format", "status", "size")])
        for i, key in enumerate(("rendered", "source", "original", "log")):
            self.tabs.setTabText(i, self.t(key))
        self.rendered.setPlaceholderText(self.t("preview_empty"))
        self.source.setPlaceholderText(self.t("preview_empty"))
        self.refresh_table()
        self.update_engine()
        self.update_format()
        self.log.clear()
        for event in self.events:
            self.log.appendPlainText(self.format_event(event))
        if not self.running:
            self.status_label.setText(self.t(self.summary[0], **self.summary[1]))
        else:
            self.update_status()

    def update_engine(self):
        key = self.engine.currentData() or "liteparse"
        self.engine_hint.setText(self.t("hint_" + key))
        names = ("liteparse", "docling") if key == "auto" else (key,)
        self.engine_state.setText("\n".join(f"{n.title()}: {self.versions.get(n) or self.t('not_installed')}" for n in names))
        if hasattr(self, "docling_original"):
            self.update_format()

    def toggle_advanced(self, checked):
        self.advanced_panel.setVisible(checked)
        self.advanced.setText(("▾  " if checked else "▸  ") + self.t("advanced"))

    def update_format(self):
        if not hasattr(self, "page_hint"):
            return
        kind = self.document_type.currentData()
        needs_pdf = kind == "type_pdf" or (kind == "type_auto" and
                    (not self.entries or any(e.format == "pdf" for e in self.entries)))
        for widget in (self.engine, self.ocr, self.page_option, self.page_hint, self.tessdata, self.artifacts):
            widget.setEnabled(needs_pdf)
        for button, _ in self.model_buttons:
            button.setEnabled(needs_pdf)
        self.ocr_language.setEnabled(needs_pdf and self.ocr.isChecked())
        self.engine_hint.setVisible(needs_pdf)
        self.engine_state.setVisible(needs_pdf)
        self.docling_original.setEnabled(needs_pdf and self.engine.currentData() != "liteparse")
        self.pdfium_hint.setEnabled(needs_pdf and self.engine.currentData() != "liteparse")

    def has_pending(self):
        return any(e.state not in ("done", "warning") for e in self.entries)

    def choose_files(self):
        filters = {"type_pdf": "PDF (*.pdf *.PDF)", "type_text": self.t("text_filter"),
                   "type_auto": self.t("all_filter")}
        paths, _ = QFileDialog.getOpenFileNames(self, self.t("add"), "", filters[self.document_type.currentData()])
        if paths:
            self.add_files(paths)

    def add_files(self, paths):
        if self.running:
            return
        known = {str(e.path).casefold() if sys.platform == "win32" else str(e.path) for e in self.entries}
        ignored = False
        for value in paths:
            path = Path(value).expanduser().resolve()
            if path.suffix.lower() not in SUPPORTED_SUFFIXES or not path.is_file():
                ignored = True
                continue
            key = str(path).casefold() if sys.platform == "win32" else str(path)
            if key not in known:
                try:
                    kind = detect_format(path)
                except (OSError, ConversionError):
                    kind = path.suffix[1:].lower()
                self.entries.append(Entry(path, format=kind))
                known.add(key)
        self.summary = ("ready", {})
        self.status_label.setText(self.t("ready"))
        self.refresh_table()
        if self.entries and self.table.currentRow() < 0:
            self.table.selectRow(0)
        if ignored:
            self.message("bad_drop")

    def refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.entries))
        colors = {"done": "#25715f", "warning": "#8a6223", "error": "#ae4b49", "working": "#216b60"}
        for row, entry in enumerate(self.entries):
            name = QTableWidgetItem(entry.path.name)
            name.setToolTip(str(entry.path))
            status = QTableWidgetItem(self.t(entry.state))
            status.setForeground(QColor(colors.get(entry.state, "#72848b")))
            try:
                byte_count = entry.path.stat().st_size
                size = f"{byte_count / 1024 / 1024:.1f} MB" if byte_count >= 1024 * 1024 else f"{byte_count / 1024:.1f} KB" if byte_count >= 1024 else f"{byte_count} B"
            except OSError:
                size = "—"
            for col, item in enumerate((name, QTableWidgetItem(entry.format.upper()), status, QTableWidgetItem(size))):
                existing = self.table.item(row, col)
                if existing:
                    existing.setText(item.text())
                    existing.setToolTip(item.toolTip())
                    existing.setForeground(item.foreground())
                else:
                    self.table.setItem(row, col, item)
        self.table.blockSignals(False)
        self.file_stack.setCurrentIndex(1 if self.entries else 0)
        self.count_label.setText(self.t("count", n=len(self.entries)))
        self.convert_button.setEnabled(self.has_pending() and not self.running)
        self.update_format()
        self.update_actions()

    def current_entry(self):
        row = self.table.currentRow()
        return self.entries[row] if 0 <= row < len(self.entries) else None

    def selection_changed(self):
        self.update_actions()
        entry = self.current_entry()
        self.rendered.clear()
        self.source.clear()
        self.rendered.base = None
        self.original_stack.setCurrentIndex(2)
        self.original_text.clear()
        if self.pdf_doc:
            self.pdf_doc.close()
        if not entry:
            return
        if entry.format == "pdf":
            self.original_stack.setCurrentIndex(0)
        if self.pdf_doc and entry.format == "pdf":
            self.pdf_doc.load(str(entry.path))
        elif entry.format not in ("pdf", "docx"):
            self.original_stack.setCurrentIndex(1)
            try:
                text, _, _ = read_text(entry.path, limit=2 * 1024 * 1024)
                if entry.path.stat().st_size > 2 * 1024 * 1024:
                    text += "\n\n" + self.t("preview_limit")
                self.original_text.setPlainText(text)
            except (OSError, ConversionError) as exc:
                self.original_text.setPlainText(str(exc))
        md = entry.result.get("markdown")
        if md:
            try:
                path = Path(md)
                with path.open("rb") as handle:
                    data = handle.read(2 * 1024 * 1024 + 1)
                truncated = len(data) > 2 * 1024 * 1024
                text = data[:2 * 1024 * 1024].decode("utf-8", errors="replace")
                if truncated:
                    text += "\n\n" + self.t("preview_limit")
                self.rendered.base = path.parent
                self.rendered.document().setBaseUrl(QUrl.fromLocalFile(str(path.parent) + "/"))
                self.rendered.setMarkdown(text)
                self.source.setPlainText(text)
            except OSError as exc:
                self.source.setPlainText(str(exc))

    def update_actions(self):
        entry = self.current_entry()
        self.remove_button.setEnabled(bool(self.table.selectionModel().selectedRows()) and not self.running)
        self.clear_button.setEnabled(bool(self.entries) and not self.running)
        self.open_pdf_button.setEnabled(entry is not None)
        self.open_md_button.setEnabled(bool(entry and entry.result.get("markdown")))
        self.open_result_button.setEnabled(bool(entry and entry.result.get("output")))

    def remove_selected(self):
        if self.running:
            return
        rows = {i.row() for i in self.table.selectionModel().selectedRows()}
        self.entries = [e for i, e in enumerate(self.entries) if i not in rows]
        self.refresh_table()
        self.selection_changed()

    def clear_files(self):
        if not self.running:
            self.entries.clear()
            self.summary = ("ready", {})
            self.status_label.setText(self.t("ready"))
            self.refresh_table()
            self.selection_changed()

    def choose_destination(self):
        path = QFileDialog.getExistingDirectory(self, self.t("destination"), self.destination.text())
        if path:
            self.destination.setText(path)

    def choose_model_dir(self, target):
        path = QFileDialog.getExistingDirectory(self, self.t("browse"), target.text())
        if path:
            target.setText(path)

    def message(self, key, question=False, **kwargs):
        box = QMessageBox(self)
        box.setWindowTitle(self.t("notice"))
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(self.t(key, **kwargs))
        box.setIcon(QMessageBox.Icon.Question if question else QMessageBox.Icon.Information)
        if question:
            yes = box.addButton(self.t("yes"), QMessageBox.ButtonRole.YesRole)
            no = box.addButton(self.t("no"), QMessageBox.ButtonRole.NoRole)
            box.setDefaultButton(no)
            box.exec()
            return box.clickedButton() == yes
        box.addButton(self.t("ok"), QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        return False

    def show_help(self):
        self.message("about_text")
        path = Path(__file__).resolve().parent.parent / ("README_EN.md" if self.language == "en" else "README_ES.md")
        if path.is_file():
            self.open_path(path)

    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, self.t("save_log"), "folio-log.txt", "Text (*.txt)")
        if not path:
            return
        try:
            Path(path).write_text(self.log.toPlainText() + "\n", encoding="utf-8")
        except OSError as exc:
            self.message("save_failed", detail=str(exc))

    def open_path(self, path):
        path = Path(path)
        if not path.exists() or not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            self.message("open_failed", detail=str(path))

    def open_original(self):
        entry = self.current_entry()
        if entry:
            self.open_path(entry.path)

    def open_markdown(self):
        entry = self.current_entry()
        if entry and entry.result.get("markdown"):
            self.open_path(entry.result["markdown"])

    def open_result(self):
        entry = self.current_entry()
        if entry and entry.result.get("output"):
            self.open_path(entry.result["output"])

    def get_options(self):
        return Options(engine=self.engine.currentData(), document_type=self.document_type.currentData().removeprefix("type_"), ocr=self.ocr.isChecked(),
                       ocr_language=self.ocr_language.currentData(), images=self.image_option.isChecked(),
                       structured_json=self.json_option.isChecked(), page_copy=self.page_option.isChecked(),
                       keep_headers=self.headers.isChecked(), tessdata_path=self.tessdata.text().strip(),
                       artifacts_path=self.artifacts.text().strip(),
                       docling_pdfium=not self.docling_original.isChecked())

    def start(self):
        if self.running:
            return
        destination = self.destination.text().strip()
        if not destination:
            self.message("choose_output")
            return
        options = self.get_options()
        self.batch_rows = [i for i, e in enumerate(self.entries) if e.state not in ("done", "warning")]
        if not self.batch_rows:
            self.message("no_pending")
            return
        self.save_settings()
        for row in self.batch_rows:
            self.entries[row].state = "waiting"
        self.cancel_requested = self.batch_finished = False
        self.active_batch_index = None
        self.events.clear()
        self.native_exception_count = 0
        self.log.clear()
        self.buffer = self.stderr_buffer = b""
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("HF_HUB_DISABLE_TELEMETRY", "1")
        env.insert("DO_NOT_TRACK", "1")
        env.insert("PYTHONFAULTHANDLER", "1")
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(Path(__file__).resolve().parent.parent))
        interpreter = Path(sys.executable)
        if interpreter.name.lower() == "pythonw.exe":
            interpreter = interpreter.with_name("python.exe")
        self.process.setProgram(str(interpreter))
        self.process.setArguments(["-X", "faulthandler", "-u", "-m", "folio.worker"])
        request = {"files": [str(self.entries[i].path) for i in self.batch_rows],
                   "destination": destination, "options": asdict(options)}
        payload = (json.dumps(request, ensure_ascii=True) + "\n").encode("utf-8")
        self.process.started.connect(lambda: self.send_job(payload))
        self.process.readyReadStandardOutput.connect(self.read_stdout)
        self.process.readyReadStandardError.connect(self.read_stderr)
        self.process.finished.connect(self.process_finished)
        self.process.errorOccurred.connect(self.process_error)
        self.process.start()
        self.set_busy(True)
        self.progress.setRange(0, 0)

    def send_job(self, payload):
        if self.process:
            self.process.write(payload)
            self.process.closeWriteChannel()

    def set_busy(self, busy):
        self.sidebar.setEnabled(not busy)
        self.add_button.setEnabled(not busy)
        self.convert_button.setEnabled(self.has_pending() and not busy)
        self.cancel_button.setEnabled(busy)
        self.update_actions()

    def read_stdout(self):
        if not self.process:
            return
        self.buffer += bytes(self.process.readAllStandardOutput())
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            self.consume_line(line)
        if len(self.buffer) > 1024 * 1024:
            self.add_event({"event": "raw", "detail": self.buffer[:8192].decode("utf-8", "replace")})
            self.buffer = b""

    def consume_line(self, line):
        text = line.decode("utf-8", "replace").rstrip()
        offset = text.find(PREFIX)
        if offset >= 0:
            try:
                event = json.loads(text[offset + len(PREFIX):])
                self.handle_event(event)
                return
            except (ValueError, KeyError, TypeError):
                pass
        if text:
            self.add_event({"event": "raw", "detail": text[:8192]})

    def read_stderr(self):
        if not self.process:
            return
        self.stderr_buffer += bytes(self.process.readAllStandardError())
        # Both standard newlines and progress bars using CR are useful in the log.
        self.stderr_buffer = self.stderr_buffer.replace(b"\r", b"\n")
        while b"\n" in self.stderr_buffer:
            line, self.stderr_buffer = self.stderr_buffer.split(b"\n", 1)
            if line.strip():
                self.add_event({"event": "raw", "detail": line.decode("utf-8", "replace")[:8192]})
        if len(self.stderr_buffer) > 1024 * 1024:
            self.add_event({"event": "raw", "detail": self.stderr_buffer[:8192].decode("utf-8", "replace")})
            self.stderr_buffer = b""

    def handle_event(self, event):
        kind = event.get("event")
        index = event.get("index")
        if kind == "started":
            self.active_batch_index = index
            self.entries[self.batch_rows[index]].state = "working"
            self.update_status()
        elif kind in ("done", "error"):
            entry = self.entries[self.batch_rows[index]]
            if kind == "done":
                entry.result = event
                actionable = [w for w in event.get("warnings", []) if w["code"] not in ("auto_native", "auto_ocr")]
                entry.state = "warning" if actionable else "done"
                for warning in event.get("warnings", []):
                    self.add_event({"event": "notice", **warning})
            else:
                entry.state = "error"
        elif kind == "phase":
            self.status_label.setText(self.format_event(event))
        elif kind == "batch_finished":
            self.batch_finished = True
        self.add_event(event)
        if kind in ("started", "done", "error"):
            self.refresh_table()
            if kind == "done":
                self.table.selectRow(self.batch_rows[index])
                self.selection_changed()

    def update_status(self):
        index = self.active_batch_index
        if index is not None and index < len(self.batch_rows):
            name = self.entries[self.batch_rows[index]].path.name
            self.status_label.setText(self.t("progress", current=index + 1, total=len(self.batch_rows), name=name))

    def format_event(self, event):
        kind = event.get("event")
        if kind == "raw":
            return event.get("detail", "")
        if kind == "started":
            return f"→ {Path(event['file']).name}"
        if kind == "done":
            return self.t("completed_detail" if event.get("pages") is not None else "completed_text_detail", **event)
        if kind in ("error", "fatal", "notice"):
            return self.t(event.get("code", "notice"), detail=event.get("detail", ""))
        if kind == "stage":
            return self.t("partial_folder", path=event["path"])
        if kind == "phase":
            if event["code"] == "pages":
                return self.t("page_phase", **event)
            return self.t(event["code"], engine=event.get("engine", ""))
        return ""

    def add_event(self, event):
        if event.get("event") == "raw" and native_exception_marker(event.get("detail", "")):
            self.native_exception_count += 1
        self.events.append(event)
        self.events = self.events[-1500:]
        text = self.format_event(event)
        if text:
            self.log.appendPlainText(text)

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.add_event({"event": "error", "code": "start_failed", "detail": self.process.errorString()})
            self.process_finished(-1, QProcess.ExitStatus.CrashExit)

    def process_finished(self, exit_code, exit_status):
        if not self.process:
            return
        self.read_stdout()
        self.read_stderr()
        if self.buffer:
            self.consume_line(self.buffer)
            self.buffer = b""
        if self.stderr_buffer:
            self.add_event({"event": "raw", "detail": self.stderr_buffer.decode("utf-8", "replace")})
            self.stderr_buffer = b""
        unexpected = not self.cancel_requested and (
            exit_status != QProcess.ExitStatus.NormalExit or exit_code != 0 or not self.batch_finished)
        for row in self.batch_rows:
            entry = self.entries[row]
            if entry.state == "working":
                entry.state = "cancelled" if self.cancel_requested else "error"
            elif entry.state == "waiting":
                entry.state = "stopped"
        if unexpected:
            self.add_event({"event": "error", "code": "worker_failed",
                            "detail": qt_exit_detail(exit_code, exit_status.name)})
        if self.native_exception_count:
            self.add_event({"event": "notice", "code": "native_notice"})
        old = self.process
        self.process = None
        old.deleteLater()
        self.set_busy(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(1 if self.batch_finished else 0)
        self.refresh_table()
        self.selection_changed()
        if self.cancel_requested:
            self.summary = ("cancel_summary", {})
        else:
            ok = sum(self.entries[i].state in ("done", "warning") for i in self.batch_rows)
            failed = sum(self.entries[i].state in ("error", "stopped") for i in self.batch_rows)
            self.summary = ("finished_native" if self.native_exception_count else "finished",
                            {"ok": ok, "failed": failed})
        self.status_label.setText(self.t(self.summary[0], **self.summary[1]))
        if self.closing:
            QTimer.singleShot(0, self.close)

    def cancel(self):
        if self.running and self.message("cancel_question", question=True):
            self.cancel_requested = True
            self.cancel_button.setEnabled(False)
            # Conversion lives in a separate process; no blocking GUI thread.
            self.process.kill()

    def closeEvent(self, event):
        self.save_settings()
        if self.running:
            if self.message("close_question", question=True):
                self.closing = self.cancel_requested = True
                self.process.kill()
            event.ignore()
            return
        event.accept()

    def dragEnterEvent(self, event):
        if not self.running and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.add_files([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])
        event.acceptProposedAction()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Folio")
    app.setOrganizationName("FolioLocal")
    app.setStyle("Fusion")
    app.setPalette(light_palette())
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "folio.png")))
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FolioLocal.Folio.Desktop")
        except (AttributeError, OSError):
            pass
    window = MainWindow()
    window.show()
    return app.exec()
