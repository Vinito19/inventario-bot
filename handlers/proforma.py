import os
import tempfile
import shutil
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from database import (
    es_admin,
    set_config,
)
from keyboards import botones_volver
from handlers.utils import edit_mensaje, finalizar, guardar_mensaje
from pdf_proforma import generar_proforma

SET_LOGO_WAIT = range(1)[0]


# Tipos MIME permitidos y sus magic bytes
ALLOWED_MIME_TYPES = {
    'image/jpeg': [b'\xFF\xD8\xFF'],
    'image/png': [b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'],
    'image/webp': [b'RIFF', b'WEBP'],
}

MIME_EXTENSIONS = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
}


def validar_mime_type(filepath: str) -> str | None:
    """
    Valida el tipo MIME de un archivo leyendo sus magic bytes.
    Retorna el MIME type si es válido, None si no lo es.
    """
    try:
        with open(filepath, 'rb') as f:
            header = f.read(16)
        
        for mime, signatures in ALLOWED_MIME_TYPES.items():
            for sig in signatures:
                if header.startswith(sig):
                    return mime
        
        if len(header) >= 12 and header.startswith(b'RIFF') and header[8:12] == b'WEBP':
            return 'image/webp'
        
        return None
    except Exception:
        return None


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
        archivo = await context.bot.get_file(file_id)
        
        # Descargar a archivo temporal primero
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
            tmp_path = tmp.name
            await archivo.download_to_drive(tmp_path)
        
        try:
            # Validar tipo MIME por magic bytes
            mime = validar_mime_type(tmp_path)
            if not mime:
                os.remove(tmp_path)
                await update.message.reply_text(
                    "⚠️ Formato no permitido. Solo se aceptan imágenes JPG, PNG o WebP.",
                    reply_markup=botones_volver(),
                )
                return SET_LOGO_WAIT
            
            # Determinar extensión correcta
            ext = MIME_EXTENSIONS.get(mime, '.jpg')
            logo_path = os.path.join(os.getcwd(), f"logo_vch{ext}")
            
            # Mover archivo temporal a ubicación final
            shutil.move(tmp_path, logo_path)
            
            set_config("logo_file_id", file_id)
            set_config("logo_path", logo_path)
            
            await update.message.reply_text(
                f"✅ Logo guardado correctamente.\nFile ID: `{file_id}`\nTipo: {mime}\nGuardado en: `{logo_path}`",
                reply_markup=botones_volver(),
            )
            return ConversationHandler.END
        except Exception:
            # Limpieza en caso de error
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
    else:
        await update.message.reply_text("⚠️ Debes enviar una foto. Intenta de nuevo:")
        return SET_LOGO_WAIT


async def proforma_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    repuesto = context.user_data.get("repuesto_compartir")
    if not repuesto:
        await edit_mensaje(query, "❌ No hay repuesto seleccionado.", reply_markup=botones_volver())
        return ConversationHandler.END

    file_ids = [repuesto[f"file_id_{n}"] for n in range(1, 5) if repuesto[f"file_id_{n}"]]
    if not file_ids:
        await edit_mensaje(query, "❌ El repuesto no tiene fotos.", reply_markup=botones_volver())
        return ConversationHandler.END

    temp_paths = []
    try:
        for file_id in file_ids:
            archivo = await context.bot.get_file(file_id)
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            await archivo.download_to_drive(tmp.name)
            temp_paths.append(tmp.name)

        ruta = generar_proforma(repuesto, temp_paths)

        chat_id = query.message.chat_id
        with open(ruta, "rb") as f:
            doc_msg = await context.bot.send_document(
                chat_id=chat_id,
                document=f,
                filename=f"proforma_{repuesto['codigo']}.pdf",
                caption=f"📄 Proforma: {repuesto['nombre']} ({repuesto['codigo']})",
            )
        guardar_mensaje(update, context, doc_msg)

        msg = await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Proforma generada. Para compartirla: abre el documento → pulsa los 3 puntos (⋮) junto al nombre del archivo a la derecha → Compartir → elige la app (WhatsApp, Signal, correo, etc.)",
            reply_markup=botones_volver(),
        )
        guardar_mensaje(update, context, msg)

        os.remove(ruta)
    except Exception as e:
        await context.bot.send_message(query.message.chat_id, f"❌ Error generando proforma: {e}")
    finally:
        for p in temp_paths:
            try:
                os.remove(p)
            except Exception:
                pass

    return ConversationHandler.END


setlogo_handler = ConversationHandler(
    entry_points=[CommandHandler("setlogo", set_logo_cmd)],
    states={SET_LOGO_WAIT: [MessageHandler(filters.PHOTO, receive_logo)]},
    fallbacks=[CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$")],
)

proforma_callback_handler = CallbackQueryHandler(proforma_callback, pattern="^proforma$")