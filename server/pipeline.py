import os, sys, re, tempfile, subprocess, wave, shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent
APPLIO_DIR = BASE_DIR / 'Applio'
PIPER_MODEL = BASE_DIR / 'piper_model' / 'es_ES-sharvard-medium.onnx'
MODEL_PTH = BASE_DIR / 'models' / 'es-male-01.pth'
MODEL_INDEX = BASE_DIR / 'models' / 'es-male-01.index'

# Applio usa rutas relativas internamente; este chdir afecta todo el proceso
os.chdir(str(APPLIO_DIR))
sys.path.insert(0, str(APPLIO_DIR))

from rvc.infer.infer import VoiceConverter
_vc = VoiceConverter()


def get_book_title(epub_path):
    from ebooklib import epub
    book = epub.read_epub(epub_path)
    meta = book.get_metadata('DC', 'title')
    if meta:
        title = meta[0][0].strip()
        # Limpiar caracteres no válidos en nombres de fichero
        return re.sub(r'[<>:"/\\|?*]', '', title) or 'audiolibro'
    return 'audiolibro'


def extract_chapters(epub_path):
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(epub_path)
    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        for tag in soup(['script', 'style']):
            tag.decompose()
        title_tag = soup.find(['h1', 'h2'])
        title = title_tag.get_text(strip=True) if title_tag else f'Capítulo {len(chapters) + 1}'

        paragraphs = [
            re.sub(r'\s+', ' ', p.get_text(strip=True)).strip()
            for p in soup.find_all('p')
            if len(p.get_text(strip=True)) > 20
        ]
        if not paragraphs:
            # fallback para EPUBs sin etiquetas <p>
            full = re.sub(r'\s+', ' ', soup.get_text(separator=' ', strip=True)).strip()
            if len(full) > 100:
                paragraphs = [full]

        if paragraphs:
            chapters.append((title, paragraphs))
    return chapters


def piper_tts(text, wav_path):
    r = subprocess.run(
        ['piper', '--model', str(PIPER_MODEL), '--output_file', str(wav_path)],
        input=text, capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f'Piper falló: {r.stderr}')


def rvc_convert(input_wav, output_wav):
    _vc.convert_audio(
        audio_input_path=str(input_wav),
        audio_output_path=str(output_wav),
        model_path=str(MODEL_PTH),
        index_path=str(MODEL_INDEX) if MODEL_INDEX.exists() else '',
        pitch=0, f0_method='rmvpe', index_rate=0.88, hop_length=128,
        split_audio=False, autotune=False, clean_audio=False, clean_strength=0.7,
        export_format='WAV', embedder_model='contentvec', embedder_model_custom=None,
        upscale_audio=False, resample_sr=0, post_process=False,
    )


def _make_silence(path, reference_wav, duration_ms=400):
    with wave.open(str(reference_wav), 'r') as ref:
        sr, ch, sw = ref.getframerate(), ref.getnchannels(), ref.getsampwidth()
    n_frames = int(sr * duration_ms / 1000)
    with wave.open(str(path), 'w') as f:
        f.setnchannels(ch)
        f.setsampwidth(sw)
        f.setframerate(sr)
        f.writeframes(b'\x00' * sw * ch * n_frames)


def _wav_duration_ms(path):
    with wave.open(str(path), 'r') as f:
        return int(f.getnframes() / f.getframerate() * 1000)


def generate_audiobook(epub_path, output_path, progress=None):
    def log(msg):
        if progress:
            progress(msg)
        print(msg, flush=True)

    chapters = extract_chapters(epub_path)
    log(f'{len(chapters)} capítulos detectados')

    tmp = Path(tempfile.mkdtemp())
    rvc_wavs = []

    try:
        for i, (title, paragraphs) in enumerate(chapters):
            log(f'[{i + 1}/{len(chapters)}] {title[:60]} ({len(paragraphs)} párrafos)')

            para_wavs = []
            for j, para in enumerate(paragraphs):
                pwav = tmp / f'piper_{i:03d}_{j:03d}.wav'
                piper_tts(para, pwav)
                para_wavs.append(pwav)

            silence = tmp / 'silence.wav'
            _make_silence(silence, para_wavs[0])

            chapter_list = tmp / f'chapter_list_{i:03d}.txt'
            with open(chapter_list, 'w') as f:
                for k, pw in enumerate(para_wavs):
                    f.write(f"file '{pw}'\n")
                    if k < len(para_wavs) - 1:
                        f.write(f"file '{silence}'\n")

            chapter_wav = tmp / f'chapter_{i:03d}.wav'
            subprocess.run(
                ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(chapter_list), '-c', 'copy', str(chapter_wav)],
                check=True, capture_output=True,
            )

            rwav = tmp / f'rvc_{i:03d}.wav'
            rvc_convert(chapter_wav, rwav)
            rvc_wavs.append(rwav)

        log('Uniendo capítulos...')
        concat = tmp / 'list.txt'
        with open(concat, 'w') as f:
            for w in rvc_wavs:
                f.write(f"file '{w}'\n")
        combined = tmp / 'combined.wav'
        subprocess.run(
            ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat), '-c', 'copy', str(combined)],
            check=True, capture_output=True,
        )

        log('Generando M4B con marcadores de capítulo...')
        meta = tmp / 'meta.txt'
        pos = 0
        with open(meta, 'w', encoding='utf-8') as f:
            f.write(';FFMETADATA1\n')
            for w, (title, _) in zip(rvc_wavs, chapters):
                dur = _wav_duration_ms(w)
                f.write(f'\n[CHAPTER]\nTIMEBASE=1/1000\nSTART={pos}\nEND={pos + dur}\ntitle={title}\n')
                pos += dur

        subprocess.run(
            ['ffmpeg', '-y', '-i', str(combined), '-i', str(meta),
             '-map_metadata', '1', '-c:a', 'aac', '-b:a', '64k', '-movflags', '+faststart',
             str(output_path)],
            check=True, capture_output=True,
        )

        log(f'Listo: {output_path}')

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
