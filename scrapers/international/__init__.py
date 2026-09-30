"""Scrapers de tiendas internacionales de repuestos."""
from scrapers.international.alibaba import AlibabaScraper
from scrapers.international.aliexpress import AliExpressScraper
from scrapers.international.elmridgea import ElmridgeaScraper
from scrapers.international.kiauto import KiautoScraper
from scrapers.international.repuestosboston import RepuestosBostonScraper

__all__ = [
    "AliExpressScraper", "AlibabaScraper", "RepuestosBostonScraper",
    "ElmridgeaScraper", "KiautoScraper",
]