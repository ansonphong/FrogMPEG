@echo off
setlocal

REM ============================================
REM FrogMPEG CLI Launcher
REM ============================================

cd /d "%~dp0"

if not exist "venv\" (
    echo Creating FrogMPEG virtual environment...
    python -m venv venv || goto :error
    call venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install -r requirements.txt || goto :error
) else (
    call venv\Scripts\activate.bat
)

python -m frogmpeg %*
goto :eof

:error
echo.
echo ERROR: FrogMPEG setup failed.
pause

