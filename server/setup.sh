#!/usr/bin/env bash
# Configura el servidor audiobook en Ubuntu.
# Ejecución: bash setup.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== [1/3] Dependencias del sistema ==="
sudo apt-get update -qq
sudo apt-get install -y ffmpeg python3 python3-pip python3-venv

echo "=== [2/3] Entorno virtual y dependencias Python ==="
python3 -m venv "$DIR/venv"
# shellcheck disable=SC1091
source "$DIR/venv/bin/activate"
pip install -q -r "$DIR/requirements.txt"

echo "=== [3/3] Abrir puerto 5000 en el firewall ==="
sudo ufw allow 5000 || true

echo ""
echo "==========================================="
echo " Setup completado."
echo "==========================================="
echo ""
echo "Arrancar el servidor:"
echo ""
echo "  source $DIR/venv/bin/activate"
echo "  python $DIR/app.py"
echo ""
echo "Accede desde el navegador en: http://<ip-del-servidor>:5000"
