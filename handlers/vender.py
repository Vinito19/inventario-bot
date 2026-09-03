from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from database import (
    buscar_repuestos,
    obtener_repuesto,
    esta_registrado,
    registrar_venta,
)
from keyboards import botones_volver
from handlers.utils import finalizar, edit_mensaje

SEARCH, SELECT_ITEM, CANTIDAD, PRECIO, CONFIRMAR_ITEM, CART_SUMMARY = range(6)


def menu_cart():
    """Teclado para el resumen del carrito."""
    keyboard = [
        [InlineKeyboardButton("➕ Agregar otro artículo", callback_data="cart_add")],
        [InlineKeyboardButton("✅ Finalizar venta", callback_data="cart_finalize")],
        [InlineKeyboardButton("❌ Cancelar todo", callback_data="cart_cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_vender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not esta_registrado(user_id):
        await update.message.reply_text("❌ No tienes acceso al bot.")
        return ConversationHandler.END

    # Inicializar carrito vacío
    context.user_data["cart"] = []

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

    # Inicializar carrito vacío
    context.user_data["cart"] = []

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

    texto = "🔍 Resultados:\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
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
        f"💵 Escribe el PRECIO FINAL por unidad (con descuento o recargo si aplica):",
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

    diferencia = round(precio_final - venta['precio'], 2)
    if diferencia < 0:
        etiqueta = "🔻 Descuento unitario"
        valor = f"${abs(diferencia):.2f}"
    elif diferencia > 0:
        etiqueta = "🔺 Recargo unitario"
        valor = f"${diferencia:.2f}"
    else:
        etiqueta = "➖ Sin variación"
        valor = "$0.00"

    await update.message.reply_text(
        f"📋 CONFIRMAR ARTÍCULO\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ Código: {venta['codigo']}\n"
        f"📝 Nombre: {venta['nombre']}\n"
        f"📦 Cantidad: {cantidad_vendida}\n"
        f"💰 Precio registrado: ${venta['precio']:.2f}\n"
        f"💵 Precio final: ${precio_final:.2f}\n"
        f"{etiqueta}: {valor}\n"
        f"🧾 Subtotal: ${subtotal:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"¿Agregar este artículo al carrito?",
        reply_markup=menu_confirmar(),
    )
    return CONFIRMAR_ITEM


async def confirmar_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar":
        await edit_mensaje(query, "❌ Artículo cancelado.", reply_markup=botones_volver())
        context.user_data.pop("venta", None)
        return SEARCH

    if query.data == "confirmar":
        venta = context.user_data["venta"]
        # Agregar al carrito (copia para no mutar la original)
        item = {
            "codigo": venta["codigo"],
            "nombre": venta["nombre"],
            "cantidad": venta["cantidad_vendida"],
            "precio_registrado": venta["precio"],
            "precio_final": venta["precio_final"],
            "subtotal": venta["subtotal"],
        }
        context.user_data["cart"].append(item)
        context.user_data.pop("venta", None)
        return await mostrar_cart(update, context)


async def mostrar_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el resumen del carrito con opciones."""
    cart = context.user_data.get("cart", [])

    if not cart:
        await update.message.reply_text("🛒 Carrito vacío.", reply_markup=botones_volver())
        return SEARCH

    texto = "🛒 CARRITO DE VENTA\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    total = 0
    for i, item in enumerate(cart, 1):
        diff = round(item["precio_final"] - item["precio_registrado"], 2)
        if diff < 0:
            etiqueta = f"🔻 -${abs(diff):.2f}"
        elif diff > 0:
            etiqueta = f"🔺 +${diff:.2f}"
        else:
            etiqueta = "➖"
        texto += (
            f"{i}. {item['codigo']} - {item['nombre']}\n"
            f"   {item['cantidad']} und × ${item['precio_final']:.2f} "
            f"({etiqueta}) = ${item['subtotal']:.2f}\n"
        )
        total += item["subtotal"]

    texto += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    texto += f"💰 TOTAL: ${total:.2f}\n"
    texto += f"📦 Artículos: {len(cart)}\n"

    # Determinar si el mensaje viene de callback (editar) o message (nuevo)
    if update.callback_query:
        await edit_mensaje(update.callback_query, texto, reply_markup=menu_cart())
    else:
        await update.message.reply_text(texto, reply_markup=menu_cart())

    return CART_SUMMARY


async def cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "cart_add":
        # Volver a buscar otro artículo
        await edit_mensaje(
            query,
            "💵 AGREGAR OTRO ARTÍCULO\n\n"
            "Escribe el código o nombre del repuesto:",
            reply_markup=botones_volver(),
        )
        return SEARCH

    if data == "cart_cancel":
        await edit_mensaje(query, "❌ Venta cancelada. Carrito vaciado.", reply_markup=botones_volver())
        context.user_data.clear()
        return ConversationHandler.END

    if data == "cart_finalize":
        return await finalizar_cart(update, context)

    return CART_SUMMARY


async def finalizar_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # No llamar query.answer() aquí porque edit_mensaje lo maneja

    cart = context.user_data.get("cart", [])
    if not cart:
        await edit_mensaje(query, "🛒 Carrito vacío.", reply_markup=botones_volver())
        return ConversationHandler.END

    usuario = query.from_user
    items_procesados = []
    errores = []

    # Procesar cada item del carrito
    for item in cart:
        try:
            resultado = registrar_venta(
                codigo=item["codigo"],
                cantidad=item["cantidad"],
                precio_unitario=item["precio_final"],
                precio_registrado=item["precio_registrado"],
                usuario_id=usuario.id,
                usuario_nombre=usuario.first_name,
            )
            items_procesados.append({
                "codigo": item["codigo"],
                "nombre": item["nombre"],
                "cantidad": item["cantidad"],
                "subtotal": item["subtotal"],
                "stock_restante": resultado["nuevo_stock"],
            })
        except Exception as e:
            errores.append(f"{item['codigo']}: {str(e)}")

    total = sum(i["subtotal"] for i in items_procesados)

    if items_procesados:
        texto = "✅ VENTA FINALIZADA\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, item in enumerate(items_procesados, 1):
            texto += (
                f"{i}. {item['codigo']} - {item['nombre']}\n"
                f"   {item['cantidad']} und × ${item['subtotal']/item['cantidad']:.2f} "
                f"= ${item['subtotal']:.2f} (Stock: {item['stock_restante']})\n"
            )
        texto += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        texto += f"💰 TOTAL: ${total:.2f}\n"
        texto += f"📦 Ítems vendidos: {len(items_procesados)}"
    else:
        texto = "❌ No se pudo procesar ningún artículo."

    if errores:
        texto += "\n\n⚠️ ERRORES:\n" + "\n".join(errores)

    await edit_mensaje(query, texto, reply_markup=botones_volver())
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
        CONFIRMAR_ITEM: [CallbackQueryHandler(confirmar_item, pattern="^(confirmar|cancelar)$")],
        CART_SUMMARY: [CallbackQueryHandler(cart_callback, pattern="^cart_")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_vender),
        CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$"),
    ],
)