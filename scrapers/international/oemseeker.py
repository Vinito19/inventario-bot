"""Scraper de OEM Seeker (Europa).

Buscador de referencias OEM. Responde dos formas según la consulta:

- Por nombre: una tabla `table.parts-table` con el nombre del repuesto, su
  código OEM (enlace /oem/<código>) y las referencias cruzadas de fabricantes
  (TRW, HELLA, ...).
- Por código: una ficha con el producto en JSON-LD.

Todo llega en HTML plano (server-rendered), sin JavaScript ni navegador. No
publica precios (la ficha pide añadir el vehículo para verlos), así que se
devuelve precio 0 y el agregador los muestra al final.
"""
import logging
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.models import Product

logger = logging.getLogger(__name__)


class OemseekerScraper(BaseScraper):
    SITE_NAME = "oemseeker"
    BASE_URL = "https://oemseeker.com"
    COUNTRY = "EU"
    currency = "EUR"
    aiohttp_primero = True
    request_delay = 1.0
    timeout = 15.0

    def search_url(self, query: str) -> str:
        return f"{self.BASE_URL}/search?q={quote_plus(query)}"

    def _parse(self, html: str) -> list[Product]:
        filas = self._tabla(html)
        if filas:
            return filas
        return self._ficha(html)

    def _tabla(self, html: str) -> list[Product]:
        soup = BeautifulSoup(html, "lxml")
        results: list[Product] = []
        for fila in soup.select("table.parts-table tbody tr"):
            celda = fila.find("th", attrs={"scope": "row"})
            enlace = fila.select_one("a[href*='/oem/']")
            if celda is None or enlace is None:
                continue
            nombre = celda.get_text(" ", strip=True)
            if not nombre:
                continue
            href = (enlace.get("href") or "").strip()
            if href.startswith("/"):
                href = self.BASE_URL + href
            # El código se muestra con espacios ("6 768 188").
            codigo = re.sub(r"\s+", "", enlace.get_text(" ", strip=True))
            referencias = " ".join(
                span.get_text(" ", strip=True)
                for span in fila.select(".number-list span")
            )
            results.append(self._make_product(
                nombre=nombre,
                extra_text=referencias,
                codigo=codigo or self._query_codigo,
                url=href,
            ))
        return results

    def _ficha(self, html: str) -> list[Product]:
        results: list[Product] = []
        for dato in self._json_ld_productos(html):
            # El código se muestra/declara con espacios ("6 768 188").
            codigo = re.sub(r"\s+", "", dato["codigo"] or self._query_codigo)
            if not codigo:
                continue
            url = dato["url"] if "/oem/" in dato["url"] else f"{self.BASE_URL}/oem/{codigo}"
            results.append(self._make_product(
                nombre=dato["nombre"], codigo=codigo, url=url,
            ))
        return results
