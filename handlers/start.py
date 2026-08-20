from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

import config
from database import obtener_usuario, registrar_usuario, aprobar_usuario, cambiar_estado_usuario, es_admin
from keyboards import menu_admin, menu_usuario, botones_admin_aprobar_rechazar
from handlers.utils import edit_mensaje


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    nombre = user.first_name

    usuario = obtener_usuario(user_id)

    if usuario is None:
        if user_id in config.ADMIN_IDS:
            registrar_usuario(user_id, nombre, rol="admin", activo=1)
            await update.message.reply_text(
                f"👑 Bienvenido, Administrador {nombre}!\n\nYa puedes usar el bot de inventario.",
                reply_markup=menu_admin(),
            )
            return

        registrar_usuario(user_id, nombre, rol="pendiente", activo=0)
        await update.message.reply_text(
            f"⚠️ Hola {nombre}, no estás autorizado aún.\n\n"
            f"Tu solicitud ha sido enviada al administrador.\n"
            f"Espera aprobación para usar el bot."
        )

        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"📩 Nueva solicitud de acceso:\n\n"
                        f"👤 Nombre: {nombre}\n"
                        f"🆔 user_id: {user_id}\n"
                        f"📅 Fecha: {update.message.date.strftime('%d/%m/%Y %H:%M')}"
                    ),
                    reply_markup=botones_admin_aprobar_rechazar(user_id),
                )
            except Exception:
                pass
        return

    if usuario["rol"] == "pendiente":
        await update.message.reply_text("⏳ Tu solicitud aún está pendiente. Espera la aprobación del administrador.")
        return

    if usuario["activo"] == 0:
        await update.message.reply_text("❌ Tu cuenta está desactivada. Contacta al administrador.")
        return

    if usuario["rol"] == "admin":
        await update.message.reply_text(
            f"👑 Bienvenido, Administrador {nombre}!",
            reply_markup=menu_admin(),
        )
    else:
        await update.message.reply_text(
            f"👋 Bienvenido, {nombre}!",
            reply_markup=menu_usuario(),
        )


async def callback_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    usuario = obtener_usuario(user_id)

    if usuario is None or usuario["activo"] == 0:
        await edit_mensaje(query, "❌ No tienes acceso al bot.")
        return

    if usuario["rol"] == "pendiente":
        await edit_mensaje(query, "⏳ Tu solicitud esta pendiente. Espera aprobacion.")
        return

    if usuario["rol"] == "admin":
        await edit_mensaje(query, "👑 Panel de administrador:", reply_markup=menu_admin())
    else:
        await edit_mensaje(query, f"👋 Bienvenido, {usuario['nombre']}!", reply_markup=menu_usuario())


async def callback_aprobar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    admin_id = query.from_user.id
    if not es_admin(admin_id):
        await edit_mensaje(query, "❌ No tienes permiso de administrador.")
        return

    data = query.data
    try:
        user_id_aprobado = int(data.replace("aprobar_", ""))
    except ValueError:
        await edit_mensaje(query, "❌ Datos inválidos.")
        return

    usuario = obtener_usuario(user_id_aprobado)
    if usuario is None:
        await edit_mensaje(query, "❌ Usuario no encontrado.")
        return

    aprobar_usuario(user_id_aprobado)

    await edit_mensaje(query, f"✅ {usuario['nombre']} ha sido aprobado.")

    try:
        await context.bot.send_message(
            chat_id=user_id_aprobado,
            text=f"🎉 ¡Bienvenido, {usuario['nombre']}!\n\nYa tienes acceso al bot de inventario.",
            reply_markup=menu_usuario(),
        )
    except Exception:
        pass


async def callback_rechazar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    admin_id = query.from_user.id
    if not es_admin(admin_id):
        await edit_mensaje(query, "❌ No tienes permiso de administrador.")
        return

    data = query.data
    try:
        user_id_rechazado = int(data.replace("rechazar_", ""))
    except ValueError:
        await edit_mensaje(query, "❌ Datos inválidos.")
        return

    usuario = obtener_usuario(user_id_rechazado)
    if usuario is None:
        await edit_mensaje(query, "❌ Usuario no encontrado.")
        return

    cambiar_estado_usuario(user_id_rechazado, 0)

    await edit_mensaje(query, f"❌ Solicitud de {usuario['nombre']} rechazada.")

    try:
        await context.bot.send_message(
            chat_id=user_id_rechazado,
            text="❌ Tu solicitud de acceso ha sido rechazada por el administrador.",
        )
    except Exception:
        pass


start_handler = CommandHandler("start", start)
inicio_callback_handler = CallbackQueryHandler(callback_inicio, pattern="^inicio$")
aprobar_callback_handler = CallbackQueryHandler(callback_aprobar, pattern="^aprobar_$")
rechazar_callback_handler = CallbackQueryHandler(callback_rechazar, pattern="^rechazar_$")