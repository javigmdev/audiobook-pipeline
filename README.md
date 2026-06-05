# Audiobook Pipeline

Generar audiolibros en castellano (España) a partir de EPUBs. Resultado en M4B con capítulos para Apple Books/iPhone.

```
EPUB → texto por capítulos/párrafos → Edge TTS (es-ES-AlvaroNeural) → M4B
```

Servidor Flask que corre en un mini PC con Ubuntu. Accedes desde cualquier navegador de la red local, arrastras el EPUB y descargas el M4B. El nombre del fichero se toma del metadata del libro.

---

## Componentes

### Edge TTS — voz neural en castellano
Usa las voces Azure Neural Voices de Microsoft. La voz `es-ES-AlvaroNeural` es castellano de España, masculina, prácticamente indistinguible de una voz humana profesional. La API es gratuita y no tiene límites prácticos. Es la misma que usa el modo "leer en voz alta" del navegador Edge.

**Requiere internet** — es lo único que requiere conexión.

### ffmpeg — montaje del audiolibro
Junta los WAVs de cada párrafo, los concatena con silencios de 400 ms, y empaqueta todo como M4B con marcadores de capítulo. M4B es el formato de audiolibro de Apple: guarda la posición de reproducción y muestra los capítulos en Apple Books/iPhone.

---

## Servidor local

### Hardware
Mini PC NiPoGi con Ryzen 7 5700U, 32 GB RAM, sin GPU. Ubuntu Server. Acceso desde el Mac u otros dispositivos por interfaz web en red local.

### Instalación

```bash
git clone https://github.com/javigmdev/audiobook-pipeline.git ~/apps/audiobook
cd ~/apps/audiobook/server
bash setup.sh
```

El script instala ffmpeg, crea un virtualenv, instala las dependencias y abre el puerto 5000 en el firewall.

### Uso

```bash
cd ~/apps/audiobook/server
source venv/bin/activate
python app.py
```

Accede desde el navegador en `http://<ip-del-servidor>:5000`. Arrastra un EPUB, pulsa Convertir, espera (el progreso aparece en tiempo real) y descarga el M4B.

---

## Cómo escucharlo en iPhone

1. Descarga el M4B en el Mac
2. Ábrelo — Apple Books lo importa automáticamente
3. Sincroniza vía iCloud, o pásalo al iPhone con AirDrop

Apple Books guarda la posición de reproducción y permite navegar por capítulos.

---

## Historia: por qué Edge TTS y no RVC

El proyecto empezó usando un enfoque más complejo: **Piper TTS** (modelo nativo castellano) + **RVC** (Retrieval-based Voice Conversion) entrenado con la voz de Jordi Boixaderas. Funcionaba pero el resultado sonaba robotizado o con artefactos del RVC.

Edge TTS Alvaro es de calidad muy superior y no requiere modelo entrenado. La única ventaja del enfoque anterior era que funcionaba sin internet, pero el resultado no era natural.

El material de RVC se conserva en el repo (`colab/`, `datasets/`, `modelos/`) por si en algún momento se quiere volver a ese enfoque.

### Lo que no funcionó

- **XTTSv2 / ebook2audiobook**: clona voces a partir de pocos segundos, pero genera acento latinoamericano siempre. Descartado por requisito de castellano.
- **Inferencia RVC local en Mac M1**: segfault al cargar el modelo HuBERT. Bug de PyTorch en Apple Silicon.
- **RVC en Docker x86_64 sobre Rosetta**: funciona pero la emulación QEMU es ~100x más lenta. Un audiolibro tardaría días.

---

## Estructura del proyecto

```
audiobook-pipeline/
├── README.md
├── CLAUDE.md
├── .gitignore
├── .gitattributes              → config Git LFS para el WAV del dataset
├── server/                     → pipeline actual (Edge TTS)
│   ├── app.py                  → app Flask
│   ├── pipeline.py             → lógica de conversión
│   ├── setup.sh                → instalación en Ubuntu
│   ├── requirements.txt
│   └── templates/index.html
├── colab/                      → pipeline antiguo RVC (conservado)
│   ├── Applio.ipynb            → entrenamiento RVC en Colab
│   └── Audiobook.ipynb         → inferencia Piper+RVC en Colab
├── datasets/                   → dataset de entrenamiento RVC
│   └── es-male-01/
│       └── es-male-01.wav      → Git LFS
└── modelos/                    → modelos RVC entrenados (gitignored)
    ├── es-male-01.pth
    └── es-male-01.index
```
