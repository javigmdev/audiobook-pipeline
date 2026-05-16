# Guía: Crear modelos de voz con RVC y generar audiolibros

## Qué es esto

Pipeline para generar audiolibros en castellano con la voz de cualquier locutor. El proceso tiene dos fases:

1. **Entrenar el modelo de voz** — aprender cómo suena una voz concreta (se hace en la nube, una vez por locutor)
2. **Generar el audiolibro** — convertir epub a audio con esa voz (se hace en local, sin límites)

---

## Herramientas

### Google Colab
Servicio gratuito de Google que te da acceso a un ordenador en la nube con GPU (tarjeta gráfica potente). Lo usamos solo para entrenar el modelo porque en local tardaría días — en Colab tarda 30-40 minutos.
- URL: `colab.research.google.com`
- GPU gratuita: Tesla T4 (14 GB)
- Las sesiones duran unas horas — hay que descargar el modelo antes de que expire

### Applio
Herramienta con interfaz web para entrenar modelos RVC. El resultado es un fichero `.pth` que contiene la "huella" de una voz. Solo se usa en Colab para entrenar — una vez tienes el `.pth` no vuelves a necesitarlo.
- GitHub: `github.com/IAHispano/Applio`
- Tiene notebook oficial para Google Colab

### RVC (Retrieval-based Voice Conversion)
Tecnología de IA que convierte el timbre de una voz en otra. Gratuita, open source, corre en local.
- **Entrenamiento**: necesita 10-20 minutos de audio limpio + Colab (~30-40 min)
- **Inferencia** (usar el modelo): rápida en local, sin límites, sin internet

### Piper TTS
Motor de síntesis de voz local, gratuito, open source. Genera audio con acento castellano nativo a partir de texto. No tiene límites ni necesita internet.

---

## Fase 1: Preparar el dataset de audio

### Conseguir el audio
Busca grabaciones donde la persona hable sola (sin música ni otras voces). Buenas fuentes:
- Muestras de audiolibros en Audible
- Entrevistas en YouTube (descargar con `yt-dlp`)
- Podcasts, documentales, doblajes

Para capturar audio del sistema en Mac sin ruido de micrófono instalar **BlackHole**:
```bash
brew install blackhole-2ch
```
- En Configuración de Sonido → seleccionar BlackHole como salida
- Grabar con QuickTime usando BlackHole como entrada
- Captura el audio digital directamente, sin pasar por el micrófono

### Extraer audio de vídeos
```bash
# Instalar ffmpeg si no está
brew install ffmpeg

# Extraer audio como WAV mono (formato para RVC)
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 44100 -ac 1 audio.wav
```

### Procesar varios vídeos de una vez
```bash
# Desde la carpeta con los vídeos
mkdir -p ../audio

for f in *; do
  name=$(basename "${f%.*}")
  ffmpeg -y -i "$f" -vn -acodec pcm_s16le -ar 44100 -ac 1 "../audio/${name}.wav"
done

# Concatenar todos en un solo fichero
cd ../audio
ls *.wav | sort | awk '{print "file \047" $0 "\047"}' > concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy ../dataset.wav
rm concat.txt
```

**Resultado**: un único `dataset.wav` con todo el audio concatenado

### Requisitos del dataset
- Mínimo 5-10 minutos (10-20 recomendado)
- Audio limpio: sin música, sin ruido de fondo, sin otras voces
- Variedad: mejor varios audios distintos que uno solo repetido
- Formato: WAV, mono, 44100 Hz

---

## Fase 2: Entrenar el modelo en Google Colab

### Abrir Applio en Colab
1. Ir a `colab.research.google.com`
2. Archivo → Abrir notebook → GitHub → buscar `IAHispano/Applio`
3. Abrir `assets/Applio.ipynb`
4. **Cambiar runtime a GPU**: Entorno de ejecución → Cambiar tipo → T4 GPU

### Ejecutar las celdas en orden
1. **Setup Runtime Environment** — prepara el entorno
2. **Install Applio** (2 celdas ocultas) — instala todo (~2-3 min)
3. Saltar **Sync with Google Drive**
4. **Start server** (method: gradio) — lanza la interfaz web

### Subir el dataset
1. En el panel izquierdo de Colab pulsar el **icono de carpeta**
2. Navegar a `Applio → assets → datasets`
3. Crear una carpeta con el nombre del locutor (ej: `jordi`)
4. Arrastrar el `dataset.wav` dentro de esa carpeta

### Configurar y entrenar en Applio
Abrir el enlace público que aparece tras ejecutar Start server e ir a la pestaña **Training**:

**Model Settings:**
- Model Name: nombre del locutor (ej: `jordi`)
- Sampling Rate: `40000`
- Vocoder: `HiFi-GAN`

**Preprocess:**
- Dataset Path: `/content/Applio/assets/datasets/nombre`
- Pulsar **Preprocess Dataset** → esperar "preprocessed successfully"

**Extract:**
- Pitch: `rmvpe`
- Embedder: `contentvec`
- Pulsar **Extract Features** → esperar "extracted successfully"

**Training:**
- Batch Size: `8`
- Total Epoch: `200`
- Save Every Epoch: `10`
- Marcar **I agree to the terms of use**
- Pulsar **Start Training** → esperar ~30-40 minutos

### Descargar el modelo
Cuando aparezca "trained successfully":
1. En Applio ir a **Export Model**
2. Descargar `nombre.pth` y `nombre.index`
3. Guardar en `ebook2audio/modelos/`

**¡Importante!** Descargar antes de que expire la sesión de Colab (~12h máx en gratuito)

---

## Fase 3: Generar audiolibros

Proyecto Docker con interfaz web donde solo tienes que:
1. Subir el epub
2. Seleccionar la voz (el `.pth` del locutor)
3. Pulsar convertir
4. Descargar el M4B

Por dentro el pipeline es automático:
```
EPUB → texto → Piper TTS (castellano) → RVC (nombre.pth) → M4B
```

- **Piper TTS**: genera audio en castellano, gratuito, local, sin límites
- **RVC**: convierte el audio para que suene con la voz del locutor
- **M4B**: formato de audiolibro compatible con iPhone y Apple Books, con capítulos y marcadores para continuar donde lo dejaste
- **Sin límites de páginas**, sin internet, sin coste

---

## Estructura de carpetas del proyecto

```
ebook2audio/
├── modelos/                  → .pth y .index de cada locutor entrenado
│   ├── jordi.pth
│   ├── jordi.index
│   └── ...
├── datasets/                 → datasets de entrenamiento
│   └── nombre-locutor/
│       ├── raw/              → vídeos originales
│       ├── audio/            → WAV individuales extraídos
│       └── dataset.wav       → dataset completo para entrenamiento
└── audiobook-app/            → proyecto Docker (fase 3, pendiente)
    ├── docker-compose.yml
    ├── ebooks/
    └── audiobooks/
```
