from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import obtener_usuario
from keyboards import menu_admin, menu_usuario


def guardar_mensaje(update_or_msg, context, msg):
    if msg and hasattr(msg, "message_id"):
        context.user_data.setdefault("msgs", []).append(msg.message_id)


async def borrar_mensajes(context: ContextTypes.DEFAULT_TYPE):
    ids = context.user_data.pop("msgs", [])
    chat_id = getattr(context, "_chat_id", None)
    if not chat_id:
        return
    for mid in ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass


async def eliminar_fotos(context: ContextTypes.DEFAULT_TYPE):
    ids = context.user_data.pop("photo_msg_ids", [])
    chat_id = getattr(context, "_chat_id", None)
    if not chat_id:
        return
    for mid in ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass


async def edit_mensaje(query, texto, reply_markup=None):
    if query.message is None:
        return
    if query.message.photo:
        await query.edit_message_caption(caption=texto, reply_markup=reply_markup)
    else:
        await query.edit_message_text(texto, reply_markup=reply_markup)


async def finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await eliminar_fotos(context)
    await borrar_mensajes(context)

    user_id = query.from_user.id
    usuario = obtener_usuario(user_id)

    if query.data == "inicio":
        chat_id = query.message.chat_id
        if usuario and usuario["rol"] == "admin" and usuario["activo"] == 1:
            await context.bot.send_message(chat_id=chat_id, text="👑 Panel de administrador:", reply_markup=menu_admin())
        elif usuario and usuario["activo"] == 1:
            await context.bot.send_message(chat_id=chat_id, text=f"👋 Bienvenido, {usuario['nombre']}!", reply_markup=menu_usuario())
        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ No tienes acceso al bot.")
    else:
        chat_id = query.message.chat_id
        await context.bot.send_message(chat_id=chat_id, text="❌ Operación cancelada.")

    return ConversationHandler.END