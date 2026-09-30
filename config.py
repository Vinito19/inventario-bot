import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

HORA_BACKUP = os.getenv("HORA_BACKUP", "00:00")
try:
    BACKUP_HORA, BACKUP_MINUTO = (int(x) for x in HORA_BACKUP.split(":"))
    if not (0 <= BACKUP_HORA <= 23 and 0 <= BACKUP_MINUTO <= 59):
        raise ValueError
except (ValueError, TypeError):
    raise ValueError(f"HORA_BACKUP inválida ('{HORA_BACKUP}'): usa formato HH:MM, p. ej. 03:00")

TIMEZONE = os.getenv("TIMEZONE", "America/Guayaquil")


def ahora():
    """Fecha y hora actual en la zona horaria configurada (Ecuador, UTC-5)."""
    return datetime.now(ZoneInfo(TIMEZONE))

if not BOT_TOKEN:
    raise ValueError("Falta BOT_TOKEN en el archivo .env")

if not ADMIN_IDS:
    print("ADVERTENCIA: No hay ADMIN_IDS configurados. Nadie podra administrar el bot.")