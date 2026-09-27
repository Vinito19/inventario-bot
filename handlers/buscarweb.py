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
from handlers.utils import edit_mensaje, _formatear_resultado, _termino_busqueda_web
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
    termino = _termino_busqueda_web(repuesto, nombre)

    await edit_mensaje(query, f"🔍 Buscando en internet: <b>{codigo}</b>...", parse_mode="HTML")
    resultado = await web_search.buscar_repuesto_web(codigo, termino, user_id=query.from_user.id)

    if not resultado:
        await edit_mensaje(
            query,
            f"❌ No se encontró información para <b>{codigo}</b> {nombre or ''}.\n\n"
            "Intenta con otro código o nombre.",
            parse_mode="HTML",
            reply_markup=botones_volver(),
        )
        return ConversationHandler.END

    lines = _formatear_resultado(resultado)

    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Nueva búsqueda", callback_data=f"buscarweb_{codigo}")],
        [InlineKeyboardButton("🏠 Inicio", callback_data="inicio")],
    ])
    await edit_mensaje(query, lines, parse_mode="HTML", reply_markup=botones)
    return ConversationHandler.END


# Solo se exporta el callback handler para el botón de detalle
buscarweb_callback_handler = CallbackQueryHandler(buscarweb_callback, pattern="^buscarweb_")