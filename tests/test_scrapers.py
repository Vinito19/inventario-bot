import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from scrapers import (
    BaseScraper,
    Product,
    SearchAggregator,
    convert_to_usd,
    format_price_usd,
    get_exchange_rate,
    normalize_price,
    to_usd,
)


def test_normalize_price_usd():
    p = normalize_price("$ 58.15")
    assert p is not None
    assert p.amount == 58.15
    assert p.currency == "USD"


def test_normalize_price_cloud_format():
    p = normalize_price("CLP 84.999")
    assert p is not None
    assert p.amount == 84999.0
    assert p.currency == "CLP"


def test_normalize_price_comma_decimal():
    p = normalize_price("1.234,56 €")
    assert p is not None
    assert p.amount == 1234.56
    assert p.currency == "EUR"


def test_normalize_price_us_symbol():
    p = normalize_price("US$ 12.99")
    assert p is not None
    assert p.amount == 12.99
    assert p.currency == "USD"


def test_normalize_price_invalido():
    assert normalize_price("") is None
    assert normalize_price(None) is None
    assert normalize_price("solo texto") is None


def test_to_usd_usd():
    assert to_usd(100, "USD") == 100.0


def test_to_usd_conversion():
    assert to_usd(100, "USD") == 100.0
    assert to_usd(100, "EUR") > 100.0


def test_to_usd_moneda_desconocida():
    with pytest.raises(ValueError):
        to_usd(100, "XYZ")


def test_convert_to_usd_usd_async():
    assert asyncio_run(convert_to_usd(50.5, "USD")) == 50.5


def test_convert_to_usd_clp_async():
    result = asyncio_run(convert_to_usd(100000, "CLP"))
    assert result == pytest.approx(110.0)


def test_get_exchange_rate_estatica():
    assert asyncio_run(get_exchange_rate("EUR")) == 1.08
    assert asyncio_run(get_exchange_rate("usd")) == 1.0


def test_format_price_usd():
    assert format_price_usd(1234.5) == "$1,234.50"


def test_format_price_usd_cero():
    assert format_price_usd(0) == "$0.00"


def test_extract_function():
    from scrapers.base import BaseScraper

    class Dummy(BaseScraper):
        def search_url(self, query):
            return "https://x.com"

        def _parse(self, html):
            return []

    d = Dummy()
    assert d._extract_function("Faro delantero derecho") == "Faro Delantero"
    assert d._extract_function("luz diurna drl") == "Luz Diurna (DRL)"
    assert d._extract_function("espejo retrovisor") == "Espejo Retrovisor"
    assert d._extract_function("bumper") == "Parachoques"
    assert d._extract_function("caliper") == "Repuesto Automotriz"


def test_extract_side():
    from scrapers.base import BaseScraper

    class Dummy(BaseScraper):
        def search_url(self, query):
            return "https://x.com"

        def _parse(self, html):
            return []

    d = Dummy()
    assert d._extract_side("faro", "ABC-123RH") == "Derecho"
    assert d._extract_side("faro", "ABC-123LH") == "Izquierdo"
    assert d._extract_side("espejo derecho", "") == "Derecho"
    assert d._extract_side("espejo izquierdo", "") == "Izquierdo"
    assert d._extract_side("espejo", "") == "No especificado"


def test_extract_technology():
    from scrapers.base import BaseScraper

    class Dummy(BaseScraper):
        def search_url(self, query):
            return "https://x.com"

        def _parse(self, html):
            return []

    d = Dummy()
    assert d._extract_technology("faro led") == "LED"
    assert d._extract_technology("xenón") == "Xenón"
    assert d._extract_technology("halógeno") == "Halógeno"
    assert d._extract_technology("faro") == "No especificada"


def test_extract_compatibility():
    from scrapers.base import BaseScraper

    class Dummy(BaseScraper):
        def search_url(self, query):
            return "https://x.com"

        def _parse(self, html):
            return []

    d = Dummy()
    compats = d._extract_compatibility("Faro para Toyota Corolla 2018-2021")
    assert any("Toyota" in c and "2018" in c for c in compats)
    assert d._extract_compatibility("faro") == ["Verificar con vendedor"]


def test_make_product_aplica_extractores():
    from scrapers.base import BaseScraper

    class Dummy(BaseScraper):
        def search_url(self, query):
            return "https://x.com"

        def _parse(self, html):
            return []

    d = Dummy()
    d._query_codigo = "FR-200RH"
    p = d._make_product(nombre="Faro LED Chevrolet Aveo 2014",
                        extra_text="derecho",
                        precio_usd=25.0,
                        moneda_original="USD",
                        precio_original=25.0,
                        url="https://x.com/p", imagen_url="https://x.com/i.jpg")
    assert p.funcion == "Faro Delantero"
    assert p.lado == "Derecho"
    assert p.tecnologia == "LED"
    assert p.sitio == "base"
    assert p.pais == ""
    assert p.precio_usd == 25.0
    assert "Aveo" in p.nombre
    assert any("Chevrolet" in c for c in p.compatibilidad)


def test_make_product_sitio_pais():
    from scrapers.ecuador.mansuera import MansueraScraper

    s = MansueraScraper()
    # MansueraScraper (paso 6) usa SITE_NAME/COUNTRY en vez de _make_product,
    # pero hereda las properties de configuración de la base.
    assert s.name == "mansuera"
    assert s.country == "Ecuador"
    assert s.base_url == "https://www.mansuera.com"


def test_product_model():
    p = Product(
        codigo="ABC-123", nombre="Faro", precio_usd=10.0, moneda_original="USD",
        precio_original=10.0, funcion="iluminacion", lado="izquierdo",
        tecnologia="LED", compatibilidad=["Toyota Corolla", "Honda Civic"],
    )
    assert p.codigo == "ABC-123"
    assert p.pais == ""
    assert len(p.fecha_busqueda) == 19
    d = p.to_dict()
    assert d["nombre"] == "Faro"
    assert d["compatibilidad"] == ["Toyota Corolla", "Honda Civic"]
    assert "fecha_busqueda" in d


def test_product_fecha_automatica():
    p = Product(codigo="1", nombre="x", precio_usd=1.0, moneda_original="USD",
                precio_original=1.0, funcion="", lado="", tecnologia="", compatibilidad=[])
    assert p.fecha_busqueda.startswith("20")


def test_aggregator_default_scrapers():
    agg = Aggregator()
    nombres = [s.name for s in agg.scrapers]
    assert "mansuera" in nombres
    assert "imotriz" in nombres
    assert "autopartsonline" in nombres
    assert "aliexpress" in nombres
    assert "alibaba" in nombres
    assert "repuestosboston" in nombres


def test_aggregator_default_scrapers():
    agg = SearchAggregator()
    assert len(agg.ecuador_scrapers) >= 1
    assert len(agg.international_scrapers) >= 1
    assert agg.ecuador_scrapers[0].SITE_NAME == "Mansuera"
    # Sólo RepuestosBoston: responde por HTTP plano y trae precios reales.
    assert [s.SITE_NAME for s in agg.international_scrapers] == ["repuestosboston"]


def test_aggregator_excluye_sitios_no_scrapeables():
    """Alibaba bloquea el bot y AliExpress no expone la rejilla de resultados."""
    from scrapers.international.alibaba import AlibabaScraper
    from scrapers.international.aliexpress import AliExpressScraper

    agg = SearchAggregator()
    registrados = [s.name for s in agg.international_scrapers]
    assert "alibaba" not in registrados
    assert "aliexpress" not in registrados
    assert AlibabaScraper().DISPONIBLE is False
    assert AliExpressScraper().DISPONIBLE is False


def test_sitios_deshabilitados_no_consultan_red():
    """Un scraper deshabilitado devuelve [] sin tocar la red."""
    import asyncio as _asyncio

    from scrapers.international.alibaba import AlibabaScraper
    from scrapers.international.aliexpress import AliExpressScraper

    for cls in (AlibabaScraper, AliExpressScraper):
        scraper = cls()

        async def _boom(*_args, **_kwargs):
            raise AssertionError("no debe pedir HTML si DISPONIBLE es False")

        scraper._get_html = _boom
        assert _asyncio.run(scraper.search("faro")) == []


def test_aggregator_search_vacio():
    agg = SearchAggregator()
    resultados = asyncio_run(agg.search(""))
    assert set(resultados.keys()) == {"ecuador", "internacional", "todos"}
    assert resultados["ecuador"] == []
    assert resultados["internacional"] == []
    assert resultados["todos"] == []


def test_aggregator_orden_por_precio_y_clasificacion():
    from scrapers.base import BaseScraper

    class FakeScraper(BaseScraper):
        name = "fake"

        def __init__(self, items):
            super().__init__()
            self._items = items

        def search_url(self, query: str) -> str:
            return "https://fake.com"

        def _parse(self, html: str) -> list:
            return self._items

        async def search(self, codigo: str, nombre: str = ""):
            return self._items

    ecu = Product(codigo="1", nombre="EC", precio_usd=5.0, moneda_original="USD",
                  precio_original=5.0, funcion="", lado="", tecnologia="",
                  compatibilidad=[], pais="Ecuador", url="https://fake.com/ec", sitio="fake")
    us = Product(codigo="2", nombre="US", precio_usd=1.0, moneda_original="USD",
                 precio_original=1.0, funcion="", lado="", tecnologia="",
                 compatibilidad=[], pais="US", url="https://fake.com/us", sitio="fake")

    agg = SearchAggregator()
    agg.ecuador_scrapers = [FakeScraper([ecu])]
    agg.international_scrapers = [FakeScraper([us])]
    resultados = asyncio_run(agg.search("x"))
    assert resultados["ecuador"] == [ecu]
    assert resultados["internacional"] == [us]
    # "todos" ordenado por precio ascendente: us (1.0) antes que ecu (5.0)
    assert resultados["todos"] == [us, ecu]


def test_aggregator_dedupe_mismo_sitio_precio():
    from scrapers.base import BaseScraper

    class FakeScraper(BaseScraper):
        name = "fake"

        def __init__(self, items):
            super().__init__()
            self._items = items

        def search_url(self, query: str) -> str:
            return "https://fake.com"

        def _parse(self, html: str) -> list:
            return self._items

        async def search(self, codigo: str, nombre: str = ""):
            return self._items

    p1 = Product(codigo="1", nombre="A", precio_usd=10.0, moneda_original="USD",
                 precio_original=10.0, funcion="", lado="", tecnologia="",
                 compatibilidad=[], pais="US", url="https://fake.com/a", sitio="fake")
    p2 = Product(codigo="2", nombre="B", precio_usd=10.0, moneda_original="USD",
                 precio_original=10.0, funcion="", lado="", tecnologia="",
                 compatibilidad=[], pais="US", url="https://fake.com/b", sitio="fake")

    agg = SearchAggregator()
    agg.ecuador_scrapers = []
    agg.international_scrapers = [FakeScraper([p1, p2])]
    resultados = asyncio_run(agg.search("x"))
    # Dedupe por sitio+precio: mismo sitio "fake" y precio 10.0 => solo uno
    assert len(resultados["todos"]) == 1


def test_aggregator_error_scraper_no_detiene():
    from scrapers.base import BaseScraper

    class ScraperError(Exception):
        pass

    class FallidoScraper(BaseScraper):
        name = "fallido"

        def search_url(self, query: str) -> str:
            return "https://fake.com"

        def _parse(self, html: str) -> list:
            return []

        async def search(self, codigo: str, nombre: str = ""):
            raise ScraperError("boom")

    class BuenScraper(BaseScraper):
        name = "bueno"

        def search_url(self, query: str) -> str:
            return "https://fake.com"

        def _parse(self, html: str) -> list:
            return []

        async def search(self, codigo: str, nombre: str = ""):
            return [Product(codigo="1", nombre="OK", precio_usd=2.0, moneda_original="USD",
                            precio_original=2.0, funcion="", lado="", tecnologia="",
                            compatibilidad=[], pais="US", url="https://fake.com/ok", sitio="bueno")]

    agg = SearchAggregator()
    agg.ecuador_scrapers = [FallidoScraper()]
    agg.international_scrapers = [BuenScraper()]
    resultados = asyncio_run(agg.search("x"))
    assert resultados["ecuador"] == []
    assert len(resultados["internacional"]) == 1


def test_mansuera_build_product():
    import asyncio

    from scrapers.ecuador.mansuera import MansueraScraper

    s = MansueraScraper()
    p = asyncio.run(s._build_product(
        codigo="FA-101",
        nombre_texto="Faro LED derecho para Toyota 2020",
        precio_texto="$120.50",
        url_producto="/producto/faro-101",
    ))
    assert p is not None
    assert p.codigo == "FA-101"
    assert p.precio_usd == 120.5
    assert p.moneda_original == "USD"
    assert p.funcion == "Faro Delantero"
    assert p.tecnologia == "LED"
    assert p.lado == "Derecho"
    assert p.sitio == "Mansuera"
    assert p.pais == "Ecuador"
    assert p.url == "https://www.mansuera.com/producto/faro-101"


def test_mansuera_build_product_precio_invalido():
    import asyncio

    from scrapers.ecuador.mansuera import MansueraScraper

    s = MansueraScraper()
    p = asyncio.run(s._build_product(
        codigo="X", nombre_texto="Faro",
        precio_texto="Agotado",
        url_producto="",
    ))
    assert p is None


def test_mansuera_site_names():
    from scrapers.ecuador.mansuera import MansueraScraper

    s = MansueraScraper()
    assert s.SITE_NAME == "Mansuera"
    assert s.COUNTRY == "Ecuador"
    assert s.BASE_URL == "https://www.mansuera.com"


def test_aliexpress_build_product_usd():
    import asyncio

    from scrapers.international.aliexpress import AliExpressScraper

    s = AliExpressScraper()
    p = asyncio.run(s._build_product(
        codigo="LX-200",
        nombre_texto="Faro LED for Toyota 2021",
        precio_texto="$45.90",
        url_producto="https://www.aliexpress.com/item/123.html",
    ))
    assert p is not None
    assert p.codigo == "LX-200"
    assert p.precio_usd == 45.9
    assert p.moneda_original == "USD"
    assert p.sitio == "AliExpress"
    assert p.pais == "Internacional"
    assert p.tecnologia == "LED"


def test_aliexpress_build_product_eur_conversion():
    import asyncio

    from scrapers.international.aliexpress import AliExpressScraper

    s = AliExpressScraper()
    p = asyncio.run(s._build_product(
        codigo="LX-201",
        nombre_texto="Brake pad",
        precio_texto="€38.50",
        url_producto="//www.aliexpress.com/item/124.html",
    ))
    assert p is not None
    assert p.moneda_original == "EUR"
    assert p.precio_usd > 38.5  # EUR -> USD la multiplica por ~1.08
    assert p.precio_original == 38.5
    assert p.url.startswith("https:")


def test_aliexpress_build_product_sin_precio():
    import asyncio

    from scrapers.international.aliexpress import AliExpressScraper

    s = AliExpressScraper()
    p = asyncio.run(s._build_product(
        codigo="X", nombre_texto="Faro",
        precio_texto="No disponible",
        url_producto="",
    ))
    assert p is None


def test_aliexpress_site_names():
    from scrapers.international.aliexpress import AliExpressScraper

    s = AliExpressScraper()
    assert s.SITE_NAME == "AliExpress"
    assert s.COUNTRY == "Internacional"
    assert s.BASE_URL == "https://www.aliexpress.com"


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


# --------------------------------------------------------------------------
# Regresión de selectores contra la estructura REAL de cada sitio
# (capturada en producción: iMotriz Vue/Yii2, RepuestosBoston Magento,
#  AliExpress CSS modules).
# --------------------------------------------------------------------------

HTML_IMOTRIZ = """
<html><body>
<div class="card d-flex flex-column bg-white border">
  <div class="card-body d-flex flex-column p-2">
    <section class="mb-auto">
      <div class="d-flex mb-2">
        <a class="description" href="/producto/abc123/92101s1000/faro-delantero-lh">
          <h2 class="font-size-14">Faro Delantero Lh Santa Fe 2018-2021</h2>
          <p class="font-size-12">Faro Delantero Lh</p>
        </a>
      </div>
      <p class="text-muted small"><strong>Marca:</strong> hyundai</p>
      <span class="text-muted small"><strong>Nº de parte:</strong> 92101S10**</span>
    </section>
  </div>
  <a href="/producto/abc123/92101s1000/faro-delantero-lh">
    <img class="img-fluid" src="https://image.imotriz.com/uploads/store/EC/115/products/faro.webp"/>
  </a>
  <div class="text-center"><a class="btn" href="/producto/abc123/92101s1000/faro-delantero-lh">Ver detalle</a></div>
</div>
<div class="card"><a class="description" href="/sin-descripcion"><h2>x</h2></a></div>
</body></html>
"""

HTML_BOSTON = """
<html><body><ul>
<li class="item product product-item">
  <div class="product-item-info">
    <a class="product photo product-item-photo"
       href="https://www.repuestosboston.cl/986102w000-deposito.html">
      <img class="product-image-photo lazy" data-src="/media/catalog/product/9/8/986.jpg"
           src="data:image/gif;base64,R0lGOD"/>
    </a>
    <div class="product details product-item-details">
      <h2 class="product name product-item-name">
        <a class="product-item-link"
           href="https://www.repuestosboston.cl/986102w000-deposito.html">Deposito Original Santa Fe 2013 2018</a>
      </h2>
      <div class="product-item-price"><span class="price">$45.000</span></div>
    </div>
  </div>
</li>
<li class="item product product-item">
  <h2 class="product name product-item-name">
    <a class="product-item-link" href="/x.html">Sin precio</a></h2>
</li>
</ul></body></html>
"""

HTML_ALIEXPRESS = """
<html><body>
<a class="us--container--3_xK0hW cards--card--3PJxwBm search-card-item"
   href="//es.aliexpress.com/item/1005009523762459.html?algo_pvid=x">
  <div class="us--imagesGallery--2rGMU5h">
    <img class="images--item--2qh24vj" alt="Faro LED DhRpc Toyota Corolla 2015"
         src="//ae-pic-a1.aliexpress-media.com/kf/faro.jpg"/>
  </div>
  <h3 class="us--titleText--WpU1HVZ">Faro LED DhRpc Toyota Corolla 2015</h3>
  <div class="us--price--3al65BO">US $21.71</div>
</a>
<a class="search-card-item" href="//es.aliexpress.com/item/2.html">
  <h3 class="us--titleText--WpU1HVZ">Faro sin precio</h3>
</a>
</body></html>
"""


def test_imotriz_search_url_real():
    from scrapers.ecuador.imotriz import ImotrizScraper

    url = ImotrizScraper().search_url("faro delantero")
    assert url == "https://www.imotriz.com.ec/catalogo/page/results?search=faro+delantero"


def test_imotriz_parse_tarjeta_real():
    from scrapers.ecuador.imotriz import ImotrizScraper

    s = ImotrizScraper()
    s._query_codigo = "92101S1000"
    productos = s._parse(HTML_IMOTRIZ)
    assert len(productos) == 1, "sólo la tarjeta con a.description + /producto/ es válida"
    p = productos[0]
    assert p.nombre == "Faro Delantero Lh Santa Fe 2018-2021"
    assert p.url == ("https://www.imotriz.com.ec/producto/abc123/92101s1000/"
                     "faro-delantero-lh")
    assert p.imagen_url.endswith("faro.webp")
    assert p.sitio == "imotriz" and p.pais == "EC"
    # iMotriz cotiza bajo pedido: no hay precio y no se debe inventar uno.
    assert p.precio_usd == 0.0 and p.precio_original == 0.0
    assert p.funcion == "Faro Delantero"
    assert p.lado == "Izquierdo", "'lh' en el nombre debe detectarse"


def test_imotriz_usa_playwright_no_cloudscraper():
    from scrapers.ecuador.imotriz import ImotrizScraper

    s = ImotrizScraper()
    assert s.use_playwright is True
    # cloudscraper devuelve 200 con la página de reto y cortaría el Playwright.
    assert s.use_cloudscraper is False
    assert s.wait_for_selector == "a[href*='/producto/']"


def test_repuestosboston_search_url_magento():
    from scrapers.international.repuestosboston import RepuestosBostonScraper

    s = RepuestosBostonScraper()
    assert s.search_url("faro") == \
        "https://www.repuestosboston.cl/catalogsearch/result/?q=faro"
    assert s.use_playwright is False, "Magento responde en HTML plano"


def test_repuestosboston_parse_precios_en_clp():
    from scrapers.currency import to_usd
    from scrapers.international.repuestosboston import RepuestosBostonScraper

    s = RepuestosBostonScraper()
    s._query_codigo = "986102W000"
    productos = s._parse(HTML_BOSTON)
    assert len(productos) == 1, "la tarjeta sin precio se descarta"
    p = productos[0]
    assert p.nombre == "Deposito Original Santa Fe 2013 2018"
    # "$45.000" es formato chileno: 45000 CLP, NO 45 USD.
    assert p.precio_original == 45000.0
    assert p.moneda_original == "CLP"
    assert p.precio_usd == to_usd(45000.0, "CLP")
    assert p.precio_usd == pytest.approx(49.5, abs=0.01)
    assert p.imagen_url == "/media/catalog/product/9/8/986.jpg"
    assert not p.imagen_url.startswith("data:")


def test_aliexpress_search_url():
    from scrapers.international.aliexpress import AliExpressScraper

    s = AliExpressScraper()
    assert s.search_url("faro delantero") == \
        "https://www.aliexpress.com/w/wholesale-faro-delantero.html"


def test_aliexpress_parse_tarjeta_real():
    from scrapers.international.aliexpress import AliExpressScraper

    s = AliExpressScraper()
    s._query_codigo = "LX-200"
    productos = s._parse(HTML_ALIEXPRESS)
    assert len(productos) == 1, "la tarjeta sin precio se descarta"
    p = productos[0]
    assert p.nombre == "Faro LED DhRpc Toyota Corolla 2015"
    assert p.precio_original == 21.71
    assert p.moneda_original == "USD"
    assert p.precio_usd == 21.71
    assert p.url.startswith("https://es.aliexpress.com/item/")
    assert p.tecnologia == "LED"


def test_aggregator_ordena_sin_precio_al_final():
    from scrapers.base import BaseScraper

    class FakeScraper(BaseScraper):
        def search_url(self, query: str) -> str:
            return "https://fake.com"

        def _parse(self, html: str) -> list:
            return []

        async def search(self, codigo: str, nombre: str = ""):
            return self._items

    def mk(nombre, precio, url):
        return Product(codigo="1", nombre=nombre, precio_usd=precio,
                       moneda_original="USD", precio_original=precio, funcion="",
                       lado="", tecnologia="", compatibilidad=[], sitio="fake",
                       url=url, pais="Ecuador")

    barato = mk("con precio", 9.0, "https://fake.com/a")
    caro = mk("caro", 30.0, "https://fake.com/b")
    sin_precio = mk("catalogo", 0.0, "https://fake.com/c")

    agg = SearchAggregator()
    agg.ecuador_scrapers = [FakeScraper.__new__(FakeScraper)]
    agg.ecuador_scrapers[0]._items = [caro, sin_precio]
    agg.international_scrapers = [FakeScraper.__new__(FakeScraper)]
    agg.international_scrapers[0]._items = [barato]

    res = asyncio_run(agg.search("x"))
    assert res["todos"][-1].nombre == "catalogo", "sin precio va al final"
    assert [p.nombre for p in res["todos"][:2]] == ["con precio", "caro"]


def _dummy_scraper():
    from scrapers.base import BaseScraper

    class Dummy(BaseScraper):
        def search_url(self, query):
            return "https://x.com"

        def _parse(self, html):
            return []

    return Dummy()


def _prod(nombre, url="", precio=0.0):
    return Product(codigo="1", nombre=nombre, precio_usd=precio,
                   moneda_original="USD", precio_original=precio, funcion="",
                   lado="", tecnologia="", compatibilidad=[], url=url)


def test_filtro_relevancia_descarta_resultados_fuera_de_tema():
    """iMotriz devuelve ductos y molduras al buscar "faro": deben descartarse."""
    s = _dummy_scraper()
    consulta = "faro"

    assert s._es_relevante(_prod("Faro Delantero Lh Santa Fe"), consulta)
    assert s._es_relevante(_prod("Farol Trasero Rh Tucson"), consulta)
    # Sin coincidencia con la consulta
    assert not s._es_relevante(_prod("ducto de aire niro 2016-2020"), consulta)
    assert not s._es_relevante(_prod("moldura de guardafango delantero lh"), consulta)
    # "Lava Faros" es un depósito limpiaparabrisas, no un faro
    assert not s._es_relevante(
        _prod("Deposito Limpia Parabrisas Completo sin Lava Faros Original"), consulta)
    # Plural simple sí se acepta
    assert s._es_relevante(_prod("Faros Delanteros Kit LED"), consulta)
    # Las palabras cortas no cuentan como coincidencia
    assert not s._es_relevante(_prod("aro de aleacion 17"), consulta)


def test_filtro_relevancia_ignora_palabras_genericas():
    """"delantero"/"santa fe" no prueban que el producto sea un faro."""
    s = _dummy_scraper()
    consulta = "faro delantero hyundai santa fe"
    assert s._es_relevante(_prod("Faro Delantero Lh Santa Fe 2018-2021"), consulta)
    assert not s._es_relevante(
        _prod("Refuerzo Delantero Original Santa Fe 2017 2018 2019"), consulta)
    assert not s._es_relevante(
        _prod("Guardafango Delantero Izquierdo Original Hyundai"), consulta)


def test_filtro_relevancia_acepta_codigo_oem_en_la_url():
    """El código OEM suele estar en la URL del producto aunque no en el nombre."""
    s = _dummy_scraper()
    s._query_codigo = "90915-YZZJ1"
    producto = _prod("Filtro de Aceite Original",
                     url="https://www.imotriz.com.ec/producto/abc/90915yzzj1/filtro")
    assert s._es_relevante(producto, "90915-YZZJ1")
    otro = _prod("Filtro de Aceite Hyundai", url="https://x.com/producto/abc/hd120")
    assert not s._es_relevante(otro, "90915-YZZJ1")


def test_make_product_no_hereda_funcion_del_termino_buscado():
    """Todos los resultados salían como "Faro Delantero" por la consulta."""
    s = _dummy_scraper()
    s._query_codigo = "90915-YZZJ1"
    s._query_nombre = "faro"
    p = s._make_product(nombre="ducto de aire niro 2016-2020", precio_usd=10.0,
                        precio_original=10.0, moneda_original="USD")
    assert p.funcion == "Repuesto Automotriz"
    assert p.nombre == "ducto de aire niro 2016-2020"


def test_search_prioriza_nombre_sobre_codigo():
    """El nombre es lo que los catálogos indexan; el código se usa de reserva."""
    from scrapers.base import BaseScraper

    pedidos = []

    class Dummy(BaseScraper):
        def search_url(self, query):
            pedidos.append(query)
            return "https://x.com"

        def _parse(self, html):
            return [_prod("Filtro de Aceite Original", "https://x.com/p1", 5.0)]

        async def _get_html(self, url, params=None):
            return "<html></html>"

    d = Dummy()
    res = asyncio_run(d.search("90915-YZZJ1", "filtro de aceite", limit=1))
    assert len(res) == 1
    assert pedidos == ["filtro de aceite"], "con resultados no se reintenta el código"


def test_search_reintenta_con_codigo_sin_guiones():
    from scrapers.base import BaseScraper

    pedidos = []

    class Vacio(BaseScraper):
        def search_url(self, query):
            pedidos.append(query)
            return "https://x.com"

        def _parse(self, html):
            return []

        async def _get_html(self, url, params=None):
            return "<html></html>"

    d = Vacio()
    assert asyncio_run(d.search("90915-YZZJ1", "", limit=5)) == []
    assert pedidos == ["90915-YZZJ1", "90915YZZJ1"]


def test_search_intenta_nombre_antes_del_codigo():
    from scrapers.base import BaseScraper

    pedidos = []

    class Vacio(BaseScraper):
        def search_url(self, query):
            pedidos.append(query)
            return "https://x.com"

        def _parse(self, html):
            return []

        async def _get_html(self, url, params=None):
            return "<html></html>"

    d = Vacio()
    asyncio_run(d.search("ABC-1", "farol trasero", limit=5))
    assert pedidos[0] == "farol trasero"


def test_aggregator_dedupe_no_colapsa_productos_sin_precio():
    from scrapers.base import BaseScraper

    class FakeScraper(BaseScraper):
        def search_url(self, query: str) -> str:
            return "https://fake.com"

        def _parse(self, html: str) -> list:
            return []

        async def search(self, codigo: str, nombre: str = ""):
            return self._items

    def mk(nombre, precio, url):
        return Product(codigo="1", nombre=nombre, precio_usd=precio,
                       moneda_original="USD", precio_original=precio, funcion="",
                       lado="", tecnologia="", compatibilidad=[], sitio="imotriz",
                       url=url, pais="EC")

    items = [mk("A", 0.0, "https://imotriz.ec/p/a"),
             mk("B", 0.0, "https://imotriz.ec/p/b"),
             mk("C", 0.0, "https://imotriz.ec/p/c")]

    agg = SearchAggregator()
    agg.ecuador_scrapers = [FakeScraper.__new__(FakeScraper)]
    agg.ecuador_scrapers[0]._items = items
    agg.international_scrapers = []

    res = asyncio_run(agg.search("x"))
    assert len(res["todos"]) == 3, "los catálogos sin precio se deduplican por URL"

class _ScraperDePrueba(BaseScraper):
    SITE_NAME = 'prueba'
    COUNTRY = 'EC'
    currency = 'USD'

    def __init__(self):
        super().__init__()
        self.consultas = []

    def search_url(self, query):
        return f'https://ejemplo.test/buscar?q={query}'

    def _parse(self, html):
        return []

    async def _get_html(self, url, params=None):
        self.consultas.append(url)
        return ''

    async def _get_html_multi(self, urls):
        self.consultas.extend(urls)
        return ['' for _ in urls]


def test_search_solo_nombre_cuando_buscar_por_codigo_es_falso():
    s = _ScraperDePrueba()
    s.buscar_por_codigo = False
    asyncio_run(s.search('92101-S1000', 'Faro Kia Soluto'))
    assert s.consultas == ['https://ejemplo.test/buscar?q=Faro Kia Soluto'], \
        'con buscar_por_codigo=False no se consulta el código'


def test_search_consulta_codigo_cuando_solo_falta_el_nombre():
    s = _ScraperDePrueba()
    asyncio_run(s.search('92101-S1000', 'Faro Kia Soluto'))
    assert s.consultas[0] == 'https://ejemplo.test/buscar?q=Faro Kia Soluto'
    assert 'https://ejemplo.test/buscar?q=92101-S1000' in s.consultas
    assert 'https://ejemplo.test/buscar?q=92101S1000' in s.consultas, \
        'se prueba además el código normalizado sin guiones'


def test_search_sin_nombre_usa_el_codigo():
    s = _ScraperDePrueba()
    asyncio_run(s.search('92101-S1000', ''))
    assert s.consultas[0] == 'https://ejemplo.test/buscar?q=92101-S1000'


def test_search_sin_nombre_ni_codigo_no_consulta():
    s = _ScraperDePrueba()
    asyncio_run(s.search('', ''))
    assert s.consultas == []


def test_imotriz_no_busca_por_codigo():
    from scrapers.ecuador.imotriz import ImotrizScraper
    assert ImotrizScraper.buscar_por_codigo is False, \
        'iMotriz sólo indexa nombres: buscar el código duplica los ~25 s de espera'


def test_mansuera_no_busca_por_codigo():
    from scrapers.ecuador.mansuera import MansueraScraper
    assert MansueraScraper.buscar_por_codigo is False, \
        'Mansuera exige seleccionar vehículo antes de mostrar productos'

class TestFiltroConsultaPorCodigo:
    """Una consulta que es sólo un código no debe aceptar piezas sin relación."""

    @staticmethod
    def _scraper():
        from scrapers.ecuador.imotriz import ImotrizScraper
        s = ImotrizScraper()
        s._query_codigo = '225.429-02'
        return s

    def test_rechaza_piezas_que_no_muestran_el_codigo(self):
        from scrapers.models import Product
        s = self._scraper()
        p = Product(codigo='225.429-02', nombre='Rodamiento Distribucion Hyundai Sonata 02-05',
                    precio_usd=12.1, moneda_original='CLP', precio_original=0.0,
                    funcion='', lado='', tecnologia='', compatibilidad=[],
                    sitio='repuestosboston',
                    url='https://www.repuestosboston.cl/rodamiento-distribucion-sonata-02-05.html')
        # El buscador difuso casa '02' con el año del título, pero no es el repuesto.
        assert s._es_relevante(p, '225.429-02') is False

    def test_acepta_el_producto_cuyo_url_incluye_el_codigo(self):
        from scrapers.models import Product
        s = self._scraper()
        p = Product(codigo='225.429-02', nombre='Faro Delantero Derecho Frontier',
                    precio_usd=80.0, moneda_original='CLP', precio_original=0.0,
                    funcion='', lado='', tecnologia='', compatibilidad=[],
                    sitio='repuestosboston',
                    url='https://www.repuestosboston.cl/22542902-faro-delantero.html')
        assert s._es_relevante(p, '225.429-02') is True

    def test_codigo_muy_corto_se_acepta_solo_con_coincidencia_exacta(self):
        from scrapers.models import Product
        s = self._scraper()
        s._query_codigo = 'A1'
        p = Product(codigo='A1', nombre='Faro Delantero', precio_usd=10.0,
                    moneda_original='USD', precio_original=0.0, funcion='', lado='',
                    tecnologia='', compatibilidad=[], sitio='x',
                    url='https://x.test/a1-faro')
        assert s._es_relevante(p, 'A1') is True
        q = Product(codigo='A1', nombre='Bomba de Agua', precio_usd=10.0,
                    moneda_original='USD', precio_original=0.0, funcion='', lado='',
                    tecnologia='', compatibilidad=[], sitio='x',
                    url='https://x.test/bomba')
        assert s._es_relevante(q, 'A1') is False

class TestLadoDelRepuesto:
    """El lado se detecta en ambas formas genders y sin falsos positivos."""

    @staticmethod
    def _s():
        from scrapers.ecuador.imotriz import ImotrizScraper
        return ImotrizScraper()

    def test_formas_femeninas(self):
        s = self._s()
        assert s._extract_side('Luz Diurna Derecha Tiggo 2 Pro', '') == 'Derecho'
        assert s._extract_side('Optico Izquierda Alternativo Kia Soluto', '') == 'Izquierdo'

    def test_formas_masculinas(self):
        s = self._s()
        assert s._extract_side('Faro delantero derecho Chery Tiggo', '') == 'Derecho'
        assert s._extract_side('Faro delantero izquierdo Kia Soluto', '') == 'Izquierdo'

    def test_abreviaturas_con_limite_de_palabra(self):
        s = self._s()
        assert s._extract_side('Faro RH Santa Fe', '') == 'Derecho'
        assert s._extract_side('Faro LH Santa Fe', '') == 'Izquierdo'
        # 'rh' dentro de otra palabra no es un lado.
        assert s._extract_side('Soporte Thork', '') == 'No especificado'
        assert s._extract_side('Bomba de Agua G4gc', '') == 'No especificado'

    def test_por_sufijo_del_codigo(self):
        s = self._s()
        assert s._extract_side('', '92101S1000-RH') == 'Derecho'
        assert s._extract_side('', '92101S1000-LH') == 'Izquierdo'

    def test_sin_lado_devuelve_no_especificado(self):
        s = self._s()
        assert s._extract_side('Amortiguador Trasero', '') == 'No especificado'

