import os
import sys
import tempfile
import shutil
import atexit

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


def _cleanup_temp_dir():
    """Limpia el directorio temporal al salir."""
    try:
        if os.path.exists(_TMPDIR):
            shutil.rmtree(_TMPDIR, ignore_errors=True)
    except Exception:
        pass


# Registrar limpieza automática al finalizar la sesión de pytest
atexit.register(_cleanup_temp_dir)


# Limpieza de cachés y artefactos al inicio de la sesión
def pytest_sessionstart(session):
    """Limpia cachés y archivos temporales antes de empezar."""
    for cache_dir in [".pytest_cache", "__pycache__", "tests/__pycache__", "handlers/__pycache__"]:
        path = os.path.join(ROOT, cache_dir)
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)


def pytest_sessionfinish(session, exitstatus):
    """Limpia al terminar la sesión completa."""
    _cleanup_temp_dir()
    # Limpiar cachés residuales
    for cache_dir in [".pytest_cache", "__pycache__", "tests/__pycache__", "handlers/__pycache__"]:
        path = os.path.join(ROOT, cache_dir)
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)


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