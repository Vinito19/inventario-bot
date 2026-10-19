"""Paquete de scrapers de repuestos (Ecuador + internacional)."""
from scrapers.aggregator import SearchAggregator
from scrapers.base import BaseScraper, MaxRetriesError, RateLimitedError, ScrapeError
from scrapers.currency import (
    EXCHANGE_RATES,
    FX_RATES,
    PriceInfo,
    convert_to_usd,
    format_price_usd,
    get_exchange_rate,
    normalize_price,
    to_usd,
)
from scrapers.models import Product

__all__ = [
    "EXCHANGE_RATES",
    "FX_RATES",
    "BaseScraper",
    "MaxRetriesError",
    "PriceInfo",
    "Product",
    "RateLimitedError",
    "ScrapeError",
    "SearchAggregator",
    "convert_to_usd",
    "format_price_usd",
    "get_exchange_rate",
    "normalize_price",
    "to_usd",
]