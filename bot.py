import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

import config
from database import init_db, registrar_admins

from telegram.ext import Application, CallbackQueryHandler, Defaults
from telegram.error import NetworkError

from backup import enviar_backup
from handlers.start import start_handler, inicio_callback_handler, aprobar_callback_handler, rechazar_callback_handler
from handlers.agregar import agregar_handler
from handlers.buscar import buscar_handler
from handlers.editar import editar_handler
from handlers.eliminar import eliminar_handler
from handlers.limpiar import limpiar_handler
from handlers.reporte import (
    reporte_handler,
    reporte_callback_handler,
    exportar_excel_handler,
    ver_stock_cero_handler,
    ver_ventas_handler,
    exportar_ventas_handler,
    ver_cambios_handler,
    exportar_cambios_handler,
    ver_ventas_mes_conv,
    ver_cambios_mes_conv,
    exportar_ventas_mes_handler,
    exportar_cambios_mes_handler,
)
from handlers.categorias import categorias_handler
from handlers.usuarios import usuarios_handler
from handlers.vender import vender_handler
from handlers.proforma import proforma_callback_handler, setlogo_handler

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")


async def error_handler(update, context):
    error = context.error
    if isinstance(error, NetworkError):
        logging.warning("Error de red temporal (usuario puede reintentar): %s", error)
        return
    logging.error("Excepción al procesar update:", exc_info=error)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Ocurrió un error inesperado. Intenta de nuevo."
            )
    except Exception:
        pass


def main():
    init_db()
    registrar_admins(config.ADMIN_IDS)
    print("[OK] Base de datos inicializada")

    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(15)
        .defaults(Defaults(tzinfo=ZoneInfo(config.TIMEZONE)))
        .build()
    )

    app.add_error_handler(error_handler)

    app.add_handler(start_handler)
    app.add_handler(aprobar_callback_handler)
    app.add_handler(rechazar_callback_handler)

    app.add_handler(agregar_handler)
    app.add_handler(buscar_handler)
    app.add_handler(editar_handler)
    app.add_handler(eliminar_handler)
    app.add_handler(limpiar_handler)
    app.add_handler(vender_handler)

    app.add_handler(reporte_handler)
    app.add_handler(reporte_callback_handler)
    app.add_handler(exportar_excel_handler)
    app.add_handler(ver_stock_cero_handler)
    app.add_handler(ver_ventas_handler)
    app.add_handler(exportar_ventas_handler)
    app.add_handler(ver_cambios_handler)
    app.add_handler(exportar_cambios_handler)
    app.add_handler(ver_ventas_mes_conv)
    app.add_handler(ver_cambios_mes_conv)
    app.add_handler(exportar_ventas_mes_handler)
    app.add_handler(exportar_cambios_mes_handler)
    app.add_handler(exportar_cambios_handler)

    app.add_handler(categorias_handler)
    app.add_handler(usuarios_handler)

    app.add_handler(setlogo_handler)
    app.add_handler(proforma_callback_handler)

    app.add_handler(inicio_callback_handler)

    hora_backup = time(config.BACKUP_HORA, config.BACKUP_MINUTO)
    app.job_queue.run_daily(enviar_backup, time=hora_backup, days=tuple(range(7)))
    print(f"[OK] Backup diario programado a las {config.BACKUP_HORA:02d}:{config.BACKUP_MINUTO:02d}")

    print("[OK] Bot iniciado correctamente")
    app.run_polling()


if __name__ == "__main__":
    main()