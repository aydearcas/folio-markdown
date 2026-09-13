@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ejecuta install_windows.cmd primero / Run install_windows.cmd first.
    pause
    exit /b 1
)
echo Diagnostico con PDF sintetico / Diagnostic using the synthetic PDF.
echo No reinstala paquetes ni borra caches / Does not reinstall packages or clear caches.
echo Puede descargar modelos / Model downloads may occur.
set "FOLIO_DIAG_READER="
echo PDFium recomendado / recommended. Original experimental: puede fallar / may fail.
choice /c PO /n /m "Lector / Reader [P=PDFium,O=Original experimental]: "
if not errorlevel 2 goto reader_ready
set "FOLIO_DIAG_READER=--original-reader"
:reader_ready
choice /c SN /n /m "Activar OCR / Enable OCR? [S=Yes,N=No]: "
if errorlevel 2 goto noocr
".venv\Scripts\python.exe" tools\diagnose_docling.py %FOLIO_DIAG_READER% --ocr
goto done
:noocr
".venv\Scripts\python.exe" tools\diagnose_docling.py %FOLIO_DIAG_READER%
:done
echo Los informes estan en diagnostics / Reports are in diagnostics.
pause
