"""Scrapers de tiendas internacionales de repuestos."""
from scrapers.international.alibaba import AlibabaScraper
from scrapers.international.aliexpress import AliExpressScraper
from scrapers.international.repuestosboston import RepuestosBostonScraper

__all__ = ["AliExpressScraper", "AlibabaScraper", "RepuestosBostonScraper"]