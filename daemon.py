#!/usr/bin/env python3
"""Daemon script for running the bot on PythonAnywhere.
Auto-restarts bot.py if it crashes."""

import os
import sys
import time

BOT_SCRIPT = "bot.py"
RESTART_DELAY = 5  # seconds before restart

def main():
    restarts = 0
    while True:
        print(f"[DAEMON] Starting bot.py (restart #{restarts})...")
        try:
            exit_code = os.system(f"{sys.executable} {BOT_SCRIPT}")
            print(f"[DAEMON] bot.py exited with code {exit_code}")
        except KeyboardInterrupt:
            print("[DAEMON] Interrupted by user. Stopping.")
            break
        except Exception as e:
            print(f"[DAEMON] Unexpected error: {e}")

        restarts += 1
        if restarts > 10:
            print("[DAEMON] Too many restarts. Stopping to avoid loop.")
            break

        print(f"[DAEMON] Restarting in {RESTART_DELAY} seconds...")
        time.sleep(RESTART_DELAY)

if __name__ == "__main__":
    main()