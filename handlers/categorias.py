from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from database import (
    obtener_categorias,
    agregar_categoria,
    eliminar_categoria,
    esta_registrado,
    es_admin,
)
from keyboards import botones_volver
from handlers.utils import finalizar, edit_mensaje

ADD_CATEGORY, CONFIRMAR_DELETE = range(2)


async def start_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not esta_registrado(user_id):
        await update.message.reply_text("❌ No tienes acceso al bot.")
        return ConversationHandler.END

    try:
        categorias = obtener_categorias()
    except Exception as e:
        await update.message.reply_text(f"❌ Error al cargar categorías: {e}")
        return ConversationHandler.END

    if not categorias:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("➕ Agregar categoría", callback_data="nueva_categoria")],
            [InlineKeyboardButton("❌ Volver", callback_data="inicio")],
        ]
        await update.message.reply_text(
            "📂 No hay categorías creadas.\n\n"
            "¿Deseas crear una nueva?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CONFIRMAR_DELETE

    texto = "📂 CATEGORÍAS\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i, cat in enumerate(categorias, 1):
        texto += f"{i}. {cat['nombre']}\n"

    texto += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("➕ Agregar categoría", callback_data="nueva_categoria")],
    ]
    for cat in categorias:
        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ {cat['nombre']}",
                callback_data=f"eliminar_cat_{cat['id']}",
            ),
        ])
    keyboard.append([InlineKeyboardButton("❌ Volver", callback_data="inicio")])

    await update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRMAR_DELETE


async def callback_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not esta_registrado(user_id):
        await edit_mensaje(query, "❌ No tienes acceso al bot.")
        return ConversationHandler.END

    try:
        categorias = obtener_categorias()
    except Exception as e:
        await edit_mensaje(query, f"❌ Error al cargar categorías: {e}")
        return ConversationHandler.END

    if not categorias:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("➕ Agregar categoría", callback_data="nueva_categoria")],
            [InlineKeyboardButton("❌ Volver", callback_data="inicio")],
        ]
        await edit_mensaje(
            query,
            "📂 No hay categorías creadas.\n\n¿Deseas crear una nueva?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CONFIRMAR_DELETE

    texto = "📂 CATEGORÍAS\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i, cat in enumerate(categorias, 1):
        texto += f"{i}. {cat['nombre']}\n"

    texto += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("➕ Agregar categoría", callback_data="nueva_categoria")],
    ]
    for cat in categorias:
        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ {cat['nombre']}",
                callback_data=f"eliminar_cat_{cat['id']}",
            ),
        ])
    keyboard.append([InlineKeyboardButton("❌ Volver", callback_data="inicio")])

    await edit_mensaje(query, texto, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRMAR_DELETE


async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not es_admin(user_id):
        await update.message.reply_text("❌ Solo el administrador puede agregar categorías.")
        return ConversationHandler.END

    nombre = update.message.text.strip()
    if not nombre:
        await update.message.reply_text("⚠️ El nombre no puede estar vacío. Intenta de nuevo:")
        return ADD_CATEGORY

    try:
        existente = None
        for cat in obtener_categorias():
            if cat["nombre"].lower() == nombre.lower():
                existente = cat
                break

        if existente:
            await update.message.reply_text(
                "⚠️ Ya existe una categoría con ese nombre. Intenta con otro:"
            )
            return ADD_CATEGORY

        agregar_categoria(nombre)

        categorias = obtener_categorias()
        texto = f"✅ Categoría '{nombre}' creada!\n\n📂 CATEGORÍAS:\n\n"
        for i, cat in enumerate(categorias, 1):
            texto += f"{i}. {cat['nombre']}\n"

        await update.message.reply_text(texto, reply_markup=botones_volver())
    except Exception as e:
        await update.message.reply_text(f"❌ Error al crear categoría: {e}")
    return ConversationHandler.END


async def confirmar_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    data = query.data

    if data == "inicio":
        return await finalizar(update, context)

    if data == "categorias":
        return await callback_categorias(update, context)

    await query.answer()

    if data == "nueva_categoria":
        user_id = query.from_user.id
        if not es_admin(user_id):
            await edit_mensaje(query, "❌ Solo el administrador puede agregar categorías.")
            return ConversationHandler.END

        await edit_mensaje(
            query,
            "📝 Escribe el nombre de la nueva categoría:",
            reply_markup=botones_volver(),
        )
        return ADD_CATEGORY

    if data.startswith("eliminar_cat_"):
        user_id = query.from_user.id
        if not es_admin(user_id):
            await edit_mensaje(query, "❌ Solo el administrador puede eliminar categorías.")
            return ConversationHandler.END

        cat_id = int(data.replace("eliminar_cat_", ""))

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("✅ Sí, eliminar", callback_data=f"confirmar_eliminar_cat_{cat_id}"),
                InlineKeyboardButton("❌ No, cancelar", callback_data="categorias"),
            ]
        ]

        await edit_mensaje(
            query,
            "⚠️ ¿Eliminar esta categoría?\n\n"
            "Los repuestos asignados quedarán sin categoría.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return CONFIRMAR_DELETE

    if data.startswith("confirmar_eliminar_cat_"):
        cat_id = int(data.replace("confirmar_eliminar_cat_", ""))
        try:
            existente = obtener_categorias()
            cat_valida = any(c["id"] == cat_id for c in existente)
            if not cat_valida:
                await edit_mensaje(
                    query,
                    "❌ La categoría ya fue eliminada.",
                    reply_markup=botones_volver(),
                )
                return ConversationHandler.END
            eliminar_categoria(cat_id)
            await edit_mensaje(query, "✅ Categoría eliminada.")

            categorias = obtener_categorias()
            if categorias:
                texto = "📂 CATEGORÍAS:\n\n"
                for i, cat in enumerate(categorias, 1):
                    texto += f"{i}. {cat['nombre']}\n"
                await edit_mensaje(query, texto, reply_markup=botones_volver())
            else:
                await edit_mensaje(
                    query, "📂 No hay categorías.", reply_markup=botones_volver()
                )
        except Exception as e:
            await edit_mensaje(query, f"❌ Error al eliminar: {e}", reply_markup=botones_volver())
        return ConversationHandler.END

    return CONFIRMAR_DELETE


categorias_handler = ConversationHandler(
    entry_points=[
        CommandHandler("categorias", start_categorias),
        CallbackQueryHandler(callback_categorias, pattern="^categorias$"),
    ],
    states={
        ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category)],
        CONFIRMAR_DELETE: [
            CallbackQueryHandler(
                confirmar_delete,
                pattern="^(inicio|nueva_categoria|eliminar_cat_|confirmar_eliminar_cat_|categorias)",
            )
        ],
    },
    fallbacks=[CallbackQueryHandler(finalizar, pattern="^(inicio|cancelar)$")],
)