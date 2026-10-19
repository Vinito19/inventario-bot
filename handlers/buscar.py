import html
import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import web_search
from database import buscar_repuestos, esta_registrado, obtener_repuesto
from handlers.proforma import proforma_callback
from handlers.utils import (
    _formatear_resultado,
    _termino_busqueda_web,
    edit_mensaje,
    finalizar,
    guardar_mensaje,
)
from keyboards import (
    botones_volver,
    menu_buscar_modo,
    menu_detalle_repuesto,
    menu_resultados,
)

logger = logging.getLogger(__name__)


def _escape(text: str) -> str:
    """Escapa caracteres HTML para prevenir inyección."""
    return html.escape(text) if text else ""


def validar_termino_busqueda(texto: str, max_len: int = 100) -> str:
    """Valida término de búsqueda."""
    if not texto or not texto.strip():
        raise ValueError("Término de búsqueda no puede estar vacío")
    texto = texto.strip()
    if len(texto) > max_len:
        raise ValueError(f"Término demasiado largo (máx {max_len} caracteres)")
    # Eliminar caracteres de control
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
    if not texto.strip():
        raise ValueError("Término de búsqueda no puede contener solo caracteres de control")
    return texto


SEARCH_MODE, SEARCH_LOCAL, SEARCH_WEB_INPUT, VIEW_ITEM = range(4)


async def start_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not esta_registrado(user_id):
        await update.message.reply_text("❌ No tienes acceso al bot.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🔍 BUSCAR REPUESTO\n\n"
        "¿Dónde deseas buscar?",
        reply_markup=menu_buscar_modo(),
    )
    return SEARCH_MODE


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
        "¿Dónde deseas buscar?",
        reply_markup=menu_buscar_modo(),
    )
    return SEARCH_MODE


async def search_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "buscar_local":
        await edit_mensaje(
            query,
            "🔍 BUSCAR EN BASE DE DATOS LOCAL\n\n"
            "Escribe el código, nombre o categoría del repuesto:",
            reply_markup=botones_volver(),
        )
        return SEARCH_LOCAL

    if data == "buscar_web":
        await edit_mensaje(
            query,
            "🌐 BUSCAR EN INTERNET\n\n"
            "Escribe el código y/o nombre del repuesto a buscar en la web:\n"
            "(Ejemplo: 4121020-BE101 faro)",
            reply_markup=botones_volver(),
        )
        return SEARCH_WEB_INPUT

    if data == "cancelar":
        await edit_mensaje(query, "❌ Búsqueda cancelada.", reply_markup=botones_volver())
        return ConversationHandler.END

    return SEARCH_MODE


async def search_local(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        termino = validar_termino_busqueda(update.message.text)
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")
        return SEARCH_LOCAL

    resultados = buscar_repuestos(termino)

    if not resultados:
        await update.message.reply_text(
            f"🔍 No se encontraron resultados para '{termino}'.\n\n"
            f"Intenta con otro término:",
            reply_markup=botones_volver(),
        )
        return SEARCH_LOCAL

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


async def search_web_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        texto_input = validar_termino_busqueda(update.message.text, max_len=150)
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")
        return SEARCH_WEB_INPUT

    # Separar código y nombre (primera palabra = código, resto = nombre)
    partes = texto_input.split(maxsplit=1)
    codigo = partes[0]
    nombre = partes[1] if len(partes) > 1 else ""

    # Si el código está en la BD, la descripción aporta marca/modelo/año.
    termino = _termino_busqueda_web(obtener_repuesto(codigo), nombre)

    msg = await update.message.reply_text(f"🔍 Buscando en internet: <b>{_escape(codigo)}</b>...", parse_mode="HTML")
    resultado = await web_search.buscar_repuesto_web(codigo, termino, user_id=update.effective_user.id)

    if not resultado:
        await msg.edit_text(
            f"❌ No se encontró información para <b>{_escape(codigo)}</b> {_escape(nombre or '')}.\n\n"
            "Intenta con otro código o nombre.",
            parse_mode="HTML",
            reply_markup=botones_volver(),
        )
        return SEARCH_WEB_INPUT

    # Formatear resultado
    lines = _formatear_resultado(resultado)

    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Nueva búsqueda web", callback_data="buscar_web")],
        [InlineKeyboardButton("📂 Buscar en local", callback_data="buscar_local")],
        [InlineKeyboardButton("🏠 Inicio", callback_data="inicio")],
    ])

    await msg.edit_text(lines, parse_mode="HTML", reply_markup=botones)
    return SEARCH_MODE


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
            "¿Dónde deseas buscar?",
            reply_markup=menu_buscar_modo(),
        )
        return SEARCH_MODE

    if data == "proforma":
        return await proforma_callback(update, context)

    if data.startswith("ver_"):
        await _mostrar_detalle(query, context, update, data)
        return VIEW_ITEM

    if data == "buscar_web":
        await edit_mensaje(
            query,
            "🌐 BUSCAR EN INTERNET\n\n"
            "Escribe el código y/o nombre del repuesto a buscar en la web:\n"
            "(Ejemplo: 4121020-BE101 faro)",
            reply_markup=botones_volver(),
        )
        return SEARCH_WEB_INPUT

    if data == "buscar_local":
        await edit_mensaje(
            query,
            "🔍 BUSCAR EN BASE DE DATOS LOCAL\n\n"
            "Escribe el código, nombre o categoría del repuesto:",
            reply_markup=botones_volver(),
        )
        return SEARCH_LOCAL

    return VIEW_ITEM


async def _mostrar_detalle(query, context, update, data):
    """Muestra el detalle de un resultado (con fotos si las tiene)."""
    idx = int(data.replace("ver_", "")) - 1
    resultados = context.user_data.get("resultados", [])
    if not (0 <= idx < len(resultados)):
        return

    repuesto = obtener_repuesto(resultados[idx]["codigo"])
    if not repuesto:
        await edit_mensaje(query, "❌ Repuesto no encontrado.", reply_markup=botones_volver())
        return

    texto = (
        f"🏷️ {repuesto['codigo']} - {repuesto['nombre']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📂 Categoría: {repuesto['categoria_nombre'] or 'Sin categoría'}\n"
        f"📝 Descripción: {repuesto['descripcion']}\n"
        f"📦 Cantidad: {repuesto['cantidad']}\n"
        f"💰 Precio: ${repuesto['precio']:.2f}\n"
        f"📍 Ubicación: {repuesto['ubicacion'] or 'Sin ubicación'}"
    )
    markup = menu_detalle_repuesto(repuesto['codigo'])
    context.user_data["repuesto_compartir"] = repuesto

    fotos = [repuesto[f"file_id_{n}"] for n in range(1, 5) if repuesto[f"file_id_{n}"]]
    if not fotos:
        await edit_mensaje(query, texto, reply_markup=markup)
        return

    try:
        media_msgs = await context.bot.send_media_group(
            chat_id=query.message.chat_id,
            media=[InputMediaPhoto(media=f) for f in fotos],
        )
        for m in media_msgs:
            guardar_mensaje(update, context, m)
        msg = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=texto,
            reply_markup=markup,
        )
        guardar_mensaje(update, context, msg)
    except Exception as exc:
        logger.warning("No se pudieron enviar las fotos del repuesto %s: %s", repuesto["codigo"], exc)
        await edit_mensaje(query, texto + "\n\n⚠️ No se pudieron enviar las fotos.", reply_markup=markup)


async def cancel_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Búsqueda cancelada.", reply_markup=botones_volver())
    return ConversationHandler.END


buscar_handler = ConversationHandler(
    entry_points=[
        CommandHandler("buscar", start_buscar),
        CallbackQueryHandler(callback_buscar, pattern="^buscar$"),
    ],
    states={
        SEARCH_MODE: [CallbackQueryHandler(search_mode_callback, pattern="^(buscar_local|buscar_web|cancelar)$")],
        SEARCH_LOCAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_local)],
        SEARCH_WEB_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_web_input)],
        VIEW_ITEM: [
            CallbackQueryHandler(view_item, pattern=r"^(inicio|buscar|ver_\d+|proforma|buscar_web|buscar_local|cancelar)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_buscar),
        CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$"),
    ],
)