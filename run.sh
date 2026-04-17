#!/bin/bash

set -e

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
fi

python3 main.py
