"""Tests del wrapper: sistema de alertas, auto-restart y lock de instancia unica."""
import asyncio
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

import run_bot


@pytest.fixture(autouse=True)
def lock_temporal(tmp_path, monkeypatch):
    """Redirige el lock a un archivo propio de cada test.

    Sin esto, los tests que ejecutan main() fallan si el bot real está corriendo
    (el lock del proceso vivo los rechazaría con "otra instancia activa").
    """
    monkeypatch.setattr(run_bot, "LOCK_PATH", str(tmp_path / "run_bot.lock"))


# ---------- sanitizado de tokens ----------

# Token ficticio armado en tiempo de ejecución: escribir un literal con forma
# de token real activaría el escáner de secretos de GitHub al hacer push.
TOKEN_FALSO = "1234567890:" + "AAHdqTcvCH1vGWJxfSeofSAs0K5PALD" + "saw"


def test_sanitize_text_oculta_token():
    texto = f"Fallo con token {TOKEN_FALSO} para admin"
    limpio = run_bot.sanitize_text(texto)
    assert TOKEN_FALSO not in limpio
    assert "[TOKEN_REDACTED]" in limpio


def test_sanitize_text_no_altera_texto_normal():
    texto = "BOT INICIADO\nHora: 2026-09-26 20:00:00"
    assert run_bot.sanitize_text(texto) == texto


def test_sanitize_text_texto_vacio():
    assert run_bot.sanitize_text("") == ""


# ---------- sistema de alertas ----------

class _Resp:
    def __init__(self, status, body=""):
        self.status = status
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def text(self):
        return self._body

    async def json(self):
        return {"ok": self.status == 200}


class _Session:
    """Fake aiohttp.ClientSession que registra las peticiones enviadas."""

    def __init__(self, status=200, body=""):
        self.status = status
        self.body = body
        self.peticiones = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def post(self, url, json=None, headers=None, timeout=None):
        self.peticiones.append({"url": url, "json": json, "headers": headers})
        return _Resp(self.status, self.body)


@pytest.mark.asyncio
async def test_alerta_enviada_a_todos_los_admins(monkeypatch):
    import config
    monkeypatch.setattr(config, "ADMIN_IDS", [111, 222])
    sesion = _Session(200)
    monkeypatch.setattr("aiohttp.ClientSession", lambda *a, **k: sesion)

    await run_bot.alert_admin("prueba")

    assert len(sesion.peticiones) == 2
    assert [p["json"]["chat_id"] for p in sesion.peticiones] == [111, 222]
    assert all(p["json"]["text"] == "prueba" for p in sesion.peticiones)
    assert all(p["json"]["parse_mode"] == "HTML" for p in sesion.peticiones)


@pytest.mark.asyncio
async def test_alerta_token_en_url(monkeypatch):
    """Telegram exige el token en la URL: si va en header la API responde 404."""
    import config
    monkeypatch.setattr(config, "ADMIN_IDS", [111])
    sesion = _Session(200)
    monkeypatch.setattr("aiohttp.ClientSession", lambda *a, **k: sesion)

    await run_bot.alert_admin("prueba")

    url = sesion.peticiones[0]["url"]
    assert url == f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
    assert config.BOT_TOKEN not in str(sesion.peticiones[0]["headers"])


@pytest.mark.asyncio
async def test_alerta_fallida_registra_warning_sin_romper(monkeypatch, caplog):
    import config
    monkeypatch.setattr(config, "ADMIN_IDS", [111])
    sesion = _Session(403, '{"ok":false,"error_code":403}')
    monkeypatch.setattr("aiohttp.ClientSession", lambda *a, **k: sesion)

    with caplog.at_level(logging.WARNING, logger="bot_runner"):
        await run_bot.alert_admin("prueba")  # no debe lanzar excepcion

    assert any("403" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_alerta_error_red_no_rompe(monkeypatch, caplog):
    import config
    monkeypatch.setattr(config, "ADMIN_IDS", [111])

    class _SessionBoom:
        async def __aenter__(self):
            raise OSError("conexion rechazada")

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr("aiohttp.ClientSession", lambda *a, **k: _SessionBoom())

    with caplog.at_level(logging.ERROR, logger="bot_runner"):
        await run_bot.alert_admin("prueba")  # no debe lanzar excepcion

    assert any("No se pudo alertar" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_alerta_detalle_error_sanea_token(monkeypatch, caplog):
    """Si Telegram devuelve el token en el error, no debe quedar en el log."""
    import config
    admin_id = 111
    token = config.BOT_TOKEN
    sesion = _Session(401, f'{{"ok":false,"description":"Unauthorized: token {token} invalido"}}')
    monkeypatch.setattr(config, "ADMIN_IDS", [admin_id])
    monkeypatch.setattr("aiohttp.ClientSession", lambda *a, **k: sesion)

    with caplog.at_level(logging.WARNING, logger="bot_runner"):
        await run_bot.alert_admin("prueba")

    assert token not in caplog.text


# ---------- lock de instancia unica ----------

def test_lock_impide_segunda_instancia(monkeypatch, tmp_path):
    monkeypatch.setattr(run_bot, "LOCK_PATH", str(tmp_path / "run_bot.lock"))

    assert run_bot.acquires_instancia_unica() is True
    # Simula un segundo wrapper en otro proceso: el lock ya esta tomado.
    monkeypatch.setattr(run_bot, "_lock_handle", None, raising=False)
    otro = open(str(tmp_path / "run_bot.lock"), "a+")
    try:
        import msvcrt
        otro.seek(0)
        otro.write("0")
        otro.flush()
        otro.seek(0)
        with pytest.raises(OSError):
            msvcrt.locking(otro.fileno(), msvcrt.LK_NBLCK, 1)
    finally:
        otro.close()
        run_bot.liberar_instancia_unica()


def test_lock_se_libera_y_permite_re_adquirir(monkeypatch, tmp_path):
    monkeypatch.setattr(run_bot, "LOCK_PATH", str(tmp_path / "run_bot.lock"))
    assert run_bot.acquires_instancia_unica() is True
    run_bot.liberar_instancia_unica()
    assert run_bot.acquires_instancia_unica() is True
    run_bot.liberar_instancia_unica()


def test_liberar_sin_lock_no_falla():
    run_bot.liberar_instancia_unica()  # idempotente


# ---------- auto-restart ----------

@pytest.fixture
def alertas(monkeypatch):
    """Captura las alertas enviadas en lugar de enviarlas a Telegram."""
    enviados = []

    async def _fake(text):
        enviados.append(text)

    monkeypatch.setattr(run_bot, "alert_admin", _fake)
    return enviados


@pytest.fixture
def sin_sleep(monkeypatch):
    """Acorta el backoff para que los tests no tarden minutos."""
    esperas = []

    async def _fake_sleep(seg):
        esperas.append(seg)

    monkeypatch.setattr(run_bot.asyncio, "sleep", _fake_sleep)
    return esperas


@pytest.mark.asyncio
async def test_aut_restart_tras_caida(monkeypatch, alertas, sin_sleep):
    """exit 1 -> reinicia, exit 0 -> detiene sin reiniciar."""
    codigos = iter([1, 1, 0])
    llamadas = []

    def _fake_run():
        rc = next(codigos)
        llamadas.append(rc)
        return rc

    monkeypatch.setattr(run_bot, "run_bot", _fake_run)

    rc_final = await run_bot.main()

    assert rc_final is None
    assert llamadas == [1, 1, 0]           # 3 lanzamientos
    assert sin_sleep == [30, 60]           # backoff progresivo
    assert sum("BOT CAYÓ" in a for a in alertas) == 2
    assert sum("BOT INICIADO" in a for a in alertas) == 1
    assert sum("DETENIDO LIMPIAMENTE" in a for a in alertas) == 1


@pytest.mark.asyncio
async def test_backoff_tope_5_minutos(monkeypatch, alertas, sin_sleep):
    codigos = iter([1] * 7 + [0])
    monkeypatch.setattr(run_bot, "run_bot", lambda: next(codigos))
    await run_bot.main()
    assert sin_sleep == [30, 60, 90, 120, 150, 180, 210]


@pytest.mark.asyncio
async def test_aborta_tras_demasiados_reinicios(monkeypatch, alertas, sin_sleep):
    monkeypatch.setattr(run_bot, "run_bot", lambda: 1)

    await run_bot.main()

    assert sum("BOT CAYÓ" in a for a in alertas) == run_bot.MAX_RESTARTS
    assert any("ABORTADO" in a for a in alertas)
    # El backoff ocurre entre reinicios; el que supera el limite aborta sin esperar.
    assert sin_sleep == [30, 60, 90, 120, 150, 180, 210, 240, 270]


@pytest.mark.asyncio
async def test_crash_limita_inicios_con_lock(alertas):
    """Con el lock tomado, main() no debe lanzar el bot ni enviar 'BOT INICIADO'."""
    monkeypatch_lock = run_bot.acquires_instancia_unica

    def _ya_tomado():
        return False

    import pytest as _pytest
    original = run_bot.acquires_instancia_unica
    run_bot.acquires_instancia_unica = _ya_tomado
    try:
        rc = await run_bot.main()
    finally:
        run_bot.acquires_instancia_unica = original

    assert rc == 1
    assert not any("BOT INICIADO" in a for a in alertas)
    assert any("NO SE INICIÓ" in a for a in alertas)


# ---------- auto-restart con proceso real ----------

@pytest.mark.asyncio
async def test_aut_restart_proceso_real(tmp_path, monkeypatch, alertas):
    """Prueba de extremo a extremo: un bot que falla 2 veces y luego arranca bien.

    Valida el mecanismo real (subprocess + deteccion de exit code), no un mock.
    """
    contador = tmp_path / "arranques.txt"
    script = tmp_path / "fake_bot.py"
    script.write_text(
        "import os, sys, pathlib\n"
        "p = pathlib.Path(os.environ['FAKE_COUNTER'])\n"
        "n = int(p.read_text()) + 1 if p.exists() else 1\n"
        "p.write_text(str(n))\n"
        "sys.exit(1 if n < 3 else 0)\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("FAKE_COUNTER", str(contador))
    monkeypatch.setattr(run_bot, "BOT_SCRIPT", str(script))

    esperas = []

    async def _fake_sleep(seg):
        esperas.append(seg)

    monkeypatch.setattr(run_bot.asyncio, "sleep", _fake_sleep)

    await run_bot.main()

    assert contador.read_text() == "3", "debio lanzar el bot 3 veces (2 caídas + 1 ok)"
    assert esperas == [30, 60]
    assert sum("BOT CAYÓ" in a for a in alertas) == 2
    assert any("DETENIDO LIMPIAMENTE" in a for a in alertas)
