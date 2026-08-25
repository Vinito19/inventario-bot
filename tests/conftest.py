import os
import sys
import tempfile

# Asegurar que el proyecto raiz sea importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Aislar la base de datos en un directorio temporal ANTES de importar database
_TMPDIR = tempfile.mkdtemp(prefix="vch_test_")
os.environ["VCH_TEST_DIR"] = _TMPDIR

import database
from database import DB_NAME

# Redirigir la DB de prueba a un archivo temporal y unico por sesion
database.DB_NAME = os.path.join(_TMPDIR, "test_inventario.db")
DB_NAME_TEST = database.DB_NAME

import pytest


@pytest.fixture(autouse=True)
def _clean_db():
    """Resetea la base de datos antes de cada test."""
    database.init_db()
    yield
    # Limpiar todas las tablas al terminar cada test
    import sqlite3
    conn = sqlite3.connect(database.DB_NAME)
    try:
        for tabla in ("repuestos", "categorias", "usuarios", "configuracion"):
            conn.execute(f"DELETE FROM {tabla}")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def tmp_img():
    """Crea una imagen temporal de prueba."""
    from PIL import Image

    ruta = os.path.join(_TMPDIR, "test_imagen.jpg")
    img = Image.new("RGB", (200, 150), color=(14, 165, 233))
    img.save(ruta, "JPEG")
    return ruta


@pytest.fixture
def tmp_img_vertical():
    """Crea una imagen vertical temporal de prueba."""
    from PIL import Image

    ruta = os.path.join(_TMPDIR, "test_imagen_v.jpg")
    img = Image.new("RGB", (150, 200), color=(200, 50, 50))
    img.save(ruta, "JPEG")
    return ruta