#!/usr/bin/env python3
"""
Búsqueda de repuestos en internet (sin API keys).
Usa DuckDuckGo HTML + parsing heurístico.
"""
import re
import asyncio
from urllib.parse import quote_plus
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup


DUCKDUCKGO_HTML = "https://html.duckduckgo.com/html/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

# Patrones para extraer info estructurada de snippets
PATTERNS = {
    "marca": re.compile(r"\b(Toyota|Honda|Ford|Chevrolet|Chevy|Nissan|Hyundai|Kia|Mazda|Subaru|Mitsubishi|Suzuki|Isuzu|Daihatsu|Lexus|Infiniti|Acura|Volkswagen|VW|Audi|BMW|Mercedes|Mercedes-Benz|Porsche|Volvo|Peugeot|Citroen|Renault|Fiat|Alfa Romeo|Lancia|Jeep|Chrysler|Dodge|Ram|GMC|Buick|Cadillac|Lincoln|Tesla|Rivian|Lucid|BYD|MG|Great Wall|Chery|JAC|BAIC|FAW|Dongfeng|SAIC|Geely|Changan|Chang\'an|JMC|JAC|Zotye|Brilliance|Haima|Lifan|Gonow|Huatai|Landwind|Yema|Zhongxing|Shuanghuan|Jonway|Hafei|Changhe|Changfeng|SGMW|Wuling|Baojun|Maxus|Roewe|Rising|IM|Neta|Hozon|Leapmotor|Xpeng|Nio|Li|Zeekr|Voyah|Aion|Deepal|Avatr|Huawei|Seres|Arcfox|Blue|Shark|Sealion|Dolphin|Seal|Atto|Yuan|Song|Han|Tang|Qin|E2|E3|E5|E6|E7|E8|E9|G3|G5|G6|G7|G9|HS|U5|U6|U7|U8|U9)\b", re.I),
    "modelo": re.compile(r"(?i)\b(CS15|CS35|CS55|CS75|CS85|CS95|Corolla|Camry|Civic|Accord|Focus|Fusion|Mustang|F-150|Silverado|Sentra|Altima|Elantra|Sonata|Optima|Sorento|Sportage|CX-5|CX-3|Outback|Forester|Impreza|WRX|STI|Lancer|Evo|Mirage|Outlander|Pajero|Tucson|Santa Fe|Kona|Venue|Palisade|Telluride|Seltos|Soul|Rio|Forte|Cerato|Spectra|Sephia|Mentor|Pride|Avella|Eado|Raeton|Alsvin|UNI-K|UNI-T|UNI-V|Oshan|X5|X7|Tiggo|Arrizo|Omni|Karry|M8|M6|T8|T9|X8|X9|E|ET|ES|EH|EHS)\b"),
    "lado": re.compile(r"\b(izquierdo|izq|left|derecho|der|right|delantero|front|trasero|rear)\b", re.I),
    "tipo": re.compile(r"\b(faro|headlight|faros|parachoques|bumper|parabrisas|windshield|espejo|mirror|retrovisor|puerta|door|capot|hood|maletero|trunk|aleron|spoiler|parrilla|grille|radiador|radiator|condensador|condenser|intercooler|motor|engine|transmision|transmission|frenos|brakes|discos|rotors|pastillas|pads|amortiguador|shock|strut|resorte|spring|brazo|control arm|bieleta|sway bar|link|terminal|tie rod|rotula|ball joint|buje|bushing|soporte|mount|biela|connecting rod|piston|piston|anillo|ring|valvula|valve|arbol|camshaft|cigueñal|crankshaft|bomba|pump|inyector|injector|sensor|sensor|modulo|module|ecu|ecm|pcm|tcm|bcm)\b", re.I),
}


async def buscar_repuesto_web(codigo: str, nombre: str = "") -> Optional[dict]:
    """
    Busca en DuckDuckGo y extrae info estructurada.
    Retorna dict con: marca, modelo, lado, tipo, fuente, snippets
    """
    query = f"{codigo} {nombre}".strip()
    if not query:
        return None

    url = f"{DUCKDUCKGO_HTML}?q={quote_plus(query)}"

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
    except Exception:
        return None

    soup = BeautifulSoup(html, "lxml")
    results = soup.select(".result__snippet, .result__url, .snippet, .web-result-description")

    snippets = []
    for r in results[:8]:
        text = r.get_text(" ", strip=True)
        if text and len(text) > 20:
            snippets.append(text)

    if not snippets:
        return None

    # Extraer info de los snippets combinados
    full_text = " | ".join(snippets)

    marca = _extraer(full_text, PATTERNS["marca"])
    modelo = _extraer(full_text, PATTERNS["modelo"])
    lado = _extraer(full_text, PATTERNS["lado"])
    tipo = _extraer(full_text, PATTERNS["tipo"])

    # Normalizar lado
    lado_norm = _normalizar_lado(lado) if lado else None

    return {
        "codigo": codigo,
        "nombre_busqueda": nombre,
        "marca": marca,
        "modelo": modelo,
        "lado": lado_norm,
        "tipo": tipo,
        "snippets": snippets[:3],
        "fuente": "DuckDuckGo (scraping)",
    }


def _extraer(texto: str, pattern: re.Pattern) -> Optional[str]:
    match = pattern.search(texto)
    if match:
        return match.group(1).capitalize()
    return None


def _normalizar_lado(lado: str) -> str:
    lado = lado.lower()
    if lado in ("izquierdo", "izq", "left"):
        return "Izquierdo"
    if lado in ("derecho", "der", "right"):
        return "Derecho"
    if lado in ("delantero", "front"):
        return "Delantero"
    if lado in ("trasero", "rear"):
        return "Trasero"
    return lado.capitalize()


async def buscar_multiples_fuentes(codigo: str, nombre: str = "") -> list[dict]:
    """
    Busca en múltiples fuentes y combina resultados.
    Actualmente solo DuckDuckGo, extensible.
    """
    resultados = []
    r = await buscar_repuesto_web(codigo, nombre)
    if r:
        resultados.append(r)
    return resultados


# Para testing directo
if __name__ == "__main__":
    async def test():
        r = await buscar_repuesto_web("4121020-BE101", "faro")
        print(r)

    asyncio.run(test())