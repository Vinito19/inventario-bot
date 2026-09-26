#!/usr/bin/env python3
"""
Callback handler para búsqueda web desde el botón en detalle de repuesto.
Patrón: buscarweb_CODIGO
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler

import config
from database import obtener_repuesto, esta_registrado
from keyboards import botones_volver
from handlers.utils import edit_mensaje
import web_search


async def buscarweb_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback desde botón en detalle de repuesto: buscarweb_CODIGO"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not esta_registrado(user_id):
        await edit_mensaje(query, "❌ No tienes acceso al bot.")
        return ConversationHandler.END

    # data = "buscarweb_CODIGO"
    try:
        codigo = query.data.split("_", 1)[1]
    except IndexError:
        await edit_mensaje(query, "⚠️ Código no válido.", reply_markup=botones_volver())
        return ConversationHandler.END

    # Obtener nombre del repuesto de la BD para mejorar búsqueda
    repuesto = obtener_repuesto(codigo)
    nombre = repuesto["nombre"] if repuesto else ""

    await edit_mensaje(query, f"🔍 Buscando en internet: <b>{codigo}</b>...", parse_mode="HTML")
    resultado = await web_search.buscar_repuesto_web(codigo, nombre)

    if not resultado:
        await edit_mensaje(
            query,
            f"❌ No se encontró información para <b>{codigo}</b> {nombre or ''}.\n\n"
            "Intenta con otro código o nombre.",
            parse_mode="HTML",
            reply_markup=botones_volver(),
        )
        return ConversationHandler.END

    # Formatear resultado (inline para evitar duplicar lógica)
    lines = [
        f"🌐 <b>BÚSQUEDA WEB: {resultado['codigo']}</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    if resultado.get("marca"):
        lines.append(f"🚗 <b>Marca:</b> {resultado['marca']}")
    if resultado.get("modelo"):
        lines.append(f"📋 <b>Modelo:</b> {resultado['modelo']}")
    if resultado.get("tipo"):
        lines.append(f"🔧 <b>Tipo de pieza:</b> {resultado['tipo']}")
    if resultado.get("lado"):
        lines.append(f"↔️ <b>Lado:</b> {resultado['lado']}")
    if resultado.get("precio_ecuador"):
        lines.append(f"💰 <b>Precio Ecuador:</b> {resultado['precio_ecuador']}")

    if resultado.get("snippets"):
        lines.append(f"\n📄 <b>Fragmentos encontrados:</b>")
        for i, s in enumerate(resultado["snippets"], 1):
            lines.append(f"  {i}. {s[:150]}...")

    lines.append(f"\n🔗 <b>Fuente:</b> {resultado['fuente']}")
    lines.append(f"⚠️ <i>Información extraída automáticamente, verificar manualmente.</i>")

    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Nueva búsqueda", callback_data=f"buscarweb_{codigo}")],
        [InlineKeyboardButton("🏠 Inicio", callback_data="inicio")],
    ])
    await edit_mensaje(query, "\n".join(lines), parse_mode="HTML", reply_markup=botones)
    return ConversationHandler.END


# Solo se exporta el callback handler para el botón de detalle
buscarweb_callback_handler = CallbackQueryHandler(buscarweb_callback, pattern="^buscarweb_")