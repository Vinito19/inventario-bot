from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from database import obtener_resumen, esta_registrado, es_admin, obtener_resumen_ventas, obtener_ventas, obtener_cambios
from handlers.utils import edit_mensaje, guardar_mensaje, borrar_mensajes
from keyboards import botones_volver
from excel_export import generar_excel, generar_excel_ventas, generar_excel_cambios


async def start_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not esta_registrado(user_id):
        await update.message.reply_text("❌ No tienes acceso al bot.")
        return

    resumen = obtener_resumen()
    admin = es_admin(user_id)

    texto = (
        "📊 REPORTE DE INVENTARIO\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Total artículos:    {resumen['total']}\n"
        f"🔢 Total unidades:     {resumen['unidades']}\n"
        f"🚫 Stock en cero:      {resumen['cero']}\n"
        f"💰 Valor total:        ${resumen['valor']:,.2f}\n\n"
    )

    if resumen["por_categoria"]:
        texto += "📂 Por categoría:\n"
        for cat in resumen["por_categoria"]:
            texto += f"  • {cat['nombre']}: {cat['total']} artículos · {cat['unidades']} unidades\n"

    if resumen["sin_categoria"]:
        texto += "\n📌 Sin categoría:\n"
        for s in resumen["sin_categoria"]:
            texto += f"  • {s['total']} artículos · {s['unidades']} unidades\n"

    texto += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    keyboard = []

    if admin:
        keyboard.append([InlineKeyboardButton("📊 Exportar a Excel", callback_data="exportar_excel")])
        keyboard.append([InlineKeyboardButton("💵 Ver ventas", callback_data="ver_ventas")])
        keyboard.append([InlineKeyboardButton("🛠️ Ver cambios", callback_data="ver_cambios")])

    keyboard.append([InlineKeyboardButton("🧹 Ver artículos en cero", callback_data="ver_stock_cero")])

    if admin:
        keyboard.append([InlineKeyboardButton("🧹 Limpiar artículos en cero", callback_data="limpiar")])

    keyboard.append([InlineKeyboardButton("🏠 Volver al menú", callback_data="inicio")])

    msg = await update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
    guardar_mensaje(update, context, msg)


async def callback_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not esta_registrado(user_id):
        await edit_mensaje(query, "❌ No tienes acceso al bot.")
        return

    resumen = obtener_resumen()
    admin = es_admin(user_id)

    texto = (
        "📊 REPORTE DE INVENTARIO\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Total artículos:    {resumen['total']}\n"
        f"🔢 Total unidades:     {resumen['unidades']}\n"
        f"🚫 Stock en cero:      {resumen['cero']}\n"
        f"💰 Valor total:        ${resumen['valor']:,.2f}\n\n"
    )

    if resumen["por_categoria"]:
        texto += "📂 Por categoría:\n"
        for cat in resumen["por_categoria"]:
            texto += f"  • {cat['nombre']}: {cat['total']} artículos · {cat['unidades']} unidades\n"

    if resumen["sin_categoria"]:
        texto += "\n📌 Sin categoría:\n"
        for s in resumen["sin_categoria"]:
            texto += f"  • {s['total']} artículos · {s['unidades']} unidades\n"

    texto += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    keyboard = []

    if admin:
        keyboard.append([InlineKeyboardButton("📊 Exportar a Excel", callback_data="exportar_excel")])
        keyboard.append([InlineKeyboardButton("💵 Ver ventas", callback_data="ver_ventas")])
        keyboard.append([InlineKeyboardButton("🛠️ Ver cambios", callback_data="ver_cambios")])

    keyboard.append([InlineKeyboardButton("🧹 Ver artículos en cero", callback_data="ver_stock_cero")])

    if admin:
        keyboard.append([InlineKeyboardButton("🧹 Limpiar artículos en cero", callback_data="limpiar")])

    keyboard.append([InlineKeyboardButton("🏠 Volver al menú", callback_data="inicio")])

    await edit_mensaje(query, texto, reply_markup=InlineKeyboardMarkup(keyboard))


async def exportar_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not es_admin(user_id):
        await edit_mensaje(query, "❌ Solo el administrador puede exportar a Excel.")
        return

    # Limpiar mensajes previos guardados (documentos de exportaciones anteriores)
    await borrar_mensajes(context, chat_id=user_id)

    await edit_mensaje(query, "⏳ Generando archivo Excel...")

    try:
        archivo = generar_excel()
        with open(archivo, "rb") as f:
            doc_msg = await context.bot.send_document(
                chat_id=user_id,
                document=f,
                caption="📊 Inventario exportado correctamente",
            )
        guardar_mensaje(update, context, doc_msg)

        await edit_mensaje(query, "✅ Archivo Excel enviado!", reply_markup=botones_volver())
    except Exception as e:
        await edit_mensaje(
            query,
            f"❌ Error al generar Excel: {str(e)}",
            reply_markup=botones_volver(),
        )
    finally:
        try:
            import os
            if os.path.exists(archivo):
                os.remove(archivo)
        except Exception:
            pass


async def ver_stock_cero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    from database import obtener_stock_cero
    stock_cero = obtener_stock_cero()

    if not stock_cero:
        await edit_mensaje(
            query,
            "🧹 No hay artículos con stock en cero.",
            reply_markup=botones_volver(),
        )
        return

    texto = "🚫 ARTÍCULOS SIN STOCK\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for r in stock_cero[:15]:
        texto += f"• {r['codigo']} - {r['nombre']}\n"

    if len(stock_cero) > 15:
        texto += f"\n... y {len(stock_cero) - 15} más\n"

    texto += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nTotal: {len(stock_cero)} artículos"

    await edit_mensaje(query, texto, reply_markup=botones_volver())


async def ver_ventas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not es_admin(user_id):
        await edit_mensaje(query, "❌ Solo el administrador puede ver las ventas.")
        return

    resumen = obtener_resumen_ventas()
    ventas = obtener_ventas()

    texto = (
        "💵 REPORTE DE VENTAS\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🧾 Número de ventas:   {resumen['ventas']}\n"
        f"📦 Unidades vendidas:  {resumen['unidades']}\n"
        f"💰 Total vendido:      ${resumen['total']:,.2f}\n\n"
    )

    if ventas:
        texto += "📋 Últimas ventas:\n"
        for v in ventas[:10]:
            texto += (
                f"• {v['fecha'][:16]} | {v['codigo']} - {v['nombre']}\n"
                f"  {v['cantidad']} und · ${v['precio_unitario']:.2f} · subtotal ${v['subtotal']:.2f} · {v['usuario_nombre']}\n"
            )
        if len(ventas) > 10:
            texto += f"\n... y {len(ventas) - 10} más\n"

    texto += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    keyboard = [
        [InlineKeyboardButton("📊 Exportar ventas a Excel", callback_data="exportar_ventas")],
        [InlineKeyboardButton("🏠 Volver al menú", callback_data="inicio")],
    ]
    await edit_mensaje(query, texto, reply_markup=InlineKeyboardMarkup(keyboard))


async def exportar_ventas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not es_admin(user_id):
        await edit_mensaje(query, "❌ Solo el administrador puede exportar ventas.")
        return

    await borrar_mensajes(context, chat_id=user_id)
    await edit_mensaje(query, "⏳ Generando archivo de ventas...")

    try:
        archivo = generar_excel_ventas()
        with open(archivo, "rb") as f:
            doc_msg = await context.bot.send_document(
                chat_id=user_id,
                document=f,
                caption="💵 Reporte de ventas",
            )
        guardar_mensaje(update, context, doc_msg)
        await edit_mensaje(query, "✅ Archivo de ventas enviado!", reply_markup=botones_volver())
    except Exception as e:
        await edit_mensaje(query, f"❌ Error al generar ventas: {str(e)}", reply_markup=botones_volver())
    finally:
        try:
            import os
            if os.path.exists(archivo):
                os.remove(archivo)
        except Exception:
            pass


async def ver_cambios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not es_admin(user_id):
        await edit_mensaje(query, "❌ Solo el administrador puede ver los cambios.")
        return

    cambios = obtener_cambios()

    texto = (
        "🛠️ REPORTE DE CAMBIOS\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    if not cambios:
        texto += "No hay cambios registrados."
    else:
        texto += f"Total de cambios: {len(cambios)}\n\n"
        texto += "📋 Últimos cambios:\n"
        for c in cambios[:10]:
            texto += (
                f"• {c['fecha'][:16]} | {c['repuesto_codigo']}\n"
                f"  {c['campo']}: '{c['valor_anterior']}' → '{c['valor_nuevo']}'\n"
                f"  👤 {c['usuario_nombre']}\n"
            )
        if len(cambios) > 10:
            texto += f"\n... y {len(cambios) - 10} más\n"

    texto += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    keyboard = [
        [InlineKeyboardButton("📊 Exportar cambios a Excel", callback_data="exportar_cambios")],
        [InlineKeyboardButton("🏠 Volver al menú", callback_data="inicio")],
    ]
    await edit_mensaje(query, texto, reply_markup=InlineKeyboardMarkup(keyboard))


async def exportar_cambios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not es_admin(user_id):
        await edit_mensaje(query, "❌ Solo el administrador puede exportar cambios.")
        return

    await borrar_mensajes(context, chat_id=user_id)
    await edit_mensaje(query, "⏳ Generando archivo de cambios...")

    try:
        archivo = generar_excel_cambios()
        with open(archivo, "rb") as f:
            doc_msg = await context.bot.send_document(
                chat_id=user_id,
                document=f,
                caption="🛠️ Reporte de cambios de edición",
            )
        guardar_mensaje(update, context, doc_msg)
        await edit_mensaje(query, "✅ Archivo de cambios enviado!", reply_markup=botones_volver())
    except Exception as e:
        await edit_mensaje(query, f"❌ Error al generar cambios: {str(e)}", reply_markup=botones_volver())
    finally:
        try:
            import os
            if os.path.exists(archivo):
                os.remove(archivo)
        except Exception:
            pass


reporte_handler = CommandHandler("reporte", start_reporte)
reporte_callback_handler = CallbackQueryHandler(callback_reporte, pattern="^reporte$")
exportar_excel_handler = CallbackQueryHandler(exportar_excel, pattern="^exportar_excel$")
ver_stock_cero_handler = CallbackQueryHandler(ver_stock_cero, pattern="^ver_stock_cero$")
ver_ventas_handler = CallbackQueryHandler(ver_ventas, pattern="^ver_ventas$")
exportar_ventas_handler = CallbackQueryHandler(exportar_ventas, pattern="^exportar_ventas$")
ver_cambios_handler = CallbackQueryHandler(ver_cambios, pattern="^ver_cambios$")
exportar_cambios_handler = CallbackQueryHandler(exportar_cambios, pattern="^exportar_cambios$")