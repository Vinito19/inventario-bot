"""Scrapers de tiendas de repuestos en Ecuador."""
from scrapers.ecuador.autopartsonline import AutopartsOnlineScraper
from scrapers.ecuador.imotriz import ImotrizScraper
from scrapers.ecuador.mansuera import MansueraScraper

__all__ = ["MansueraScraper", "ImotrizScraper", "AutopartsOnlineScraper"]