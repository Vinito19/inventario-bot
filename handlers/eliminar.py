from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from database import buscar_repuestos, eliminar_repuesto, esta_registrado, es_admin
from keyboards import menu_confirmar, botones_volver
from handlers.utils import finalizar, edit_mensaje

SEARCH, CONFIRMAR = range(2)


async def start_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not es_admin(user_id):
        await update.message.reply_text("❌ Solo el administrador puede eliminar repuestos.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🗑️ ELIMINAR REPUESTO\n\n"
        "Escribe el código o nombre del repuesto a eliminar:",
        reply_markup=botones_volver(),
    )
    return SEARCH


async def callback_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not es_admin(user_id):
        await edit_mensaje(query, "❌ Solo el administrador puede eliminar repuestos.")
        return ConversationHandler.END

    await edit_mensaje(
        query,
        "🗑️ ELIMINAR REPUESTO\n\n"
        "Escribe el código o nombre del repuesto a eliminar:",
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
            f"⚠️ ¿ELIMINAR este repuesto?\n\n"
            f"🏷️ Código: {r['codigo']}\n"
            f"📝 Nombre: {r['nombre']}\n"
            f"📦 Stock: {r['cantidad']}\n\n"
            f"⚠️ Esta acción no se puede deshacer.",
            reply_markup=menu_confirmar(),
        )
        return CONFIRMAR

    texto = "🔍 Resultados:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, r in enumerate(resultados[:10], 1):
        texto += f"{i}. {r['codigo']} - {r['nombre']}\n"

    await update.message.reply_text(
        texto + "\nEscribe el código exacto del repuesto a eliminar:",
        reply_markup=botones_volver(),
    )
    context.user_data["resultados"] = resultados
    return SEARCH


async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar":
        await edit_mensaje(query, "❌ Eliminación cancelada.", reply_markup=botones_volver())
        return ConversationHandler.END

    if query.data == "confirmar":
        repuesto = context.user_data["repuesto"]
        try:
            eliminar_repuesto(repuesto["codigo"])
            await edit_mensaje(
                query,
                f"✅ Repuesto eliminado:\n\n"
                f"🏷️ {repuesto['codigo']} - {repuesto['nombre']}",
                reply_markup=botones_volver(),
            )
        except Exception as e:
            await edit_mensaje(
                query,
                f"❌ Error al eliminar: {str(e)}",
                reply_markup=botones_volver(),
            )
        return ConversationHandler.END


async def cancel_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Eliminación cancelada.", reply_markup=botones_volver())
    return ConversationHandler.END


eliminar_handler = ConversationHandler(
    entry_points=[
        CommandHandler("eliminar", start_eliminar),
        CallbackQueryHandler(callback_eliminar, pattern="^eliminar$"),
    ],
    states={
        SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search)],
        CONFIRMAR: [CallbackQueryHandler(confirmar, pattern="^(confirmar|cancelar)$")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_eliminar),
        CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$"),
    ],
)