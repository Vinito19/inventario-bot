import sqlite3

import pytest
import database
from database import (
    init_db,
    registrar_admins,
    registrar_usuario,
    obtener_usuario,
    es_admin,
    esta_registrado,
    aprobar_usuario,
    cambiar_estado_usuario,
    obtener_usuarios,
    eliminar_usuario_db,
    contar_admins_activos,
    agregar_categoria,
    obtener_categorias,
    obtener_categoria_por_nombre,
    eliminar_categoria,
    agregar_repuesto,
    obtener_repuesto,
    buscar_repuestos,
    editar_repuesto,
    editar_repuesto_fotos,
    eliminar_repuesto,
    obtener_stock_cero,
    eliminar_stock_cero,
    obtener_resumen,
    get_config,
    set_config,
    registrar_venta,
    obtener_ventas,
    obtener_resumen_ventas,
    registrar_cambio,
    obtener_cambios,
    DB_NAME,
)


def _fotos():
    return [f"file_{i}" for i in range(1, 5)]


@pytest.fixture(autouse=True)
def setup_categoria():
    cat_id = agregar_categoria("Frenos")
    return cat_id


# ---------- USUARIOS ----------

def test_registrar_y_obtener_usuario():
    registrar_usuario(111, "Juan", rol="usuario", activo=1)
    u = obtener_usuario(111)
    assert u["nombre"] == "Juan"
    assert u["rol"] == "usuario"
    assert u["activo"] == 1


def test_registrar_admins():
    registrar_admins([999])
    u = obtener_usuario(999)
    assert u["rol"] == "admin"
    assert u["activo"] == 1


def test_es_admin_y_esta_registrado():
    registrar_usuario(222, "Ana", rol="admin", activo=1)
    registrar_usuario(333, "Pedro", rol="usuario", activo=1)
    assert es_admin(222) is True
    assert es_admin(333) is False
    assert esta_registrado(222) is True


def test_usuario_desactivado_no_esta_registrado():
    registrar_usuario(444, "Luis", rol="usuario", activo=1)
    cambiar_estado_usuario(444, 0)
    assert esta_registrado(444) is False


def test_aprobar_usuario():
    registrar_usuario(555, "Rol", rol="pendiente", activo=0)
    aprobar_usuario(555)
    u = obtener_usuario(555)
    assert u["rol"] == "usuario"
    assert u["activo"] == 1


def test_obtener_usuarios_orden():
    registrar_usuario(1, "A")
    registrar_usuario(2, "B")
    usuarios = obtener_usuarios()
    ids = [u["user_id"] for u in usuarios]
    assert 1 in ids and 2 in ids


def test_eliminar_usuario_db():
    registrar_usuario(666, "X")
    eliminar_usuario_db(666)
    assert obtener_usuario(666) is None


def test_contar_admins_activos():
    registrar_admins([100, 101])
    assert contar_admins_activos() >= 2


# ---------- CATEGORIAS ----------

def test_agregar_y_obtener_categorias(setup_categoria):
    categorias = obtener_categorias()
    nombres = [c["nombre"] for c in categorias]
    assert "Frenos" in nombres


def test_categoria_duplicada_ignorada(setup_categoria):
    cat_id = agregar_categoria("frenos")  # duplicado case-insensitive en BD? NO, UNIQUE es case-sensitive
    # La constraint UNIQUE es sensible a mayusculas en SQLite, asi que 'frenos' != 'Frenos'
    assert cat_id is not None


def test_obtener_categoria_por_nombre_nocase(setup_categoria):
    c = obtener_categoria_por_nombre("frenos")
    assert c is not None
    assert c["nombre"] == "Frenos"


def test_eliminar_categoria_setea_null(setup_categoria):
    repuesto = {
        "codigo": "T-001", "nombre": "Test", "descripcion": "d",
        "cantidad": 5, "precio": 10.0, "file_ids": _fotos(),
        "categoria_id": setup_categoria, "ubicacion": "A1",
    }
    agregar_repuesto(**repuesto)
    eliminar_categoria(setup_categoria)
    r = obtener_repuesto("T-001")
    assert r["categoria_id"] is None


# ---------- REPUESTOS ----------

def test_agregar_y_obtener_repuesto(setup_categoria):
    agregar_repuesto("R-001", "Pastilla", "desc", 10, 5.5, _fotos(), setup_categoria, "B2")
    r = obtener_repuesto("R-001")
    assert r["nombre"] == "Pastilla"
    assert r["cantidad"] == 10
    assert r["categoria_nombre"] == "Frenos"


def test_agregar_repuesto_requiere_4_fotos(setup_categoria):
    with pytest.raises(ValueError):
        agregar_repuesto("R-002", "X", "d", 1, 1.0, ["f1"], setup_categoria, "A")


def test_agregar_codigo_duplicado_error(setup_categoria):
    agregar_repuesto("R-003", "A", "d", 1, 1.0, _fotos(), setup_categoria, "A")
    with pytest.raises(ValueError):
        agregar_repuesto("R-003", "B", "d", 1, 1.0, _fotos(), setup_categoria, "A")


def test_buscar_repuestos(setup_categoria):
    agregar_repuesto("BRK-001", "Pastillas freno", "ceramica", 5, 20.0, _fotos(), setup_categoria, "A")
    agregar_repuesto("BRK-002", "Disco freno", "ventilado", 3, 50.0, _fotos(), setup_categoria, "B")

    res = buscar_repuestos("freno")
    assert len(res) >= 2

    res2 = buscar_repuestos("BRK-001")
    assert len(res2) >= 1
    assert res2[0]["codigo"] == "BRK-001"


def test_buscar_escapa_wildcards(setup_categoria):
    agregar_repuesto("100%", "Pct", "d", 1, 1.0, _fotos(), setup_categoria, "A")
    res = buscar_repuestos("100%")
    assert len(res) >= 1


def test_editar_repuesto(setup_categoria):
    agregar_repuesto("E-001", "Nombre", "d", 1, 1.0, _fotos(), setup_categoria, "A")
    editar_repuesto("E-001", "precio", 99.9)
    editar_repuesto("E-001", "cantidad", 7)
    r = obtener_repuesto("E-001")
    assert r["precio"] == 99.9
    assert r["cantidad"] == 7


def test_editar_repuesto_campo_no_permitido(setup_categoria):
    agregar_repuesto("E-002", "N", "d", 1, 1.0, _fotos(), setup_categoria, "A")
    with pytest.raises(ValueError):
        editar_repuesto("E-002", "codigo; DROP TABLE repuestos;--", 1)


def test_editar_repuesto_fotos(setup_categoria):
    agregar_repuesto("E-003", "N", "d", 1, 1.0, _fotos(), setup_categoria, "A")
    nuevas = ["n1", "n2", "n3", "n4"]
    editar_repuesto_fotos("E-003", nuevas)
    r = obtener_repuesto("E-003")
    assert r["file_id_1"] == "n1"
    assert r["file_id_4"] == "n4"


def test_eliminar_repuesto(setup_categoria):
    agregar_repuesto("E-004", "N", "d", 1, 1.0, _fotos(), setup_categoria, "A")
    eliminar_repuesto("E-004")
    assert obtener_repuesto("E-004") is None


def test_stock_cero(setup_categoria):
    agregar_repuesto("Z-001", "Cero", "d", 0, 1.0, _fotos(), setup_categoria, "A")
    agregar_repuesto("Z-002", "Con", "d", 5, 1.0, _fotos(), setup_categoria, "A")
    cero = obtener_stock_cero()
    codigos = [r["codigo"] for r in cero]
    assert "Z-001" in codigos
    assert "Z-002" not in codigos


def test_eliminar_stock_cero(setup_categoria):
    agregar_repuesto("Z-003", "A", "d", 0, 1.0, _fotos(), setup_categoria, "A")
    agregar_repuesto("Z-004", "B", "d", 4, 1.0, _fotos(), setup_categoria, "A")
    n = eliminar_stock_cero()
    assert n == 1
    assert obtener_repuesto("Z-003") is None
    assert obtener_repuesto("Z-004") is not None


def test_obtener_resumen(setup_categoria):
    agregar_repuesto("R-100", "A", "d", 3, 10.0, _fotos(), setup_categoria, "A")
    agregar_repuesto("R-101", "B", "d", 2, 5.0, _fotos(), setup_categoria, "A")
    res = obtener_resumen()
    assert res["total"] == 2
    assert res["unidades"] == 5
    assert res["valor"] == 40.0
    assert res["cero"] == 0
    assert any(c["nombre"] == "Frenos" for c in res["por_categoria"])


# ---------- CONFIGURACION ----------

def test_set_get_config():
    set_config("clave_test", "valor123")
    assert get_config("clave_test") == "valor123"


def test_get_config_inexistente():
    assert get_config("no_existe") is None


# ---------- VENTAS ----------

def test_registrar_venta_descuenta_stock(setup_categoria):
    agregar_repuesto("V-001", "Pastilla", "d", 10, 5.0, _fotos(), setup_categoria, "A")
    res = registrar_venta("V-001", 2, 4.0, 5.0, 999, "Admin")
    r = obtener_repuesto("V-001")
    assert res["nuevo_stock"] == 8
    assert r["cantidad"] == 8
    assert res["subtotal"] == 8.0  # 2 * 4.0


def test_registrar_venta_stock_insuficiente(setup_categoria):
    agregar_repuesto("V-002", "Disco", "d", 3, 5.0, _fotos(), setup_categoria, "A")
    with pytest.raises(ValueError):
        registrar_venta("V-002", 5, 5.0, 5.0, 999, "Admin")
    # Stock intacto tras fallo
    assert obtener_repuesto("V-002")["cantidad"] == 3


def test_registrar_venta_cantidad_cero(setup_categoria):
    agregar_repuesto("V-003", "Filtro", "d", 5, 5.0, _fotos(), setup_categoria, "A")
    with pytest.raises(ValueError):
        registrar_venta("V-003", 0, 5.0, 5.0, 999, "Admin")


def test_obtener_ventas_y_resumen(setup_categoria):
    agregar_repuesto("V-004", "Bujia", "d", 20, 10.0, _fotos(), setup_categoria, "A")
    registrar_venta("V-004", 3, 9.0, 10.0, 111, "Juan")
    registrar_venta("V-004", 2, 10.0, 10.0, 111, "Juan")
    ventas = obtener_ventas()
    assert len(ventas) == 2
    res = obtener_resumen_ventas()
    assert res["ventas"] == 2
    assert res["unidades"] == 5
    assert abs(res["total"] - (3 * 9.0 + 2 * 10.0)) < 0.01


# ---------- HISTORIAL DE CAMBIOS ----------

def test_registrar_y_obtener_cambios(setup_categoria):
    agregar_repuesto("C-001", "Pastilla", "d", 10, 5.0, _fotos(), setup_categoria, "A")
    registrar_cambio("C-001", "precio", 5.0, 6.5, 999, "Admin")
    registrar_cambio("C-001", "cantidad", 10, 8, 111, "Juan")
    cambios = obtener_cambios()
    assert len(cambios) == 2
    assert cambios[0]["campo"] == "cantidad"
    assert cambios[0]["valor_anterior"] == "10"
    assert cambios[0]["usuario_nombre"] == "Juan"