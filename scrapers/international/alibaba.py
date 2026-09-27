"""Scraper de Alibaba (China, mayorista).

Estado: DESHABILITADO. Alibaba redirige el tráfico automatizado a
error.alibaba.com/error404.htm tanto con peticiones HTTP como con un
navegador real, por lo que no es posible obtener resultados de forma
estable. La clase se conserva para documentar el hallazgo, pero
`DISPONIBLE = False` evita que el agregador pierda tiempo en cada búsqueda.
Es un sitio B2B de mayorista, no orientado al repuesto finalista.
"""
import logging
from typing import List
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.models import Product

logger = logging.getLogger(__name__)


class AlibabaScraper(BaseScraper):
    SITE_NAME = "alibaba"
    BASE_URL = "https://www.alibaba.com"
    COUNTRY = "CN"
    currency = "USD"
    use_cloudscraper = True
    use_playwright = True
    request_delay = 3.0
    DISPONIBLE = False

    def search_url(self, query: str) -> str:
        params = urlencode({"fsb": "y", "IndexArea": "product_en", "SearchText": query})
        return f"{self.base_url}/trade/search?{params}"

    async def search(self, codigo: str, nombre: str = "", limit: int = 5) -> List[Product]:
        if not self.DISPONIBLE:
            logger.info("[alibaba] omitido: el sitio bloquea el acceso automatizado")
            return []
        return await super().search(codigo, nombre, limit)

    def _parse(self, html: str) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for card in soup.select("a[href*='/product/'], .J-offer-wrapper a[href]"):
            title = card.select_one("h4, .title, [class*=title]") or card
            href = card.get("href", "").split("?")[0]
            if href.startswith("//"):
                href = "https:" + href
            if not href.startswith("http"):
                href = self.base_url + href
            img = card.select_one("img[src]")
            results.append(self._make_product(
                nombre=title.get_text(" ", strip=True),
                url=href,
                imagen_url=img.get("src", "") if img else "",
            ))
        return results
