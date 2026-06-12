@echo off
title AI Local Hardware Detector
echo Starting AI Local Hardware Detector...

cd /d "%~dp0"

if not exist ".venv" (
    echo Virtual environment not found. Creating one...
    python -m venv .venv
    if errorlevel 1 (
        echo Error: Python is not installed or not in PATH.
        pause
        exit /b 1
    )
    echo Installing dependencies...
    .venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo Error installing dependencies.
        pause
        exit /b 1
    )
)

echo Launching desktop application...
start "" ".venv\Scripts\pythonw.exe" gui.py
if errorlevel 1 (
    echo Failed to launch app using pythonw, trying with standard python...
    .venv\Scripts\python.exe gui.py
)

exit /b 0
