"""Scraper de Repuestos Boston (Chile, precios en CLP).

Tienda Magento: la búsqueda responde en HTML plano, sin necesidad de
JavaScript. La ruta real es /catalogsearch/result/?q=<consulta>.
Los precios se expresan en pesos chilenos con punto de miles ("$45.000"),
por lo que se toma el monto del texto pero se etiqueta siempre como CLP.
"""
import logging
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.currency import normalize_price, to_usd
from scrapers.base import BaseScraper
from scrapers.models import Product

logger = logging.getLogger(__name__)


class RepuestosBostonScraper(BaseScraper):
    SITE_NAME = "repuestosboston"
    BASE_URL = "https://www.repuestosboston.cl"
    COUNTRY = "CL"
    currency = "CLP"
    use_cloudscraper = True
    request_delay = 2.0
    timeout = 20.0

    def search_url(self, query: str) -> str:
        return f"{self.BASE_URL}/catalogsearch/result/?q={quote_plus(query)}"

    def _parse(self, html: str) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        results: List[Product] = []
        for card in soup.select("li.product-item"):
            link = card.select_one("a.product-item-link") or card.select_one("a[href]")
            titulo = card.select_one(".product-item-name a, h2.product-item-name a, h2")
            if titulo is None or link is None:
                continue
            nombre = titulo.get_text(" ", strip=True)
            if not nombre:
                continue

            href = link.get("href", "").strip()
            if href.startswith("/"):
                href = self.BASE_URL + href

            # El precio del sitio es CLP aunque use el símbolo "$".
            precio_original = 0.0
            price_el = card.select_one(".price")
            if price_el is not None:
                info = normalize_price(price_el.get_text(" ", strip=True))
                if info is not None:
                    precio_original = info.amount
            if precio_original <= 0:
                continue

            try:
                precio_usd = to_usd(precio_original, self.currency)
            except ValueError:
                precio_usd = 0.0

            img = card.select_one("img.product-image-photo, img[src]")
            imagen = ""
            if img is not None:
                # Magento carga las imágenes en data-src (src es un placeholder).
                imagen = img.get("data-src") or img.get("src") or ""
                if imagen.startswith("data:"):
                    imagen = ""

            results.append(self._make_product(
                nombre=nombre,
                precio_usd=precio_usd,
                moneda_original=self.currency,
                precio_original=precio_original,
                url=href,
                imagen_url=imagen,
            ))
        return results
