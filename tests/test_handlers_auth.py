import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
import config
import database
from database import registrar_usuario


class Msg:
    def __init__(self, text=None, chat_id=1):
        self.text = text
        self.chat_id = chat_id
        self.date = None
        self.photo = None
        self.document = None

    async def reply_text(self, *args, **kwargs):
        return {"ok": True, "args": args, "kwargs": kwargs}

    async def reply_photo(self, *args, **kwargs):
        return {"ok": True, "args": args, "kwargs": kwargs}


class MockMessage:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.photo = None

    async def edit_message_text(self, *args, **kwargs):
        return {"ok": True}

    async def edit_message_caption(self, *args, **kwargs):
        return {"ok": True}


class Query:
    def __init__(self, data, from_id, chat_id):
        self.data = data
        self.from_user = type("U", (), {"id": from_id})()
        self.message = MockMessage(chat_id)

    async def answer(self):
        return None

    async def edit_message_text(self, *args, **kwargs):
        return {"ok": True}

    async def edit_message_caption(self, *args, **kwargs):
        return {"ok": True}


class User:
    def __init__(self, user_id, first_name="Test"):
        self.id = user_id
        self.first_name = first_name


class Update:
    def __init__(self, message=None, callback_query=None, effective_user=None):
        self.message = message
        self.callback_query = callback_query
        self.effective_user = effective_user or (message.effective_user if message else None)


class Bot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, reply_markup=None, **kw):
        self.sent.append((chat_id, text))
        return type("M", (), {"message_id": len(self.sent)})()

    async def send_document(self, chat_id, document, filename=None, caption=None, **kw):
        self.sent.append((chat_id, caption or filename))
        return type("M", (), {"message_id": len(self.sent)})()

    async def delete_message(self, chat_id, message_id):
        return None

    async def get_file(self, file_id):
        return type("F", (), {"download_to_drive": self._dl})()

    async def _dl(self, path):
        return None


class Context:
    def __init__(self, user_id, is_admin=False):
        self.bot = Bot()
        self.user_data = {}
        self._chat_id = user_id
        self.bot_data = {"chat_id": user_id}
        self.bot_id = user_id
        # NO registrar usuario aquí - los tests se encargan de su setup


# ---------- /start ----------

@pytest.mark.asyncio
async def test_start_nuevo_usuario_pendiente(monkeypatch):
    from handlers import start as sh

    user_id = 7001
    update = Update(
        message=Msg("", chat_id=user_id),
        effective_user=User(user_id),
    )
    context = Context(user_id)

    await sh.start(update, context)

    u = database.obtener_usuario(user_id)
    assert u is not None
    assert u["rol"] == "pendiente"
    assert u["activo"] == 0


@pytest.mark.asyncio
async def test_start_admin_existente(monkeypatch):
    from handlers import start as sh

    user_id = config.ADMIN_IDS[0] if config.ADMIN_IDS else 999
    registrar_usuario(user_id, "AdminReal", rol="admin", activo=1)
    update = Update(
        message=Msg("", chat_id=user_id),
        effective_user=User(user_id),
    )
    context = Context(user_id, is_admin=True)

    await sh.start(update, context)

    u = database.obtener_usuario(user_id)
    assert u["rol"] == "admin"


@pytest.mark.asyncio
async def test_callback_inicio_sin_acceso(monkeypatch):
    from handlers import start as sh

    user_id = 8001
    query = Query("inicio", user_id, user_id)
    update = Update(callback_query=query, effective_user=User(user_id))
    context = Context(user_id)

    await sh.callback_inicio(update, context)
    # No debe lanzar error; simplemente edita mensaje


@pytest.mark.asyncio
async def test_callback_aprobar_no_admin():
    from handlers import start as sh

    admin_id = 9001
    query = Query("aprobar_9999", admin_id, admin_id)
    update = Update(callback_query=query, effective_user=User(admin_id))
    context = Context(admin_id)  # usuario normal, no admin

    await sh.callback_aprobar(update, context)
    # No debe aprobar porque no es admin
    u = database.obtener_usuario(9999)
    assert u is None or u["rol"] != "usuario"


@pytest.mark.asyncio
async def test_callback_aprobar_admin_ok():
    from handlers import start as sh

    admin_id = 9002
    registrar_usuario(admin_id, "Admin", rol="admin", activo=1)
    pendiente_id = 7002
    registrar_usuario(pendiente_id, "Nuevo", rol="pendiente", activo=0)

    query = Query(f"aprobar_{pendiente_id}", admin_id, admin_id)
    update = Update(callback_query=query, effective_user=User(admin_id))
    context = Context(admin_id, is_admin=True)

    await sh.callback_aprobar(update, context)

    u = database.obtener_usuario(pendiente_id)
    assert u["rol"] == "usuario"
    assert u["activo"] == 1


@pytest.mark.asyncio
async def test_callback_aprobar_datos_invalidos():
    from handlers import start as sh

    admin_id = 9003
    registrar_usuario(admin_id, "Admin", rol="admin", activo=1)
    query = Query("aprobar_abc", admin_id, admin_id)
    update = Update(callback_query=query, effective_user=User(admin_id))
    context = Context(admin_id, is_admin=True)

    await sh.callback_aprobar(update, context)  # no debe lanzar
    # El handler captura ValueError y muestra mensaje de error


# ---------- utilidades edit_mensaje / finalizar ----------

@pytest.mark.asyncio
async def test_edit_mensaje_texto():
    from handlers.utils import edit_mensaje

    query = Query("dummy", 9999, 9999)
    await edit_mensaje(query, "Hola")
    # no debe lanzar


@pytest.mark.asyncio
async def test_finalizar_inicio_admin():
    from handlers.utils import finalizar

    admin_id = 9010
    registrar_usuario(admin_id, "Admin", rol="admin", activo=1)
    query = Query("inicio", admin_id, admin_id)
    update = Update(callback_query=query, effective_user=User(admin_id))
    context = Context(admin_id, is_admin=True)

    resultado = await finalizar(update, context)
    assert resultado is not None  # ConversationHandler.END


# ---------- /setlogo permisos ----------

@pytest.mark.asyncio
async def test_set_logo_no_admin():
    from handlers.proforma import set_logo_cmd

    user_id = 9101
    update = Update(message=Msg("", chat_id=user_id), effective_user=User(user_id))
    context = Context(user_id)  # usuario normal
    resultado = await set_logo_cmd(update, context)
    assert resultado is not None


@pytest.mark.asyncio
async def test_set_logo_admin():
    from handlers.proforma import set_logo_cmd

    user_id = 9102
    registrar_usuario(user_id, "Admin", rol="admin", activo=1)
    update = Update(message=Msg("", chat_id=user_id), effective_user=User(user_id))
    context = Context(user_id, is_admin=True)
    resultado = await set_logo_cmd(update, context)
    assert resultado is not None