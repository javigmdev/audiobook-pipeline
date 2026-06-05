# Contexto del proyecto — audiobook-pipeline

## Objetivo
Generar audiolibros en **castellano** (España, no latinoamericano) a partir de epubs. Resultado en M4B con capítulos para Apple Books/iPhone (con marcadores de posición).

## Comunicación
- El usuario prefiere comunicarse en **castellano** (español de España)
- Respuestas concisas y directas

## Pipeline actual

```
EPUB → texto por capítulos/párrafos → Edge TTS (es-ES-AlvaroNeural) → M4B con capítulos
```

Servidor Flask en `server/` corriendo en un mini PC Ubuntu (NiPoGi, Ryzen 7 5700U, 32 GB RAM, sin GPU). Accesible desde cualquier dispositivo de la red local en `http://<ip>:5000`.

## Decisiones de herramientas

### Edge TTS (Microsoft Azure Neural Voices)
- Voz `es-ES-AlvaroNeural` — masculina, castellano de España, calidad excelente
- API gratuita, sin límites prácticos
- Requiere conexión a internet (es lo único que requiere)
- Mucho más natural que cualquier opción local que probamos

### Por qué se descartó RVC + Piper
Estuvo activo durante un tiempo (Piper TTS local + RVC para clonar la voz del narrador Jordi Boixaderas). Funcionaba pero:
- Piper `es_ES-davefx-medium` y `es_ES-sharvard-medium` sonaban robotizados
- RVC añadía artefactos al convertir
- El resultado final no era natural

El modelo entrenado de Jordi (`modelos/es-male-01*`) y el notebook de Applio se conservan en el repo por si en algún momento se vuelve a este enfoque.

## Historia: opciones descartadas previamente

### XTTSv2 / ebook2audiobook
Genera acento latinoamericano siempre, independientemente de la voz de referencia. Descartado por requisito de castellano.

### Entrenamiento RVC local en Mac M1 con MPS
PyTorch tiene operaciones no soportadas en MPS que caen a CPU. ~180x más lento que una T4 real. El entrenamiento se hacía en Colab.

### Inferencia RVC local en Mac M1
La carga del modelo HuBERT con `transformers.HubertModel` produce **segfault** en Apple Silicon. Bug conocido de PyTorch en M1. En Linux x86_64 (el servidor actual) no ocurre.

### Inferencia RVC en Docker x86_64 vía Rosetta (Mac)
Funciona pero la emulación QEMU es ~100x más lenta. Inviable.

## Estructura del repo

```
.
├── README.md
├── CLAUDE.md
├── .gitignore
├── .gitattributes              # config Git LFS para el WAV del dataset
├── colab/
│   ├── Applio.ipynb            # entrenamiento RVC (conservado por si vuelve)
│   └── Audiobook.ipynb         # pipeline antiguo Piper+RVC en Colab (conservado)
├── server/                     # pipeline actual: Flask + Edge TTS
│   ├── app.py
│   ├── pipeline.py
│   ├── setup.sh
│   ├── requirements.txt
│   └── templates/index.html
├── datasets/
│   └── es-male-01/
│       └── es-male-01.wav      # dataset RVC Git LFS (conservado)
└── modelos/                    # modelos RVC entrenados (gitignored, conservados local)
    ├── es-male-01_200e_11200s.pth
    └── es-male-01.index
```

## Servidor local

### Puesta en marcha (una sola vez en el servidor)

```bash
git clone <repo> ~/apps/audiobook
cd ~/apps/audiobook/server
bash setup.sh
```

### Arrancar el servidor

```bash
cd ~/apps/audiobook/server
source venv/bin/activate
python app.py
```

### Notas técnicas
- División del EPUB en capítulos por documento, párrafos por `<p>` con fallback al texto completo
- 400 ms de silencio entre párrafos
- Un trabajo a la vez (Semaphore); peticiones simultáneas reciben HTTP 409
- SSE en `/status/<job_id>` para progreso en tiempo real
- Nombre del libro extraído del metadata DC del EPUB para el fichero descargado

## Convenciones

### Idioma del código y comentarios
- README, CLAUDE.md, comentarios y mensajes de usuario en **castellano**
- Nombres de archivos, variables y funciones en **inglés**

## Cosas pendientes / posibles mejoras
- Probar otras voces neurales de Edge TTS (`es-ES-ElviraNeural`, etc.)
- Usar el `<nav>` del EPUB para títulos de capítulos más precisos
- Configurar systemd para arranque automático del servidor al encender el mini PC
