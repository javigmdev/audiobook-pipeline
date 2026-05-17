# Audiobook Pipeline

Pipeline para generar audiolibros en castellano con la voz de cualquier narrador. El proceso tiene dos fases:

1. **Entrenar el modelo de voz** — aprender cómo suena una voz concreta (se hace en la nube, una vez por narrador)
2. **Generar el audiolibro** — convertir epub a audio con esa voz (se hace en local, sin límites)

---

## Herramientas y por qué las usamos

### Google Colab + Applio — solo para entrenar
Entrenar un modelo RVC requiere GPU. En un Mac M1 Pro, el MPS (GPU Metal) de PyTorch tiene muchas operaciones no soportadas que caen al CPU, haciendo el entrenamiento RVC ~180x más lento que en una GPU real — días en vez de minutos.

Google Colab proporciona una GPU Tesla T4 gratuita en la nube. Applio es la herramienta con interfaz web que corre sobre Colab para gestionar el proceso de entrenamiento. Juntos entrenan el modelo en 30-40 minutos.

Una vez terminado el entrenamiento, el archivo `.pth` se descarga y Colab ya no se necesita más para esa voz.

- URL de Colab: `colab.research.google.com`
- GPU gratuita: Tesla T4 (14 GB)
- Las sesiones expiran tras unas horas de inactividad — activa la sincronización con Google Drive para guardar el modelo automáticamente
- Si el límite de GPU gratuito está agotado, espera un rato y vuelve a intentarlo

### RVC (Retrieval-based Voice Conversion)
Tecnología de IA que convierte el timbre de una voz a otra. Gratuito y open source.
- **Entrenamiento** (en Colab): aprende una voz a partir de 10-20 min de audio limpio, produce un archivo `.pth`
- **Inferencia** (en local): convierte cualquier audio para que suene como esa voz — rápido en CPU, sin límites, sin internet

### Piper TTS — para el acento castellano
Otros motores TTS como XTTSv2 clonan el timbre de voz pero generan acento latinoamericano independientemente de la voz de referencia. Piper TTS tiene un modelo nativo de español de España (`es_ES`) que garantiza el acento correcto.

Piper genera el audio base en castellano y luego RVC lo transforma para que suene como el narrador objetivo.

---

## Fase 1: Preparar el dataset de audio

### Obtener el audio
Busca grabaciones donde la persona hable sola (sin música ni otras voces). Buenas fuentes:
- Muestras de audiolibros en Audible
- Entrevistas en YouTube (descargar con `yt-dlp`)
- Podcasts, documentales, doblajes

Para capturar audio del sistema en Mac sin ruido de micrófono, instala **BlackHole**:
```bash
brew install blackhole-2ch
```
- Preferencias del Sistema → Sonido → seleccionar BlackHole como salida
- Grabar con QuickTime usando BlackHole como entrada
- Captura el audio digital directamente, sin pasar por el micrófono

### Extraer audio de vídeos
```bash
# Instalar ffmpeg si no está disponible
brew install ffmpeg

# Extraer audio como WAV mono (formato para RVC)
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 44100 -ac 1 audio.wav
```

### Procesar varios vídeos a la vez
```bash
# Desde la carpeta que contiene los vídeos
mkdir -p ../audio

for f in *; do
  name=$(basename "${f%.*}")
  ffmpeg -y -i "$f" -vn -acodec pcm_s16le -ar 44100 -ac 1 "../audio/${name}.wav"
done

# Concatenar todos en un único archivo
cd ../audio
ls *.wav | sort | awk '{print "file \047" $0 "\047"}' > concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy ../es-male-01.wav
rm concat.txt
```

**Resultado**: un único `es-male-01.wav` con todo el audio concatenado

### Requisitos del dataset
- Mínimo 5-10 minutos (10-20 recomendado)
- Audio limpio: sin música, sin ruido de fondo, sin otras voces
- Variedad: mejor usar varias grabaciones distintas que una sola repetida
- Formato: WAV, mono, 44100 Hz

### Convención de nombres
```
es-male-01    → español, masculino, primero
es-female-01  → español, femenino, primero
en-male-01    → inglés, masculino, primero
```

---

## Fase 2: Entrenar el modelo en Google Colab

### Abrir el notebook
1. Ir a `colab.research.google.com`
2. Archivo → Abrir notebook → GitHub
3. Buscar `javigmdev/audiobook-pipeline`
4. Abrir `colab/Applio.ipynb`
5. **Cambiar a runtime con GPU**: Runtime → Cambiar tipo de entorno de ejecución → T4 GPU

### Ejecutar las celdas en orden
1. **Setup Runtime Environment** — prepara el entorno
2. **Install Applio** (2 celdas ocultas) — instala todo (~2-3 min)
3. **Sync with Google Drive** — aceptar el permiso. Guarda el modelo automáticamente en Google Drive al terminar el entrenamiento
4. **Start server** (method: gradio) — lanza la interfaz web

### Subir el dataset
1. En el panel izquierdo de Colab hacer clic en el **icono de carpeta**
2. Navegar a `Applio → assets → datasets`
3. Crear una carpeta con el nombre de la voz (ej. `es-male-01`)
4. Arrastrar el archivo `es-male-01.wav` dentro de esa carpeta

### Configurar y entrenar en Applio
Abrir el enlace público que aparece al ejecutar Start server e ir a la pestaña **Training**:

**Model Settings:**
- Model Name: nombre de la voz (ej. `es-male-01`)
- Sampling Rate: `40000`
- Vocoder: `HiFi-GAN`

**Preprocess:**
- Dataset Path: `/content/Applio/assets/datasets/es-male-01` — esta es la **carpeta**, no el archivo wav
- Clic en **Preprocess Dataset** → esperar "preprocessed successfully"

**Extract:**
- Pitch: `rmvpe`
- Embedder: `contentvec`
- Clic en **Extract Features** → esperar "extracted successfully"

**Training:**
- Batch Size: `8`
- Total Epoch: `200`
- Save Every Epoch: `10`
- Marcar **I agree to the terms of use**
- Clic en **Start Training** → esperar ~30-40 minutos

### Descargar el modelo
Cuando aparezca "trained successfully":
1. En Applio bajar hasta **Export Model**
2. Clic en **Refresh** y seleccionar el modelo en los desplegables **Pth file** e **Index File**
3. Descargar ambos archivos
4. Guardarlos en `modelos/` como `es-male-01.pth` y `es-male-01.index`

**Si la sesión expira:** el modelo está guardado en Google Drive en `ApplioExported/` — descargarlo desde ahí.

---

## Fase 3: Generar audiolibros (en Colab)

La inferencia se hace en Google Colab por las razones explicadas más abajo. Es un único notebook que toma un epub y devuelve un M4B con capítulos.

### Requisitos previos
- Los archivos `es-male-01.pth` y `es-male-01.index` subidos a Google Drive en `MyDrive/audiobook-models/`
- Un epub para convertir

### Abrir el notebook
1. Ir a `colab.research.google.com`
2. Archivo → Abrir notebook → GitHub
3. Buscar `javigmdev/audiobook-pipeline`
4. Abrir `colab/Audiobook.ipynb`
5. **Cambiar a runtime con GPU**: Runtime → Cambiar tipo de entorno de ejecución → T4 GPU

### Ejecutar
1. **Celda 1 (Instalar dependencias)** — ~2-3 min
2. **Celda 2 (Descargar modelos)** — ~1 min (HuBERT, RMVPE, FCPE, contentvec, Piper)
3. **Celda 3 (Conectar Google Drive)** — acepta el permiso
4. **Subir el epub** al panel de archivos de Colab (icono carpeta a la izquierda) como `libro.epub`
5. **Celda 4 (Configurar rutas)** — verifica que todo está en su sitio
6. **Celda 5 (Generar)** — procesa cada capítulo (Piper → RVC con tu modelo)
7. **Celda 6 (Descargar)** — descarga el M4B (también queda guardado en tu Drive)

El pipeline:
```
EPUB → texto → Piper TTS (castellano) → RVC (es-male-01.pth) → M4B con capítulos
```

**M4B**: audiolibro con capítulos para Apple Books e iPhone. Guarda la posición de reproducción.

### Por qué Colab y no local

Se intentaron dos enfoques locales (ambos descartados):

**Local con virtualenv (Python 3.11, Mac M1 Pro)**
- Piper TTS funciona bien en CPU.
- La inferencia RVC con `transformers.HubertModel` produce un **segmentation fault** consistente en Apple Silicon con CPU, tras cargar los pesos del modelo HuBERT.
- Probado con `NUMBA_DISABLE_JIT=1`, `PYTORCH_ENABLE_MPS_FALLBACK=1` y forzando MPS — el crash persiste. Es un bug conocido de PyTorch en M1 con ciertas arquitecturas de modelo.

**Docker con emulación x86_64 vía Rosetta**
- Evita el segfault porque corre Linux x86 dentro del contenedor.
- Pero la emulación QEMU+Rosetta para ML es brutalmente lenta — ~100x más lenta que x86 nativo.
- Un capítulo tarda más de 6 minutos en convertir; un audiolibro entero sería días de cómputo. Inviable.

**Conclusión**: la inferencia RVC necesita Linux x86 o GPU para ser viable. Colab cumple ambas (Linux + T4 GPU) y es gratuito. Si en el futuro hay acceso a una máquina Linux x86, el código de inferencia que se preparó se puede recuperar del historial de git.

---

## Estructura del proyecto

```
audiobook-pipeline/
├── .gitignore
├── .gitattributes              → config Git LFS para archivos wav
├── README.md
├── colab/
│   ├── Applio.ipynb            → notebook para entrenar la voz (Fase 2)
│   └── Audiobook.ipynb         → notebook para generar audiolibros (Fase 3)
├── datasets/
│   └── es-male-01/             → wav rastreado via Git LFS, resto ignorado
│       ├── raw/                → vídeos originales (ignorado)
│       ├── audio/              → WAVs individuales extraídos (ignorado)
│       └── es-male-01.wav      → dataset completo (Git LFS)
└── modelos/                    → ignorado por git (archivos .pth)
    ├── es-male-01.pth
    └── es-male-01.index
```
