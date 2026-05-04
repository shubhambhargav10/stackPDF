import os
import shutil
import socket
import threading
import time
import webbrowser

from werkzeug.serving import make_server

from app import app, resolve_pdf_download


APP_NAME = 'StackPDF'
DEFAULT_PORT = 5003


class ServerThread(threading.Thread):
    def __init__(self, host='127.0.0.1', port=DEFAULT_PORT):
        super().__init__(daemon=True)
        self.host = host
        self.port = find_free_port(host, port)
        self.server = make_server(host, self.port, app, threaded=True)
        self.context = app.app_context()
        self.context.push()

    @property
    def url(self):
        return f'http://{self.host}:{self.port}'

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


class StackPDFApi:
    def __init__(self):
        self.window = None

    def save_pdf(self, folder_path, view='full'):
        try:
            import webview

            pdf_path, download_name = resolve_pdf_download(folder_path, view)
            destination = self.window.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=download_name,
            )

            if not destination:
                return {'ok': False, 'cancelled': True}

            if isinstance(destination, (list, tuple)):
                destination = destination[0]

            if not destination.lower().endswith('.pdf'):
                destination += '.pdf'

            destination_dir = os.path.dirname(destination)
            if destination_dir:
                os.makedirs(destination_dir, exist_ok=True)
            shutil.copy2(pdf_path, destination)

            return {'ok': True, 'path': destination}
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}


def find_free_port(host, preferred_port):
    for port in [preferred_port, 0]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return sock.getsockname()[1]
    raise RuntimeError('No available local port found')


def wait_until_ready(url, timeout=8):
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except Exception:
            time.sleep(0.15)
    return False


def launch_desktop_window(url, server):
    try:
        import webview
    except ImportError:
        webbrowser.open(url)
        print(f'{APP_NAME} is running at {url}')
        return

    api = StackPDFApi()
    window = webview.create_window(
        APP_NAME,
        url,
        width=1040,
        height=860,
        min_size=(720, 640),
        confirm_close=False,
        js_api=api,
    )
    api.window = window

    def on_closed():
        server.stop()

    window.events.closed += on_closed
    webview.start(debug=False)


def main():
    server = ServerThread()
    server.start()

    if not wait_until_ready(server.url):
        raise RuntimeError(f'Unable to start {APP_NAME} server at {server.url}')

    launch_desktop_window(server.url, server)


if __name__ == '__main__':
    main()
