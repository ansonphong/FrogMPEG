@echo off
setlocal

REM ============================================
REM FrogMPEG GUI Launcher
REM ============================================

cd /d "%~dp0"

if not exist "venv\" (
    echo Creating FrogMPEG virtual environment...
    python -m venv venv || goto :error
    echo.
    echo Installing FrogMPEG...
    venv\Scripts\python.exe -m pip install --upgrade pip
    venv\Scripts\python.exe -m pip install -e . || goto :error
    echo.
    echo Setup complete!
    echo.
)

echo Launching FrogMPEG GUI...
venv\Scripts\python.exe -m src gui
goto :eof

:error
echo.
echo ERROR: FrogMPEG setup failed.
pause
