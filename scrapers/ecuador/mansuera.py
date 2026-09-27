"""Scraper de Mansuera (Ecuador).

Store basado en la plataforma iCommKT: la ruta real de búsqueda es
/productos?search=<consulta> y el catálogo está indexado por vehículo
(marca/modelo/año), por lo que una búsqueda sólo por código de parte devuelve
cero resultados aunque el sitio tenga el producto.

El HTML llega completo por HTTP (las tarjetas son `div.item` con un JSON
`data-cart-item` que trae sku, nombre, precio y stock), así que se pide sin
navegador y sólo se recurre a Playwright si el sitio cambia.
"""
import json
import logging
from typing import Any, Dict, List, Optional
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
    # Las tarjetas se renderizan en el servidor: pedir por HTTP evita pagar el
    # arranque del navegador (~9 s) en cada consulta.
    aiohttp_primero = True
    wait_for_selector = "div.item [data-cart-item]"
    settle_ms = 5000
    timeout = 40.0
    request_delay = 2.0
    # El catálogo exige seleccionar vehículo: buscar por código siempre cae en
    # la pantalla de "requiere vehículo" y solo añade tiempo.
    buscar_por_codigo = False
    # "Faro Kia Soluto" no está indexado, pero "Faro Kia" sí.
    degradar_consulta = True

    def search_url(self, query: str) -> str:
        return f"{self.BASE_URL}/productos?search={quote_plus(query)}"

    def _parse(self, html: str) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        results: List[Product] = []

        # El listado usa tarjetas `div.item`; el enlace del producto es un slug
        # en la raíz ("/faro-delantero-rh-soluto-1-4"), no una ruta /producto.
        vistos = set()
        for card in soup.select("div.item"):
            link = card.select_one("a.b2c-media-frame__inner[href]") \
                or card.select_one("a[href]")
            if link is None:
                continue
            href = (link.get("href") or "").strip()
            if not href or href in vistos:
                continue

            datos = self._datos_carrito(card)
            nombre = (datos.get("nombre") or self._nombre_producto(card, link) or "").strip()
            precio = self._precio_producto(card, datos)
            if not nombre or precio is None:
                continue

            vistos.add(href)
            if href.startswith("/"):
                href = self.BASE_URL + href
            producto = self._construir(
                codigo=self._query_codigo,
                nombre_texto=nombre,
                precio_texto="",
                url_producto=href,
                imagen_url=self._imagen(card),
                precio_monto=precio,
            )
            if producto is not None:
                results.append(producto)

        if not results:
            logger.info("[mansuera] el catálogo no devuelve tarjetas para la consulta")
        return results

    @staticmethod
    def _datos_carrito(card) -> Dict[str, Any]:
        """El botón de carrito lleva el producto en JSON (skus, precio, stock)."""
        boton = card.select_one("[data-cart-item]")
        if boton is None:
            return {}
        try:
            datos = json.loads(boton["data-cart-item"])
        except (TypeError, ValueError):
            return {}
        return datos if isinstance(datos, dict) else {}

    @staticmethod
    def _contenedor_producto(link):
        """Sube desde el enlace hasta la tarjeta que lo contiene."""
        nodo = link.parent
        for _ in range(6):
            if nodo is None or nodo.name is None or nodo.name == "body":
                return None
            if nodo.name == "div" and "item" in (nodo.get("class") or []):
                return nodo
            nodo = nodo.parent
        return None

    @staticmethod
    def _nombre_producto(card, link) -> str:
        # El nombre está en el `title` del enlace y en el bloque "Repuesto".
        if link.get("title"):
            return link["title"].strip()
        etiqueta = card.find("p", string=lambda t: t and "Repuesto" in t)
        if etiqueta is not None:
            valor = etiqueta.find_next_sibling("p")
            if valor is not None and valor.get("title"):
                return valor["title"].strip()
            if valor is not None:
                texto = valor.get_text(" ", strip=True)
                if texto:
                    return texto
        for selector in ("h1, h2, h3, h4", "[class*=title]", "[class*=nombre]"):
            el = card.select_one(selector)
            if el is not None:
                texto = el.get_text(" ", strip=True)
                if texto:
                    return texto
        img = card.find("img")
        if img is not None and img.get("alt"):
            return img["alt"].strip()
        return link.get_text(" ", strip=True)

    @staticmethod
    def _precio_producto(card, datos: Dict[str, Any]) -> Optional[float]:
        """Precio del producto: primero el JSON del carrito, luego el texto.

        Se devuelve el monto ya numérico. El precio del catálogo no está en una
        clase con nombre ("$ 72.542" bajo la etiqueta "Precio") y al volver a
        interpretarlo como texto el punto se contaría como separador de miles.
        """
        if datos:
            try:
                monto = float(datos.get("precio") or 0)
            except (TypeError, ValueError):
                monto = 0.0
            if monto > 0:
                return monto
        for selector in ("[class*=price]", "[class*=precio]", "[class*=amount]"):
            for el in card.select(selector):
                info = normalize_price(el.get_text(" ", strip=True))
                if info is not None and info.amount > 0:
                    return info.amount
        etiqueta = card.find("p", string=lambda t: t and "Precio" in t)
        if etiqueta is not None:
            valor = etiqueta.find_next_sibling("p")
            if valor is not None:
                info = normalize_price(valor.get_text(" ", strip=True))
                if info is not None and info.amount > 0:
                    return info.amount
        return None

    @staticmethod
    def _imagen(card) -> str:
        marco = card.select_one(".b2c-media-frame img") or card.find("img")
        if marco is None:
            return ""
        for atributo in ("data-src", "data-original", "src"):
            url = (marco.get(atributo) or "").strip()
            # El logo del sitio es la imagen de reserva cuando no hay foto.
            if url and "logomansuera" not in url:
                return url if url.startswith("http") else f"https://www.mansuera.com{url}"
        return ""

    def _construir(self, codigo: str, nombre_texto: str, precio_texto: str,
                   url_producto: str, imagen_url: str = "",
                   precio_monto: Optional[float] = None) -> Optional[Product]:
        # El precio del JSON es un número real ("72.542" = 72,54 dólares). Si se
        # volviera a pasar por texto, el punto se leería como separador de miles
        # y un faro de $72,54 se guardaría como $72.542.
        if precio_monto is not None:
            info = None
            monto = float(precio_monto)
        else:
            info = normalize_price(precio_texto or "")
            monto = info.amount if info is not None else 0.0

        if monto <= 0:
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
            precio_usd=monto,
            moneda_original="USD",
            precio_original=monto,
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
