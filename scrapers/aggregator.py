"""Orquesta la búsqueda en múltiples scrapers con prioridad Ecuador."""
import asyncio
import logging
from typing import Dict, List

from scrapers.ecuador.imotriz import ImotrizScraper
from scrapers.ecuador.mansuera import MansueraScraper
from scrapers.international.repuestosboston import RepuestosBostonScraper
from scrapers.models import Product

logger = logging.getLogger(__name__)


class SearchAggregator:
    """Agrega resultados de múltiples scrapers con prioridad Ecuador."""

    def __init__(self):
        # Scrapers de Ecuador (prioridad alta)
        self.ecuador_scrapers = [
            MansueraScraper(),
            ImotrizScraper(),
            # Agregar más scrapers de Ecuador aquí
        ]

        # Scrapers internacionales (fallback).
        # Fuera del registro: Alibaba bloquea el tráfico automatizado y
        # AliExpress sólo expone tarjetas de recomendación en el HTML (la
        # rejilla real requiere una API mtop firmada por sesión). Incluirlos
        # devolvería precios de productos ajenos al repuesto buscado.
        self.international_scrapers = [
            RepuestosBostonScraper(),
            # Agregar más scrapers internacionales aquí
        ]

    async def search(self, codigo: str, nombre: str = "") -> Dict[str, List[Product]]:
        """
        Buscar repuesto con prioridad Ecuador → Internacional.

        Returns:
            Dict con estructura:
            {
                "ecuador": [productos],
                "internacional": [productos],
                "todos": [productos ordenados por precio]
            }
        """
        resultados: Dict[str, List[Product]] = {
            "ecuador": [],
            "internacional": [],
            "todos": [],
        }

        # 1. Buscar primero en sitios de Ecuador
        logger.info("Iniciando búsqueda en sitios de Ecuador para: %s", codigo)
        ecuador_results = await self._gather_all(self.ecuador_scrapers, codigo, nombre)

        for result in ecuador_results:
            if isinstance(result, Exception):
                logger.error("Error en scraper Ecuador: %s", result)
                continue
            resultados["ecuador"].extend(result)

        # 2. Buscar en internacionales siempre (para comparación de precios)
        logger.info("Buscando también en sitios internacionales para comparación")
        intl_results = await self._gather_all(self.international_scrapers, codigo, nombre)

        for result in intl_results:
            if isinstance(result, Exception):
                logger.error("Error en scraper internacional: %s", result)
                continue
            resultados["internacional"].extend(result)

        # 3. Combinar todos los resultados y ordenar por precio.
        # Los productos sin precio (precio 0, catálogos bajo cotización)
        # van al final: no se pueden comparar.
        resultados["todos"] = resultados["ecuador"] + resultados["internacional"]
        resultados["todos"].sort(key=lambda x: (x.precio_usd <= 0, x.precio_usd))

        # 4. Eliminar duplicados (mismo sitio + mismo precio).
        # Sin precio no se puede usar el precio como clave: se usa la URL o
        # el nombre, porque un catálogo bajo cotización devuelve todo a 0.
        seen = set()
        unique_results = []
        for prod in resultados["todos"]:
            if prod.precio_usd > 0:
                key = f"{prod.sitio}_{prod.precio_usd}"
            else:
                key = f"{prod.sitio}_{(prod.url or prod.nombre).strip().lower()}"
            if key not in seen:
                seen.add(key)
                unique_results.append(prod)

        resultados["todos"] = unique_results

        logger.info(
            "Búsqueda completada: %s Ecuador, %s Internacional",
            len(resultados["ecuador"]),
            len(resultados["internacional"]),
        )

        return resultados

    async def _gather_all(self, scrapers, codigo: str, nombre: str):
        return await asyncio.gather(
            *(scraper.search(codigo, nombre) for scraper in scrapers),
            return_exceptions=True,
        )