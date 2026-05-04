#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Installing Python dependencies..."
python3 -m pip install -r requirements.txt

echo "Building StackPDF for macOS..."
python3 build_desktop.py

echo
echo "Build complete. Check the dist folder."
