from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler

from database import obtener_stock_cero, eliminar_stock_cero, es_admin
from keyboards import menu_confirmar, botones_volver
from handlers.utils import finalizar, edit_mensaje

CONFIRMAR = 0


async def start_limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not es_admin(user_id):
        await update.message.reply_text("❌ Solo el administrador puede limpiar el inventario.")
        return ConversationHandler.END

    stock_cero = obtener_stock_cero()

    if not stock_cero:
        await update.message.reply_text(
            "🧹 No hay artículos con stock en cero.",
            reply_markup=botones_volver(),
        )
        return ConversationHandler.END

    texto = (
        "🧹 LIMPIAR ARTÍCULOS EN CERO\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Se encontraron {len(stock_cero)} artículos con stock en cero:\n\n"
    )

    for r in stock_cero[:10]:
        texto += f"• {r['codigo']} - {r['nombre']}\n"

    if len(stock_cero) > 10:
        texto += f"... y {len(stock_cero) - 10} más\n"

    texto += (
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Esta acción no se puede deshacer.\n\n"
        "¿Deseas eliminarlos todos?"
    )

    context.user_data["total_cero"] = len(stock_cero)
    await update.message.reply_text(texto, reply_markup=menu_confirmar())
    return CONFIRMAR


async def callback_limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not es_admin(user_id):
        await edit_mensaje(query, "❌ Solo el administrador puede limpiar el inventario.")
        return ConversationHandler.END

    stock_cero = obtener_stock_cero()

    if not stock_cero:
        await edit_mensaje(
            query,
            "🧹 No hay artículos con stock en cero.",
            reply_markup=botones_volver(),
        )
        return ConversationHandler.END

    texto = (
        "🧹 LIMPIAR ARTÍCULOS EN CERO\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Se encontraron {len(stock_cero)} artículos con stock en cero:\n\n"
    )

    for r in stock_cero[:10]:
        texto += f"• {r['codigo']} - {r['nombre']}\n"

    if len(stock_cero) > 10:
        texto += f"... y {len(stock_cero) - 10} más\n"

    texto += (
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Esta acción no se puede deshacer.\n\n"
        "¿Deseas eliminarlos todos?"
    )

    context.user_data["total_cero"] = len(stock_cero)
    await edit_mensaje(query, texto, reply_markup=menu_confirmar())
    return CONFIRMAR


async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar":
        await edit_mensaje(query, "❌ Limpieza cancelada.", reply_markup=botones_volver())
        return ConversationHandler.END

    if query.data == "confirmar":
        eliminados = eliminar_stock_cero()
        await edit_mensaje(
            query,
            f"✅ Limpieza completada\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🗑️ {eliminados} artículos eliminados\n\n"
            f"Use /reporte para ver el inventario actualizado.",
            reply_markup=botones_volver(),
        )
        return ConversationHandler.END


limpiar_handler = ConversationHandler(
    entry_points=[
        CommandHandler("limpiar", start_limpiar),
        CallbackQueryHandler(callback_limpiar, pattern="^limpiar$"),
    ],
    states={
        CONFIRMAR: [CallbackQueryHandler(confirmar, pattern="^(confirmar|cancelar)$")],
    },
    fallbacks=[CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$")],
)