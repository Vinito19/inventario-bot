import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

HORA_BACKUP = os.getenv("HORA_BACKUP", "00:00")
BACKUP_HORA, BACKUP_MINUTO = (int(x) for x in HORA_BACKUP.split(":"))

TIMEZONE = os.getenv("TIMEZONE", "America/Guayaquil")

if not BOT_TOKEN:
    raise ValueError("Falta BOT_TOKEN en el archivo .env")

if not ADMIN_IDS:
    print("ADVERTENCIA: No hay ADMIN_IDS configurados. Nadie podra administrar el bot.")