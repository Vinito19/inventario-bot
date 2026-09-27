"""Scraper de iMotriz Ecuador (marketplace de autopartes).

El sitio es una aplicación Yii2 + Vue con protección anti-bot: la búsqueda
sólo responde con el DOM renderizado por JavaScript, por eso se usa Playwright.
Los resultados NO incluyen precio (el portal trabaja bajo pedido de
cotización), así que los productos se devuelven con precio 0.
"""
import logging
from typing import List, Tuple
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.models import Product

logger = logging.getLogger(__name__)


class ImotrizScraper(BaseScraper):
    SITE_NAME = "imotriz"
    BASE_URL = "https://www.imotriz.com.ec"
    COUNTRY = "EC"
    currency = "USD"
    use_playwright = True
    # cloudscraper NO debe usarse aquí: devuelve 200 con la página de reto
    # anti-bot, y al ser "exitosa" impide que se intente Playwright.
    use_cloudscraper = False
    wait_for_selector = "a[href*='/producto/']"
    settle_ms = 2500
    timeout = 30.0
    request_delay = 2.0
    # El buscador sólo indexa nombres descriptivos: buscar el código OEM cuesta
    # una carga completa de la SPA (~25 s) y siempre devuelve el aviso de
    # "selecciona un vehículo" sin productos.
    buscar_por_codigo = False
    # El catálogo de iMotriz cotiza bajo pedido: no se puede obtener precio.
    TIENE_PRECIO = False

    def search_url(self, query: str) -> str:
        return f"{self.BASE_URL}/catalogo/page/results?search={quote_plus(query)}"

    @staticmethod
    def _meta(card) -> Tuple[str, str]:
        """Extrae 'Marca:' y 'Nº de parte:' de la tarjeta."""
        marca = ""
        parte = ""
        for tag in card.find_all(["p", "span"]):
            strong = tag.find("strong")
            if strong is None:
                continue
            etiqueta = strong.get_text(" ", strip=True).rstrip(":").lower()
            valor = tag.get_text(" ", strip=True)
            if ":" in valor:
                valor = valor.split(":", 1)[1].strip()
            if etiqueta.startswith("marca"):
                marca = valor
            elif "parte" in etiqueta:
                parte = valor
        return marca, parte

    def _parse(self, html: str) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        results: List[Product] = []
        for card in soup.select("div.card"):
            desc = card.select_one("a.description")
            link = card.select_one("a[href*='/producto/']")
            if desc is None or link is None:
                continue
            titulo = desc.select_one("h2, h3")
            if titulo is None:
                continue
            nombre = titulo.get_text(" ", strip=True)
            if not nombre:
                continue

            subtitulo = desc.select_one("p")
            marca, parte = self._meta(card)

            href = link.get("href", "").strip()
            if href.startswith("/"):
                href = self.BASE_URL + href

            img = card.select_one("img[src*='imotriz.com'], img[src*='/uploads/']")

            extra = " ".join(filter(None, [marca, parte,
                                            subtitulo.get_text(" ", strip=True) if subtitulo else ""]))
            results.append(self._make_product(
                nombre=nombre,
                extra_text=extra,
                precio_usd=0.0,
                precio_original=0.0,
                moneda_original=self.currency,
                url=href,
                imagen_url=img.get("src", "") if img else "",
            ))

        if not results:
            logger.info("[imotriz] sin resultados en el catálogo para la consulta")
        return results
