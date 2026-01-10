@echo off
setlocal

REM ============================================
REM FrogMPEG CLI Launcher
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

venv\Scripts\python.exe -m frogmpeg %*
goto :eof

:error
echo.
echo ERROR: FrogMPEG setup failed.
pause
