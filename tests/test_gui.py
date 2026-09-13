"""Real Qt smoke checks if PySide6 is installed; skipped otherwise."""
import importlib.util
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None
if QT_AVAILABLE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QMenu
    from PySide6.QtCore import QSettings, QUrl, Qt, QItemSelectionModel, QProcess
    from PySide6.QtGui import QTextDocument, QPalette, QColor
    from PySide6.QtTest import QTest
    from folio.app import MainWindow, LocalMarkdown


@unittest.skipUnless(QT_AVAILABLE, "PySide6 not installed: GUI was not executed")
class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.temp = tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        settings = QSettings(str(Path(self.temp.name) / "test.ini"), QSettings.Format.IniFormat)
        settings.clear()
        self.window = MainWindow(settings=settings)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_language_switch(self):
        self.window.language_combo.setCurrentIndex(1)
        self.assertEqual(self.window.convert_button.text(), "Convert to Markdown")
        self.window.language_combo.setCurrentIndex(0)
        self.assertEqual(self.window.convert_button.text(), "Convertir a Markdown")

    def test_queue_and_preview(self):
        source = Path(__file__).resolve().parents[1] / "examples" / "synthetic_article.pdf"
        self.window.add_files([str(source), str(source)])
        self.assertEqual(len(self.window.entries), 1)
        self.assertTrue(self.window.convert_button.isEnabled())
        self.window.clear_files()
        self.assertFalse(self.window.convert_button.isEnabled())

    def test_engine_selection(self):
        self.window.engine.setCurrentIndex(1)
        self.assertEqual(self.window.get_options().engine, "docling")
        self.window.ocr_language.setCurrentIndex(1)
        self.assertEqual(self.window.get_options().ocr_language, "spa")

    def test_experimental_reader_is_opt_in_and_persists(self):
        self.window.engine.setCurrentIndex(self.window.engine.findData("docling"))
        self.assertFalse(self.window.docling_original.isChecked())
        self.assertTrue(self.window.get_options().docling_pdfium)
        self.window.docling_original.setChecked(True)
        self.assertFalse(self.window.get_options().docling_pdfium)
        self.window.save_settings()
        self.window.docling_original.setChecked(False)
        self.window.restore_settings()
        self.assertTrue(self.window.docling_original.isChecked())
        self.window.engine.setCurrentIndex(self.window.engine.findData("liteparse"))
        self.assertFalse(self.window.docling_original.isEnabled())
        self.window.engine.setCurrentIndex(self.window.engine.findData("docling"))
        self.assertTrue(self.window.docling_original.isEnabled())
        self.window.document_type.setCurrentIndex(2)
        self.assertFalse(self.window.docling_original.isEnabled())
        self.window.language_combo.setCurrentIndex(1)
        self.assertEqual(self.window.docling_original.text(), "Use original (experimental)")
        self.assertIn("tends to fail", self.window.pdfium_hint.text())

    def test_pre_023_saved_reader_migrates_without_changing_other_settings(self):
        self.window.settings.setValue("docling_pdfium", False)
        self.window.settings.setValue("ocr", False)
        self.window.settings.setValue("destination", self.temp.name)
        self.window.restore_settings()
        self.assertTrue(self.window.get_options().docling_pdfium)
        self.assertFalse(self.window.ocr.isChecked())
        self.assertEqual(self.window.destination.text(), self.temp.name)
        self.window.save_settings()
        self.assertEqual(self.window.settings.value("docling_reader"), "pdfium")

    def test_native_dump_remains_visible_after_normal_exit(self):
        self.window.process = QProcess(self.window)
        self.window.batch_rows = []
        self.window.batch_finished = True
        self.window.consume_line(b"Windows fatal exception: access violation")
        self.window.process_finished(0, QProcess.ExitStatus.NormalExit)
        self.assertEqual(self.window.summary[0], "finished_native")
        self.assertTrue(any(e.get("code") == "native_notice" for e in self.window.events))
        self.assertIsNone(self.window.process)

    def test_no_remote_image_loads(self):
        viewer = LocalMarkdown()
        viewer.base = Path(self.temp.name)
        result = viewer.loadResource(QTextDocument.ResourceType.ImageResource, QUrl("https://example.com/pixel.png"))
        self.assertIsNone(result)

    def test_local_path_escape_blocked(self):
        viewer = LocalMarkdown()
        viewer.base = Path(self.temp.name)
        result = viewer.loadResource(QTextDocument.ResourceType.ImageResource, QUrl.fromLocalFile("/tmp/outside.png"))
        self.assertIsNone(result)

    def test_document_type_and_pdf_controls(self):
        self.assertEqual(self.window.get_options().document_type, "auto")
        self.assertEqual(self.window.get_options().engine, "auto")
        self.window.document_type.setCurrentIndex(2)
        self.assertEqual(self.window.get_options().document_type, "text")
        self.assertFalse(self.window.engine.isEnabled())
        self.assertFalse(self.window.ocr.isEnabled())
        self.assertFalse(self.window.page_option.isEnabled())
        self.window.document_type.setCurrentIndex(1)
        self.assertTrue(self.window.engine.isEnabled())

    def test_dark_system_palette_context_menu_and_icon(self):
        old = self.app.palette()
        dark = QPalette(old)
        dark.setColor(QPalette.ColorRole.Window, QColor("#202020"))
        dark.setColor(QPalette.ColorRole.Base, QColor("#202020"))
        dark.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
        dark.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
        self.app.setPalette(dark)
        try:
            self.window.source.setPlainText("Selected text")
            self.window.source.selectAll()
            menu = self.window.source.createStandardContextMenu()
            menu.ensurePolished()
            menu.show()
            self.app.processEvents()
            self.assertEqual(menu.palette().color(QPalette.ColorRole.Window).name(), "#ffffff")
            self.assertEqual(menu.palette().color(QPalette.ColorRole.WindowText).name(), "#202e35")
            self.assertFalse(self.window.windowIcon().isNull())
            self.assertFalse(self.window.windowIcon().pixmap(16, 16).isNull())
            menu.close()
            menu.deleteLater()
        finally:
            self.app.setPalette(old)

    def test_save_log_button_writes_selected_file(self):
        target = Path(self.temp.name) / "saved-log.txt"
        self.window.log.setPlainText("CrashExit: diagnóstico de prueba")
        with patch("folio.app.QFileDialog.getSaveFileName", return_value=(str(target), "Text (*.txt)")):
            self.window.save_log_button.click()
        self.assertEqual(target.read_text(encoding="utf-8"), "CrashExit: diagnóstico de prueba\n")

    def test_disclosure_click_and_focus_do_not_shift_button(self):
        button = self.window.advanced
        self.window.side_scroll.ensureWidgetVisible(button)
        self.app.processEvents()
        before = button.sizeHint()
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertTrue(self.window.advanced_panel.isVisible())
        button.setFocus()
        self.app.processEvents()
        self.assertEqual(button.sizeHint(), before)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.assertFalse(self.window.advanced_panel.isVisible())

    def test_multiple_selection_survives_language_switch(self):
        root = Path(__file__).resolve().parents[1] / "examples"
        self.window.add_files([str(root / "sample_notes.txt"), str(root / "sample_document.docx")])
        selection = self.window.table.selectionModel()
        selection.select(self.window.table.model().index(1, 0), QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        self.assertEqual(len(selection.selectedRows()), 2)
        self.window.language_combo.setCurrentIndex(1)
        self.assertEqual(len(selection.selectedRows()), 2)
        QTest.mouseClick(self.window.remove_button, Qt.MouseButton.LeftButton)
        self.assertFalse(self.window.entries)
        self.assertFalse(self.window.remove_button.isEnabled())

    def test_actual_text_batch_in_process_and_completed_button(self):
        root = Path(__file__).resolve().parents[1] / "examples"
        self.window.versions["liteparse"] = self.window.versions["docling"] = None
        self.window.destination.setText(str(Path(self.temp.name) / "gui_results"))
        self.window.add_files([str(root / "sample_notes.txt"), str(root / "sample_document.docx")])
        self.assertFalse(self.window.engine.isEnabled())
        with patch.object(self.window, "message", side_effect=AssertionError("Unexpected blocking dialog")):
            QTest.mouseClick(self.window.convert_button, Qt.MouseButton.LeftButton)
            deadline = time.monotonic() + 15
            while self.window.process is not None and time.monotonic() < deadline:
                self.app.processEvents()
                QTest.qWait(10)
            if self.window.process:
                self.window.process.kill()
                self.window.process.waitForFinished(1000)
                self.fail("Text batch did not finish")
        self.assertEqual([e.state for e in self.window.entries], ["done", "done"])
        self.assertFalse(self.window.convert_button.isEnabled())
        self.assertFalse(self.window.cancel_button.isEnabled())
        self.assertIn("9281", self.window.source.toPlainText())
        self.assertTrue(self.window.open_md_button.isEnabled())
        self.window.language_combo.setCurrentIndex(1)
        self.assertIn("2 completed", self.window.status_label.text())
        self.assertNotIn("None", self.window.log.toPlainText())


if __name__ == "__main__":
    unittest.main()
