import os
import uuid
import shutil
import zipfile
import tempfile
import sys
from flask import Flask, Response, jsonify, render_template, request, send_file


def resource_path(*parts):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base_path, *parts)


def configure_playwright_browser_path():
    if os.environ.get('PLAYWRIGHT_BROWSERS_PATH'):
        return

    candidates = [
        resource_path('ms-playwright'),
        resource_path('.playwright-browsers'),
        os.path.join(os.path.abspath(os.path.dirname(__file__)), 'ms-playwright'),
        os.path.join(os.path.abspath(os.path.dirname(__file__)), '.playwright-browsers'),
    ]

    executable_dir = os.path.dirname(os.path.abspath(sys.executable))
    current_dir = executable_dir
    for _ in range(6):
        candidates.append(os.path.join(current_dir, 'ms-playwright'))
        candidates.append(os.path.join(current_dir, '.playwright-browsers'))
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir

    for browser_path in candidates:
        if os.path.isdir(browser_path):
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browser_path
            return


configure_playwright_browser_path()

from generatePdf import generate_pdf


app = Flask(
    __name__,
    template_folder=resource_path('templates'),
    static_folder=resource_path('static'),
)

UPLOAD_BASE = tempfile.gettempdir()


def clean_macosx(dest):
    macosx_dir = os.path.join(dest, '__MACOSX')
    if os.path.exists(macosx_dir):
        shutil.rmtree(macosx_dir)
    for root, dirs, files in os.walk(dest):
        for f in files:
            if f.startswith('._'):
                os.remove(os.path.join(root, f))
        dirs[:] = [d for d in dirs if d != '__MACOSX']


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('folder_zip')
    if not f:
        return jsonify({'error': 'No file received.'}), 400
    if not f.filename.endswith('.zip'):
        return jsonify({'error': 'Only .zip archives are supported.'}), 400

    dest = os.path.join(UPLOAD_BASE, 'pdfgen_' + uuid.uuid4().hex)
    os.makedirs(dest, exist_ok=True)

    try:
        with zipfile.ZipFile(f.stream) as zf:
            zf.extractall(dest)
    except zipfile.BadZipFile:
        return jsonify({'error': 'Invalid or corrupt ZIP file.'}), 400

    clean_macosx(dest)

    entries = os.listdir(dest)
    if len(entries) == 1 and os.path.isdir(os.path.join(dest, entries[0])):
        dest = os.path.join(dest, entries[0])

    # Detect package type so the frontend knows which download buttons to show
    from generatePdf import detect_package_type
    package_type, _ = detect_package_type(dest)

    return jsonify({'folder_path': dest, 'package_type': package_type})


@app.route('/generate')
def generate():
    folder_path = request.args.get('folder')

    def stream():
        if not folder_path:
            yield 'data:No folder path provided.\n\n'
            return
        try:
            for message in generate_pdf(folder_path, stream=True):
                yield f'data:{message}\n\n'
            yield 'data: DONE\n\n'
        except Exception as e:
            yield f'data:Oops! ERROR: {str(e)}\n\n'

    return Response(stream(), mimetype='text/event-stream')


def resolve_pdf_download(folder_path, view='full'):
    if not folder_path:
        raise FileNotFoundError('No folder specified.')

    temp_pdf_dir = os.path.join(folder_path, 'temp_pdf')

    if view == 'desktop':
        candidates = sorted([
            f for f in os.listdir(temp_pdf_dir)
            if f.endswith('_desktop.pdf')
        ])
        if not candidates:
            raise FileNotFoundError('Desktop PDF not found.')
        return os.path.join(temp_pdf_dir, candidates[0]), 'email_desktop.pdf'

    if view == 'mobile':
        candidates = sorted([
            f for f in os.listdir(temp_pdf_dir)
            if f.endswith('_mobile.pdf')
        ])
        if not candidates:
            raise FileNotFoundError('Mobile PDF not found.')
        return os.path.join(temp_pdf_dir, candidates[0]), 'email_mobile.pdf'

    pdf_path = os.path.join(folder_path, 'final_output.pdf')
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError('PDF not found. Please generate it first.')
    return pdf_path, 'output.pdf'


@app.route('/download')
def download():
    folder_path = request.args.get('folder')
    view        = request.args.get('view', 'full')   # 'desktop' | 'mobile' | 'full'

    try:
        pdf_path, download_name = resolve_pdf_download(folder_path, view)
    except FileNotFoundError as exc:
        return str(exc), 404

    return send_file(pdf_path, as_attachment=True, download_name=download_name, mimetype='application/pdf')


def run_web(host='127.0.0.1', port=5003, debug=False):
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == '__main__':
    run_web(debug=True)
