#!/usr/bin/env bash
# Configura el servidor audiobook en Ubuntu (x86_64, sin GPU).
# Ejecución: bash setup.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== [1/6] Dependencias del sistema ==="
sudo apt-get update -qq
sudo apt-get install -y ffmpeg python3-pip python3-venv git curl

echo "=== [2/6] Clonando Applio ==="
if [ ! -d "$DIR/Applio" ]; then
    git clone --depth 1 --branch 3.6.2 https://github.com/IAHispano/Applio.git "$DIR/Applio"
else
    echo "  Applio ya existe, saltando."
fi

echo "=== [3/6] Entorno virtual y dependencias Python ==="
python3 -m venv "$DIR/venv"
# shellcheck disable=SC1091
source "$DIR/venv/bin/activate"

echo "  Instalando PyTorch CPU..."
pip install -q torch==2.7.1 torchaudio==2.7.1 torchvision==0.22.1 \
    --index-url https://download.pytorch.org/whl/cpu

echo "  Instalando dependencias de Applio..."
# Eliminar sufijo +cu128 (GPU CUDA) del requirements de Applio
sed 's/+cu128//g' "$DIR/Applio/requirements.txt" > /tmp/applio_req_cpu.txt
pip install -q -r /tmp/applio_req_cpu.txt

echo "  Instalando dependencias del servidor..."
pip install -q -r "$DIR/requirements.txt"

echo "=== [4/6] Descargando modelos auxiliares de Applio ==="
mkdir -p "$DIR/Applio/rvc/models/embedders/contentvec"
mkdir -p "$DIR/Applio/rvc/models/predictors"

_dl() {
    local dest="$1" url="$2"
    if [ ! -f "$dest" ]; then
        echo "  Descargando $(basename "$dest")..."
        curl -fsSL -o "$dest" "$url"
    else
        echo "  $(basename "$dest") ya existe, saltando."
    fi
}

_dl "$DIR/Applio/rvc/models/embedders/hubert_base.pt" \
    "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt"
_dl "$DIR/Applio/rvc/models/embedders/contentvec/pytorch_model.bin" \
    "https://huggingface.co/IAHispano/Applio/resolve/main/Resources/embedders/contentvec/pytorch_model.bin"
_dl "$DIR/Applio/rvc/models/embedders/contentvec/config.json" \
    "https://huggingface.co/IAHispano/Applio/resolve/main/Resources/embedders/contentvec/config.json"
_dl "$DIR/Applio/rvc/models/predictors/rmvpe.pt" \
    "https://huggingface.co/IAHispano/Applio/resolve/main/Resources/predictors/rmvpe.pt"
_dl "$DIR/Applio/rvc/models/predictors/fcpe.pt" \
    "https://huggingface.co/IAHispano/Applio/resolve/main/Resources/predictors/fcpe.pt"

echo "=== [5/6] Descargando modelo Piper TTS (es_ES-davefx-medium) ==="
mkdir -p "$DIR/piper_model"
_dl "$DIR/piper_model/es_ES-sharvard-medium.onnx" \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx"
_dl "$DIR/piper_model/es_ES-sharvard-medium.onnx.json" \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx.json"

echo "=== [6/6] Preparando directorio de modelos RVC ==="
mkdir -p "$DIR/models"

echo ""
echo "==========================================="
echo " Setup completado."
echo "==========================================="
echo ""
echo "PASO SIGUIENTE — copia tu modelo RVC:"
echo ""
echo "  cp /ruta/a/es-male-01_200e_11200s.pth  $DIR/models/es-male-01.pth"
echo "  cp /ruta/a/es-male-01.index            $DIR/models/es-male-01.index"
echo ""
echo "Después arranca el servidor:"
echo ""
echo "  source $DIR/venv/bin/activate"
echo "  python $DIR/app.py"
echo ""
echo "Accede desde el Mac en: http://<ip-del-servidor>:5000"
