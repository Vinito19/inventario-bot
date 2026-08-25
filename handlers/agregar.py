from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from database import (
    obtener_categoria_por_nombre,
    obtener_categorias,
    agregar_repuesto,
    obtener_repuesto,
    esta_registrado,
    es_admin,
)
from keyboards import menu_categorias, menu_confirmar, botones_volver
from handlers.utils import finalizar, edit_mensaje, guardar_mensaje, eliminar_fotos

SELECT_CATEGORY, PHOTO_1, PHOTO_2, PHOTO_3, PHOTO_4, CODIGO, NOMBRE, DESCRIPCION, CANTIDAD, PRECIO, UBICACION, CONFIRMAR = range(12)

FILTRO_IMAGEN = filters.PHOTO | filters.Document.IMAGE


def obtener_file_id(update: Update):
    if update.message.photo:
        return update.message.photo[-1].file_id
    if update.message.document:
        return update.message.document.file_id
    return None


async def no_es_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ Debes enviar una imagen (foto). Intenta de nuevo:",
        reply_markup=botones_volver(),
    )


async def start_agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not esta_registrado(user_id):
        await update.message.reply_text("❌ No tienes acceso al bot.")
        return ConversationHandler.END

    categorias = obtener_categorias()
    if not categorias:
        await update.message.reply_text(
            "⚠️ No hay categorías creadas. Primero crea una categoría con /categorias.",
            reply_markup=botones_volver(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "📦 AGREGAR NUEVO REPUESTO\n\n"
        "Selecciona la categoría del repuesto:",
        reply_markup=menu_categorias(categorias, puede_agregar=es_admin(user_id)),
    )
    return SELECT_CATEGORY


async def callback_agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not esta_registrado(user_id):
        await edit_mensaje(query, "❌ No tienes acceso al bot.")
        return ConversationHandler.END

    categorias = obtener_categorias()
    if not categorias:
        await edit_mensaje(
            query,
            "⚠️ No hay categorías creadas. Primero crea una categoría con /categorias.",
            reply_markup=botones_volver(),
        )
        return ConversationHandler.END

    await edit_mensaje(
        query,
        "📦 AGREGAR NUEVO REPUESTO\n\n"
        "Selecciona la categoría del repuesto:",
        reply_markup=menu_categorias(categorias, puede_agregar=es_admin(user_id)),
    )
    return SELECT_CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "cancelar":
        await edit_mensaje(query, "❌ Operación cancelada.", reply_markup=botones_volver())
        return ConversationHandler.END

    if data == "agregar_categoria":
        await edit_mensaje(
            query,
            "📝 Escribe el nombre de la nueva categoría:",
            reply_markup=botones_volver(),
        )
        return SELECT_CATEGORY

    if data.startswith("cat_"):
        try:
            cat_id = int(data.replace("cat_", ""))
        except ValueError:
            categorias = obtener_categorias()
            admin = es_admin(query.from_user.id)
            await edit_mensaje(query, "⚠️ Opción no válida. Intenta de nuevo:", reply_markup=menu_categorias(categorias, puede_agregar=admin))
            return SELECT_CATEGORY
        context.user_data["categoria_id"] = cat_id
        await edit_mensaje(
            query,
            "📷 Foto 1 de 4: Imagen principal\n\n"
            "Envía la foto principal del repuesto.\n"
            "(Ejemplo: vista completa del producto)\n\n"
            "━━━━━━━━━━░░░░░░░░░░░░ 25%",
            reply_markup=botones_volver(),
        )
        return PHOTO_1

    categorias = obtener_categorias()
    admin = es_admin(query.from_user.id)
    await edit_mensaje(query, "⚠️ Opción no válida. Intenta de nuevo:", reply_markup=menu_categorias(categorias, puede_agregar=admin))
    return SELECT_CATEGORY


async def nuevo_nombre_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not es_admin(user_id):
        categorias = obtener_categorias()
        await update.message.reply_text(
            "❌ Solo el administrador puede agregar categorías.",
            reply_markup=menu_categorias(categorias) if categorias else botones_volver(),
        )
        return SELECT_CATEGORY

    nombre = update.message.text.strip()
    if not nombre:
        await update.message.reply_text("⚠️ El nombre no puede estar vacío. Intenta de nuevo:")
        return SELECT_CATEGORY

    existente = obtener_categoria_por_nombre(nombre)
    if existente:
        await update.message.reply_text("⚠️ Ya existe una categoría con ese nombre. Intenta con otro:")
        return SELECT_CATEGORY

    from database import agregar_categoria
    agregar_categoria(nombre)

    categorias = obtener_categorias()
    await update.message.reply_text(
        f"✅ Categoría '{nombre}' creada correctamente.\n\n"
        f"Selecciona la categoría del repuesto:",
        reply_markup=menu_categorias(categorias),
    )
    return SELECT_CATEGORY


async def photo_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = obtener_file_id(update)
    if file_id:
        context.user_data["file_ids"] = [file_id]
        msg = await update.message.reply_text(
            "✅ Foto 1 recibida\n\n"
            "📷 Foto 2 de 4: Vista lateral\n\n"
            "Envía la vista lateral del repuesto.\n\n"
            "━━━━━━━━━━━━━━━━━━░░░░░░ 50%",
            reply_markup=botones_volver(),
        )
        guardar_mensaje(update, context, msg)
        return PHOTO_2

    msg = await update.message.reply_text("⚠️ Debes enviar una imagen. Intenta de nuevo:")
    guardar_mensaje(update, context, msg)
    return PHOTO_1


async def photo_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = obtener_file_id(update)
    if file_id:
        context.user_data["file_ids"].append(file_id)
        msg = await update.message.reply_text(
            "✅ Foto 2 recibida\n\n"
            "📷 Foto 3 de 4: Detalle/número de parte\n\n"
            "Envía foto del detalle o número de parte visible.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━░░ 75%",
            reply_markup=botones_volver(),
        )
        guardar_mensaje(update, context, msg)
        return PHOTO_3

    msg = await update.message.reply_text("⚠️ Debes enviar una imagen. Intenta de nuevo:")
    guardar_mensaje(update, context, msg)
    return PHOTO_2


async def photo_3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = obtener_file_id(update)
    if file_id:
        context.user_data["file_ids"].append(file_id)
        msg = await update.message.reply_text(
            "✅ Foto 3 recibida\n\n"
            "📷 Foto 4 de 4: Otra vista\n\n"
            "Envía la última foto del repuesto.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%",
            reply_markup=botones_volver(),
        )
        guardar_mensaje(update, context, msg)
        return PHOTO_4

    msg = await update.message.reply_text("⚠️ Debes enviar una imagen. Intenta de nuevo:")
    guardar_mensaje(update, context, msg)
    return PHOTO_3


async def photo_4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = obtener_file_id(update)
    if file_id:
        context.user_data["file_ids"].append(file_id)
        msg = await update.message.reply_text(
            "✅ 4 fotos recibidas correctamente\n\n"
            "📝 Escribe el CÓDIGO del repuesto:\n"
            "(Ejemplo: BRK-001)",
            reply_markup=botones_volver(),
        )
        guardar_mensaje(update, context, msg)
        return CODIGO

    msg = await update.message.reply_text("⚠️ Debes enviar una imagen. Intenta de nuevo:")
    guardar_mensaje(update, context, msg)
    return PHOTO_4


async def codigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    codigo_texto = update.message.text.strip()
    if not codigo_texto:
        msg = await update.message.reply_text("⚠️ El código no puede estar vacío. Intenta de nuevo:")
        guardar_mensaje(update, context, msg)
        return CODIGO

    existente = obtener_repuesto(codigo_texto)
    if existente:
        msg = await update.message.reply_text(
            f"⚠️ Ya existe un repuesto con el código '{codigo_texto}'.\n"
            f"Intenta con otro código:"
        )
        guardar_mensaje(update, context, msg)
        return CODIGO

    context.user_data["codigo"] = codigo_texto
    msg = await update.message.reply_text(
        f"✅ Código: {codigo_texto}\n\n"
        f"📝 Escribe el NOMBRE del repuesto:\n"
        f"(Ejemplo: Pastillas de freno)",
        reply_markup=botones_volver(),
    )
    guardar_mensaje(update, context, msg)
    return NOMBRE


async def nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre_texto = update.message.text.strip()
    if not nombre_texto:
        msg = await update.message.reply_text("⚠️ El nombre no puede estar vacío. Intenta de nuevo:")
        guardar_mensaje(update, context, msg)
        return NOMBRE

    context.user_data["nombre"] = nombre_texto
    msg = await update.message.reply_text(
        f"✅ Nombre: {nombre_texto}\n\n"
        f"📝 Escribe la DESCRIPCIÓN:\n"
        f"(Ejemplo: Pastillas cerámicas universales 2020-2024)",
        reply_markup=botones_volver(),
    )
    guardar_mensaje(update, context, msg)
    return DESCRIPCION


async def descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto:
        msg = await update.message.reply_text("⚠️ La descripción no puede estar vacía. Intenta de nuevo:")
        guardar_mensaje(update, context, msg)
        return DESCRIPCION
    context.user_data["descripcion"] = texto
    msg = await update.message.reply_text(
        "📝 Escribe la CANTIDAD en stock:\n"
        "(Solo números)",
        reply_markup=botones_volver(),
    )
    guardar_mensaje(update, context, msg)
    return CANTIDAD


async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto.isdigit():
        msg = await update.message.reply_text("⚠️ Debes escribir un número entero. Intenta de nuevo:")
        guardar_mensaje(update, context, msg)
        return CANTIDAD

    context.user_data["cantidad"] = int(texto)
    msg = await update.message.reply_text(
        f"✅ Cantidad: {texto}\n\n"
        f"📝 Escribe el PRECIO:\n"
        f"(Ejemplo: 185.00)",
        reply_markup=botones_volver(),
    )
    guardar_mensaje(update, context, msg)
    return PRECIO


async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    try:
        precio_valor = float(texto)
    except ValueError:
        msg = await update.message.reply_text("⚠️ Debes escribir un número válido. Intenta de nuevo:")
        guardar_mensaje(update, context, msg)
        return PRECIO

    context.user_data["precio"] = precio_valor
    msg = await update.message.reply_text(
        f"✅ Precio: ${precio_valor:.2f}\n\n"
        f"📝 Escribe la UBICACIÓN:\n"
        f"(Ejemplo: Estante A-3)",
        reply_markup=botones_volver(),
    )
    guardar_mensaje(update, context, msg)
    return UBICACION


async def ubicacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto:
        msg = await update.message.reply_text("⚠️ La ubicación no puede estar vacía. Intenta de nuevo:")
        guardar_mensaje(update, context, msg)
        return UBICACION
    context.user_data["ubicacion"] = texto

    ud = context.user_data
    categorias = obtener_categorias()
    cat_nombre = "Sin categoría"
    for c in categorias:
        if c["id"] == ud["categoria_id"]:
            cat_nombre = c["nombre"]
            break

    resumen = (
        "📋 RESUMEN DEL REPUESTO\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Categoría:  📂 {cat_nombre}\n"
        f"Código:      {ud['codigo']}\n"
        f"Nombre:      {ud['nombre']}\n"
        f"Descripción: {ud['descripcion']}\n"
        f"Cantidad:    {ud['cantidad']} unidades\n"
        f"Precio:      ${ud['precio']:.2f}\n"
        f"Ubicación:   {ud['ubicacion']}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📷 4 fotos adjuntas\n\n"
        "¿Confirmar registro?"
    )

    context.user_data["photo_msg_ids"] = []
    for i, file_id in enumerate(ud["file_ids"], 1):
        try:
            if i == 1:
                msg = await update.message.reply_photo(photo=file_id, caption=resumen, reply_markup=menu_confirmar())
            else:
                msg = await update.message.reply_photo(photo=file_id)
            context.user_data["photo_msg_ids"].append(msg.message_id)
        except Exception:
            if i == 1:
                msg = await update.message.reply_text(resumen, reply_markup=menu_confirmar())
                context.user_data["photo_msg_ids"].append(msg.message_id)

    return CONFIRMAR


async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar":
        await edit_mensaje(query, "❌ Registro cancelado.", reply_markup=botones_volver())
        context.user_data.clear()
        return ConversationHandler.END

    if query.data == "confirmar":
        ud = context.user_data
        try:
            agregar_repuesto(
                codigo=ud["codigo"],
                nombre=ud["nombre"],
                descripcion=ud["descripcion"],
                cantidad=ud["cantidad"],
                precio=ud["precio"],
                file_ids=ud["file_ids"],
                categoria_id=ud["categoria_id"],
                ubicacion=ud["ubicacion"],
            )
            await eliminar_fotos(context)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=(
                    "✅ Repuesto registrado correctamente!\n\n"
                    f"🏷️ Código: {ud['codigo']}\n"
                    f"📝 Nombre: {ud['nombre']}\n"
                    f"📦 Cantidad: {ud['cantidad']}\n"
                    f"💰 Precio: ${ud['precio']:.2f}"
                ),
                reply_markup=botones_volver(),
            )
        except Exception as e:
            await edit_mensaje(
                query,
                f"❌ Error al guardar: {str(e)}",
                reply_markup=botones_volver(),
            )
        context.user_data.clear()
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operación cancelada.", reply_markup=botones_volver())
    context.user_data.clear()
    return ConversationHandler.END


async def callback_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await eliminar_fotos(context)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="❌ Operación cancelada.",
        reply_markup=botones_volver(),
    )
    context.user_data.clear()
    return ConversationHandler.END


agregar_handler = ConversationHandler(
    entry_points=[
        CommandHandler("agregar", start_agregar),
        CallbackQueryHandler(callback_agregar, pattern="^agregar$"),
    ],
    states={
        SELECT_CATEGORY: [
            CallbackQueryHandler(select_category, pattern="^(cat_[0-9]+|cancelar|agregar_categoria)$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_nombre_categoria),
        ],
        PHOTO_1: [
            MessageHandler(FILTRO_IMAGEN, photo_1),
            MessageHandler(filters.ALL & ~filters.COMMAND, no_es_imagen),
        ],
        PHOTO_2: [
            MessageHandler(FILTRO_IMAGEN, photo_2),
            MessageHandler(filters.ALL & ~filters.COMMAND, no_es_imagen),
        ],
        PHOTO_3: [
            MessageHandler(FILTRO_IMAGEN, photo_3),
            MessageHandler(filters.ALL & ~filters.COMMAND, no_es_imagen),
        ],
        PHOTO_4: [
            MessageHandler(FILTRO_IMAGEN, photo_4),
            MessageHandler(filters.ALL & ~filters.COMMAND, no_es_imagen),
        ],
        CODIGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, codigo)],
        NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nombre)],
        DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, descripcion)],
        CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad)],
        PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio)],
        UBICACION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ubicacion)],
        CONFIRMAR: [CallbackQueryHandler(confirmar, pattern="^(confirmar|cancelar)$")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$"),
    ],
)