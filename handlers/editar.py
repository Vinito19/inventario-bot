from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from database import buscar_repuestos, obtener_repuesto, editar_repuesto, editar_repuesto_fotos, esta_registrado
from keyboards import menu_editar, menu_cantidad, menu_confirmar, botones_volver
from handlers.utils import finalizar, edit_mensaje

SEARCH, SELECT_ITEM, SELECT_FIELD, EDIT_VALUE, CONFIRMAR = range(5)

FILTRO_IMAGEN = filters.PHOTO | filters.Document.IMAGE


async def start_editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not esta_registrado(user_id):
        await update.message.reply_text("❌ No tienes acceso al bot.")
        return ConversationHandler.END

    await update.message.reply_text(
        "✏️ EDITAR REPUESTO\n\n"
        "Escribe el código o nombre del repuesto a editar:",
        reply_markup=botones_volver(),
    )
    return SEARCH


async def callback_editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not esta_registrado(user_id):
        await edit_mensaje(query, "❌ No tienes acceso al bot.")
        return ConversationHandler.END

    await edit_mensaje(
        query,
        "✏️ EDITAR REPUESTO\n\n"
        "Escribe el código o nombre del repuesto a editar:",
        reply_markup=botones_volver(),
    )
    return SEARCH


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    termino = update.message.text.strip()
    resultados = buscar_repuestos(termino)

    if not resultados:
        await update.message.reply_text(
            f"🔍 No se encontraron resultados para '{termino}'.\n"
            f"Intenta con otro término:",
            reply_markup=botones_volver(),
        )
        return SEARCH

    if len(resultados) == 1:
        r = resultados[0]
        context.user_data["repuesto"] = dict(r)
        await update.message.reply_text(
            f"📋 Repuesto encontrado:\n\n"
            f"🏷️ Código: {r['codigo']}\n"
            f"📝 Nombre: {r['nombre']}\n"
            f"📦 Stock: {r['cantidad']}\n"
            f"💰 Precio: ${r['precio']:.2f}\n"
            f"📍 Ubicación: {r['ubicacion'] or 'Sin ubicación'}\n\n"
            f"¿Qué campo deseas editar?",
            reply_markup=menu_editar(),
        )
        return SELECT_FIELD

    texto = "🔍 Resultados:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, r in enumerate(resultados[:10], 1):
        texto += f"{i}. {r['codigo']} - {r['nombre']} (Stock: {r['cantidad']})\n"

    context.user_data["resultados"] = resultados
    await update.message.reply_text(
        texto + "\nEscribe el código del repuesto a editar:",
        reply_markup=botones_volver(),
    )
    return SELECT_ITEM


async def select_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    codigo = update.message.text.strip()
    repuesto = obtener_repuesto(codigo)

    if not repuesto:
        await update.message.reply_text(
            f"❌ No se encontró el repuesto '{codigo}'.\nIntenta de nuevo:",
            reply_markup=botones_volver(),
        )
        return SEARCH

    context.user_data["repuesto"] = dict(repuesto)
    await update.message.reply_text(
        f"📋 Repuesto encontrado:\n\n"
        f"🏷️ Código: {repuesto['codigo']}\n"
        f"📝 Nombre: {repuesto['nombre']}\n"
        f"📦 Stock: {repuesto['cantidad']}\n"
        f"💰 Precio: ${repuesto['precio']:.2f}\n"
        f"📍 Ubicación: {repuesto['ubicacion'] or 'Sin ubicación'}\n\n"
        f"¿Qué campo deseas editar?",
        reply_markup=menu_editar(),
    )
    return SELECT_FIELD


async def select_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    repuesto = context.user_data["repuesto"]

    if data == "cancelar":
        await edit_mensaje(query, "❌ Edición cancelada.", reply_markup=botones_volver())
        return ConversationHandler.END

    if data == "editar_cantidad":
        context.user_data["campo"] = "cantidad"
        await edit_mensaje(
            query,
            f"📦 Stock actual: {repuesto['cantidad']} unidades\n\n"
            f"¿Qué acción deseas realizar?",
            reply_markup=menu_cantidad(),
        )
        return EDIT_VALUE

    if data == "editar_precio":
        context.user_data["campo"] = "precio"
        await edit_mensaje(
            query,
            f"💰 Precio actual: ${repuesto['precio']:.2f}\n\n"
            f"📝 Escribe el nuevo precio:",
            reply_markup=botones_volver(),
        )
        return EDIT_VALUE

    if data == "editar_ubicacion":
        context.user_data["campo"] = "ubicacion"
        await edit_mensaje(
            query,
            f"📍 Ubicación actual: {repuesto['ubicacion'] or 'Sin ubicación'}\n\n"
            f"📝 Escribe la nueva ubicación:",
            reply_markup=botones_volver(),
        )
        return EDIT_VALUE

    if data == "editar_nombre":
        context.user_data["campo"] = "nombre"
        await edit_mensaje(
            query,
            f"📝 Nombre actual: {repuesto['nombre']}\n\n"
            f"📝 Escribe el nuevo nombre:",
            reply_markup=botones_volver(),
        )
        return EDIT_VALUE

    if data == "editar_categoria":
        from keyboards import menu_categorias
        from database import obtener_categorias
        categorias = obtener_categorias()
        context.user_data["campo"] = "categoria_id"
        await edit_mensaje(
            query,
            "📂 Selecciona la nueva categoría:",
            reply_markup=menu_categorias(categorias),
        )
        return EDIT_VALUE

    if data == "editar_fotos":
        await edit_mensaje(
            query,
            "📷 Envía la nueva Foto 1 (imagen principal):",
            reply_markup=botones_volver(),
        )
        context.user_data["campo"] = "fotos"
        context.user_data["fotos_nuevas"] = []
        return EDIT_VALUE

    await edit_mensaje(query, "⚠️ Opción no válida.", reply_markup=menu_editar())
    return SELECT_FIELD


async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        data = query.data
    else:
        data = None

    repuesto = context.user_data["repuesto"]
    campo = context.user_data["campo"]

    if query and data == "cancelar":
        await edit_mensaje(query, "❌ Edición cancelada.", reply_markup=botones_volver())
        return ConversationHandler.END

    if campo == "fotos" and update.message and not (update.message.photo or update.message.document):
        await update.message.reply_text("⚠️ Debes enviar una imagen. Intenta de nuevo:")
        return EDIT_VALUE

    if campo == "cantidad" and query and data and data.startswith("cant_"):
        valor_str = data.replace("cant_", "")
        if valor_str == "custom":
            await edit_mensaje(
                query,
                f"📦 Stock actual: {repuesto['cantidad']}\n\n"
                f"📝 Escribe la cantidad exacta:",
                reply_markup=botones_volver(),
            )
            return EDIT_VALUE

        try:
            delta = int(valor_str)
        except ValueError:
            await edit_mensaje(query, "⚠️ Valor no valido.", reply_markup=botones_volver())
            return EDIT_VALUE
        nueva_cantidad = repuesto["cantidad"] + delta
        if nueva_cantidad < 0:
            nueva_cantidad = 0

        context.user_data["nuevo_valor"] = nueva_cantidad
        await edit_mensaje(
            query,
            f"📦 Stock actual: {repuesto['cantidad']}\n"
            f"📈 Cambio: {'+' if delta > 0 else ''}{delta}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Stock nuevo: {nueva_cantidad}\n\n"
            f"¿Confirmar cambio?",
            reply_markup=menu_confirmar(),
        )
        return CONFIRMAR

    if update.message and update.message.text:
        texto = update.message.text.strip()

        if campo in ("categoria_id", "fotos"):
            await update.message.reply_text("⚠️ Usa los botones para seleccionar este campo.")
            return EDIT_VALUE

        if campo == "cantidad":
            if not texto.isdigit():
                await update.message.reply_text("⚠️ Debe ser un numero entero. Intenta de nuevo:")
                return EDIT_VALUE
            nueva_cantidad = int(texto)
            context.user_data["nuevo_valor"] = nueva_cantidad
        elif campo == "precio":
            try:
                nuevo_precio = float(texto)
            except ValueError:
                await update.message.reply_text("⚠️ Debe ser un numero valido. Intenta de nuevo:")
                return EDIT_VALUE
            context.user_data["nuevo_valor"] = nuevo_precio
        elif campo == "nombre" or campo == "ubicacion" or campo == "descripcion":
            if not texto:
                await update.message.reply_text("⚠️ El valor no puede estar vacio. Intenta de nuevo:")
                return EDIT_VALUE
            context.user_data["nuevo_valor"] = texto
        else:
            context.user_data["nuevo_valor"] = texto

        valor_anterior = repuesto[campo]
        if campo == "categoria_id":
            valor_anterior = repuesto["categoria_nombre"] or "Sin categoria"

        await update.message.reply_text(
            f"📝 Campo: {campo}\n"
            f"Valor anterior: {valor_anterior}\n"
            f"Valor nuevo: {context.user_data['nuevo_valor']}\n\n"
            f"¿Confirmar cambio?",
            reply_markup=menu_confirmar(),
        )
        return CONFIRMAR

    if campo == "fotos" and update.message and (update.message.photo or update.message.document):
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
        else:
            file_id = update.message.document.file_id
        fotos = context.user_data["fotos_nuevas"]
        fotos.append(file_id)

        num = len(fotos)
        if num < 4:
            await update.message.reply_text(
                f"✅ Foto {num} recibida\n\n"
                f"📷 Foto {num + 1} de 4:",
                reply_markup=botones_volver(),
            )
            return EDIT_VALUE
        else:
            context.user_data["nuevo_valor"] = fotos
            await update.message.reply_text(
                "✅ 4 fotos actualizadas\n\n¿Confirmar cambio?",
                reply_markup=menu_confirmar(),
            )
            return CONFIRMAR

    if query and data and data.startswith("cat_"):
        cat_id = int(data.replace("cat_", ""))
        context.user_data["nuevo_valor"] = cat_id
        await edit_mensaje(
            query,
            "✅ Categoría actualizada\n\n¿Confirmar cambio?",
            reply_markup=menu_confirmar(),
        )
        return CONFIRMAR

    return EDIT_VALUE


async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar":
        await edit_mensaje(query, "❌ Edición cancelada.", reply_markup=botones_volver())
        context.user_data.clear()
        return ConversationHandler.END

    if query.data == "confirmar":
        repuesto = context.user_data["repuesto"]
        campo = context.user_data["campo"]
        nuevo_valor = context.user_data["nuevo_valor"]

        try:
            if campo == "fotos":
                editar_repuesto_fotos(repuesto["codigo"], nuevo_valor)
            else:
                editar_repuesto(repuesto["codigo"], campo, nuevo_valor)

            valor_mostrar = (repuesto["categoria_nombre"] or "Sin categoria") if campo == "categoria_id" else ("4 fotos" if campo == "fotos" else repuesto[campo])
            await edit_mensaje(
                query,
                f"✅ Campo '{campo}' actualizado correctamente!\n\n"
                f"🏷️ {repuesto['codigo']} - {repuesto['nombre']}",
                reply_markup=botones_volver(),
            )
        except Exception as e:
            await edit_mensaje(
                query,
                f"❌ Error al actualizar: {str(e)}",
                reply_markup=botones_volver(),
            )
        context.user_data.clear()
        return ConversationHandler.END


async def cancel_editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Edición cancelada.", reply_markup=botones_volver())
    context.user_data.clear()
    return ConversationHandler.END


editar_handler = ConversationHandler(
    entry_points=[
        CommandHandler("editar", start_editar),
        CallbackQueryHandler(callback_editar, pattern="^editar$"),
    ],
    states={
        SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search)],
        SELECT_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_item)],
        SELECT_FIELD: [CallbackQueryHandler(select_field, pattern="^editar_|cancelar$")],
        EDIT_VALUE: [
            CallbackQueryHandler(edit_value, pattern="^(cant_|cat_|cancelar)"),
            MessageHandler(FILTRO_IMAGEN, edit_value),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value),
        ],
        CONFIRMAR: [CallbackQueryHandler(confirmar, pattern="^(confirmar|cancelar)$")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_editar),
        CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$"),
    ],
)