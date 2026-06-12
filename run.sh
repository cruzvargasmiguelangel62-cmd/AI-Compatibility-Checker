#!/bin/bash

# Navigate to script directory
cd "$(dirname "$0")"

echo "Starting AI Local Hardware Detector..."

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Error: Python 3 is not installed or not in PATH."
        exit 1
    fi
    echo "Installing dependencies..."
    .venv/bin/pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error installing dependencies."
        exit 1
    fi
fi

echo "Launching desktop application..."
.venv/bin/python gui.py
