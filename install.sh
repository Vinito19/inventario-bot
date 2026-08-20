#!/bin/bash
set -e

# ============================================================
# Instalacion automatica del bot de inventario en Oracle Cloud
# Sistema: Ubuntu 22.04+
# ============================================================

GITHUB_USER="Vinito19"
REPO_NAME="inventario-bot"
REPO_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
APP_DIR="/opt/inventario-bot"
SERVICE_NAME="inventario-bot"

echo "=== [1/6] Actualizando sistema ==="
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip curl

echo "=== [2/6] Clonando el repositorio ==="
if [ ! -d "$APP_DIR" ]; then
    sudo git clone "$REPO_URL" "$APP_DIR"
else
    echo "Directorio $APP_DIR ya existe, actualizando..."
    cd "$APP_DIR"
    sudo git pull
fi
sudo chown -R ubuntu:ubuntu "$APP_DIR"
cd "$APP_DIR"

echo "=== [3/6] Creando entorno virtual ==="
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "=== [4/6] Configurando variables de entorno ==="
if [ ! -f "$APP_DIR/.env" ]; then
    read -rp "Ingresa tu BOT_TOKEN de Telegram: " BOT_TOKEN
    read -rp "Ingresa tu ADMIN_IDS (separados por coma si son varios): " ADMIN_IDS
    read -rp "Hora del backup diario (HH:MM, default 00:00): " HORA
    HORA=${HORA:-00:00}

    tee "$APP_DIR/.env" > /dev/null <<EOF
BOT_TOKEN=$BOT_TOKEN
ADMIN_IDS=$ADMIN_IDS
HORA_BACKUP=$HORA
TIMEZONE=America/Guayaquil
EOF
    chmod 600 "$APP_DIR/.env"
    echo ".env creado correctamente"
else
    echo ".env ya existe, no se sobrescribe"
fi

echo "=== [5/6] Creando servicio systemd ==="
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null <<EOF
[Unit]
Description=Bot de Inventario de Repuesto VCH
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/bot.py
Restart=always
RestartSec=10
EnvironmentFile=$APP_DIR/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.service"

echo "=== [6/6] Iniciando el bot ==="
sudo systemctl restart "${SERVICE_NAME}.service"
sleep 3

STATUS=$(systemctl is-active "${SERVICE_NAME}.service")
if [ "$STATUS" = "active" ]; then
    echo ""
    echo "=============================================="
    echo " BOT DESPLEGADO CORRECTAMENTE ✅"
    echo "=============================================="
    echo "Estado:    $STATUS"
    echo "Comando:   sudo systemctl status $SERVICE_NAME"
    echo "Logs:      sudo journalctl -u $SERVICE_NAME -f"
    echo "Reinicio:  sudo systemctl restart $SERVICE_NAME"
    echo ""
    echo "El bot se ejecuta 24/7 y se reinicia solo si falla."
else
    echo "⚠️ El bot no arranco. Revisa los logs:"
    echo "   sudo journalctl -u $SERVICE_NAME -f"
    exit 1
fi