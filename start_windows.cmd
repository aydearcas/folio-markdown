@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Ejecuta install_windows.cmd primero / Run install_windows.cmd first.
    pause
    exit /b 1
)
start "Folio" ".venv\Scripts\pythonw.exe" "%~dp0main.py"
