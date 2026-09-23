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
        logging.FileHandler(os.path.join(ROOT, "bot_runner.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("bot_runner")


async def alert_admin(text: str):
    """Envía mensaje a todos los admins via Bot API directo (sin depender del bot corriendo)."""
    try:
        import aiohttp
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        for admin_id in config.ADMIN_IDS:
            payload = {"chat_id": admin_id, "text": text, "parse_mode": "HTML"}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status != 200:
                        log.warning(f"Alerta a admin {admin_id} falló: {resp.status}")
    except Exception as e:
        log.error(f"No se pudo alertar a admin: {e}")


def run_bot():
    """Ejecuta bot.py como subprocess y retorna (returncode, stdout, stderr)."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "bot.py"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    # Leer salida en tiempo real y loguear
    for line in proc.stdout:
        print(line, end="")  # También a consola
    proc.wait()
    return proc.returncode


async def main():
    restart_count = 0
    max_restarts = 10
    restart_window = 300  # 5 min
    restarts = []

    log.info("=" * 50)
    log.info("INICIANDO WRAPPER DEL BOT")
    log.info(f"Admins configurados: {config.ADMIN_IDS}")
    log.info("=" * 50)

    # Alerta de inicio
    await alert_admin(
        f"🟢 <b>BOT INICIADO</b>\n"
        f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Wrapper PID: {os.getpid()}"
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
                f"🔵 <b>BOT DETENIDO LIMPIAMENTE</b>\n"
                f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Exit code: 0"
            )
            break

        restart_count += 1
        log.error(f"Bot cayó con exit code {rc}. Reinicios en ventana: {len(restarts)}")

        # Alerta de crash
        await alert_admin(
            f"🔴 <b>BOT CAYÓ - REINICIANDO</b>\n"
            f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Exit code: {rc}\n"
            f"Reinicio #{restart_count}\n"
            f"Reinicios en últimos 5 min: {len(restarts)}"
        )

        if len(restarts) >= max_restarts:
            log.critical("Demasiados reinicios en poco tiempo. Abortando.")
            await alert_admin(
                f"💀 <b>BOT ABORTADO: DEMASIADOS CRASHES</b>\n"
                f"Más de {max_restarts} reinicios en {restart_window//60} min.\n"
                f"Requiere intervención manual."
            )
            break

        wait = min(30 * restart_count, 300)  # Backoff: 30s, 60s, 90s... máx 5 min
        log.info(f"Esperando {wait}s antes de reiniciar...")
        await asyncio.sleep(wait)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Wrapper detenido por usuario (Ctrl+C)")
        asyncio.run(alert_admin(
            f"🟡 <b>WRAPPER DETENIDO MANUALMENTE</b>\n"
            f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ))