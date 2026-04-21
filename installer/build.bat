@echo off
REM Build fux-voice.exe via PyInstaller
REM Aufruf: installer\build.bat

setlocal
cd /d "%~dp0\.."

echo [1/3] Pruefe Python Venv ...
if not exist "venv\Scripts\python.exe" (
    echo   Erstelle Venv ...
    python -m venv venv || goto :error
)

echo [2/3] Installiere Abhaengigkeiten ...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt || goto :error
python -m pip install pyinstaller || goto :error

echo [3/3] Baue fux-voice.exe ...
pyinstaller --clean --noconfirm installer\fux-voice.spec || goto :error

echo.
echo ============================================================
echo   FERTIG — Ausgabe: dist\fux-voice.exe
echo ============================================================
exit /b 0

:error
echo.
echo FEHLER beim Build.
exit /b 1
