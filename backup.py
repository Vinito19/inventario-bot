import logging
import os
import sqlite3
import tempfile
import zipfile
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
    """Envia el backup comprimido de la base de datos al primer admin configurado."""
    if not config.ADMIN_IDS:
        logging.warning("Sin ADMIN_IDS, no se puede enviar backup.")
        return

    destino = config.ADMIN_IDS[0]
    try:
        ruta_db = hacer_backup_db()
    except Exception as e:
        logging.error("Error creando backup: %s", e)
        return

    ruta_zip = ruta_db + ".zip"
    nombre_zip = nombre_backup().replace(".db", ".zip")
    try:
        with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(ruta_db, arcname=nombre_backup())
        with open(ruta_zip, "rb") as f:
            await context.bot.send_document(
                chat_id=destino,
                document=f,
                filename=nombre_zip,
                caption=f"Backup automatico - {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            )
        logging.info("Backup enviado a %s", destino)
    except Exception as e:
        logging.error("Error enviando backup: %s", e)
    finally:
        for ruta in (ruta_zip, ruta_db):
            try:
                os.remove(ruta)
            except OSError:
                pass