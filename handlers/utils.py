from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import obtener_usuario
from keyboards import menu_admin, menu_usuario


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

    user_id = query.from_user.id
    usuario = obtener_usuario(user_id)

    if query.data == "inicio":
        if usuario and usuario["rol"] == "admin" and usuario["activo"] == 1:
            await edit_mensaje(query, "👑 Panel de administrador:", reply_markup=menu_admin())
        elif usuario and usuario["activo"] == 1:
            await edit_mensaje(query, f"👋 Bienvenido, {usuario['nombre']}!", reply_markup=menu_usuario())
        else:
            await edit_mensaje(query, "❌ No tienes acceso al bot.")
    else:
        await edit_mensaje(query, "❌ Operación cancelada.")

    return ConversationHandler.END