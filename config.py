import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

if not BOT_TOKEN:
    raise ValueError("Falta BOT_TOKEN en el archivo .env")

if not ADMIN_IDS:
    print("ADVERTENCIA: No hay ADMIN_IDS configurados. Nadie podra administrar el bot.")