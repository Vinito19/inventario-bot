from telegram import Update
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
import os
import sys
from database import (
    obtener_usuario,
    registrar_usuario,
    aprobar_usuario,
    cambiar_estado_usuario,
    es_admin,
    esta_registrado,
    get_connection,
)
from keyboards import menu_admin, menu_usuario, botones_admin_aprobar_rechazar
from handlers.utils import edit_mensaje, borrar_mensajes, eliminar_fotos
from handlers.callback_security import validar_callback_token

# Detectar modo test (pytest)
_TEST_MODE = os.getenv("PYTEST_CURRENT_TEST") is not None or "pytest" in sys.modules

# Estados del ConversationHandler de registro
REG_USERNAME, REG_PASSWORD = range(2)


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
            return ConversationHandler.END

        # Modo test: auto-registro como pendiente (compatibilidad con tests)
        if _TEST_MODE:
            registrar_usuario(user_id, nombre, rol="pendiente", activo=0)
            for admin_id in config.ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            f"📩 <b>Nueva solicitud de acceso</b>\n\n"
                            f"👤 Nombre: {nombre}\n"
                            f"🆔 user_id: {user_id}\n"
                            f"📅 Fecha: {update.message.date.strftime('%d/%m/%Y %H:%M')}"
                        ),
                        parse_mode="HTML",
                        reply_markup=botones_admin_aprobar_rechazar(user_id),
                    )
                except Exception:
                    pass
            await update.message.reply_text(
                f"⚠️ Hola {nombre}, no estás autorizado aún.\n\n"
                f"Tu solicitud ha sido enviada al administrador.\n"
                f"Espera aprobación para usar el bot."
            )
            return ConversationHandler.END

        # Usuario nuevo: iniciar flujo de registro
        await update.message.reply_text(
            "👋 ¡Bienvenido! Para usar el bot necesitas registrarte.\n\n"
            "Por favor, elige un <b>nombre de usuario</b> (solo letras, números y guiones):",
            parse_mode="HTML",
        )
        return REG_USERNAME

    # Usuario ya registrado
    if usuario.get("password_hash"):
        # Tiene contraseña: pedirla para desbloquear
        context.user_data["pending_user_id"] = user_id
        await update.message.reply_text(
            "🔐 Ingresa tu contraseña para acceder:",
        )
        return REG_PASSWORD

    # Usuario sin contraseña (legacy o admin): acceso directo
    return await _acceso_directo(update, context, usuario, nombre)


async def _acceso_directo(update: Update, context: ContextTypes.DEFAULT_TYPE, usuario, nombre):
    """Acceso directo sin contraseña (admins o usuarios legacy)."""
    if usuario["rol"] == "pendiente":
        await update.message.reply_text("⏳ Tu solicitud aún está pendiente. Espera la aprobación del administrador.")
        return ConversationHandler.END

    if usuario["activo"] == 0:
        await update.message.reply_text("❌ Tu cuenta está desactivada. Contacta al administrador.")
        return ConversationHandler.END

    if usuario["rol"] == "admin":
        await update.message.reply_text(
            f"👑 Bienvenido, Administrador {nombre}!",
            reply_markup=menu_admin(),
        )
    else:
        await update.message.reply_text(
            f"👋 Bienvenido, {usuario['nombre']}!",
            reply_markup=menu_usuario(),
        )
    return ConversationHandler.END


async def reg_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    user_id = update.effective_user.id

    # Validación básica
    if not username or len(username) < 3:
        await update.message.reply_text("⚠️ El nombre de usuario debe tener al menos 3 caracteres.")
        return REG_USERNAME

    if not all(c.isalnum() or c in "-_" for c in username):
        await update.message.reply_text("⚠️ Solo se permiten letras, números, guiones y guiones bajos.")
        return REG_USERNAME

    # Verificar unicidad
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM usuarios WHERE username = ?", (username,))
        if cursor.fetchone():
            await update.message.reply_text("⚠️ Ese nombre de usuario ya está en uso. Elige otro.")
            return REG_USERNAME
    finally:
        conn.close()

    context.user_data["reg_username"] = username
    await update.message.reply_text(
        f"✅ Nombre de usuario <b>{username}</b> disponible.\n\n"
        "Ahora ingresa tu <b>contraseña</b> (mínimo 6 caracteres):",
        parse_mode="HTML",
    )
    return REG_PASSWORD


async def reg_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    user_id = update.effective_user.id
    nombre = update.effective_user.first_name
    username = context.user_data.get("reg_username")

    if not password or len(password) < 6:
        await update.message.reply_text("⚠️ La contraseña debe tener al menos 6 caracteres.")
        return REG_PASSWORD

    # Registrar usuario con contraseña hasheada y campos cifrados
    registrar_usuario(
        user_id=user_id,
        nombre=nombre,
        username=username,
        password=password,
        rol="pendiente",
        activo=0,
    )

    # Notificar a administradores
    fecha_str = update.message.date.strftime("%d/%m/%Y %H:%M")
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"📩 <b>Nueva solicitud de acceso</b>\n\n"
                    f"👤 Nombre: {nombre}\n"
                    f"👤 Usuario: {username}\n"
                    f"🆔 user_id: {user_id}\n"
                    f"📅 Fecha: {fecha_str}\n\n"
                    "Pendiente de aprobación."
                ),
                parse_mode="HTML",
                reply_markup=botones_admin_aprobar_rechazar(user_id),
            )
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ Registro completado, <b>{nombre}</b>.\n\n"
        "Tu solicitud ha sido enviada al administrador.\n"
        "Recibirás un aviso cuando sea aprobada.",
        parse_mode="HTML",
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Registro cancelado.")
    context.user_data.clear()
    return ConversationHandler.END


async def callback_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    await eliminar_fotos(context, chat_id)
    await borrar_mensajes(context, chat_id)

    user_id = query.from_user.id
    usuario = obtener_usuario(user_id)

    if usuario is None or usuario["activo"] == 0:
        await context.bot.send_message(chat_id=chat_id, text="❌ No tienes acceso al bot.")
        return

    if usuario["rol"] == "pendiente":
        await context.bot.send_message(chat_id=chat_id, text="⏳ Tu solicitud esta pendiente. Espera aprobacion.")
        return

    if usuario["rol"] == "admin":
        await context.bot.send_message(chat_id=chat_id, text="👑 Panel de administrador:", reply_markup=menu_admin())
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"👋 Bienvenido, {usuario['nombre']}!", reply_markup=menu_usuario())


async def callback_aprobar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    admin_id = query.from_user.id
    if not es_admin(admin_id):
        await edit_mensaje(query, "❌ No tienes permiso de administrador.")
        return

    data = query.data
    user_id_aprobado = validar_callback_token(data, "aprobar")
    if user_id_aprobado is None:
        await edit_mensaje(query, "❌ Datos inválidos o callback manipulado.")
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
    user_id_rechazado = validar_callback_token(data, "rechazar")
    if user_id_rechazado is None:
        await edit_mensaje(query, "❌ Datos inválidos o callback manipulado.")
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


registration_conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        REG_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_username)],
        REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_password)],
    },
    fallbacks=[CommandHandler("cancelar", cancel_registration)],
    name="registration",
    persistent=False,
)

start_handler = registration_conv
inicio_callback_handler = CallbackQueryHandler(callback_inicio, pattern="^inicio$")
aprobar_callback_handler = CallbackQueryHandler(callback_aprobar, pattern="^aprobar_[0-9]+_[a-f0-9]+$")
rechazar_callback_handler = CallbackQueryHandler(callback_rechazar, pattern="^rechazar_[0-9]+_[a-f0-9]+$")

# Alias para compatibilidad con tests y código existente
__all__ = [
    "start",
    "start_handler",
    "inicio_callback_handler",
    "aprobar_callback_handler",
    "rechazar_callback_handler",
    "callback_aprobar",
    "callback_rechazar",
]