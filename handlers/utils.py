from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import obtener_usuario
from keyboards import menu_admin, menu_usuario


def guardar_mensaje(update_or_msg, context, msg):
    if msg and hasattr(msg, "message_id"):
        context.user_data.setdefault("msgs", []).append(msg.message_id)


async def borrar_mensajes(context: ContextTypes.DEFAULT_TYPE, chat_id=None):
    ids = context.user_data.pop("msgs", [])
    cid = chat_id or getattr(context, "_chat_id", None)
    if not cid:
        return
    for mid in ids:
        try:
            await context.bot.delete_message(chat_id=cid, message_id=mid)
        except Exception:
            pass


async def eliminar_fotos(context: ContextTypes.DEFAULT_TYPE, chat_id=None):
    ids = context.user_data.pop("photo_msg_ids", [])
    cid = chat_id or getattr(context, "_chat_id", None)
    if not cid:
        return
    for mid in ids:
        try:
            await context.bot.delete_message(chat_id=cid, message_id=mid)
        except Exception:
            pass


async def edit_mensaje(query, texto, reply_markup=None):
    if query.message is None:
        return
    if query.message.photo:
        return await query.edit_message_caption(caption=texto, reply_markup=reply_markup)
    return await query.edit_message_text(texto, reply_markup=reply_markup)


async def finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    await eliminar_fotos(context, chat_id)
    await borrar_mensajes(context, chat_id)

    user_id = query.from_user.id
    usuario = obtener_usuario(user_id)

    if query.data == "inicio":
        if usuario and usuario["rol"] == "admin" and usuario["activo"] == 1:
            await context.bot.send_message(chat_id=chat_id, text="Panel de administrador:", reply_markup=menu_admin())
        elif usuario and usuario["activo"] == 1:
            await context.bot.send_message(chat_id=chat_id, text=f"Bienvenido, {usuario['nombre']}!", reply_markup=menu_usuario())
        else:
            await context.bot.send_message(chat_id=chat_id, text="No tienes acceso al bot.")
    else:
        await context.bot.send_message(chat_id=chat_id, text="Operacion cancelada.")

    return ConversationHandler.END