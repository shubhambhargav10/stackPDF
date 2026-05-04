# StackPDF Desktop App

StackPDF can run as a normal Flask web app or as a desktop window on macOS and Windows.

## Development

Install dependencies:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

Run as a browser app:

```bash
python app.py
```

Run as a desktop app:

```bash
python desktop.py
```

The desktop launcher starts a local Flask server on `127.0.0.1`, opens a native app window with `pywebview`, and shuts the server down when the window closes. If `pywebview` is not installed, it falls back to opening the app in the default browser.

## Build

Build the current platform:

```bash
python build_desktop.py
```

Or use the convenience scripts:

```bash
./build_mac.sh
```

```bat
build_windows.bat
```

Outputs are created in `dist/`.

Build on macOS to create a macOS app. Build on Windows to create a Windows app. PyInstaller does not cross-compile reliably, so use each operating system to create its own build.

The build script also downloads Playwright Chromium and copies it into the build output.

On macOS, distribute these together:

```text
dist/StackPDF.app
dist/ms-playwright/
```

On Windows, distribute the whole folder:

```text
dist/StackPDF/
```

## Windows Notes

Before building on Windows, install Python 3.10 or newer from python.org and enable the "Add python.exe to PATH" option during setup.

After unzipping the project folder, open Command Prompt or PowerShell in the project folder and run:

```bat
build_windows.bat
```

That script installs Python packages and builds the app for you:

```bash
pip install -r requirements.txt
python build_desktop.py
```

Most Windows 10/11 machines already include Microsoft Edge WebView2 Runtime, which `pywebview` uses for the desktop window. If the desktop window does not open on an older machine, install Microsoft Edge WebView2 Runtime from Microsoft.

Windows Firewall may ask to allow Python or StackPDF on private networks. Allow it if you want the app to run normally.

## Playwright Note

The PDF generator uses Playwright Chromium. For development, `python -m playwright install chromium` is enough.

For distribution, the build script copies Playwright Chromium into the output folder. This makes the app larger, but users should not need to run `python -m playwright install chromium` after receiving the built app.
