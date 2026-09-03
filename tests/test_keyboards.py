import pytest

import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from keyboards import (
    menu_admin,
    menu_usuario,
    menu_categorias,
    menu_editar,
    menu_cantidad,
    menu_confirmar,
    botones_volver,
    menu_resultados,
    menu_detalle_repuesto,
    botones_usuario_pendientes,
    botones_admin_aprobar_rechazar,
    botones_usuarios,
    botones_detalle_usuario,
)


def _extract_data(menu):
    """Extrae todos los callback_data de un teclado."""
    datas = []
    for row in menu.inline_keyboard:
        for btn in row:
            datas.append(btn.callback_data)
    return datas


def test_menu_admin():
    m = menu_admin()
    datas = _extract_data(m)
    esperados = ["agregar", "buscar", "editar", "vender", "reporte", "limpiar",
                 "eliminar", "categorias", "usuarios"]
    for e in esperados:
        assert e in datas, f"Falta boton {e} en menu_admin"


def test_menu_usuario():
    m = menu_usuario()
    datas = _extract_data(m)
    assert "agregar" in datas
    assert "buscar" in datas
    assert "editar" in datas
    assert "vender" in datas
    assert "reporte" in datas
    # Un usuario NO debe ver opciones de admin
    assert "usuarios" not in datas
    assert "categorias" not in datas
    assert "eliminar" not in datas
    assert "limpiar" not in datas


def test_menu_categorias_con_agregar():
    cats = [{"id": 1, "nombre": "Frenos"}, {"id": 2, "nombre": "Filtros"}]
    m = menu_categorias(cats, puede_agregar=True)
    datas = _extract_data(m)
    assert "cat_1" in datas
    assert "cat_2" in datas
    assert "agregar_categoria" in datas
    assert "cancelar" in datas


def test_menu_categorias_sin_agregar():
    cats = [{"id": 1, "nombre": "Frenos"}]
    m = menu_categorias(cats, puede_agregar=False)
    datas = _extract_data(m)
    assert "agregar_categoria" not in datas  # no-admin no ve agregar


def test_menu_editar():
    m = menu_editar()
    datas = _extract_data(m)
    esperados = ["editar_cantidad", "editar_precio", "editar_ubicacion",
                 "editar_nombre", "editar_descripcion", "editar_fotos",
                 "editar_categoria", "cancelar"]
    for e in esperados:
        assert e in datas


def test_menu_cantidad():
    m = menu_cantidad()
    datas = _extract_data(m)
    for e in ["cant_1", "cant_5", "cant_10", "cant_-1", "cant_-5",
              "cant_-10", "cant_custom", "cancelar"]:
        assert e in datas


def test_menu_confirmar():
    m = menu_confirmar()
    datas = _extract_data(m)
    assert "confirmar" in datas
    assert "cancelar" in datas


def test_botones_volver():
    m = botones_volver()
    datas = _extract_data(m)
    assert "inicio" in datas


def test_menu_resultados():
    res = [
        {"codigo": "A-1", "nombre": "Pieza"},
        {"codigo": "B-2", "nombre": "Tornillo"},
    ]
    m = menu_resultados(res)
    datas = _extract_data(m)
    assert "ver_1" in datas
    assert "ver_2" in datas
    assert "buscar" in datas
    assert "inicio" in datas


def test_menu_resultados_max_10():
    res = [{"codigo": f"C-{i}", "nombre": f"N{i}"} for i in range(15)]
    m = menu_resultados(res)
    datas = _extract_data(m)
    ver_items = [d for d in datas if d.startswith("ver_")]
    assert len(ver_items) == 10  # solo los primeros 10


def test_menu_detalle_repuesto():
    m = menu_detalle_repuesto()
    datas = _extract_data(m)
    assert "proforma" in datas
    assert "buscar" in datas
    assert "inicio" in datas


def test_botones_usuario_pendientes():
    pend = [{"nombre": "Juan", "user_id": 111}]
    m = botones_usuario_pendientes(pend)
    datas = _extract_data(m)
    assert "ver_user_111" in datas


def test_botones_admin_aprobar_rechazar():
    m = botones_admin_aprobar_rechazar(123)
    datas = _extract_data(m)
    assert "aprobar_123" in datas
    assert "rechazar_123" in datas


def test_botones_usuarios():
    usuarios = [
        {"nombre": "Admin", "rol": "admin", "activo": 1, "user_id": 1},
        {"nombre": "User", "rol": "usuario", "activo": 0, "user_id": 2},
    ]
    m = botones_usuarios(usuarios)
    datas = _extract_data(m)
    assert "ver_user_1" in datas
    assert "ver_user_2" in datas
    assert "agregar_usuario" in datas
    assert "inicio" in datas


def test_botones_detalle_usuario():
    u = {"user_id": 5, "rol": "usuario", "activo": 1}
    m = botones_detalle_usuario(u)
    datas = _extract_data(m)
    assert "cambiar_estado_5" in datas
    assert "cambiar_rol_5" in datas
    assert "eliminar_usuario_5" in datas
    assert "usuarios" in datas


def test_botones_detalle_usuario_admin():
    u = {"user_id": 6, "rol": "admin", "activo": 1}
    m = botones_detalle_usuario(u)
    datas = _extract_data(m)
    assert "cambiar_rol_6" in datas  # texto depende del rol