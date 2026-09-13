@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ejecuta install_windows.cmd primero / Run install_windows.cmd first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto failed
".venv\Scripts\python.exe" tools\smoke_test.py --engine text
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('liteparse') else 1)"
if errorlevel 1 goto docling
echo.
echo Prueba real de LiteParse sin OCR / Actual LiteParse smoke test, OCR off.
".venv\Scripts\python.exe" tools\smoke_test.py --engine liteparse
if errorlevel 1 goto failed
:docling
".venv\Scripts\python.exe" -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('docling') else 1)"
if errorlevel 1 goto done
echo.
echo Docling y OCR pueden descargar modelos / Docling and OCR may download models.
choice /c SN /n /m "Probar Docling ahora / Test Docling now? [S=Yes,N=No]: "
if errorlevel 2 goto done
".venv\Scripts\python.exe" tools\smoke_test.py --engine docling
if errorlevel 1 goto failed
:done
echo Comprobaciones terminadas / Checks finished.
pause
exit /b 0
:failed
echo Fallo en una comprobacion. Revisa el mensaje anterior / A check failed. Review the message above.
pause
exit /b 1
