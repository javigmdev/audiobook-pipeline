import threading, uuid, time
from pathlib import Path
from flask import Flask, request, render_template, Response, send_file, jsonify

from pipeline import generate_audiobook

app = Flask(__name__)
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'outputs'
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

_jobs: dict = {}
_busy = threading.Semaphore(1)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    if 'epub' not in request.files:
        return jsonify({'error': 'Falta el archivo'}), 400
    f = request.files['epub']
    if not f.filename.lower().endswith('.epub'):
        return jsonify({'error': 'Debe ser un archivo .epub'}), 400
    if not _busy.acquire(blocking=False):
        return jsonify({'error': 'Ya hay una conversión en curso. Espera a que termine.'}), 409

    job_id = str(uuid.uuid4())[:8]
    epub_path = UPLOAD_DIR / f'{job_id}.epub'
    output_path = OUTPUT_DIR / f'{job_id}.m4b'
    f.save(str(epub_path))
    _jobs[job_id] = {'status': 'running', 'messages': [], 'output': str(output_path)}

    def run():
        try:
            def on_progress(msg):
                _jobs[job_id]['messages'].append(msg)
            generate_audiobook(str(epub_path), str(output_path), on_progress)
            _jobs[job_id]['status'] = 'done'
        except Exception as e:
            _jobs[job_id]['status'] = 'error'
            _jobs[job_id]['error'] = str(e)
        finally:
            epub_path.unlink(missing_ok=True)
            _busy.release()

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id):
    def stream():
        sent = 0
        while True:
            job = _jobs.get(job_id)
            if not job:
                yield 'data: ERROR: trabajo no encontrado\n\n'
                return
            while sent < len(job['messages']):
                yield f"data: {job['messages'][sent]}\n\n"
                sent += 1
            if job['status'] == 'done':
                yield 'data: DONE\n\n'
                return
            if job['status'] == 'error':
                yield f"data: ERROR: {job.get('error', 'desconocido')}\n\n"
                return
            time.sleep(0.5)

    return Response(
        stream(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@app.route('/download/<job_id>')
def download(job_id):
    job = _jobs.get(job_id)
    if not job or job['status'] != 'done':
        return 'No disponible', 404
    return send_file(job['output'], as_attachment=True, download_name='audiolibro.m4b')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
