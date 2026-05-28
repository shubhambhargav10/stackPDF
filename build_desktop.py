import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP_NAME = 'StackPDF'
BROWSER_DIR = ROOT / '.playwright-browsers'


def data_arg(source, target):
    separator = ';' if platform.system() == 'Windows' else ':'
    return f'{source}{separator}{target}'


def install_playwright_browser():
    env = os.environ.copy()
    env['PLAYWRIGHT_BROWSERS_PATH'] = str(BROWSER_DIR)
    command = [sys.executable, '-m', 'playwright', 'install', 'chromium']

    print('Installing Playwright Chromium into:', BROWSER_DIR)
    subprocess.check_call(command, cwd=ROOT, env=env)


def bundled_browser_destination():
    if platform.system() == 'Darwin':
        return ROOT / 'dist' / 'ms-playwright'
    return ROOT / 'dist' / APP_NAME / 'ms-playwright'


def copy_playwright_browser():
    destination = bundled_browser_destination()

    if destination.exists():
        shutil.rmtree(destination)

    print('Copying Playwright Chromium to:', destination)
    shutil.copytree(BROWSER_DIR, destination, symlinks=True)


def clean_previous_build():
    for path in [ROOT / 'build', ROOT / 'dist', ROOT / f'{APP_NAME}.spec']:
        if path.is_dir():
            print('Removing old folder:', path)
            shutil.rmtree(path)
        elif path.exists():
            print('Removing old file:', path)
            path.unlink()


def main():
    clean_previous_build()
    install_playwright_browser()

    command = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--noconfirm',
        '--clean',
        '--noupx',
        '--onedir',
        '--windowed',
        '--name',
        APP_NAME,
        '--add-data',
        data_arg(ROOT / 'templates', 'templates'),
        '--add-data',
        data_arg(ROOT / 'static', 'static'),
        '--hidden-import',
        'playwright.sync_api',
        '--hidden-import',
        'PyPDF2',
        str(ROOT / 'desktop.py'),
    ]

    print('Running:', ' '.join(map(str, command)))
    subprocess.check_call(command, cwd=ROOT)
    copy_playwright_browser()

    print()
    print(f'Done. Build output is in: {ROOT / "dist"}')
    print('Playwright Chromium was copied next to the app build.')


if __name__ == '__main__':
    main()