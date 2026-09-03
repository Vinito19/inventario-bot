from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from database import (
    buscar_repuestos,
    obtener_repuesto,
    esta_registrado,
    registrar_venta,
)
from keyboards import menu_confirmar, botones_volver
from handlers.utils import finalizar, edit_mensaje

SEARCH, SELECT_ITEM, CANTIDAD, PRECIO, CONFIRMAR = range(5)


async def start_vender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not esta_registrado(user_id):
        await update.message.reply_text("❌ No tienes acceso al bot.")
        return ConversationHandler.END

    await update.message.reply_text(
        "💵 REGISTRAR VENTA\n\n"
        "Escribe el código o nombre del repuesto vendido:",
        reply_markup=botones_volver(),
    )
    return SEARCH


async def callback_vender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not esta_registrado(user_id):
        await edit_mensaje(query, "❌ No tienes acceso al bot.")
        return ConversationHandler.END

    await edit_mensaje(
        query,
        "💵 REGISTRAR VENTA\n\n"
        "Escribe el código o nombre del repuesto vendido:",
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
        context.user_data["venta"] = dict(r)
        return await pedir_cantidad(update, context, r)

    texto = "🔍 Resultados:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, r in enumerate(resultados[:10], 1):
        texto += f"{i}. {r['codigo']} - {r['nombre']} (Stock: {r['cantidad']})\n"

    context.user_data["resultados"] = resultados
    await update.message.reply_text(
        texto + "\nEscribe el código exacto del repuesto vendido:",
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
        return SELECT_ITEM

    context.user_data["venta"] = dict(repuesto)
    return await pedir_cantidad(update, context, repuesto)


async def pedir_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE, r):
    context.user_data["venta"] = dict(r)
    await update.message.reply_text(
        f"📋 Repuesto seleccionado:\n\n"
        f"🏷️ Código: {r['codigo']}\n"
        f"📝 Nombre: {r['nombre']}\n"
        f"📦 Stock disponible: {r['cantidad']}\n"
        f"💰 Precio registrado: ${r['precio']:.2f}\n\n"
        f"📝 ¿Cuántas unidades vendiste?",
        reply_markup=botones_volver(),
    )
    return CANTIDAD


async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto.isdigit() or int(texto) <= 0:
        await update.message.reply_text("⚠️ Escribe un número entero mayor que cero. Intenta de nuevo:")
        return CANTIDAD

    cantidad_vendida = int(texto)
    venta = context.user_data["venta"]
    if cantidad_vendida > venta["cantidad"]:
        await update.message.reply_text(
            f"⚠️ Stock insuficiente. Solo hay {venta['cantidad']} unidades disponibles.\n"
            f"Escribe una cantidad válida:"
        )
        return CANTIDAD

    context.user_data["venta"]["cantidad_vendida"] = cantidad_vendida
    await update.message.reply_text(
        f"✅ Cantidad: {cantidad_vendida}\n\n"
        f"💰 Precio registrado: ${venta['precio']:.2f}\n"
        f"💵 Escribe el PRECIO FINAL por unidad (con descuento si aplica):",
        reply_markup=botones_volver(),
    )
    return PRECIO


async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    try:
        precio_final = round(float(texto), 2)
    except ValueError:
        await update.message.reply_text("⚠️ Escribe un número válido. Intenta de nuevo:")
        return PRECIO

    if precio_final < 0:
        await update.message.reply_text("⚠️ El precio no puede ser negativo. Intenta de nuevo:")
        return PRECIO

    venta = context.user_data["venta"]
    cantidad_vendida = venta["cantidad_vendida"]
    subtotal = round(cantidad_vendida * precio_final, 2)

    context.user_data["venta"]["precio_final"] = precio_final
    context.user_data["venta"]["subtotal"] = subtotal

    await update.message.reply_text(
        f"📋 CONFIRMAR VENTA\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ Código: {venta['codigo']}\n"
        f"📝 Nombre: {venta['nombre']}\n"
        f"📦 Cantidad: {cantidad_vendida}\n"
        f"💰 Precio registrado: ${venta['precio']:.2f}\n"
        f"💵 Precio final: ${precio_final:.2f}\n"
        f"🔻 Descuento unitario: ${round(venta['precio'] - precio_final, 2):.2f}\n"
        f"🧾 Subtotal: ${subtotal:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"¿Confirmar venta?",
        reply_markup=menu_confirmar(),
    )
    return CONFIRMAR


async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar":
        await edit_mensaje(query, "❌ Venta cancelada.", reply_markup=botones_volver())
        context.user_data.clear()
        return ConversationHandler.END

    if query.data == "confirmar":
        venta = context.user_data["venta"]
        usuario = query.from_user
        try:
            resultado = registrar_venta(
                codigo=venta["codigo"],
                cantidad=venta["cantidad_vendida"],
                precio_unitario=venta["precio_final"],
                precio_registrado=venta["precio"],
                usuario_id=usuario.id,
                usuario_nombre=usuario.first_name,
            )
            await edit_mensaje(
                query,
                "✅ Venta registrada correctamente!\n\n"
                f"🏷️ {venta['codigo']} - {venta['nombre']}\n"
                f"📦 Vendidos: {venta['cantidad_vendida']}\n"
                f"🧾 Subtotal: ${venta['subtotal']:.2f}\n"
                f"📦 Stock restante: {resultado['nuevo_stock']}",
                reply_markup=botones_volver(),
            )
        except Exception as e:
            await edit_mensaje(
                query,
                f"❌ Error al registrar venta: {str(e)}",
                reply_markup=botones_volver(),
            )
        context.user_data.clear()
        return ConversationHandler.END


async def cancel_vender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Venta cancelada.", reply_markup=botones_volver())
    context.user_data.clear()
    return ConversationHandler.END


vender_handler = ConversationHandler(
    entry_points=[
        CommandHandler("vender", start_vender),
        CallbackQueryHandler(callback_vender, pattern="^vender$"),
    ],
    states={
        SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search)],
        SELECT_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_item)],
        CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad)],
        PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio)],
        CONFIRMAR: [CallbackQueryHandler(confirmar, pattern="^(confirmar|cancelar)$")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_vender),
        CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$"),
    ],
)