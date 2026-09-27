"""Bot simulado para probar el auto-restart del wrapper.

Falla 'N_FALLAS' veces (codigo de salida 1) y luego termina limpiamente (0).
Cuenta los arranques en el archivo indicado por la variable FAKE_COUNTER.
"""
import os
import pathlib
import sys

N_FALLAS = int(os.getenv("FAKE_FALLAS", "2"))
contador = pathlib.Path(os.environ["FAKE_COUNTER"])
n = int(contador.read_text()) + 1 if contador.exists() else 1
contador.write_text(str(n))
print(f"[fake_bot] arranque #{n}", flush=True)

if n <= N_FALLAS:
    print(f"[fake_bot] simulando crash (arranque #{n} de {N_FALLAS})", flush=True)
    sys.exit(1)

print("[fake_bot] arranque correcto, terminado limpiamente", flush=True)
sys.exit(0)
