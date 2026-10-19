"""Scraper de Repuestos Automotrices JC Quito (Ecuador).

Tienda WooCommerce: la búsqueda responde en HTML plano, sin JavaScript.
Ruta: /?s=<consulta>&post_type=product

Las tarjetas son `li.product` con el nombre en
`h2.woocommerce-loop-product__title` y el enlace en
`a.woocommerce-loop-product__link`. El catálogo no publica precios (se cotiza
por WhatsApp), así que se devuelve precio 0 y el agregador los muestra al
final. No indexa códigos OEM: buscar por código sólo devuelve ruido.
"""
import logging
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.models import Product

logger = logging.getLogger(__name__)


class JcgfScraper(BaseScraper):
    SITE_NAME = "JCGF"
    COUNTRY = "Ecuador"
    BASE_URL = "https://www.repuestosautomotrices.com"
    currency = "USD"
    request_delay = 1.5
    timeout = 15.0
    # El catálogo no indexa códigos OEM: consultarlos sólo añade una petición.
    buscar_por_codigo = False

    def search_url(self, query: str) -> str:
        return f"{self.BASE_URL}/?s={quote_plus(query)}&post_type=product"

    def _parse(self, html: str) -> list[Product]:
        soup = BeautifulSoup(html, "lxml")
        results: list[Product] = []
        for card in soup.select("li.product"):
            enlace = card.select_one("a.woocommerce-loop-product__link[href]") \
                or card.select_one("a[href]")
            titulo = card.select_one("h2.woocommerce-loop-product__title")
            if enlace is None or titulo is None:
                continue
            nombre = titulo.get_text(" ", strip=True)
            href = (enlace.get("href") or "").strip()
            if not nombre or not href:
                continue
            if href.startswith("/"):
                href = self.BASE_URL + href

            imagen = ""
            img = card.find("img")
            if img is not None:
                imagen = img.get("data-src") or img.get("src") or ""
                # Sin foto el catálogo usa el marcador de WooCommerce.
                if "woocommerce-placeholder" in imagen or imagen.startswith("data:"):
                    imagen = ""

            results.append(self._make_product(
                nombre=nombre, url=href, imagen_url=imagen,
            ))
        return results
