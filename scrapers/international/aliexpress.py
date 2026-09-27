"""Scraper para AliExpress (internacional, con conversión de moneda).

Las tarjetas usan clases CSS hasheadas que cambian con frecuencia, así que
se anclan en atributos estables: `a.search-card-item`, `img[alt]` y
`[class*=price--]`. La carga nunca llega a "networkidle" por el long-polling
de recomendaciones, por eso se espera al DOM + selector.
"""
import logging
import re
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.currency import normalize_price, to_usd
from scrapers.models import Product

logger = logging.getLogger(__name__)

_PRICE_FALLBACK = re.compile(r"(\d[\d.,]*)")

_CURRENCY_BY_SYMBOL = (
    ("US $", "USD"),
    ("US$", "USD"),
    ("€", "EUR"),
    ("EUR", "EUR"),
    ("£", "GBP"),
    ("GBP", "GBP"),
    ("$", "USD"),
    ("USD", "USD"),
)


class AliExpressScraper(BaseScraper):
    SITE_NAME = "AliExpress"
    COUNTRY = "Internacional"
    BASE_URL = "https://www.aliexpress.com"
    currency = "USD"
    use_playwright = True
    wait_for_selector = "a.search-card-item, a[href*='/item/']"
    settle_ms = 4000
    timeout = 40.0
    request_delay = 2.0
    # La rejilla real de resultados se carga desde una API mtop firmada por
    # sesión; el HTML que se sirve sólo trae tarjetas de recomendación
    # (bolsos, ropa, linternas) que no corresponden a la consulta. Se
    # deshabilita para no mostrar precios de productos ajenos al repuesto.
    DISPONIBLE = False

    def search_url(self, query: str) -> str:
        slug = "-".join((query or "").split())
        return f"{self.BASE_URL}/w/wholesale-{quote(slug)}.html"

    def _parse(self, html: str) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        results: List[Product] = []
        # Se prefieren las tarjetas de búsqueda; a[href*='/item/'] también
        # matchea las recomendaciones inyectadas por la API de related.
        tarjetas = soup.select("a.search-card-item") or soup.select("a[href*='/item/']")
        for card in tarjetas:
            titulo = card.select_one("[class*=titleText], [class*=title--]")
            imagen = card.select_one("img[alt]")
            if titulo is not None:
                nombre = titulo.get_text(" ", strip=True)
            elif imagen is not None:
                nombre = (imagen.get("alt") or "").strip()
            else:
                continue
            if not nombre:
                continue

            precio_el = card.select_one("[class*=price--]")
            precio_texto = precio_el.get_text() if precio_el is not None else ""
            href = (card.get("href") or "").strip()
            imagen_url = ""
            if imagen is not None:
                imagen_url = imagen.get("src") or imagen.get("data-src") or ""

            producto = self._construir(
                codigo=self._query_codigo,
                nombre_texto=nombre,
                precio_texto=precio_texto,
                url_producto=href,
                imagen_url=imagen_url,
            )
            if producto is not None:
                results.append(producto)
        return results

    async def search(self, codigo: str, nombre: str = "", limit: int = 5) -> List[Product]:
        """Busca en AliExpress respetando el límite de resultados."""
        if not self.DISPONIBLE:
            logger.info("[aliexpress] omitido: la rejilla de resultados no es "
                        "accesible sin la API mtop firmada")
            return []
        return await super().search(codigo, nombre, limit)

    def _construir(self, codigo: str, nombre_texto: str, precio_texto: str,
                   url_producto: str, imagen_url: str = "") -> Optional[Product]:
        """Construye un Product a partir del texto crudo de la tarjeta."""
        info = normalize_price(precio_texto or "")
        moneda = self._detectar_moneda(precio_texto) or (info.currency if info else self.currency)

        if info is not None and info.amount > 0:
            precio_original = info.amount
        else:
            match = _PRICE_FALLBACK.search(precio_texto or "")
            if not match:
                logger.debug("[aliexpress] precio no parseable: %r", precio_texto)
                return None
            try:
                precio_original = float(match.group(1).replace(",", ""))
            except ValueError:
                return None
            if precio_original <= 0:
                return None

        try:
            precio_usd = to_usd(precio_original, moneda)
        except ValueError:
            precio_usd = to_usd(precio_original, self.currency)

        if url_producto and not url_producto.startswith("http"):
            url_producto = (f"https:{url_producto}" if url_producto.startswith("//")
                            else f"{self.BASE_URL}/{url_producto.lstrip('/')}")
        if not url_producto.startswith("http"):
            url_producto = ""

        texto_completo = nombre_texto or codigo
        return Product(
            codigo=codigo,
            nombre=nombre_texto.strip(),
            precio_usd=precio_usd,
            moneda_original=moneda,
            precio_original=precio_original,
            funcion=self._extract_function(texto_completo),
            lado=self._extract_side(texto_completo, codigo),
            tecnologia=self._extract_technology(texto_completo),
            compatibilidad=self._extract_compatibility(texto_completo),
            componente_hermano=self._extract_sibling_component(texto_completo, codigo),
            sitio=self.SITE_NAME,
            pais=self.COUNTRY,
            url=url_producto,
            imagen_url=imagen_url,
        )

    async def _build_product(self, codigo: str, nombre_texto: str,
                             precio_texto: str, url_producto: str) -> Optional[Product]:
        """Alias asíncrono usado por las pruebas y el flujo legacy."""
        return self._construir(codigo, nombre_texto, precio_texto, url_producto)

    @staticmethod
    def _detectar_moneda(texto: str) -> Optional[str]:
        if not texto:
            return None
        for simbolo, moneda in _CURRENCY_BY_SYMBOL:
            if simbolo in texto:
                return moneda
        return None
