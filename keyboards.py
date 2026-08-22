from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def menu_admin():
    keyboard = [
        [InlineKeyboardButton("➕ Agregar repuesto", callback_data="agregar")],
        [InlineKeyboardButton("🔍 Buscar repuesto", callback_data="buscar")],
        [InlineKeyboardButton("✏️ Editar stock/repuesto", callback_data="editar")],
        [InlineKeyboardButton("📊 Reporte + Exportar Excel", callback_data="reporte")],
        [InlineKeyboardButton("🧹 Limpiar stock en cero", callback_data="limpiar")],
        [InlineKeyboardButton("🗑️ Eliminar repuesto", callback_data="eliminar")],
        [InlineKeyboardButton("📂 Gestionar categorías", callback_data="categorias")],
        [InlineKeyboardButton("👤 Gestionar usuarios", callback_data="usuarios")],
    ]
    return InlineKeyboardMarkup(keyboard)


def menu_usuario():
    keyboard = [
        [InlineKeyboardButton("➕ Agregar repuesto", callback_data="agregar")],
        [InlineKeyboardButton("🔍 Buscar repuesto", callback_data="buscar")],
        [InlineKeyboardButton("✏️ Editar stock/repuesto", callback_data="editar")],
        [InlineKeyboardButton("📊 Ver reporte", callback_data="reporte")],
    ]
    return InlineKeyboardMarkup(keyboard)


def menu_categorias(categorias, puede_agregar=True):
    keyboard = []
    for cat in categorias:
        keyboard.append([InlineKeyboardButton(f"📂 {cat['nombre']}", callback_data=f"cat_{cat['id']}")])
    if puede_agregar:
        keyboard.append([InlineKeyboardButton("➕ Agregar categoría", callback_data="agregar_categoria")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
    return InlineKeyboardMarkup(keyboard)


def menu_editar():
    keyboard = [
        [InlineKeyboardButton("📦 Modificar cantidad", callback_data="editar_cantidad")],
        [InlineKeyboardButton("💰 Modificar precio", callback_data="editar_precio")],
        [InlineKeyboardButton("📍 Modificar ubicación", callback_data="editar_ubicacion")],
        [InlineKeyboardButton("📝 Modificar nombre", callback_data="editar_nombre")],
        [InlineKeyboardButton("📝 Modificar descripción", callback_data="editar_descripcion")],
        [InlineKeyboardButton("📷 Actualizar fotos", callback_data="editar_fotos")],
        [InlineKeyboardButton("📂 Cambiar categoría", callback_data="editar_categoria")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")],
    ]
    return InlineKeyboardMarkup(keyboard)


def menu_cantidad():
    keyboard = [
        [
            InlineKeyboardButton("+1", callback_data="cant_1"),
            InlineKeyboardButton("+5", callback_data="cant_5"),
            InlineKeyboardButton("+10", callback_data="cant_10"),
        ],
        [
            InlineKeyboardButton("-1", callback_data="cant_-1"),
            InlineKeyboardButton("-5", callback_data="cant_-5"),
            InlineKeyboardButton("-10", callback_data="cant_-10"),
        ],
        [InlineKeyboardButton("🔢 Cantidad personalizada", callback_data="cant_custom")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")],
    ]
    return InlineKeyboardMarkup(keyboard)


def menu_confirmar():
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="confirmar"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def botones_volver():
    keyboard = [
        [InlineKeyboardButton("🏠 Volver al menú", callback_data="inicio")],
    ]
    return InlineKeyboardMarkup(keyboard)


def menu_resultados(resultados):
    keyboard = []
    for i, r in enumerate(resultados[:10], 1):
        keyboard.append([
            InlineKeyboardButton(
                f"👁️ {i}. {r['codigo']} - {r['nombre']}",
                callback_data=f"ver_{i}",
            )
        ])
    keyboard.append([InlineKeyboardButton("🔍 Nueva búsqueda", callback_data="buscar")])
    keyboard.append([InlineKeyboardButton("🏠 Volver al menú", callback_data="inicio")])
    return InlineKeyboardMarkup(keyboard)


def menu_detalle_repuesto():
    keyboard = [
        [InlineKeyboardButton("📤 Compartir por WhatsApp", callback_data="compartir_whatsapp")],
        [InlineKeyboardButton("🔍 Nueva búsqueda", callback_data="buscar")],
        [InlineKeyboardButton("🏠 Volver al menú", callback_data="inicio")],
    ]
    return InlineKeyboardMarkup(keyboard)


def botones_usuario_pendientes(usuarios):
    keyboard = []
    for u in usuarios:
        keyboard.append([
            InlineKeyboardButton(
                f"👤 {u['nombre']} ({u['user_id']})",
                callback_data=f"ver_user_{u['user_id']}",
            ),
        ])
    keyboard.append([InlineKeyboardButton("❌ Volver", callback_data="inicio")])
    return InlineKeyboardMarkup(keyboard)


def botones_admin_aprobar_rechazar(user_id):
    keyboard = [
        [
            InlineKeyboardButton("✅ Aprobar", callback_data=f"aprobar_{user_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_{user_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def botones_usuarios(usuarios):
    keyboard = []
    for u in usuarios:
        rol_icono = "👑" if u["rol"] == "admin" else "👤"
        estado = "✅" if u["activo"] else "❌"
        keyboard.append([
            InlineKeyboardButton(
                f"{rol_icono} {u['nombre']} {estado}",
                callback_data=f"ver_user_{u['user_id']}",
            ),
        ])
    keyboard.append([InlineKeyboardButton("➕ Agregar usuario", callback_data="agregar_usuario")])
    keyboard.append([InlineKeyboardButton("❌ Volver", callback_data="inicio")])
    return InlineKeyboardMarkup(keyboard)


def botones_detalle_usuario(usuario):
    uid = usuario["user_id"]
    texto_estado = "🟢 Activar" if not usuario["activo"] else "🔴 Desactivar"
    texto_rol = "⬇️ Quitar admin" if usuario["rol"] == "admin" else "⬆️ Hacer admin"
    keyboard = [
        [InlineKeyboardButton(texto_estado, callback_data=f"cambiar_estado_{uid}")],
        [InlineKeyboardButton(texto_rol, callback_data=f"cambiar_rol_{uid}")],
        [InlineKeyboardButton("🗑️ Eliminar usuario", callback_data=f"eliminar_usuario_{uid}")],
        [InlineKeyboardButton("❌ Volver", callback_data="usuarios")],
    ]
    return InlineKeyboardMarkup(keyboard)