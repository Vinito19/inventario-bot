"""Scraper de Kiauto (España, precios en EUR).

Tienda con búsqueda server-rendered en /rb/{término}. Responde HTML plano,
no necesita JavaScript ni Playwright.

Ruta de búsqueda: /rb/{consulta} (path segment, no query param).
Ejemplo: /rb/9824241480  -> "Búsqueda: 9824241480 | Kiauto"

Selectores:
  - article.product-item (cada resultado)
  - enlace: a[href] dentro del article
  - nombre: texto del article (incluye características)
  - precio: aparece en el texto como "35' 38 €" o "XX €"
  - imagen: img dentro del article (src/data-src)

El sitio incluye el código OEM en la URL del producto (p00PG... o p00398...).
"""
import logging
import re
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.models import Product

logger = logging.getLogger(__name__)


class KiautoScraper(BaseScraper):
    SITE_NAME = "kiauto"
    BASE_URL = "https://www.kiauto.es"
    COUNTRY = "ES"
    currency = "EUR"
    use_cloudscraper = True
    aiohttp_primero = True  # HTML plano, server-rendered
    request_delay = 1.5
    timeout = 15.0
    buscar_por_codigo = True  # el código funciona bien en /rb/{codigo}

    def search_url(self, query: str) -> str:
        # La ruta real es /rb/{término} (path segment, codificado)
        return f"{self.BASE_URL}/rb/{quote_plus(query)}"

    def _es_relevante(self, producto: Product, consulta: str) -> bool:
        """Kiauto: la búsqueda por código OEM es precisa (devuelve el repuesto
        exacto), pero las tarjetas no incluyen el código en el nombre visible.
        Si la consulta original era un código OEM puro (alfanumérico sin
        espacios), se confía en el resultado.
        """
        # Detectar consulta que es solo un código OEM (alfanumérico, sin
        # espacios, 6+ caracteres): Kiauto la resuelve bien.
        if re.match(r"^[A-Z0-9]{6,}$", consulta, re.IGNORECASE):
            return True
        return super()._es_relevante(producto, consulta)

    def _extraer_precio(self, texto: str) -> float:
        """Extrae precio en EUR del texto.
        Formatos vistos: "35' 38 €", "38,50 €", "35 €", "1.200,00 €"
        """
        # Buscar patrones de precio con €
        for patron in (
            r"([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s*€",  # 1.200,00 €
            r"(\d+(?:[.,]\d{2}))\s*€",                       # 38,50 €
            r"(\d+)\s*[']\s*(\d{2})\s*€",                    # 35' 38 € -> 35.38
        ):
            m = re.search(patron, texto)
            if m:
                try:
                    if "'" in patron and m.lastindex == 2:
                        return float(f"{m.group(1)}.{m.group(2)}")
                    return float(m.group(1).replace(",", ".").replace(".", ""))
                except Exception:
                    pass
        return 0.0

    def _parse(self, html: str) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        results: List[Product] = []

        # La búsqueda por código devuelve 2 articles; por nombre devuelve muchos.
        for art in soup.select("article.product-item"):
            # Enlace de detalle
            link = art.select_one("a[href]")
            if not link:
                continue
            href = link.get("href", "").strip()
            if not href:
                continue
            if href.startswith("/"):
                href = self.BASE_URL + href

            # Nombre completo (el texto del article)
            nombre = art.get_text(" ", strip=True)
            if not nombre:
                continue

            # Precio del texto del article
            precio_original = self._extraer_precio(nombre)

            # Imagen
            img = art.select_one("img[src]")
            imagen = ""
            if img:
                imagen = img.get("data-src") or img.get("src") or ""
                if imagen.startswith("data:"):
                    imagen = ""

            # Código: extraer de la URL del producto (p00PG3304316432903, p0039802012163601)
            codigo = ""
            m = re.search(r"/p00([A-Z0-9]+)", href)
            if m:
                codigo = m.group(1)

            results.append(self._make_product(
                nombre=nombre,
                codigo=codigo or self._query_codigo,
                precio_usd=precio_original,
                moneda_original=self.currency,
                precio_original=precio_original,
                url=href,
                imagen_url=imagen,
            ))
        return results