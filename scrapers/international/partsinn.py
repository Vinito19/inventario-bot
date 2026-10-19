"""Scraper de PARTSinn (Lituania, precios en EUR).

Catálogo de OEM genuino: la búsqueda por código resuelve una ficha en
/oem/<código> que publica el producto en JSON-LD (nombre, código, precio y
moneda). Responde en HTML plano, sin JavaScript.

Sólo indexa códigos OEM exactos: buscar por nombre devuelve "No offers found".
El precio viene como rango (lowPrice) y en EUR, así que se convierte a USD.
"""
import logging
from urllib.parse import quote_plus

from scrapers.base import BaseScraper
from scrapers.currency import to_usd
from scrapers.models import Product

logger = logging.getLogger(__name__)


class PartsinnScraper(BaseScraper):
    SITE_NAME = "partsinn"
    BASE_URL = "https://partsinn.lt"
    COUNTRY = "EU"
    currency = "EUR"
    request_delay = 1.5
    timeout = 15.0
    buscar_por_codigo = True

    def search_url(self, query: str) -> str:
        return f"{self.BASE_URL}/oem/{quote_plus(query)}"

    def _parse(self, html: str) -> list[Product]:
        results: list[Product] = []
        for dato in self._json_ld_productos(html):
            codigo = dato["codigo"] or self._query_codigo
            if not codigo:
                continue
            # El nodo Product no siempre trae url; la ficha siempre cuelga de
            # /oem/<código>. La página "sin ofertas" no publica Product, así
            # que no hay riesgo de inventar un repuesto.
            url = dato["url"] if "/oem/" in dato["url"] else f"{self.BASE_URL}/oem/{codigo}"
            precio_original = dato["precio"]
            precio_usd = 0.0
            if precio_original > 0 and dato["moneda"]:
                try:
                    precio_usd = to_usd(precio_original, dato["moneda"])
                except ValueError:
                    precio_usd = 0.0
            results.append(self._make_product(
                nombre=dato["nombre"],
                codigo=codigo,
                precio_usd=precio_usd,
                moneda_original=dato["moneda"] or self.currency,
                precio_original=precio_original,
                url=url,
            ))
        return results
