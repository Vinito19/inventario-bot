"""Scraper de Elmridgea (Europa, precios en EUR).

Magento 2 / tienda similar: la búsqueda por código exacto redirige a la ficha
del producto (con JSON-LD con precio, sku, gtin). La búsqueda por nombre
devuelve una lista con .product-item.

Rutas:
  - búsqueda: /advanced_search_result.htm?keyword=<consulta>
  - ficha de producto: URL amigable con -p-<id>.htm

Selectores:
  - lista: .product-item (recomendaciones en ficha, productos reales en lista)
  - ficha: h1[itemprop=name], script[type=application/ld+json] (offers.price)
  - precio: JSON-LD offers.price (EUR)
"""
import json
import logging
import re
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.models import Product

logger = logging.getLogger(__name__)


class ElmridgeaScraper(BaseScraper):
    SITE_NAME = "elmridgea"
    BASE_URL = "https://eshop.elmridgea.com"
    COUNTRY = "ES"
    currency = "EUR"
    use_cloudscraper = True
    request_delay = 1.5
    timeout = 20.0
    aiohttp_primero = True  # HTML plano; la ficha también tiene JSON-LD

    def search_url(self, query: str) -> str:
        return f"{self.BASE_URL}/advanced_search_result.htm?keyword={quote_plus(query)}"

    def _es_ficha_producto(self, soup: BeautifulSoup) -> bool:
        """Detecta si la página es una ficha de producto (redirección por código exacto)."""
        # La ficha tiene h1 principal + JSON-LD Product con offers.price
        return bool(soup.select_one("h1[itemprop=name], h1.page-title")) and \
               bool(soup.find("script", type="application/ld+json", string=re.compile(r"offers.*price", re.I)))

    def _parse_ficha(self, html: str) -> List[Product]:
        """Parsea la ficha de producto (un solo producto, el buscado)."""
        soup = BeautifulSoup(html, "lxml")
        results: List[Product] = []

        # Nombre del h1 o itemprop=name
        h1 = soup.select_one("h1[itemprop=name], h1.page-title, h1")
        nombre = h1.get_text(" ", strip=True) if h1 else "Producto Elmridgea"
        if not nombre:
            return results

        # JSON-LD para precio, sku, gtin, disponibilidad
        precio_original = 0.0
        precio_usd = 0.0
        sku = ""
        gtin = ""
        url_producto = ""
        imagen = ""
        disponible = True

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                datos = json.loads(script.string or "")
            except Exception:
                continue
            if isinstance(datos, dict) and datos.get("@type") == "Product":
                # precio
                offers = datos.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                if isinstance(offers, dict):
                    precio_str = offers.get("price", "")
                    if precio_str:
                        try:
                            precio_original = float(str(precio_str).replace(",", "."))
                        except Exception:
                            precio_original = 0.0
                    url_producto = offers.get("url", "") or url_producto
                sku = str(datos.get("sku", "")).strip()
                gtin = str(datos.get("gtin13", "")).strip()
                imagen = datos.get("image", "") or imagen
                disponible = offers.get("availability", "").endswith("InStock")
                break

        if precio_original <= 0:
            # fallback: buscar en priceBox del DOM principal (fuera de .product-item)
            for pb in soup.select("[data-role=priceBox]"):
                if pb.find_parent(class_="product-item"):
                    continue
                txt = pb.get_text(" ", strip=True)
                # formato típico: "82,99€" o "82,99 €"
                m = re.search(r"([\d.,]+)\s*€", txt)
                if m:
                    try:
                        precio_original = float(m.group(1).replace(",", "."))
                        break
                    except Exception:
                        pass

        if precio_original > 0:
            precio_usd = precio_original  # ya en EUR, _make_product no convierte si currency=EUR

        # Código: preferir gtin/sku del JSON-LD, luego query_codigo
        codigo = gtin or sku or self._query_codigo

        results.append(self._make_product(
            nombre=nombre,
            codigo=codigo,
            precio_usd=precio_usd,
            moneda_original=self.currency,
            precio_original=precio_original,
            url=url_producto or "",
            imagen_url=imagen,
        ))
        return results

    def _parse_lista(self, html: str) -> List[Product]:
        """Parsea la lista de resultados de búsqueda por nombre."""
        soup = BeautifulSoup(html, "lxml")
        results: List[Product] = []

        for item in soup.select(".product-item"):
            # Saltar recomendaciones si estamos en ficha: las recomendaciones
            # son .product-item DENTRO de contenedores de recomendaciones.
            # Heurística: en lista de resultados, .product-item tiene enlace de producto.
            link = item.select_one("a.product-item-link, a.product-item-photo, a[itemprop=url]")
            if not link:
                continue
            href = link.get("href", "").strip()
            if not href:
                continue
            if href.startswith("/"):
                href = self.BASE_URL + href

            meta = item.select_one("meta[itemprop=name]")
            if meta and meta.get("content"):
                nombre = meta["content"].strip()
            else:
                nombre_el = item.select_one(".product-item-name a, .product.name a, [itemprop=name]")
                nombre = nombre_el.get_text(" ", strip=True) if nombre_el else ""
            if not nombre:
                continue

            # Precio: en .price o [data-role=priceBox] (mismo elemento que .price-final_price)
            precio_original = 0.0
            pb = item.select_one(".price-final_price[data-role=priceBox], .price, [data-role=priceBox]")
            if pb:
                txt = pb.get_text(" ", strip=True)
                m = re.search(r"([\d.,]+)\s*€", txt)
                if m:
                    try:
                        precio_original = float(m.group(1).replace(",", "."))
                    except Exception:
                        pass

            # Imagen: data-src o src
            img = item.select_one("img.product-image-photo, img[src]")
            imagen = ""
            if img:
                imagen = img.get("data-src") or img.get("src") or ""
                if imagen.startswith("data:"):
                    imagen = ""

            # SKU: buscar en data-product-id o en meta
            sku = ""
            for attr in ("data-product-id", "data-sku", "itemprop"):
                val = item.get(attr)
                if val:
                    sku = val.strip()
                    break

            results.append(self._make_product(
                nombre=nombre,
                codigo=sku or self._query_codigo,
                precio_usd=precio_original,
                moneda_original=self.currency,
                precio_original=precio_original,
                url=href,
                imagen_url=imagen,
            ))
        return results

    def _parse(self, html: str) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        if self._es_ficha_producto(soup):
            logger.debug("[elmridgea] parseando ficha de producto (redirección por código)")
            return self._parse_ficha(html)
        logger.debug("[elmridgea] parseando lista de resultados")
        return self._parse_lista(html)