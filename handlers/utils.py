from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import obtener_usuario
from keyboards import menu_admin, menu_usuario

# Tope del término de búsqueda web: los catálogos responden peor con textos largos.
MAX_TERMINO_BUSQUEDA = 90


def _campo(repuesto, clave: str) -> str:
    """Lee un campo del repuesto tanto de dict como de sqlite3.Row."""
    try:
        valor = repuesto[clave]
    except (KeyError, IndexError, TypeError):
        valor = getattr(repuesto, clave, "")
    return " ".join(str(valor or "").split())


def _termino_busqueda_web(repuesto=None, nombre: str = "") -> str:
    """Arma el texto a buscar con nombre + descripción del repuesto.

    `nombre` sólo dice el tipo de pieza ("Faro de compuerta"); la descripción
    añade marca, modelo, año y lado ("Faro de compuerta derecha Renault
    Sandero"), que es lo que permite encontrar el repuesto en los catálogos.
    """
    nombre = (nombre or "").strip()
    if not repuesto:
        return nombre[:MAX_TERMINO_BUSQUEDA]

    descripcion = _campo(repuesto, "descripcion")
    if nombre and nombre.lower() == _campo(repuesto, "nombre").lower():
        # Viene del mismo registro: el nombre ya se toma de aquí y anteponerlo
        # duplicaría el tipo de pieza ("Faro Kia Soluto Faro delantero...").
        nombre = ""

    partes = [_campo(repuesto, "nombre")]
    base = partes[0].lower()
    if descripcion:
        # Cuando nombre y descripción comparten el tipo de pieza
        # ("Faro" / "Faro delantero Kia Soluto..."), la descripción ya es el
        # término más específico: anteponer el nombre sólo lo duplicaría.
        primero_nombre = base.split(maxsplit=1)[0] if base else ""
        primero_desc = descripcion.lower().split(maxsplit=1)[0]
        if primero_nombre and primero_nombre == primero_desc:
            partes[0] = descripcion
        elif descripcion.lower() not in base:
            partes.append(descripcion)
    if nombre and nombre.strip().lower() not in " ".join(partes).lower():
        partes.insert(0, nombre.strip())
    return " ".join(p for p in partes if p)[:MAX_TERMINO_BUSQUEDA]


def _precio_producto(prod: dict) -> str:
    """Línea de precio. Catálogos sin precio (0) se muestran como 'a consultar'."""
    if (prod.get("precio_usd") or 0) > 0:
        return f"💰 <b>${prod['precio_usd']:.2f} USD</b>"
    return "💰 <b>Precio a consultar con el vendedor</b>"


def _formatear_resultado(r: dict) -> str:
    """Formatea resultados de búsqueda con prioridad Ecuador."""
    from markupsafe import escape

    lines = [
        f"🌐 <b>BÚSQUEDA WEB: {escape(r['codigo'])}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # Mostrar resultados de Ecuador primero
    if r.get("resultados_ecuador"):
        lines.append(f"\n🇪🇨 <b>RESULTADOS EN ECUADOR ({len(r['resultados_ecuador'])})</b>")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        for i, prod in enumerate(r["resultados_ecuador"][:3], 1):
            lines.append(f"\n<b>{i}. {escape(prod['sitio'])}</b>")
            lines.append(f"📦 {escape(prod['nombre'][:80])}")
            lines.append(_precio_producto(prod))
            lines.append(f"🔧 Función: {escape(prod['funcion'])}")
            lines.append(f"↔️ Lado: {escape(prod['lado'])}")
            lines.append(f"💡 Tecnología: {escape(prod['tecnologia'])}")

            if prod.get("compatibilidad"):
                compat = ", ".join(prod["compatibilidad"][:2])
                lines.append(f"🚗 Compatible: {escape(compat)}")

            if prod.get("componente_hermano"):
                lines.append(f"🔗 Hermano: {escape(prod['componente_hermano'])}")

            lines.append(f"🔗 <a href='{escape(prod['url'])}'>Ver producto</a>")

    # Mostrar resultados internacionales si existen
    if r.get("resultados_internacional"):
        lines.append(f"\n🌍 <b>RESULTADOS INTERNACIONALES ({len(r['resultados_internacional'])})</b>")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        for i, prod in enumerate(r["resultados_internacional"][:3], 1):
            lines.append(f"\n<b>{i}. {escape(prod['sitio'])} ({escape(prod['pais'])})</b>")
            lines.append(f"📦 {escape(prod['nombre'][:80])}")
            if (prod.get("precio_usd") or 0) > 0:
                lines.append(f"💰 <b>${prod['precio_usd']:.2f} USD</b> "
                             f"(orig: {prod['moneda_original']} {prod['precio_original']:.2f})")
            else:
                lines.append("💰 <b>Precio a consultar con el vendedor</b>")
            lines.append(f"🔧 Función: {escape(prod['funcion'])}")
            lines.append(f"↔️ Lado: {escape(prod['lado'])}")
            lines.append(f"💡 Tecnología: {escape(prod['tecnologia'])}")

            if prod.get("compatibilidad"):
                compat = ", ".join(prod["compatibilidad"][:2])
                lines.append(f"🚗 Compatible: {escape(compat)}")

            if prod.get("componente_hermano"):
                lines.append(f"🔗 Hermano: {escape(prod['componente_hermano'])}")

            lines.append(f"🔗 <a href='{escape(prod['url'])}'>Ver producto</a>")

    # Mensaje si no hay resultados de scrapers (fallback genérico)
    if not r.get("resultados_ecuador") and not r.get("resultados_internacional"):
        if r.get("marca"):
            lines.append(f"🚗 <b>Marca:</b> {escape(r['marca'])}")
        if r.get("modelo"):
            lines.append(f"📋 <b>Modelo:</b> {escape(r['modelo'])}")
        if r.get("tipo"):
            lines.append(f"🔧 <b>Tipo de pieza:</b> {escape(r['tipo'])}")
        if r.get("lado"):
            lines.append(f"↔️ <b>Lado:</b> {escape(r['lado'])}")
        if r.get("precio_ecuador"):
            lines.append(f"💰 <b>Precio Ecuador:</b> {escape(r['precio_ecuador'])}")
        if r.get("snippets"):
            lines.append("\n📄 <b>Fragmentos encontrados:</b>")
            for i, s in enumerate(r["snippets"], 1):
                lines.append(f"  {i}. {escape(s[:150])}...")
        if not r.get("marca") and not r.get("modelo") and not r.get("precio_ecuador") \
                and not r.get("snippets"):
            lines.append("\n❌ No se encontraron resultados para este código.")
            lines.append("\n<i>Intenta con otro código o nombre de repuesto.</i>")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 Total: {r.get('total_ecuador', 0)} Ecuador "
                 f"+ {r.get('total_internacional', 0)} Internacional")
    lines.append("⚠️ <i>Precios convertidos a USD. Verificar disponibilidad con vendedor.</i>")

    return "\n".join(lines).replace("\r", "")


def guardar_mensaje(update_or_msg, context, msg):
    if msg and hasattr(msg, "message_id"):
        context.user_data.setdefault("msgs", []).append(msg.message_id)


async def borrar_mensajes(context: ContextTypes.DEFAULT_TYPE, chat_id=None):
    ids = context.user_data.pop("msgs", [])
    cid = chat_id or getattr(context, "_chat_id", None)
    if not cid:
        return
    for mid in ids:
        try:
            await context.bot.delete_message(chat_id=cid, message_id=mid)
        except Exception:
            pass


async def eliminar_fotos(context: ContextTypes.DEFAULT_TYPE, chat_id=None):
    ids = context.user_data.pop("photo_msg_ids", [])
    cid = chat_id or getattr(context, "_chat_id", None)
    if not cid:
        return
    for mid in ids:
        try:
            await context.bot.delete_message(chat_id=cid, message_id=mid)
        except Exception:
            pass


async def edit_mensaje(query, texto, reply_markup=None):
    if query.message is None:
        return
    if query.message.photo:
        return await query.edit_message_caption(caption=texto, reply_markup=reply_markup)
    return await query.edit_message_text(texto, reply_markup=reply_markup)


async def finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    await eliminar_fotos(context, chat_id)
    await borrar_mensajes(context, chat_id)

    user_id = query.from_user.id
    usuario = obtener_usuario(user_id)

    if query.data == "inicio":
        if usuario and usuario["rol"] == "admin" and usuario["activo"] == 1:
            await context.bot.send_message(chat_id=chat_id, text="👑 Panel de administrador:", reply_markup=menu_admin())
        elif usuario and usuario["activo"] == 1:
            await context.bot.send_message(chat_id=chat_id, text=f"👋 Bienvenido, {usuario['nombre']}!", reply_markup=menu_usuario())
        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ No tienes acceso al bot.")
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Operación cancelada.")

    return ConversationHandler.END