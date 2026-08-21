from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from database import buscar_repuestos, obtener_repuesto, esta_registrado
from keyboards import botones_volver, menu_resultados
from handlers.utils import finalizar, edit_mensaje, guardar_mensaje

SEARCH, VIEW_ITEM = range(2)


async def start_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not esta_registrado(user_id):
        await update.message.reply_text("❌ No tienes acceso al bot.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🔍 BUSCAR REPUESTO\n\n"
        "Escribe el código, nombre o categoría del repuesto:",
        reply_markup=botones_volver(),
    )
    return SEARCH


async def callback_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not esta_registrado(user_id):
        await edit_mensaje(query, "❌ No tienes acceso al bot.")
        return ConversationHandler.END

    await edit_mensaje(
        query,
        "🔍 BUSCAR REPUESTO\n\n"
        "Escribe el código, nombre o categoría del repuesto:",
        reply_markup=botones_volver(),
    )
    return SEARCH


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    termino = update.message.text.strip()
    if not termino:
        await update.message.reply_text("⚠️ Escribe algo para buscar. Intenta de nuevo:")
        return SEARCH

    resultados = buscar_repuestos(termino)

    if not resultados:
        await update.message.reply_text(
            f"🔍 No se encontraron resultados para '{termino}'.\n\n"
            f"Intenta con otro término:",
            reply_markup=botones_volver(),
        )
        return SEARCH

    texto = f"🔍 Resultados para '{termino}':\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i, r in enumerate(resultados[:10], 1):
        cat = r["categoria_nombre"] or "Sin categoría"
        texto += (
            f"{i}. 🏷️ {r['codigo']} - {r['nombre']}\n"
            f"   📂 {cat} | 📦 {r['cantidad']} | 💰 ${r['precio']:.2f}\n"
            f"   📍 {r['ubicacion'] or 'Sin ubicación'}\n\n"
        )

    if len(resultados) > 10:
        texto += f"... y {len(resultados) - 10} resultados más\n"

    texto += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nTotal: {len(resultados)} resultados\n\n"
    texto += "Presiona un resultado para ver sus fotos y detalles:"

    context.user_data["resultados"] = resultados
    context.user_data["termino"] = termino

    msg = await update.message.reply_text(texto, reply_markup=menu_resultados(resultados))
    guardar_mensaje(update, context, msg)
    return VIEW_ITEM


async def view_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    data = query.data

    if data == "inicio":
        return await finalizar(update, context)

    await query.answer()

    if data == "buscar":
        await edit_mensaje(
            query,
            "🔍 BUSCAR REPUESTO\n\n"
            "Escribe el código, nombre o categoría del repuesto:",
            reply_markup=botones_volver(),
        )
        return SEARCH

    if data.startswith("ver_"):
        idx = int(data.replace("ver_", "")) - 1
        resultados = context.user_data.get("resultados", [])
        if 0 <= idx < len(resultados):
            repuesto = obtener_repuesto(resultados[idx]["codigo"])
            if not repuesto:
                await edit_mensaje(query, "❌ Repuesto no encontrado.", reply_markup=botones_volver())
                return VIEW_ITEM

            texto = (
                f"🏷️ {repuesto['codigo']} - {repuesto['nombre']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📂 Categoría: {repuesto['categoria_nombre'] or 'Sin categoría'}\n"
                f"📝 Descripción: {repuesto['descripcion']}\n"
                f"📦 Cantidad: {repuesto['cantidad']}\n"
                f"💰 Precio: ${repuesto['precio']:.2f}\n"
                f"📍 Ubicación: {repuesto['ubicacion'] or 'Sin ubicación'}"
            )

            fotos = [repuesto[f"file_id_{n}"] for n in range(1, 5) if repuesto[f"file_id_{n}"]]

            if fotos:
                chat_id = query.message.chat_id
                try:
                    media_msgs = await context.bot.send_media_group(
                        chat_id=chat_id,
                        media=[InputMediaPhoto(media=f) for f in fotos],
                    )
                    for m in media_msgs:
                        guardar_mensaje(update, context, m)
                    msg = await context.bot.send_message(
                        chat_id=chat_id,
                        text=texto,
                        reply_markup=menu_resultados(resultados),
                    )
                    guardar_mensaje(update, context, msg)
                except Exception:
                    msg = await edit_mensaje(query, texto + "\n\n⚠️ No se pudieron enviar las fotos.", reply_markup=menu_resultados(resultados))
            else:
                await edit_mensaje(query, texto, reply_markup=menu_resultados(resultados))

        return VIEW_ITEM

    return VIEW_ITEM


async def cancel_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Búsqueda cancelada.", reply_markup=botones_volver())
    return ConversationHandler.END


buscar_handler = ConversationHandler(
    entry_points=[
        CommandHandler("buscar", start_buscar),
        CallbackQueryHandler(callback_buscar, pattern="^buscar$"),
    ],
    states={
        SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search)],
        VIEW_ITEM: [CallbackQueryHandler(view_item, pattern=r"^(inicio|buscar|ver_\d+)$")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_buscar),
        CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$"),
    ],
)