from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from database import (
    obtener_usuarios,
    obtener_usuario,
    eliminar_usuario_db,
    cambiar_estado_usuario,
    es_admin,
    contar_admins_activos,
)
from keyboards import botones_usuarios, botones_detalle_usuario, botones_volver
from handlers.utils import finalizar, edit_mensaje

ADD_USER_ID, ADD_USER_NAME, CONFIRMAR_DELETE = range(3)


async def start_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not es_admin(user_id):
        await update.message.reply_text("❌ Solo el administrador puede gestionar usuarios.")
        return ConversationHandler.END

    usuarios = obtener_usuarios()
    texto = "👤 USUARIOS REGISTRADOS\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for u in usuarios:
        rol = "👑 Admin" if u["rol"] == "admin" else "👤 Usuario"
        estado = "✅" if u["activo"] else "❌"
        texto += f"• {u['nombre']} ({u['user_id']}) - {rol} {estado}\n"

    texto += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    await update.message.reply_text(texto, reply_markup=botones_usuarios(usuarios))
    return CONFIRMAR_DELETE


async def callback_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not es_admin(user_id):
        await edit_mensaje(query, "❌ Solo el administrador puede gestionar usuarios.")
        return ConversationHandler.END

    usuarios = obtener_usuarios()
    texto = "👤 USUARIOS REGISTRADOS\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for u in usuarios:
        rol = "👑 Admin" if u["rol"] == "admin" else "👤 Usuario"
        estado = "✅" if u["activo"] else "❌"
        texto += f"• {u['nombre']} ({u['user_id']}) - {rol} {estado}\n"

    texto += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    await edit_mensaje(query, texto, reply_markup=botones_usuarios(usuarios))
    return CONFIRMAR_DELETE


async def agregar_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not es_admin(user_id):
        await edit_mensaje(query, "❌ Solo el administrador puede agregar usuarios.")
        return ConversationHandler.END

    await edit_mensaje(
        query,
        "👤 AGREGAR NUEVO USUARIO\n\n"
        "Escribe el user_id del nuevo usuario:",
        reply_markup=botones_volver(),
    )
    return ADD_USER_ID


async def add_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    if not es_admin(user_id_admin):
        await update.message.reply_text("❌ Solo el administrador puede agregar usuarios.")
        return ConversationHandler.END

    texto = update.message.text.strip()
    if not texto.isdigit():
        await update.message.reply_text("⚠️ El user_id debe ser un número. Intenta de nuevo:")
        return ADD_USER_ID

    nuevo_user_id = int(texto)
    existente = obtener_usuario(nuevo_user_id)
    if existente:
        await update.message.reply_text(
            f"⚠️ El usuario {nuevo_user_id} ya está registrado.\n"
            f"Intenta con otro user_id:"
        )
        return ADD_USER_ID

    context.user_data["nuevo_user_id"] = nuevo_user_id
    await update.message.reply_text(
        f"✅ user_id: {nuevo_user_id}\n\n"
        f"📝 Escribe el nombre del nuevo usuario:",
        reply_markup=botones_volver(),
    )
    return ADD_USER_NAME


async def add_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_admin = update.effective_user.id
    if not es_admin(user_id_admin):
        await update.message.reply_text("❌ Solo el administrador puede agregar usuarios.")
        return ConversationHandler.END

    nombre = update.message.text.strip()
    if not nombre:
        await update.message.reply_text("⚠️ El nombre no puede estar vacío. Intenta de nuevo:")
        return ADD_USER_NAME

    nuevo_user_id = context.user_data["nuevo_user_id"]

    from database import registrar_usuario
    registrar_usuario(nuevo_user_id, nombre, rol="usuario", activo=1)

    await update.message.reply_text(
        f"✅ Usuario agregado correctamente!\n\n"
        f"👤 Nombre: {nombre}\n"
        f"🆔 user_id: {nuevo_user_id}\n"
        f"🔑 Rol: usuario",
        reply_markup=botones_volver(),
    )

    try:
        await context.bot.send_message(
            chat_id=nuevo_user_id,
            text=f"🎉 ¡Bienvenido, {nombre}!\n\nYa tienes acceso al bot de inventario.",
        )
    except Exception:
        pass

    return ConversationHandler.END


async def ver_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id_admin = query.from_user.id
    if not es_admin(user_id_admin):
        await edit_mensaje(query, "❌ Solo el administrador puede ver detalles de usuarios.")
        return ConversationHandler.END

    data = query.data
    if data.startswith("ver_user_"):
        user_id_ver = int(data.replace("ver_user_", ""))
        usuario = obtener_usuario(user_id_ver)

        if not usuario:
            await edit_mensaje(query, "❌ Usuario no encontrado.", reply_markup=botones_volver())
            return ConversationHandler.END

        rol = "👑 Admin" if usuario["rol"] == "admin" else "👤 Usuario"
        estado = "✅ Activo" if usuario["activo"] else "❌ Desactivado"

        texto = (
            f"👤 DETALLE DEL USUARIO\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Nombre: {usuario['nombre']}\n"
            f"🆔 user_id: {usuario['user_id']}\n"
            f"🔑 Rol: {rol}\n"
            f"📊 Estado: {estado}\n"
            f"📅 Registro: {usuario['fecha']}"
        )

        if usuario["user_id"] == user_id_admin:
            await edit_mensaje(
                query,
                texto + "\n\n⚠️ No puedes eliminarte a ti mismo.",
                reply_markup=botones_volver(),
            )
        else:
            await edit_mensaje(query, texto, reply_markup=botones_detalle_usuario(usuario))

        return CONFIRMAR_DELETE

    return CONFIRMAR_DELETE


async def eliminar_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id_admin = query.from_user.id
    if not es_admin(user_id_admin):
        await edit_mensaje(query, "❌ Solo el administrador puede eliminar usuarios.")
        return ConversationHandler.END

    data = query.data
    if data.startswith("eliminar_usuario_"):
        user_id_eliminar = int(data.replace("eliminar_usuario_", ""))

        if user_id_eliminar == user_id_admin:
            await edit_mensaje(
                query,
                "⚠️ No puedes eliminarte a ti mismo.",
                reply_markup=botones_volver(),
            )
            return ConversationHandler.END

        usuario = obtener_usuario(user_id_eliminar)
        if not usuario:
            await edit_mensaje(query, "❌ Usuario no encontrado.", reply_markup=botones_volver())
            return ConversationHandler.END

        if usuario["rol"] == "admin" and usuario["activo"] == 1:
            admin_count = contar_admins_activos()
            if admin_count <= 1:
                await edit_mensaje(
                    query,
                    "⚠️ No se puede eliminar al ultimo administrador.",
                    reply_markup=botones_volver(),
                )
                return ConversationHandler.END

        eliminar_usuario_db(user_id_eliminar)

        await edit_mensaje(
            query,
            f"✅ Usuario {usuario['nombre']} eliminado.",
            reply_markup=botones_volver(),
        )

        try:
            await context.bot.send_message(
                chat_id=user_id_eliminar,
                text="❌ Tu acceso al bot ha sido revocado por el administrador.",
            )
        except Exception:
            pass

        return ConversationHandler.END

    return CONFIRMAR_DELETE


async def cancel_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operación cancelada.", reply_markup=botones_volver())
    return ConversationHandler.END


usuarios_handler = ConversationHandler(
    entry_points=[
        CommandHandler("usuarios", start_usuarios),
        CallbackQueryHandler(callback_usuarios, pattern="^usuarios$"),
    ],
    states={
        ADD_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_user_id)],
        ADD_USER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_user_name)],
        CONFIRMAR_DELETE: [
            CallbackQueryHandler(
                agregar_usuario,
                pattern="^agregar_usuario$",
            ),
            CallbackQueryHandler(
                ver_usuario,
                pattern="^ver_user_",
            ),
            CallbackQueryHandler(
                eliminar_usuario,
                pattern="^eliminar_usuario_",
            ),
            CallbackQueryHandler(callback_usuarios, pattern="^usuarios$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_usuarios),
        CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$"),
    ],
)