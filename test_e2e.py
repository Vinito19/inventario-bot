#!/usr/bin/env python3
"""
Test E2E real contra bot vivo (polling).
Uso: python test_e2e.py
Requisito: bot corriendo en otra terminal (python bot.py)
"""
import asyncio
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config
from telegram import Bot, Update, Message, User, Chat
from telegram.ext import Application
from datetime import datetime

ADMIN_ID = config.ADMIN_IDS[0] if config.ADMIN_IDS else 6296592750
BOT_TOKEN = config.BOT_TOKEN

async def run_e2e():
    print(f"[+] Conectando a bot {BOT_TOKEN[:10]}... como admin {ADMIN_ID}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    await app.initialize()
    await app.start()
    print("[OK] Application iniciada")

    try:
        # ---------- 1. /start como admin ----------
        print("\n[TEST 1] /start admin")
        upd = Update(
            update_id=1,
            message=Message(
                message_id=1,
                date=datetime.now(),
                chat=Chat(id=ADMIN_ID, type='private'),
                from_user=User(id=ADMIN_ID, first_name='AdminTest', is_bot=False),
                text='/start'
            )
        )
        await app.process_update(upd)
        print("   -> /start procesado (debe mostrar menu admin)")

        # ---------- 2. /reporte ----------
        print("\n[TEST 2] /reporte")
        upd = Update(
            update_id=2,
            message=Message(
                message_id=2,
                date=datetime.now(),
                chat=Chat(id=ADMIN_ID, type='private'),
                from_user=User(id=ADMIN_ID, first_name='AdminTest', is_bot=False),
                text='/reporte'
            )
        )
        await app.process_update(upd)
        print("   -> /reporte procesado (debe mostrar resumen + botones)")

        # ---------- 3. /categorias ----------
        print("\n[TEST 3] /categorias")
        upd = Update(
            update_id=3,
            message=Message(
                message_id=3,
                date=datetime.now(),
                chat=Chat(id=ADMIN_ID, type='private'),
                from_user=User(id=ADMIN_ID, first_name='AdminTest', is_bot=False),
                text='/categorias'
            )
        )
        await app.process_update(upd)
        print("   -> /categorias procesado")

        # ---------- 4. /usuarios ----------
        print("\n[TEST 4] /usuarios")
        upd = Update(
            update_id=4,
            message=Message(
                message_id=4,
                date=datetime.now(),
                chat=Chat(id=ADMIN_ID, type='private'),
                from_user=User(id=ADMIN_ID, first_name='AdminTest', is_bot=False),
                text='/usuarios'
            )
        )
        await app.process_update(upd)
        print("   -> /usuarios procesado")

        # ---------- 5. Callback "inicio" (volver al menú) ----------
        print("\n[TEST 5] Callback 'inicio'")
        from telegram import CallbackQuery
        cb = CallbackQuery(
            id='test_cb_1',
            from_user=User(id=ADMIN_ID, first_name='AdminTest', is_bot=False),
            chat_instance='test',
            data='inicio',
            message=Message(
                message_id=5,
                date=datetime.now(),
                chat=Chat(id=ADMIN_ID, type='private'),
                from_user=User(id=ADMIN_ID, first_name='AdminTest', is_bot=False),
                text='Menú anterior'
            )
        )
        upd = Update(update_id=5, callback_query=cb)
        await app.process_update(upd)
        print("   -> Callback 'inicio' procesado")

        print("\n[OK] TODOS LOS TESTS E2E ENVIADOS")
        print("   Revisa tu Telegram: debes ver respuestas del bot a cada comando")

    finally:
        await app.stop()
        await app.shutdown()
        print("[OK] Application detenida")

if __name__ == '__main__':
    asyncio.run(run_e2e())