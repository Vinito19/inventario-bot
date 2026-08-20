import logging
import sqlite3
import tempfile
from datetime import datetime

import config
from database import DB_NAME


def hacer_backup_db():
    """Crea un backup consistente de la base de datos en un archivo temporal."""
    src = sqlite3.connect(DB_NAME, timeout=10)
    tmp = tempfile.NamedTemporaryFile(prefix="backup_inventario_", suffix=".db", delete=False)
    tmp.close()
    try:
        dst = sqlite3.connect(tmp.name)
        try:
            src.backup(dst)
            logging.info("Backup creado en %s", tmp.name)
            return tmp.name
        finally:
            dst.close()
    finally:
        src.close()


def nombre_backup():
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"backup_inventario_{fecha}.db"


async def enviar_backup(context):
    """Envia el backup de la base de datos al primer admin configurado."""
    if not config.ADMIN_IDS:
        logging.warning("Sin ADMIN_IDS, no se puede enviar backup.")
        return

    destino = config.ADMIN_IDS[0]
    try:
        ruta = hacer_backup_db()
    except Exception as e:
        logging.error("Error creando backup: %s", e)
        return

    try:
        with open(ruta, "rb") as f:
            await context.bot.send_document(
                chat_id=destino,
                document=f,
                filename=nombre_backup(),
                caption=f"Backup automatico - {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            )
        logging.info("Backup enviado a %s", destino)
    except Exception as e:
        logging.error("Error enviando backup: %s", e)
    finally:
        import os

        try:
            os.remove(ruta)
        except OSError:
            pass