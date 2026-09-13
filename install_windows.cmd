@echo off
setlocal
cd /d "%~dp0"
echo Folio - Instalacion local / Local setup
echo Recomendado / Recommended: Python 3.12 de 64 bits.
echo.
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.12 tools\bootstrap.py
    goto done
)
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.11 tools\bootstrap.py
    goto done
)
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
    python tools\bootstrap.py
    goto done
)
echo No se encuentra Python / Python was not found.
echo Instala Python 3.12 de 64 bits desde https://www.python.org/downloads/windows/
echo Activa Add python.exe to PATH y vuelve a ejecutar este archivo.
echo Install Python 3.12 64-bit, select Add python.exe to PATH, then run this again.
:done
echo.
pause
