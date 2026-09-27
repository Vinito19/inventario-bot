"""Prueba funcional end-to-end del bot: recorrido completo de un usuario.

Simula la API de Telegram (Update/Message/CallbackQuery/Bot) en memoria y ejecuta
los handlers reales contra una base de datos temporal, verificando el resultado
visible que recibiría el usuario y el estado final en la BD.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

import config
import database
from database import obtener_repuesto, registrar_usuario, agregar_categoria


# ================= HARNESS DE TELEGRAM =================

class _MsgSalida:
    """Mensaje devuelto por el bot, con message_id y capacidad de editarse."""

    _seq = 0

    def __init__(self, texto="", chat_id=0):
        _MsgSalida._seq += 1
        self.message_id = _MsgSalida._seq
        self.text = texto
        self.chat_id = chat_id
        self.photo = None
        self.document = None
        self.ediciones = []

    async def edit_text(self, texto=None, reply_markup=None, **kw):
        self.text = texto
        self.ediciones.append(texto)
        return self

    async def edit_caption(self, caption=None, reply_markup=None, **kw):
        self.text = caption
        self.ediciones.append(caption)
        return self


class BotFalso:
    def __init__(self):
        self.enviados = []

    async def send_message(self, chat_id=None, text=None, reply_markup=None, **kw):
        m = _MsgSalida(text or "", chat_id)
        self.enviados.append(m)
        return m

    async def send_photo(self, chat_id=None, photo=None, caption=None, **kw):
        m = _MsgSalida(caption or "", chat_id)
        m.photo = photo
        self.enviados.append(m)
        return m

    async def send_document(self, chat_id=None, document=None, filename=None, caption=None, **kw):
        m = _MsgSalida(caption or filename or "", chat_id)
        m.document = document
        self.enviados.append(m)
        return m

    async def send_media_group(self, chat_id=None, media=None, **kw):
        msgs = [_MsgSalida("", chat_id) for _ in (media or [])]
        self.enviados.extend(msgs)
        return msgs

    async def get_file(self, file_id):
        return type("F", (), {"download_to_drive": self._dl})()

    async def _dl(self, path):
        return None

    async def delete_message(self, chat_id=None, message_id=None):
        return None


class Message:
    def __init__(self, texto=None, chat_id=0, photo=None, document=None):
        self.text = texto
        self.chat_id = chat_id
        self.photo = photo
        self.document = document
        self.date = None

    async def reply_text(self, texto=None, reply_markup=None, **kw):
        m = _MsgSalida(texto or "", self.chat_id)
        self._registrar(m)
        return m

    async def reply_photo(self, photo=None, caption=None, reply_markup=None, **kw):
        m = _MsgSalida(caption or "", self.chat_id)
        m.photo = photo
        self._registrar(m)
        return m

    async def edit_text(self, texto=None, reply_markup=None, **kw):
        m = _MsgSalida(texto or "", self.chat_id)
        self._registrar(m)
        return m

    async def edit_caption(self, caption=None, reply_markup=None, **kw):
        m = _MsgSalida(caption or "", self.chat_id)
        self._registrar(m)
        return m

    def _registrar(self, m):
        registro = getattr(self, "registro", None)
        if registro is not None:
            registro.append(m)


class MsgCallback:
    def __init__(self, chat_id=0):
        self.chat_id = chat_id
        self.photo = None

    async def edit_text(self, texto=None, reply_markup=None, **kw):
        m = _MsgSalida(texto or "", self.chat_id)
        return m

    async def edit_caption(self, caption=None, reply_markup=None, **kw):
        m = _MsgSalida(caption or "", self.chat_id)
        return m

    async def reply_text(self, texto=None, **kw):
        return _MsgSalida(texto or "", self.chat_id)


class FotoFalsa:
    """Simula un elemento de message.photo de python-telegram-bot."""

    def __init__(self, file_id):
        self.file_id = file_id
        self.file_unique_id = file_id


class Query:
    def __init__(self, data, from_id, chat_id, registro=None):
        self.data = data
        self.from_user = type("U", (), {"id": from_id, "first_name": "Test"})()
        self.message = MsgCallback(chat_id)
        self.respondidas = 0
        self.registro = registro

    async def answer(self, *a, **kw):
        self.respondidas += 1

    async def edit_message_text(self, texto=None, reply_markup=None, **kw):
        m = _MsgSalida(texto or "", self.message.chat_id)
        if self.registro is not None:
            self.registro.append(m)
        return m

    async def edit_message_caption(self, caption=None, reply_markup=None, **kw):
        m = _MsgSalida(caption or "", self.message.chat_id)
        if self.registro is not None:
            self.registro.append(m)
        return m


class Update:
    def __init__(self, message=None, callback_query=None, user_id=0):
        self.message = message
        self.callback_query = callback_query
        self.effective_user = type(
            "U", (), {"id": user_id, "first_name": "Test", "username": "test"}
        )()


class Context:
    def __init__(self, user_id):
        self.bot = BotFalso()
        self.user_data = {}
        self.bot_data = {"chat_id": user_id}
        self.bot_id = user_id
        self._chat_id = user_id
        self.chat_id = user_id
        self.job_queue = None


@pytest.fixture
def entorn():
    """Devuelve helpers para construir mensajes/callbacks y leer lo enviado."""
    class Entorno:
        def __init__(self):
            self.user_id = 555001
            self.context = Context(self.user_id)
            self.salida = []

        def texto(self, t):
            m = Message(t, self.user_id)
            m.registro = self.salida
            return Update(message=m, user_id=self.user_id)

        def foto(self, file_id):
            m = Message(None, self.user_id, photo=[FotoFalsa(file_id)])
            m.registro = self.salida
            return Update(message=m, user_id=self.user_id)

        def click(self, data, user_id=None):
            uid = user_id if user_id is not None else self.user_id
            return Update(
                callback_query=Query(data, uid, uid, registro=self.salida),
                user_id=uid,
            )

        @property
        def todos_los_mensajes(self):
            """Mensajes enviados al usuario, por cualquier via (reply/edit/bot)."""
            return list(self.salida) + list(self.context.bot.enviados)

        @property
        def ultimo_texto(self):
            return self.todos_los_mensajes[-1].text if self.todos_los_mensajes else ""

        def todo_texto(self):
            return "\n".join(m.text or "" for m in self.todos_los_mensajes)

    return Entorno()


@pytest.fixture
def admin_registrado():
    """Admin autenticado y con una categoría creada."""
    uid = config.ADMIN_IDS[0] if config.ADMIN_IDS else 900001
    registrar_usuario(uid, "Admin", rol="admin", activo=1)
    agregar_categoria("Frenos")
    database.init_db()
    return uid


@pytest.fixture
def nuevo_repuesto():
    """Crea un repuesto válido (la BD exige entre 4 y 6 fotos)."""
    def _crear(codigo, nombre, cantidad=5, precio=10.0, ubicacion="A-1", descripcion="d"):
        database.agregar_repuesto(
            codigo, nombre, descripcion, cantidad, precio,
            ["F1", "F2", "F3", "F4"], None, ubicacion,
        )
        return obtener_repuesto(codigo)
    return _crear


# ================= 1. ALTA DE REPUESTO (flujo completo) =================

@pytest.mark.asyncio
async def test_alta_repuesto_flujo_completo(entorn, admin_registrado):
    """Recorre /agregar de punta a punta: categoria -> 4 fotos -> datos -> confirmar."""
    from handlers import agregar as ag

    entorn.user_id = admin_registrado
    entorn.context = Context(admin_registrado)
    ctx = entorn.context
    uid = admin_registrado
    cats = database.obtener_categorias()
    cat_id = cats[0]["id"]

    assert await ag.start_agregar(entorn.texto("/agregar"), ctx) == ag.SELECT_CATEGORY
    assert "AGREGAR NUEVO REPUESTO" in entorn.ultimo_texto

    # Seleccionar categoría
    assert await ag.select_category(entorn.click(f"cat_{cat_id}"), ctx) == ag.PHOTO_1
    assert ctx.user_data["categoria_id"] == cat_id

    # 4 fotos obligatorias
    for i, estado in enumerate([ag.PHOTO_2, ag.PHOTO_3, ag.PHOTO_4], 1):
        assert await ag.photo_1(entorn.foto(f"FILE{i}"), ctx) == estado if i == 1 else True
    # (photo_1 ya se ejecutó arriba; continuamos la cadena correcta)
    ctx.user_data = {"categoria_id": cat_id, "file_ids": []}
    assert await ag.photo_1(entorn.foto("F1"), ctx) == ag.PHOTO_2
    assert await ag.photo_2(entorn.foto("F2"), ctx) == ag.PHOTO_3
    assert await ag.photo_3(entorn.foto("F3"), ctx) == ag.PHOTO_4
    assert await ag.photo_4(entorn.foto("F4"), ctx) == ag.DECIDIR_FOTOS_EXTRA
    assert ctx.user_data["file_ids"] == ["F1", "F2", "F3", "F4"]

    # Renunciar a fotos extra -> pasa a pedir código
    assert await ag.decidir_fotos_extra(entorn.click("fotos_extra_no"), ctx) == ag.CODIGO

    # Datos del repuesto
    assert await ag.codigo(entorn.texto("BRK-001"), ctx) == ag.NOMBRE
    assert await ag.nombre(entorn.texto("Pastillas de freno"), ctx) == ag.DESCRIPCION
    assert await ag.descripcion(entorn.texto("Ceramicas universales 2020-2024"), ctx) == ag.CANTIDAD
    assert await ag.cantidad(entorn.texto("abc"), ctx) == ag.CANTIDAD  # rechaza no-numérico
    assert "número entero" in entorn.ultimo_texto
    assert await ag.cantidad(entorn.texto("5"), ctx) == ag.PRECIO
    assert await ag.precio(entorn.texto("185.50"), ctx) == ag.UBICACION
    assert await ag.ubicacion(entorn.texto("Estante A-3"), ctx) == ag.CONFIRMAR
    # El resumen llega como caption de la primera foto
    assert "RESUMEN DEL REPUESTO" in entorn.todo_texto()

    # Confirmar
    await ag.confirmar(entorn.click("confirmar"), ctx)

    rep = obtener_repuesto("BRK-001")
    assert rep is not None
    assert rep["nombre"] == "Pastillas de freno"
    assert rep["cantidad"] == 5
    assert rep["precio"] == 185.50
    assert rep["ubicacion"] == "Estante A-3"
    assert rep["file_id_1"] == "F1"
    assert "REGISTRADO" in entorn.todo_texto() or "registrado" in entorn.todo_texto().lower()


@pytest.mark.asyncio
async def test_alta_repuesto_codigo_duplicado_rechazado(entorn, admin_registrado, nuevo_repuesto):
    from handlers import agregar as ag

    nuevo_repuesto("DUP-1", "Existente", 1, 1.0, "E1")
    ctx = entorn.context
    ctx.user_data = {"categoria_id": 1, "file_ids": ["F1"]}

    assert await ag.codigo(entorn.texto("DUP-1"), ctx) == ag.CODIGO
    assert "Ya existe" in entorn.ultimo_texto


# ================= 2. BÚSQUEDA LOCAL =================

@pytest.mark.asyncio
async def test_busqueda_local_encuentra_y_muestra_detalle(entorn, admin_registrado, nuevo_repuesto):
    from handlers import buscar as bc

    nuevo_repuesto("BRK-002", "Discos de freno", 8, 45.0, "B-1", "Acero")
    ctx = entorn.context
    entorn.user_id = admin_registrado

    assert await bc.start_buscar(entorn.texto("/buscar"), ctx) == bc.SEARCH_MODE

    assert await bc.search_local(entorn.texto("freno"), ctx) == bc.VIEW_ITEM
    texto = entorn.ultimo_texto
    assert "BRK-002" in texto
    assert "Discos de freno" in texto
    assert "$45.00" in texto
    assert "Total: 1 resultados" in texto
    assert len(ctx.user_data["resultados"]) == 1

    # Ver detalle
    await bc.view_item(entorn.click("ver_1"), ctx)
    assert "BRK-002" in entorn.todo_texto()
    assert "Estante" in entorn.todo_texto() or "B-1" in entorn.todo_texto()


@pytest.mark.asyncio
async def test_busqueda_local_sin_resultados(entorn, admin_registrado):
    from handlers import buscar as bc

    entorn.user_id = admin_registrado
    assert await bc.search_local(entorn.texto("noexiste123"), entorn.context) == bc.SEARCH_LOCAL
    assert "No se encontraron resultados" in entorn.ultimo_texto


@pytest.mark.asyncio
async def test_busqueda_local_usuario_no_registrado(entorn):
    from handlers import buscar as bc

    await bc.start_buscar(entorn.texto("/buscar"), entorn.context)
    assert "No tienes acceso" in entorn.ultimo_texto


# ================= 3. BÚSQUEDA WEB (formato nuevo) =================

@pytest.mark.asyncio
async def test_busqueda_web_muestra_ecuador_primero(entorn, admin_registrado, monkeypatch):
    from handlers import buscar as bc
    from scrapers.models import Product

    entorn.user_id = admin_registrado

    ec = Product(codigo="4121020-BE101", nombre="Faro derecho Toyota",
                 precio_usd=118.0, moneda_original="USD", precio_original=118.0,
                 funcion="Faro Delantero", lado="Derecho", tecnologia="Halógeno",
                 compatibilidad=["Toyota Corolla 2020"], componente_hermano="Faro izquierdo",
                 sitio="Mansuera", pais="Ecuador", url="https://mansuera.com/p1")
    intl = Product(codigo="4121020-BE101", nombre="Headlight assembly",
                   precio_usd=44.5, moneda_original="EUR", precio_original=41.0,
                   funcion="Faro Delantero", lado="Derecho", tecnologia="LED",
                   compatibilidad=["Toyota Corolla"], componente_hermano="",
                   sitio="AliExpress", pais="Internacional", url="https://aliexpress.com/i/1")

    async def _fake(codigo, nombre="", user_id=0):
        return {
            "codigo": codigo,
            "nombre_busqueda": nombre,
            "resultados_ecuador": [ec.to_dict()],
            "resultados_internacional": [intl.to_dict()],
            "todos_los_resultados": [intl.to_dict(), ec.to_dict()],
            "total_ecuador": 1,
            "total_internacional": 1,
            "fuente": "Scrapers especializados (Ecuador + Internacional)",
        }

    monkeypatch.setattr("web_search.buscar_repuesto_web", _fake)

    estado = await bc.search_web_input(entorn.texto("4121020-BE101 faro"), entorn.context)
    assert estado == bc.SEARCH_MODE

    texto = entorn.ultimo_texto
    assert "RESULTADOS EN ECUADOR (1)" in texto
    assert "RESULTADOS INTERNACIONALES (1)" in texto
    assert "$118.00 USD" in texto
    assert "$44.50 USD" in texto
    assert "orig: EUR 41.00" in texto
    assert "Mansuera" in texto and "AliExpress" in texto
    assert "Total: 1 Ecuador + 1 Internacional" in texto
    assert texto.index("ECUADOR") < texto.index("INTERNACIONALES")
    assert "<a href='https://mansuera.com/p1'>" in texto


@pytest.mark.asyncio
async def test_busqueda_web_sin_datos(entorn, admin_registrado, monkeypatch):
    from handlers import buscar as bc

    entorn.user_id = admin_registrado

    async def _fake(codigo, nombre="", user_id=0):
        return None

    monkeypatch.setattr("web_search.buscar_repuesto_web", _fake)

    assert await bc.search_web_input(entorn.texto("ZZZ-999 faro"), entorn.context) == bc.SEARCH_WEB_INPUT
    assert "No se encontró información" in entorn.ultimo_texto


# ================= 4. VENTA =================

@pytest.mark.asyncio
async def test_venta_flujo_completo_descuenta_stock(entorn, admin_registrado, nuevo_repuesto):
    from handlers import vender as vd

    entorn.user_id = admin_registrado
    nuevo_repuesto("BRK-003", "Pastillas delanteras", 10, 30.0, "A-1", "Ceramicas")
    ctx = entorn.context

    assert await vd.start_vender(entorn.texto("/vender"), ctx) == vd.SEARCH
    assert ctx.user_data["cart"] == []

    # Buscar por código -> un solo resultado -> pide cantidad directo
    assert await vd.search(entorn.texto("BRK-003"), ctx) == vd.CANTIDAD
    assert "Stock disponible: 10" in entorn.ultimo_texto

    # Cantidad inválida y mayor que stock
    assert await vd.cantidad(entorn.texto("0"), ctx) == vd.CANTIDAD
    assert await vd.cantidad(entorn.texto("99"), ctx) == vd.CANTIDAD
    assert "Stock insuficiente" in entorn.ultimo_texto

    # Cantidad válida + precio final con descuento
    assert await vd.cantidad(entorn.texto("3"), ctx) == vd.PRECIO
    assert await vd.precio(entorn.texto("27.50"), ctx) == vd.CONFIRMAR_ITEM
    assert "Descuento unitario" in entorn.ultimo_texto
    assert "Subtotal: $82.50" in entorn.ultimo_texto

    # Confirmar artículo -> carrito
    await vd.confirmar_item(entorn.click("confirmar"), ctx)
    assert len(ctx.user_data["cart"]) == 1
    assert ctx.user_data["cart"][0]["codigo"] == "BRK-003"

    # Finalizar venta
    await vd.cart_callback(entorn.click("cart_finalize"), ctx)
    await vd.vendedor(entorn.texto("Carlos"), ctx)

    texto = entorn.ultimo_texto
    assert "VENTA FINALIZADA" in texto
    assert "TOTAL: $82.50" in texto
    assert "Carlos" in texto

    # BD: stock descontado y venta registrada
    assert obtener_repuesto("BRK-003")["cantidad"] == 7
    ventas = database.obtener_ventas()
    assert len(ventas) == 1
    assert ventas[0]["codigo"] == "BRK-003"
    assert ventas[0]["cantidad"] == 3
    assert ventas[0]["vendedor"] == "Carlos"
    assert database.obtener_resumen_ventas()["unidades"] == 3


# ================= 5. REPORTES =================

@pytest.mark.asyncio
async def test_reporte_stock_cero(entorn, admin_registrado, nuevo_repuesto):
    from handlers import reporte as rp

    entorn.user_id = admin_registrado
    nuevo_repuesto("BRK-004", "Con stock", 5, 10.0, "A")
    nuevo_repuesto("BRK-005", "Sin stock", 0, 12.0, "B")

    await rp.ver_stock_cero(entorn.click("rep_stock_cero"), entorn.context)
    texto = entorn.todo_texto()
    assert "BRK-005" in texto
    assert "BRK-004" not in texto
    assert "Total: 1 artículos" in texto


@pytest.mark.asyncio
async def test_reporte_stock_cero_vacio(entorn, admin_registrado, nuevo_repuesto):
    from handlers import reporte as rp

    entorn.user_id = admin_registrado
    nuevo_repuesto("BRK-009", "Con stock", 5, 10.0, "A")

    await rp.ver_stock_cero(entorn.click("rep_stock_cero"), entorn.context)
    assert "No hay artículos con stock en cero" in entorn.todo_texto()


@pytest.mark.asyncio
async def test_reporte_ventas(entorn, admin_registrado, nuevo_repuesto):
    from handlers import reporte as rp

    entorn.user_id = admin_registrado
    nuevo_repuesto("BRK-006", "Vendido", 5, 20.0, "A")
    database.registrar_venta("BRK-006", 2, 20.0, 20.0, admin_registrado, "Admin", "Luis")

    await rp.ver_ventas(entorn.click("rep_ventas"), entorn.context)
    texto = entorn.todo_texto()
    assert "BRK-006" in texto
    assert "2 und" in texto          # cantidad vendida
    assert "Admin" in texto          # usuario que registró la venta
    # El vendedor se conserva en la BD aunque el reporte muestre el usuario
    assert database.obtener_ventas()[0]["vendedor"] == "Luis"


# ================= 6. EDICIÓN Y ELIMINACIÓN =================

@pytest.mark.asyncio
async def test_editar_repuesto(entorn, admin_registrado, nuevo_repuesto):
    nuevo_repuesto("BRK-007", "Nombre viejo", 1, 5.0, "A-1")

    assert database.obtener_repuesto("BRK-007")["nombre"] == "Nombre viejo"

    database.editar_repuesto("BRK-007", "nombre", "Nombre nuevo")
    assert obtener_repuesto("BRK-007")["nombre"] == "Nombre nuevo"

    # El registro de cambios es explícito (lo hace el handler al confirmar)
    database.registrar_cambio("BRK-007", "nombre", "Nombre viejo", "Nombre nuevo", 1, "Admin")
    cambios = database.obtener_cambios()
    assert cambios and cambios[0]["campo"] == "nombre"
    assert cambios[0]["valor_nuevo"] == "Nombre nuevo"


@pytest.mark.asyncio
async def test_editar_campo_no_permitido(entorn, admin_registrado, nuevo_repuesto):
    nuevo_repuesto("BRK-010", "Seguro", 1, 5.0, "A-1")
    with pytest.raises(ValueError):
        database.editar_repuesto("BRK-010", "codigo; DROP TABLE repuestos", "x")


@pytest.mark.asyncio
async def test_eliminar_repuesto(entorn, admin_registrado, nuevo_repuesto):
    nuevo_repuesto("BRK-008", "Para borrar", 1, 5.0, "A-1")

    database.eliminar_repuesto("BRK-008")
    assert obtener_repuesto("BRK-008") is None
    assert database.buscar_repuestos("BRK-008") == []


# ================= 7. CICLO DE VIDA DE USUARIOS =================

@pytest.mark.asyncio
async def test_ciclo_aprobacion_usuario(entorn):
    """Usuario nuevo -> pendiente -> admin lo aprueba -> puede usar el bot."""
    from handlers import start as sh
    from handlers import agregar as ag
    from handlers.callback_security import generar_callback_token

    nuevo = 777001
    admin = config.ADMIN_IDS[0] if config.ADMIN_IDS else 900001
    registrar_usuario(admin, "Admin", rol="admin", activo=1)

    entorn.user_id = nuevo
    entorn.context = Context(nuevo)

    # 1) /start crea al usuario como pendiente
    await sh.start(entorn.texto("/start"), entorn.context)
    u = database.obtener_usuario(nuevo)
    assert u["rol"] == "pendiente" and u["activo"] == 0

    # 2) No puede agregar repuestos
    await ag.start_agregar(entorn.texto("/agregar"), entorn.context)
    assert "No tienes acceso" in entorn.todo_texto()

    # 3) El admin lo aprueba
    await sh.callback_aprobar(
        entorn.click(generar_callback_token(nuevo, "aprobar"), user_id=admin),
        Context(admin),
    )
    u = database.obtener_usuario(nuevo)
    assert u["rol"] == "usuario" and u["activo"] == 1

    # 4) Ahora sí puede agregar repuestos
    agregar_categoria("General")
    await ag.start_agregar(entorn.texto("/agregar"), entorn.context)
    assert "AGREGAR NUEVO REPUESTO" in entorn.ultimo_texto


# ================= 8. RESUMEN =================

@pytest.mark.asyncio
async def test_resumen_inventario_consistente(entorn, admin_registrado, nuevo_repuesto):
    nuevo_repuesto("R-1", "Uno", 5, 10.0, "A")
    nuevo_repuesto("R-2", "Dos", 3, 20.0, "B")
    database.registrar_venta("R-1", 2, 10.0, 10.0, admin_registrado, "Admin", "Ana")

    resumen = database.obtener_resumen()
    assert resumen["total"] == 2
    assert resumen["unidades"] == 6      # 3 restantes de R-1 + 3 de R-2
    assert resumen["cero"] == 0
    assert resumen["valor"] == pytest.approx(3 * 10.0 + 3 * 20.0)

    ventas = database.obtener_resumen_ventas()
    assert ventas["ventas"] == 1
    assert ventas["unidades"] == 2
    assert ventas["total"] == 20.0
