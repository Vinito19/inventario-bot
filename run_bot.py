#!/usr/bin/env python3
"""
Wrapper para ejecutar el bot con:
- Reinicio automático en crash
- Alerta a administrador por Telegram al caer
- Logs rotativos
"""
import os
import sys
import time
import subprocess
import logging
import asyncio
import re
from datetime import datetime

# Configurar paths
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import config

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(os.getenv("LOG_FILE", os.path.join(ROOT, "bot_runner.log")),
                            encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("bot_runner")

# Patrón para detectar tokens de Telegram en logs/URLs
# Formato: [bot]NNNNNNNNN:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX (34-35 chars after :)
TOKEN_PATTERN = re.compile(r'(?:bot)?\d{8,10}:[A-Za-z0-9_-]{34,35}\b')

LOCK_PATH = os.path.join(ROOT, "run_bot.lock")
BOT_SCRIPT = os.getenv("BOT_SCRIPT", "bot.py")
MAX_RESTARTS = int(os.getenv("MAX_RESTARTS", "10"))
RESTART_WINDOW = int(os.getenv("RESTART_WINDOW", "300"))  # ventana de reinicios (segundos)
BACKOFF_BASE = int(os.getenv("BACKOFF_BASE", "30"))
BACKOFF_MAX = int(os.getenv("BACKOFF_MAX", "300"))
_lock_handle = None


def acquires_instancia_unica() -> bool:
    """Toma un lock de archivo para garantizar una sola instancia del wrapper.

    Dos wrappers harían getUpdates simultáneos -> telegram.error.Conflict.
    El lock se mantiene abierto durante toda la vida del proceso.
    """
    global _lock_handle
    f = open(LOCK_PATH, "a+")
    try:
        f.seek(0)
        if not f.read(1):
            f.seek(0)
            f.write("0")
            f.flush()
        f.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return False
    f.seek(0)
    f.truncate()
    f.write(str(os.getpid()))
    f.flush()
    _lock_handle = f  # no cerrar: mantiene el lock
    return True


def liberar_instancia_unica():
    """Libera el lock de instancia única."""
    global _lock_handle
    if _lock_handle is None:
        return
    try:
        _lock_handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(_lock_handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        _lock_handle.close()
        _lock_handle = None


def sanitize_text(text: str) -> str:
    """Elimina tokens de Telegram del texto para evitar exposición en logs/alertas."""
    if not text:
        return text
    return TOKEN_PATTERN.sub('[TOKEN_REDACTED]', text)


async def alert_admin(text: str):
    """Envía mensaje a todos los admins via Bot API directo (sin depender del bot corriendo).
    Telegram exige el token en la URL; nunca se loguea la URL para no exponerlo."""
    try:
        import aiohttp
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        for admin_id in config.ADMIN_IDS:
            payload = {"chat_id": admin_id, "text": text, "parse_mode": "HTML"}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status != 200:
                        detalle = sanitize_text((await resp.text())[:200])
                        log.warning(f"Alerta a admin {admin_id} falló: {resp.status} {detalle}")
                    else:
                        log.info(f"Alerta enviada a admin {admin_id}")
    except Exception as e:
        log.error(f"No se pudo alertar a admin: {sanitize_text(str(e))}")


def run_bot():
    """Ejecuta bot.py como subprocess y retorna (returncode, stdout, stderr)."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, BOT_SCRIPT],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    # Leer salida en tiempo real y loguear
    for line in proc.stdout:
        print(line, end="", flush=True)  # También a consola
    proc.wait()
    return proc.returncode


async def main():
    restart_count = 0
    max_restarts = MAX_RESTARTS
    restart_window = RESTART_WINDOW  # ventana en la que se cuentan reinicios
    restarts = []

    log.info("=" * 50)
    log.info("INICIANDO WRAPPER DEL BOT")
    log.info(f"Admins configurados: {config.ADMIN_IDS}")
    log.info("=" * 50)

    # Evitar dos instancias simultáneas (provocan Conflict en getUpdates)
    if not acquires_instancia_unica():
        log.critical(
            "Ya hay otra instancia del wrapper corriendo (run_bot.lock). "
            "Ciérrala antes de iniciar otra, o el bot entrará en Conflict."
        )
        await alert_admin(
            sanitize_text(
                "🟠 <b>NO SE INICIÓ EL BOT</b>\n"
                "Ya existe otra instancia del wrapper activa.\n"
                "Cierra la anterior para evitar conflictos de polling."
            )
        )
        liberar_instancia_unica()
        return 1

    log.info(f"Lock de instancia única adquirido (PID {os.getpid()})")

    # Alerta de inicio
    await alert_admin(
        sanitize_text(
            f"🟢 <b>BOT INICIADO</b>\n"
            f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Wrapper PID: {os.getpid()}"
        )
    )

    while True:
        log.info(f"Iniciando bot (intento #{restart_count + 1})...")
        rc = run_bot()

        now = time.time()
        restarts = [t for t in restarts if now - t < restart_window]
        restarts.append(now)

        if rc == 0:
            log.info("Bot terminó limpiamente (exit 0). No se reinicia.")
            await alert_admin(
                sanitize_text(
                    f"🔵 <b>BOT DETENIDO LIMPIAMENTE</b>\n"
                    f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Exit code: 0"
                )
            )
            break

        restart_count += 1
        log.error(f"Bot cayó con exit code {rc}. Reinicios en ventana: {len(restarts)}")

        # Alerta de crash
        await alert_admin(
            sanitize_text(
                f"🔴 <b>BOT CAYÓ - REINICIANDO</b>\n"
                f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Exit code: {rc}\n"
                f"Reinicio #{restart_count}\n"
                f"Reinicios en últimos 5 min: {len(restarts)}"
            )
        )

        if len(restarts) >= max_restarts:
            log.critical("Demasiados reinicios en poco tiempo. Abortando.")
            await alert_admin(
                sanitize_text(
                    f"💀 <b>BOT ABORTADO: DEMASIADOS CRASHES</b>\n"
                    f"Más de {max_restarts} reinicios en {restart_window//60} min.\n"
                    f"Requiere intervención manual."
                )
            )
            break

        wait = min(BACKOFF_BASE * restart_count, BACKOFF_MAX)  # 30s, 60s, 90s... máx 5 min
        log.info(f"Esperando {wait}s antes de reiniciar...")
        await asyncio.sleep(wait)

    liberar_instancia_unica()
    log.info("Lock de instancia única liberado")


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()) or 0)
    except KeyboardInterrupt:
        log.info("Wrapper detenido por usuario (Ctrl+C)")
        liberar_instancia_unica()
        asyncio.run(alert_admin(
            sanitize_text(
                f"🟡 <b>WRAPPER DETENIDO MANUALMENTE</b>\n"
                f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        ))