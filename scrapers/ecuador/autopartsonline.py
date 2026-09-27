"""Scraper de AutoParts Online Shop (EE. UU., OpenCart)."""
from typing import List
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.currency import normalize_price
from scrapers.models import Product


class AutopartsOnlineScraper(BaseScraper):
    SITE_NAME = "autopartsonline"
    BASE_URL = "https://autopartsonlineshop.com"
    COUNTRY = "US"
    currency = "USD"
    request_delay = 2.0

    def search_url(self, query: str) -> str:
        return f"{self.base_url}/index.php?route=product/search&{urlencode({'search': query})}"

    def _parse(self, html: str) -> List[Product]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for card in soup.select(".product-thumb, .product-layout, div[class*=product]"):
            link = card.select_one("a[href]")
            title = card.select_one(".name, .caption h4, .product-title, h4")
            if not link or not title:
                continue
            href = link.get("href", "")
            if href.startswith("/"):
                href = self.base_url + href
            img = card.select_one("img[src]")
            price_el = card.select_one(".price, [class*=price]")
            price_info = normalize_price(price_el.get_text(" ", strip=True)) if price_el else None
            results.append(self._make_product(
                nombre=title.get_text(" ", strip=True),
                precio_usd=price_info.amount if price_info else 0.0,
                moneda_original=price_info.currency if price_info else self.currency,
                precio_original=price_info.amount if price_info else 0.0,
                url=href,
                imagen_url=img.get("src", "") if img else "",
            ))
        return results