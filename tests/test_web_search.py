import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import asyncio

import pytest

from scrapers.models import Product

HTML_IMOTRIZ = """
<html><body>
<div class="card d-flex flex-column bg-white border">
  <section class="mb-auto">
    <a class="description" href="/producto/abc/92101s1000/faro-delantero-lh">
      <h2>Faro Delantero Lh Santa Fe 2018-2021</h2>
      <p>Faro Delantero Lh</p>
    </a>
    <p><strong>Marca:</strong> hyundai</p>
    <span><strong>Nº de parte:</strong> 92101S10**</span>
  </section>
  <a href="/producto/abc/92101s1000/faro-delantero-lh">
    <img src="https://image.imotriz.com/uploads/faro.webp"/>
  </a>
</div>
</body></html>
"""


def _producto(nombre, precio, sitio="Mansuera", pais="Ecuador", url="https://x.com/p"):
    return Product(
        codigo="TEST-1", nombre=nombre, precio_usd=precio, moneda_original="USD",
        precio_original=precio, funcion="Faro Delantero", lado="Derecho",
        tecnologia="LED", compatibilidad=[], sitio=sitio, pais=pais, url=url,
    )


@pytest.fixture(autouse=True)
def limpiar_cache():
    import web_search
    web_search.CACHE._data = {}
    web_search.CACHE._save()
    yield
    web_search.CACHE._data = {}
    web_search.CACHE._save()


def test_buscar_repuesto_web_con_scrapers(monkeypatch):
    import web_search

    class FakeAggregator:
        async def search(self, codigo, nombre=""):
            return {
                "ecuador": [_producto("Faro derecho", 25.0, pais="Ecuador")],
                "internacional": [_producto("Faro headlight", 15.0,
                                            sitio="AliExpress", pais="Internacional")],
                "todos": [
                    _producto("Faro headlight", 15.0, sitio="AliExpress", pais="Internacional"),
                    _producto("Faro derecho", 25.0, pais="Ecuador"),
                ],
            }

    monkeypatch.setattr(web_search, "SearchAggregator", FakeAggregator)

    resultado = asyncio.run(web_search.buscar_repuesto_web("TEST-1", "faro"))
    assert resultado is not None
    assert resultado["codigo"] == "TEST-1"
    assert resultado["total_ecuador"] == 1
    assert resultado["total_internacional"] == 1
    assert len(resultado["resultados_ecuador"]) == 1
    assert len(resultado["todos_los_resultados"]) == 2
    assert "Scrapers especializados" in resultado["fuente"]
    # El dict serializable via JSON
    import json
    json.dumps(resultado)


def test_buscar_repuesto_web_fallback_generico(monkeypatch):
    import web_search

    class FakeAggregator:
        async def search(self, codigo, nombre=""):
            return {"ecuador": [], "internacional": [], "todos": []}

    async def fake_generico(codigo, nombre=""):
        return {"codigo": codigo, "nombre_busqueda": nombre, "marca": "Toyota",
                "modelo": "Corolla", "lado": None, "tipo": None,
                "precio_ecuador": None, "snippets": ["fragmento prueba"],
                "fuente": "DuckDuckGo + Bing + Brave (scraping)"}

    monkeypatch.setattr(web_search, "SearchAggregator", FakeAggregator)
    monkeypatch.setattr(web_search, "_buscar_en_motores_genericos", fake_generico)

    resultado = asyncio.run(web_search.buscar_repuesto_web("TEST-2", "faro"))
    assert resultado is not None
    assert resultado["marca"] == "Toyota"
    assert "DuckDuckGo" in resultado["fuente"]


def test_buscar_repuesto_web_sin_resultados(monkeypatch):
    import web_search

    class FakeAggregator:
        async def search(self, codigo, nombre=""):
            return {"ecuador": [], "internacional": [], "todos": []}

    async def fake_generico(codigo, nombre=""):
        return None

    monkeypatch.setattr(web_search, "SearchAggregator", FakeAggregator)
    monkeypatch.setattr(web_search, "_buscar_en_motores_genericos", fake_generico)

    resultado = asyncio.run(web_search.buscar_repuesto_web("TEST-3", "faro"))
    assert resultado is None


def test_buscar_repuesto_web_codigo_invalido():
    import web_search
    resultado = asyncio.run(web_search.buscar_repuesto_web("!!!", "faro"))
    assert resultado is None


def test_formatear_resultado_web_nuevo_formato():
    from handlers.utils import _formatear_resultado

    resultado = {
        "codigo": "TEST-1",
        "nombre_busqueda": "faro",
        "resultados_ecuador": [_producto("Faro derecho", 25.0).to_dict()],
        "resultados_internacional": [
            _producto("Faro headlight", 15.0, sitio="AliExpress",
                      pais="Internacional").to_dict()
        ],
        "todos_los_resultados": [
            _producto("Faro headlight", 15.0, sitio="AliExpress",
                      pais="Internacional").to_dict(),
            _producto("Faro derecho", 25.0).to_dict(),
        ],
        "total_ecuador": 1,
        "total_internacional": 1,
        "fuente": "Scrapers especializados (Ecuador + Internacional)",
    }
    texto = _formatear_resultado(resultado)
    assert "BÚSQUEDA WEB" in texto
    assert "RESULTADOS EN ECUADOR (1)" in texto
    assert "RESULTADOS INTERNACIONALES (1)" in texto
    assert "$25.00 USD" in texto
    assert "$15.00 USD" in texto
    assert "AliExpress" in texto
    assert "Total: 1 Ecuador + 1 Internacional" in texto
    # Prioridad Ecuador: aparece primero que Internacional
    assert texto.index("ECUADOR") < texto.index("INTERNACIONALES")


def test_formatear_resultado_web_escape_html():
    from handlers.utils import _formatear_resultado

    p = _producto("Faro <script>", 10.0).to_dict()
    p["sitio"] = "<b>Hack</b>"
    resultado = {
        "codigo": "TEST-X",
        "resultados_ecuador": [p],
        "resultados_internacional": [],
        "todos_los_resultados": [p],
        "total_ecuador": 1,
        "total_internacional": 0,
    }
    texto = _formatear_resultado(resultado)
    assert "<script>" not in texto
    assert "&lt;script&gt;" in texto


def test_formatear_resultado_web_formato_clasico():
    from handlers.utils import _formatear_resultado

    resultado = {
        "codigo": "TEST-2",
        "marca": "Toyota",
        "modelo": "Corolla",
        "tipo": "faro",
        "lado": "Izquierdo",
        "precio_ecuador": "$120.00",
        "snippets": ["snippet uno", "snippet dos"],
        "fuente": "DuckDuckGo + Bing + Brave (scraping)",
    }
    texto = _formatear_resultado(resultado)
    assert "Toyota" in texto
    assert "$120.00" in texto
    assert "snippet uno" in texto


def test_formatear_resultado_web_sin_resultados():
    from handlers.utils import _formatear_resultado

    resultado = {
        "codigo": "TEST-3",
        "resultados_ecuador": [],
        "resultados_internacional": [],
        "total_ecuador": 0,
        "total_internacional": 0,
    }
    texto = _formatear_resultado(resultado)
    assert "No se encontraron resultados" in texto


def test_formatear_resultado_web_orig_moneda():
    from handlers.utils import _formatear_resultado

    import asyncio
    from scrapers.international.aliexpress import AliExpressScraper

    s = AliExpressScraper()
    p = asyncio.run(s._build_product(
        codigo="LX-1", nombre_texto="Brake pad",
        precio_texto="€38.50", url_producto="//x.com/i",
    )).to_dict()
    resultado = {
        "codigo": "LX-1",
        "resultados_ecuador": [],
        "resultados_internacional": [p],
        "todos_los_resultados": [p],
        "total_ecuador": 0,
        "total_internacional": 1,
    }
    texto = _formatear_resultado(resultado)
    assert "orig: EUR" in texto


def test_formatear_resultado_producto_sin_precio():
    """Un catálogo bajo cotización (precio 0) no debe mostrarse como $0.00."""
    from handlers.utils import _formatear_resultado
    from scrapers.ecuador.imotriz import ImotrizScraper

    s = ImotrizScraper()
    s._query_codigo = "92101S1000"
    p = s._parse(HTML_IMOTRIZ)[0].to_dict()
    resultado = {
        "codigo": "92101S1000",
        "resultados_ecuador": [p],
        "resultados_internacional": [],
        "todos_los_resultados": [p],
        "total_ecuador": 1,
        "total_internacional": 0,
    }
    texto = _formatear_resultado(resultado)
    assert "Precio a consultar" in texto
    assert "$0.00" not in texto
    assert "Faro Delantero Lh Santa Fe 2018-2021" in texto

class TestTerminoBusquedaWeb:
    """El término de búsqueda web debe incorporar la descripción de la BD."""

    def test_une_nombre_y_descripcion(self):
        from handlers.utils import _termino_busqueda_web
        rep = {'nombre': 'Faro de compuerta',
               'descripcion': 'Faro de compuerta derecha Ranault Sandero'}
        # La descripción ya contiene el nombre: no se repite.
        assert _termino_busqueda_web(rep) == 'Faro de compuerta derecha Ranault Sandero'

    def test_no_duplica_si_la_descripcion_ya_esta_en_el_nombre(self):
        from handlers.utils import _termino_busqueda_web
        rep = {'nombre': 'Faro delantero', 'descripcion': 'faro delantero derecho kia soluto'}
        assert _termino_busqueda_web(rep) == 'faro delantero derecho kia soluto'

    def test_antepone_el_nombre_ingresado_por_el_usuario(self):
        from handlers.utils import _termino_busqueda_web
        rep = {'nombre': 'Faro', 'descripcion': 'Faro delantero derecho Toyota RAV4'}
        assert _termino_busqueda_web(rep, 'faro kia sportage') == \
            'faro kia sportage Faro delantero derecho Toyota RAV4'

    def test_sin_repuesto_devuelve_el_nombre_ingresado(self):
        from handlers.utils import _termino_busqueda_web
        assert _termino_busqueda_web(None, 'Faro Kia Soluto') == 'Faro Kia Soluto'
        assert _termino_busqueda_web({}, '') == ''

    def test_no_duplica_el_nombre_que_viene_del_mismo_registro(self):
        import sqlite3
        from handlers.utils import _termino_busqueda_web
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE repuestos (codigo, nombre, descripcion)")
        con.execute("INSERT INTO repuestos VALUES ('92102H7000', 'Faro Kia Soluto',"
                    " 'Faro delantero Kia Soluto lado derecho año 2021 2023')")
        fila = con.execute("SELECT * FROM repuestos").fetchone()
        # El handler pasa nombre=fila['nombre']: no debe quedar "Faro Kia Soluto
        # Faro delantero Kia Soluto...".
        assert _termino_busqueda_web(fila, fila["nombre"]) == \
            'Faro delantero Kia Soluto lado derecho año 2021 2023'

    def test_limita_la_longitud_del_termino(self):
        from handlers.utils import MAX_TERMINO_BUSQUEDA, _termino_busqueda_web
        rep = {'nombre': 'Faro', 'descripcion': 'detalle ' * 60}
        assert len(_termino_busqueda_web(rep)) <= MAX_TERMINO_BUSQUEDA

    def test_acepta_sqlite3_row_como_en_la_base_real(self):
        import sqlite3
        from handlers.utils import _termino_busqueda_web
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE repuestos (codigo, nombre, descripcion)")
        con.execute("INSERT INTO repuestos VALUES ('92102H7000', 'Faro Kia Soluto',"
                    " 'Faro delantero Kia Soluto lado derecho año 2021 2023')")
        fila = con.execute("SELECT * FROM repuestos").fetchone()
        # obtener_repuesto() devuelve sqlite3.Row, no dict: no debe explotar.
        assert _termino_busqueda_web(fila) == \
            'Faro delantero Kia Soluto lado derecho año 2021 2023'

    def test_fila_sin_descripcion_no_falla(self):
        import sqlite3
        from handlers.utils import _termino_busqueda_web
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE repuestos (codigo, nombre, descripcion)")
        con.execute("INSERT INTO repuestos VALUES ('X1', 'Retrovisor', NULL)")
        fila = con.execute("SELECT * FROM repuestos").fetchone()
        assert _termino_busqueda_web(fila) == 'Retrovisor'
