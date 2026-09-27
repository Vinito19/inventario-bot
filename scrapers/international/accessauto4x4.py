"""Scraper de AccessAuto4x4 (España, precios en EUR).

Tienda PrestaShop. Búsqueda en /es/buscar?s=<consulta>.
Responde HTML plano (aunque con muchos recursos), no requiere Playwright.

Selectores (PrestaShop estándar):
  - article.product-miniature.js-product-miniature
  - enlace: a.product-miniature__link
  - nombre: h2.h3.product-title a  (o .product-title a)
  - precio: .product-price-and-shipping .price, o span[itemprop=price]
  - imagen: .product-miniature__image img (srcset/data-src)
  - referencia/SKU: en URL del producto o en .product-reference

Moneda: EUR (€)
"""
import logging
import re
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.currency import normalize_price, to_usd
from scrapers.base import BaseScraper
from scrapers.models import Product

logger = logging.getLogger(__name__)


class AccessAuto4x4Scraper(BaseScraper):
    SITE_NAME = "accessauto4x4"
    BASE_URL = "https://accessauto4x4.com"
    COUNTRY = "ES"
    currency = "EUR"
    use_cloudscraper = True
    aiohttp_primero = True
    request_delay = 1.5
    timeout = 20.0
    buscar_por_codigo = True

    def search_url(self, query: str) -> str:
        return f"{self.BASE_URL}/es/buscar?s={quote_plus(query)}"

    def _parse(self, html: str) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        results: List[Product] = []

        for art in soup.select("article.product-miniature.js-product-miniature"):
            link = art.select_one("a.product-miniature__link")
            if not link:
                continue
            href = link.get("href", "").strip()
            if not href:
                continue
            if href.startswith("/"):
                href = self.BASE_URL + href

            # Nombre: h2.h3.product-title a
            titulo = art.select_one("h2.h3.product-title a, .product-title a, [itemprop=name]")
            nombre = titulo.get_text(" ", strip=True) if titulo else ""
            if not nombre:
                continue

            # Precio: .product-price-and-shipping .price
            precio_original = 0.0
            precio_el = art.select_one(".product-price-and-shipping .price, [itemprop=price]")
            if precio_el:
                info = normalize_price(precio_el.get_text(" ", strip=True))
                if info:
                    precio_original = info.amount

            # Imagen: .product-miniature__image img (srcset/data-full-size-image-url)
            imagen = ""
            img = art.select_one(".product-miniature__image img, img.product-miniature__image")
            if img:
                imagen = (img.get("data-full-size-image-url") or
                          img.get("data-src") or
                          img.get("src") or "")
                if imagen.startswith("data:"):
                    imagen = ""

            # SKU/referencia: data-id-product o en URL
            sku = ""
            if art.get("data-id-product"):
                sku = art["data-id-product"]
            elif "ref-" in href:
                m = re.search(r"ref-([A-Z0-9\-]+)", href)
                if m:
                    sku = m.group(1)

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