@echo off
setlocal

cd /d "%~dp0"

echo Installing Python dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto error

echo Building StackPDF for Windows...
python build_desktop.py
if errorlevel 1 goto error

echo.
echo Build complete. Check the dist folder.
exit /b 0

:error
echo.
echo Build failed. Make sure Python is installed and available as "python".
echo If "python" is not recognized, try checking "py --version" or reinstall Python with "Add python.exe to PATH" enabled.
exit /b 1
