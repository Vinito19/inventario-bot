#!/usr/bin/env python3
"""
Handler para búsqueda web de repuestos.
Comando: /buscarweb <codigo> [nombre]
Botón en menú de repuesto.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters

import config
from database import obtener_repuesto, esta_registrado
from keyboards import botones_volver
from handlers.utils import edit_mensaje, finalizar
import web_search

SEARCH_WEB = range(1)[0]


async def buscarweb_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /buscarweb <codigo> [nombre]"""
    user_id = update.effective_user.id
    if not esta_registrado(user_id):
        await update.message.reply_text("❌ No tienes acceso al bot.")
        return ConversationHandler.END

    args = context.args
    if not args:
        await update.message.reply_text(
            "🔍 BÚSQUEDA WEB DE REPUESTO\n\n"
            "Uso: <code>/buscarweb CODIGO [NOMBRE]</code>\n\n"
            "Ejemplo: <code>/buscarweb 4121020-BE101 faro</code>",
            parse_mode="HTML",
            reply_markup=botones_volver(),
        )
        return ConversationHandler.END

    codigo = args[0]
    nombre = " ".join(args[1:]) if len(args) > 1 else ""
    return await _buscar_y_mostrar(update, context, codigo, nombre)


async def buscarweb_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback desde botón en detalle de repuesto"""
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
    return await _mostrar_resultado(query, context, resultado, codigo, nombre)


async def _buscar_y_mostrar(update: Update, context: ContextTypes.DEFAULT_TYPE, codigo: str, nombre: str):
    msg = await update.message.reply_text(f"🔍 Buscando en internet: <b>{codigo}</b>...", parse_mode="HTML")
    resultado = await web_search.buscar_repuesto_web(codigo, nombre)
    return await _mostrar_resultado_msg(update, context, msg, resultado, codigo, nombre)


async def _mostrar_resultado(query, context, resultado, codigo, nombre):
    """Muestra resultado editando el mensaje del callback"""
    if not resultado:
        await edit_mensaje(
            query,
            f"❌ No se encontró información para <b>{codigo}</b> {nombre or ''}.\n\n"
            "Intenta con otro código o nombre.",
            parse_mode="HTML",
            reply_markup=botones_volver(),
        )
        return ConversationHandler.END

    texto = _formatear_resultado(resultado)
    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Nueva búsqueda", callback_data=f"buscarweb_{codigo}")],
        [InlineKeyboardButton("🏠 Inicio", callback_data="inicio")],
    ])
    await edit_mensaje(query, texto, parse_mode="HTML", reply_markup=botones)
    return ConversationHandler.END


async def _mostrar_resultado_msg(update, context, msg, resultado, codigo, nombre):
    """Muestra resultado editando un mensaje previo"""
    if not resultado:
        await msg.edit_text(
            f"❌ No se encontró información para <b>{codigo}</b> {nombre or ''}.\n\n"
            "Intenta con otro código o nombre.",
            parse_mode="HTML",
            reply_markup=botones_volver(),
        )
        return ConversationHandler.END

    texto = _formatear_resultado(resultado)
    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Nueva búsqueda", callback_data=f"buscarweb_{codigo}")],
        [InlineKeyboardButton("🏠 Inicio", callback_data="inicio")],
    ])
    await msg.edit_text(texto, parse_mode="HTML", reply_markup=botones)
    return ConversationHandler.END


def _formatear_resultado(r: dict) -> str:
    lines = [
        f"🌐 <b>BÚSQUEDA WEB: {r['codigo']}</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    if r.get("marca"):
        lines.append(f"🚗 <b>Marca:</b> {r['marca']}")
    if r.get("modelo"):
        lines.append(f"📋 <b>Modelo:</b> {r['modelo']}")
    if r.get("tipo"):
        lines.append(f"🔧 <b>Tipo de pieza:</b> {r['tipo']}")
    if r.get("lado"):
        lines.append(f"↔️ <b>Lado:</b> {r['lado']}")

    if r.get("snippets"):
        lines.append(f"\n📄 <b>Fragmentos encontrados:</b>")
        for i, s in enumerate(r["snippets"], 1):
            lines.append(f"  {i}. {s[:150]}...")

    lines.append(f"\n🔗 <b>Fuente:</b> {r['fuente']}")
    lines.append(f"⚠️ <i>Información extraída automáticamente, verificar manualmente.</i>")

    return "\n".join(lines)


buscarweb_handler = CommandHandler("buscarweb", buscarweb_cmd)
buscarweb_callback_handler = CallbackQueryHandler(buscarweb_callback, pattern="^buscarweb_")