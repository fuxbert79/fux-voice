@echo off
REM Start ohne Build fuer schnelles Testen.
setlocal
cd /d "%~dp0\.."

if not exist "venv\Scripts\python.exe" (
    echo Erstelle Venv ...
    python -m venv venv || exit /b 1
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul
    python -m pip install -r requirements.txt || exit /b 1
) else (
    call venv\Scripts\activate.bat
)

python main.py
