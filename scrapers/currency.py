"""Normalización y conversión de precios a USD."""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiohttp

_PRICE_RE = re.compile(r"([A-Z$€£¥]{1,3})?\s*([\d][\d.,]{1,15})\s*([A-Z$€£¥]{1,3})?", re.I)

CURRENCY_BY_SYMBOL = {
    "$": "USD",
    "US$": "USD",
    "USD": "USD",
    "€": "EUR",
    "EUR": "EUR",
    "£": "GBP",
    "GBP": "GBP",
    "R$": "BRL",
    "BRL": "BRL",
    "$M": "MXN",
    "MXN": "MXN",
    "COP": "COP",
    "$C": "CAD",
    "CAD": "CAD",
    "S/": "PEN",
    "PEN": "PEN",
    "¥": "CNY",
    "CN¥": "CNY",
    "CNY": "CNY",
    "RMB": "CNY",
    "$CL": "CLP",
    "CLP": "CLP",
    "$AR": "ARS",
    "ARS": "ARS",
    "₪": "ILS",
    "ILS": "ILS",
}

# Tasas de cambio aproximadas (se intenta actualizar vía API gratuita)
EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "BRL": 0.20,
    "MXN": 0.058,
    "COP": 0.00025,
    "CAD": 0.73,
    "PEN": 0.27,
    "CNY": 0.14,
    "CLP": 0.0011,
    "ARS": 0.00095,
    "ILS": 0.27,
}

FX_RATES = EXCHANGE_RATES  # alias de compatibilidad

CACHE_FILE = Path(__file__).parent / "exchange_rates_cache.json"


def _load_rates_cache() -> dict:
    try:
        if CACHE_FILE.exists():
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _save_rates_cache(cache: dict) -> None:
    try:
        CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass


@dataclass
class PriceInfo:
    amount: float
    currency: str
    raw: str


async def get_exchange_rate(currency: str) -> float:
    """Obtener tasa de cambio a USD (tabla estática, caché local o API gratuita)."""
    currency = currency.upper()

    if currency in EXCHANGE_RATES:
        return EXCHANGE_RATES[currency]

    cache = _load_rates_cache()
    if currency in cache:
        return cache[currency]

    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.exchangerate-api.com/v4/latest/{currency}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rate = 1 / data["rates"]["USD"]
                    EXCHANGE_RATES[currency] = rate
                    cache[currency] = rate
                    _save_rates_cache(cache)
                    return rate
    except Exception:
        pass

    # Fallback a tasa por defecto
    return EXCHANGE_RATES.get(currency, 1.0)


async def convert_to_usd(amount: float, from_currency: str) -> float:
    """Convertir un monto de cualquier moneda a USD."""
    if from_currency.upper() == "USD":
        return round(amount, 2)
    rate = await get_exchange_rate(from_currency)
    return round(amount * rate, 2)


def format_price_usd(price_usd: float) -> str:
    """Formatear precio en USD."""
    return f"${price_usd:,.2f}"


def _parse_amount(num: str) -> Optional[float]:
    s = num.strip().replace(" ", "")
    if not re.fullmatch(r"[\d.,]+", s):
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) in (1, 2) and len(parts[0]) <= 4:
            pass
        else:
            s = s.replace(".", "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def normalize_price(raw: str) -> Optional[PriceInfo]:
    """Extrae monto y moneda de un texto de precio."""
    if not raw:
        return None
    text = raw.strip()
    m = _PRICE_RE.search(text)
    if not m:
        return None
    pre, num, post = m.groups()
    amount = _parse_amount(num)
    if amount is None:
        return None
    symbol = (pre or post or "").upper().replace("US$", "USD")
    if not symbol:
        currency = "USD"
    else:
        currency = CURRENCY_BY_SYMBOL.get(symbol)
        if currency is None:
            return None
    return PriceInfo(amount=amount, currency=currency, raw=raw.strip())


def to_usd(amount: float, currency: str) -> float:
    """Convierte un monto a USD usando las tasas locales (síncrono)."""
    if currency == "USD":
        return round(amount, 2)
    rate = FX_RATES.get(currency.upper())
    if rate is None:
        raise ValueError(f"No hay tasa de cambio configurada para {currency}")
    return round(amount * rate, 2)