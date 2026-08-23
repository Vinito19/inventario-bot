from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from database import (
    obtener_repuesto,
    esta_registrado,
    es_admin,
    set_config,
    get_config,
)
from keyboards import botones_volver
from handlers.utils import edit_mensaje, finalizar, guardar_mensaje
from pdf_proforma import generar_proforma

SET_LOGO_WAIT = range(1)[0]


async def set_logo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not es_admin(user_id):
        await update.message.reply_text("❌ Solo el administrador puede configurar el logo.")
        return ConversationHandler.END

    await update.message.reply_text(
        "📷 Envía la foto del logo para usar en las proformas:",
        reply_markup=botones_volver(),
    )
    return SET_LOGO_WAIT


async def receive_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not es_admin(user_id):
        await update.message.reply_text("❌ Solo el administrador puede configurar el logo.")
        return ConversationHandler.END

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        set_config("logo_file_id", file_id)
        await update.message.reply_text(
            f"✅ Logo guardado correctamente.\nFile ID: `{file_id}`",
            reply_markup=botones_volver(),
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text("⚠️ Debes enviar una foto. Intenta de nuevo:")
        return SET_LOGO_WAIT


async def proforma_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    repuesto = context.user_data.get("repuesto_compartir")
    if not repuesto:
        await edit_mensaje(query, "❌ No hay repuesto seleccionado.", reply_markup=botones_volver())
        return VIEW_ITEM

    fotos = [repuesto[f"file_id_{n}"] for n in range(1, 5) if repuesto[f"file_id_{n}"]]
    if not fotos:
        await edit_mensaje(query, "❌ El repuesto no tiene fotos.", reply_markup=botones_volver())
        return VIEW_ITEM

    try:
        from pdf_proforma import generar_proforma
        ruta = generar_proforma(repuesto, fotos)

        chat_id = query.message.chat_id
        with open(ruta, "rb") as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=f,
                filename=f"proforma_{repuesto['codigo']}.pdf",
                caption=f"📄 Proforma: {repuesto['nombre']} ({repuesto['codigo']})",
            )

        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Proforma generada y enviada. Para compartirla: mantén presionado el documento → compartir → elige la app (WhatsApp, Signal, correo, etc.)",
            reply_markup=botones_volver(),
        )

        import os
        os.remove(ruta)
    except Exception as e:
        await context.bot.send_message(query.message.chat_id, f"❌ Error generando proforma: {e}")

    return VIEW_ITEM


VIEW_ITEM = "VIEW_ITEM"  # placeholder

setlogo_handler = ConversationHandler(
    entry_points=[CommandHandler("setlogo", set_logo_cmd)],
    states={SET_LOGO_WAIT: [MessageHandler(filters.PHOTO, receive_logo)]},
    fallbacks=[CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$")],
)

proforma_callback_handler = CallbackQueryHandler(proforma_callback, pattern="^proforma$")