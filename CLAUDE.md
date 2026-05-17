# Contexto del proyecto — audiobook-pipeline

## Objetivo
Generar audiolibros en **castellano** (España, no latinoamericano) a partir de epubs, usando la voz de un narrador específico (actualmente Jordi Boixaderas). Resultado en M4B con capítulos para Apple Books/iPhone (con marcadores de posición). El usuario quería evitar límites de páginas, costes recurrentes y dependencia de internet.

## Origen del proyecto
El proyecto arrancó con la app **ebook2audiobook** (de ahí el nombre del directorio `ebook2audio`). Es un proyecto open source que convierte epubs a audiolibros usando XTTSv2 para clonar la voz a partir de una muestra de audio. Se descartó por dos razones:

1. **XTTSv2 genera acento latinoamericano** independientemente de la voz de referencia castellana que se le pase. No hay forma de forzar acento de España en XTTSv2 — el modelo solo tiene "spanish" como idioma y por defecto suena latino. El usuario probó con muestras de Jordi en castellano y el resultado seguía sonando latinoamericano.
2. **Clonación zero-shot vs entrenamiento**: XTTSv2 hace clonación a partir de unos segundos de muestra (zero-shot). El resultado es aproximado, no fiel. Para una voz reconocible y consistente a lo largo de horas de audiolibro, hace falta entrenar un modelo dedicado a esa voz — eso es lo que hace RVC.

El pipeline actual reemplaza XTTSv2 por **Piper TTS** (que sí tiene modelo nativo `es_ES` para castellano) + **RVC** entrenado con la voz del narrador (calidad muy superior a la clonación zero-shot).

## Comunicación
- El usuario prefiere comunicarse en **castellano** (español de España)
- Respuestas concisas y directas

## Pipeline (tres fases)

```
[Fase 1: local]      epub no aplica aquí → preparar dataset de audio del narrador
[Fase 2: Colab]      WAV del narrador → entrenamiento RVC → modelo .pth
[Fase 3: Colab]      epub → Piper TTS (castellano) → RVC (.pth) → M4B/MP3
```

### Fase 1 — Preparar dataset (local en Mac)
Extraer 15-20 min de voz limpia del narrador (muestras de Audible, vídeos, podcasts), procesar con `ffmpeg` a WAV mono 44100 Hz y concatenar. El dataset final se guarda en `datasets/es-male-01/es-male-01.wav` (rastreado con Git LFS).

### Fase 2 — Entrenar el modelo (Colab + Applio)
Notebook: `colab/Applio.ipynb`. Usa GPU T4 gratuita de Colab. El entrenamiento local en Mac M1 con MPS era ~180x más lento que la T4 (se intentó y se descartó). El modelo se guarda en `MyDrive/audiobook-models/` y localmente en `modelos/`.

### Fase 3 — Generar audiolibros (Colab)
Notebook: `colab/Audiobook.ipynb`. Toma un epub, lo trocea por capítulos con `ebooklib`, sintetiza cada capítulo con Piper TTS (modelo `es_ES-davefx-medium`) y aplica el modelo RVC entrenado. Junta los WAVs en un M4B con marcadores de capítulo via `ffmpeg`.

## Decisiones de herramientas

- **Piper TTS** (no XTTSv2): XTTSv2 clona timbre pero genera acento latinoamericano independientemente de la voz de referencia. Piper tiene modelo nativo `es_ES`.
- **RVC** (no XTTSv2): para personalizar la voz al narrador, no solo el acento.
- **Applio** (no rvc-python): rvc-python está roto (pin a `numpy<=1.23.5`, sin wheels ARM64, conflictos imposibles). Applio funciona.
- **Colab para entrenar e inferir**: ver "Lo que NO funcionó" abajo.
- **Git LFS** para WAVs: el dataset (~94 MB) no cabe en git normal.

## Lo que NO funcionó (no reintentar)

### Entrenamiento local en Mac M1 con MPS
PyTorch tiene muchas operaciones no soportadas en MPS que caen a CPU. Benchmark: CPU 0.002s vs MPS 0.373s para 10 iteraciones de padding. 180x más lento que una T4 real. **Descartado** — todo el entrenamiento en Colab.

### Inferencia local con virtualenv (Python 3.11, Mac M1)
- Piper funciona bien en CPU.
- La inferencia RVC con `transformers.HubertModel` produce **segfault consistente** en Apple Silicon al cargar pesos del HuBERT.
- Probado: `NUMBA_DISABLE_JIT=1`, `PYTORCH_ENABLE_MPS_FALLBACK=1`, forzar device MPS, ejecutar en subproceso aislado. Todo sigue petando.
- Es un bug conocido de PyTorch en M1 con esa arquitectura de modelo.

### Inferencia local con Docker
- Primer intento con `rvc-python`: conflictos de dependencias imposibles (numpy, omegaconf sin wheels ARM64, incluso forzando `linux/amd64`).
- Segundo intento con Applio en Docker (`linux/amd64` via Rosetta): **funciona** pero la emulación QEMU es ~100x más lenta. Un capítulo tarda >6 min, un libro entero serían días. Inviable.

### XTTSv2 / ebook2audiobook
Genera acento latinoamericano siempre. Descartado por requisito de castellano.

### Edge TTS
Tiene límites de uso (no es local). Descartado por requisito de "sin límites".

## Estado actual

- Modelo `es-male-01` (voz de Jordi Boixaderas) entrenado: 200 épocas, 11200 pasos, ~18 min de dataset
- Modelo guardado en `modelos/es-male-01_200e_11200s.pth` y `modelos/es-male-01.index` (locales, también en `MyDrive/audiobook-models/`)
- Notebook de inferencia listo: `colab/Audiobook.ipynb`
- No hay app local — todo en Colab

## Estructura del repo

```
.
├── README.md
├── CLAUDE.md
├── .gitignore
├── .gitattributes              # config Git LFS
├── colab/
│   ├── Applio.ipynb            # entrenamiento (Fase 2)
│   └── Audiobook.ipynb         # generación (Fase 3)
├── datasets/
│   └── es-male-01/
│       └── es-male-01.wav      # dataset Git LFS
└── modelos/                    # .pth y .index (gitignored)
```

## Convenciones

### Nombres de modelos de voz
Formato `[idioma]-[género]-[número]`:
- `es-male-01` → español (España), masculino, primero
- `es-female-01`, `en-male-01`, etc.

### Idioma del código y comentarios
- README, CLAUDE.md, comentarios y mensajes de usuario en **castellano**
- Nombres de archivos, variables y funciones en **inglés** (decisión consciente del usuario para mantener consistencia con el código fuente)

## Cosas pendientes / posibles mejoras
- Si en el futuro hay acceso a una máquina Linux x86 (VPS, PC con Linux), se puede recuperar del historial de git el código de la app local con Gradio que funcionaba salvo por el segfault de M1
- Entrenar más voces (otras `es-male-XX`, `es-female-XX`)
