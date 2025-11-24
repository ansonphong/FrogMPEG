@echo off
setlocal

REM ============================================
REM FrogMPEG GUI Launcher
REM ============================================

cd /d "%~dp0"

if not exist "venv\" (
    echo Creating FrogMPEG virtual environment...
    python -m venv venv || goto :error
    call venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install -e . || goto :error
) else (
    call venv\Scripts\activate.bat
)

python -m frogmpeg gui
goto :eof

:error
echo.
echo ERROR: FrogMPEG setup failed.
pause

