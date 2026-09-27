"""Scraper de Mansuera (Ecuador).

Store basado en la plataforma iCommKT: la ruta real de búsqueda es
/productos?search=<consulta> y el contenido llega por JavaScript, así que se
usa Playwright. Limitación conocida: el catálogo está indexado por vehículo
(marca/modelo/año), por lo que una búsqueda sólo por código de parte puede
devolver cero resultados aunque el sitio tenga el producto.
"""
import logging
from typing import List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.currency import normalize_price
from scrapers.models import Product

logger = logging.getLogger(__name__)


class MansueraScraper(BaseScraper):
    SITE_NAME = "Mansuera"
    COUNTRY = "Ecuador"
    BASE_URL = "https://www.mansuera.com"
    currency = "USD"
    use_playwright = True
    wait_for_selector = "a[href*='/producto']"
    settle_ms = 5000
    timeout = 40.0
    request_delay = 2.0
    # El catálogo exige seleccionar vehículo: buscar por código siempre cae en
    # la pantalla de "requiere vehículo" y solo añade tiempo.
    buscar_por_codigo = False

    def search_url(self, query: str) -> str:
        return f"{self.BASE_URL}/productos?search={quote_plus(query)}"

    def _parse(self, html: str) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        results: List[Product] = []

        # Se recorre cada enlace de producto y se sube al contenedor más
        # cercano que tenga imagen y precio: las clases son de Tailwind y
        # cambian con cada despliegue.
        vistos = set()
        for link in soup.select("a[href*='/producto']"):
            href = (link.get("href") or "").strip()
            if not href or href in vistos:
                continue
            card = self._contenedor_producto(link)
            if card is None:
                continue
            nombre = self._nombre_producto(card, link)
            if not nombre:
                continue
            precio = self._precio_producto(card)
            if precio is None:
                continue
            vistos.add(href)
            if href.startswith("/"):
                href = self.BASE_URL + href
            img = card.select_one("img")
            results.append(self._construir(
                codigo=self._query_codigo,
                nombre_texto=nombre,
                precio_texto=precio,
                url_producto=href,
                imagen_url=(img.get("src") or "") if img else "",
            ))

        if not results:
            logger.info("[mansuera] sin resultados: el catálogo requiere seleccionar vehículo")
        return results

    @staticmethod
    def _contenedor_producto(link):
        """Sube desde el enlace hasta el div con imagen y precio."""
        nodo = link.parent
        for _ in range(5):
            if nodo is None or nodo.name is None:
                return None
            if nodo.name == "body":
                return None
            if nodo.find("img") is not None and normalize_price(nodo.get_text(" ", strip=True)):
                return nodo
            nodo = nodo.parent
        return None

    @staticmethod
    def _nombre_producto(card, link) -> str:
        for selector in ("h1, h2, h3, h4", "[class*=title]", "[class*=nombre]"):
            el = card.select_one(selector)
            if el is not None:
                texto = el.get_text(" ", strip=True)
                if texto:
                    return texto
        img = card.find("img")
        if img is not None and img.get("alt"):
            return img["alt"].strip()
        texto = link.get_text(" ", strip=True)
        return texto

    @staticmethod
    def _precio_producto(card) -> Optional[str]:
        for selector in ("[class*=price]", "[class*=precio]", "[class*=amount]"):
            for el in card.select(selector):
                info = normalize_price(el.get_text(" ", strip=True))
                if info is not None and info.amount > 0:
                    return el.get_text(" ", strip=True)
        return None

    def _construir(self, codigo: str, nombre_texto: str, precio_texto: str,
                   url_producto: str, imagen_url: str = "") -> Optional[Product]:
        info = normalize_price(precio_texto or "")
        if info is None or info.amount <= 0:
            logger.debug("[mansuera] precio no parseable: %r", precio_texto)
            return None

        if url_producto and not url_producto.startswith("http"):
            url_producto = self.BASE_URL + url_producto if url_producto.startswith("/") \
                else f"{self.BASE_URL}/{url_producto}"
        if not url_producto.startswith("http"):
            url_producto = ""

        texto_completo = nombre_texto or codigo
        return Product(
            codigo=codigo,
            nombre=nombre_texto.strip(),
            precio_usd=info.amount,
            moneda_original="USD",
            precio_original=info.amount,
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
