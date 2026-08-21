#!/bin/bash
set -e

# ============================================================
# Actualizacion del bot en la nube
# Trae los ultimos cambios desde GitHub y reinicia el servicio
# Uso:  bash update.sh
# ============================================================

APP_DIR="/opt/inventario-bot"
SERVICE="inventario-bot"

cd "$APP_DIR"

echo "=== [1/3] Descargando cambios desde GitHub ==="
OUTPUT=$(sudo git pull)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "Already up to date"; then
    echo "Sin cambios nuevos. El bot sigue como estaba."
    exit 0
fi

echo "=== [2/3] Actualizando dependencias ==="
source venv/bin/activate
pip install -r requirements.txt

echo "=== [3/3] Reiniciando el servicio ==="
sudo systemctl restart "$SERVICE"
sleep 3

STATUS=$(systemctl is-active "$SERVICE")
if [ "$STATUS" = "active" ]; then
    echo ""
    echo "=============================================="
    echo " BOT ACTUALIZADO CORRECTAMENTE"
    echo "=============================================="
    echo "Logs:   sudo journalctl -u $SERVICE -f"
else
    echo "El bot no arranco. Revisa los logs:"
    echo "  sudo journalctl -u $SERVICE -f"
    exit 1
fi