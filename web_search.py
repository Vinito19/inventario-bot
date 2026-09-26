#!/usr/bin/env python3
"""
Búsqueda robusta de repuestos en internet (sin API keys).
- Async nativo (aiohttp)
- Múltiples motores: DuckDuckGo, Bing, Brave
- Extracción de precio SOLO si es Ecuador (USD, $, "ecuador", ".ec")
- Reintentos con backoff exponencial
- Caché persistente en archivo (JSON)
- Rate limiting local
"""
import re
import json
import asyncio
import time
import random
from pathlib import Path
from urllib.parse import quote_plus
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

import aiohttp
from bs4 import BeautifulSoup

# ─── Validación y sanitización de entrada ───────────────────────────────
CODIGO_PATTERN = re.compile(r'^[a-zA-Z0-9\-\.]{1,50}$')
NOMBRE_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-\.\,\/]{0,100}$')


def validar_codigo_busqueda(codigo: str) -> str:
    """
    Valida y sanitiza el código antes de buscar.
    Solo permite alfanuméricos, guiones y puntos.
    """
    if not codigo:
        raise ValueError("Código vacío")
    # Eliminar cualquier carácter no permitido
    limpio = re.sub(r'[^a-zA-Z0-9\-\.]', '', codigo)
    if not limpio:
        raise ValueError("Código de búsqueda inválido: solo se permiten letras, números, guiones y puntos")
    if len(limpio) > 50:
        raise ValueError("Código demasiado largo (máx 50 caracteres)")
    if not CODIGO_PATTERN.match(limpio):
        raise ValueError("Formato de código inválido")
    return limpio


def validar_nombre_busqueda(nombre: str) -> str:
    """
    Valida y sanitiza el nombre/descripción antes de buscar.
    Permite alfanuméricos, espacios, guiones, puntos, comas y barras.
    """
    if not nombre:
        return ""
    # Eliminar caracteres no permitidos
    limpio = re.sub(r'[^a-zA-Z0-9\s\-\.\,\/]', '', nombre)
    if len(limpio) > 100:
        limpio = limpio[:100]
    return limpio.strip()


# ─── Configuración ─────────────────────────────────────────────────────
CACHE_FILE = Path(__file__).parent / "web_search_cache.json"
CACHE_TTL = 3600 * 24  # 24 horas

# Motores de búsqueda (HTML scraping)
SEARCH_ENGINES = [
    {
        "name": "duckduckgo",
        "url": "https://html.duckduckgo.com/html/",
        "param": "q",
        "selectors": [".result__snippet", ".result__url", ".snippet", ".web-result-description"],
    },
    {
        "name": "bing",
        "url": "https://www.bing.com/search",
        "param": "q",
        "selectors": [".b_caption p", ".b_snippet", ".b_algoSlug"],
    },
    {
        "name": "brave",
        "url": "https://search.brave.com/search",
        "param": "q",
        "selectors": [".snippet-description", ".result-snippet", ".snippet"],
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-EC,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Patrones de extracción
PATTERNS = {
    "marca": re.compile(
        r"\b(Toyota|Honda|Ford|Chevrolet|Chevy|Nissan|Hyundai|Kia|Mazda|Subaru|Mitsubishi|Suzuki|Isuzu|Daihatsu|"
        r"Lexus|Infiniti|Acura|Volkswagen|VW|Audi|BMW|Mercedes|Mercedes-Benz|Porsche|Volvo|Peugeot|Citroen|Renault|"
        r"Fiat|Alfa Romeo|Lancia|Jeep|Chrysler|Dodge|Ram|GMC|Buick|Cadillac|Lincoln|Tesla|Rivian|Lucid|BYD|MG|"
        r"Great Wall|Chery|JAC|BAIC|FAW|Dongfeng|SAIC|Geely|Changan|Chang'an|JMC|Zotye|Brilliance|Haima|Lifan|"
        r"Gonow|Huatai|Landwind|Yema|Zhongxing|Shuanghuan|Jonway|Hafei|Changhe|Changfeng|SGMW|Wuling|Baojun|"
        r"Maxus|Roewe|Rising|IM|Neta|Hozon|Leapmotor|Xpeng|Nio|Li|Zeekr|Voyah|Aion|Deepal|Avatr|Huawei|Seres|"
        r"Arcfox|Blue|Shark|Sealion|Dolphin|Seal|Atto|Yuan|Song|Han|Tang|Qin|E2|E3|E5|E6|E7|E8|E9|G3|G5|G6|G7|G9|HS|U5|U6|U7|U8|U9)\b",
        re.I,
    ),
    "modelo": re.compile(
        r"(?i)\b(CS15|CS35|CS55|CS75|CS85|CS95|Corolla|Camry|Civic|Accord|Focus|Fusion|Mustang|F-150|Silverado|"
        r"Sentra|Altima|Elantra|Sonata|Optima|Sorento|Sportage|CX-5|CX-3|Outback|Forester|Impreza|WRX|STI|Lancer|Evo|"
        r"Mirage|Outlander|Pajero|Tucson|Santa Fe|Kona|Venue|Palisade|Telluride|Seltos|Soul|Rio|Forte|Cerato|Spectra|"
        r"Sephia|Mentor|Pride|Avella|Eado|Raeton|Alsvin|UNI-K|UNI-T|UNI-V|Oshan|X5|X7|Tiggo|Arrizo|Omni|Karry|M8|M6|T8|T9|X8|X9|E|ET|ES|EH|EHS)\b",
    ),
    "lado": re.compile(r"\b(izquierdo|izq|left|derecho|der|right|delantero|front|trasero|rear)\b", re.I),
    "tipo": re.compile(
        r"\b(faro|headlight|faros|parachoques|bumper|parabrisas|windshield|espejo|mirror|retrovisor|puerta|door|"
        r"capot|hood|maletero|trunk|aleron|spoiler|parrilla|grille|radiador|radiator|condensador|condenser|"
        r"intercooler|motor|engine|transmision|transmission|frenos|brakes|discos|rotors|pastillas|pads|"
        r"amortiguador|shock|strut|resorte|spring|brazo|control arm|bieleta|sway bar|link|terminal|tie rod|"
        r"rotula|ball joint|buje|bushing|soporte|mount|biela|connecting rod|piston|anillo|ring|valvula|valve|"
        r"arbol|camshaft|cigueñal|crankshaft|bomba|pump|inyector|injector|sensor|modulo|module|ecu|ecm|pcm|tcm|bcm)\b",
        re.I,
    ),
    # Precio en Ecuador: USD, $, "ecuador", ".ec", "quito", "guayaquil"
    "precio_ec": re.compile(
        r"(?i)(\$|usd)\s*([\d.,]{2,10})\b.*?(ecuador|\.ec|quito|guayaquil|cuenca|ambato|machala|loja|riobamba|"
        r"santo domingo|ibarra|tulcan|latacunga|esmeraldas|puerto viejo|manta|babaoyo|azogues|nueva loja|"
        r"coca|tena|puy|macuco|palenque|san lorenzo|pedernales|jama|santa ana|paján|jipijapa|nobol|daules|"
        r"balzar|colimes|el triunfo|marcabeli|balsas|arenillas|huaquillas|pasaje|piñas|zaruma|portovelo|"
        r"cajamarca|calvas|chinchipe|paltas|pindal|pucara|quien|saraguro|sozoranga|veintimilla|zapotillo)",
    ),
    # Precio genérico (fallback)
    "precio": re.compile(r"(?i)(\$|usd|precio)\s*([\d.,]{2,10})"),
}

# Rate limiter por usuario (token bucket)
class UserRateLimiter:
    def __init__(self, max_per_user: int = 3, window: int = 60):
        self.max_per_user = max_per_user
        self.window = window
        self.user_requests: Dict[int, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def acquire(self, user_id: int) -> bool:
        """Intenta adquirir un slot para el usuario. Retorna True si OK, False si rate limited."""
        async with self._lock:
            now = time.time()
            # Limpiar requests antiguos
            self.user_requests[user_id] = [
                t for t in self.user_requests[user_id] if now - t < self.window
            ]
            if len(self.user_requests[user_id]) >= self.max_per_user:
                return False  # Rate limited
            self.user_requests[user_id].append(now)
            return True

USER_RATE_LIMITER = UserRateLimiter(max_per_user=3, window=60)

# ─── Caché persistente ────────────────────────────────────────────────
class Cache:
    def __init__(self, path: Path, ttl: int):
        self.path = path
        self.ttl = ttl
        self._data: Dict[str, tuple[Any, float]] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for k, v in raw.items():
                    self._data[k] = (v["value"], v["timestamp"])
            except Exception:
                self._data = {}

    def _save(self):
        try:
            raw = {k: {"value": v[0], "timestamp": v[1]} for k, v in self._data.items()}
            # Permisos restrictivos: solo owner read/write (0o600)
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False)
        except Exception:
            pass

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        if key in self._data:
            value, ts = self._data[key]
            if now - ts < self.ttl:
                return value
            else:
                del self._data[key]
                self._save()
        return None

    def set(self, key: str, value: Any):
        self._data[key] = (value, time.time())
        self._save()

CACHE = Cache(CACHE_FILE, CACHE_TTL)

# ─── Utilidades ───────────────────────────────────────────────────────
def _extraer(texto: str, pattern: re.Pattern) -> Optional[str]:
    match = pattern.search(texto)
    if match:
        return match.group(1).capitalize() if match.lastindex == 1 else match.group(0).capitalize()
    return None


def _extraer_precio_ecuador(texto: str) -> Optional[str]:
    """Extrae precio solo si hay indicio de Ecuador en el texto."""
    # Buscar patrón específico Ecuador
    match = PATTERNS["precio_ec"].search(texto)
    if match:
        # match groups: 0=full, 1=símbolo($/USD), 2=valor, 3=indicador Ecuador
        simbolo = match.group(1) if match.lastindex >= 1 else "$"
        valor = match.group(2) if match.lastindex >= 2 else ""
        return f"{simbolo}{valor}".strip()

    # Fallback: precio genérico pero SOLO si texto menciona Ecuador
    if any(kw in texto.lower() for kw in ("ecuador", ".ec", "quito", "guayaquil", "cuenca", "ambato", "machala")):
        match = PATTERNS["precio"].search(texto)
        if match:
            simbolo = match.group(1) if match.lastindex >= 1 else "$"
            valor = match.group(2) if match.lastindex >= 2 else ""
            return f"{simbolo}{valor}".strip()
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


def _limpiar_valor(valor: str) -> str:
    # Normalizar separadores de miles/decimales
    valor = valor.replace(".", "").replace(",", ".")
    try:
        return f"{float(valor):.2f}"
    except ValueError:
        return valor

# ─── Búsqueda por motor ───────────────────────────────────────────────
async def _buscar_en_motor(session: aiohttp.ClientSession, engine: dict, query: str) -> List[str]:
    """Busca en un motor específico y retorna lista de snippets."""
    url = f"{engine['url']}?{engine['param']}={quote_plus(query)}"

    try:
        timeout = aiohttp.ClientTimeout(total=12)
        async with session.get(url, timeout=timeout) as resp:
            if resp.status != 200:
                return []
            html = await resp.text()
    except asyncio.TimeoutError:
        return []
    except aiohttp.ClientError:
        return []
    except Exception:
        return []

    soup = BeautifulSoup(html, "lxml")
    snippets = []
    for selector in engine["selectors"]:
        for el in soup.select(selector):
            text = el.get_text(" ", strip=True)
            if text and len(text) > 15:
                snippets.append(text)
    return snippets


async def _buscar_con_reintentos(session: aiohttp.ClientSession, query: str, max_intentos: int = 2) -> List[str]:
    """Busca en todos los motores con reintentos y backoff."""
    todos_snippets = []

    for engine in SEARCH_ENGINES:
        for intento in range(max_intentos):
            try:
                snippets = await _buscar_en_motor(session, engine, query)
                if snippets:
                    todos_snippets.extend(snippets)
                    break  # Éxito con este motor
            except Exception:
                pass

            if intento < max_intentos - 1:
                wait = (2 ** intento) + random.uniform(0, 0.5)
                await asyncio.sleep(wait)

    return todos_snippets


# ─── Función principal ────────────────────────────────────────────────
async def buscar_repuesto_web(codigo: str, nombre: str = "", user_id: int = 0) -> Optional[Dict]:
    """
    Busca repuesto y retorna dict con: marca, modelo, lado, tipo, precio_ecuador, snippets, fuente.
    """
    # Rate limit por usuario (1 búsqueda = 1 request, no por motor)
    if user_id > 0:
        allowed = await USER_RATE_LIMITER.acquire(user_id)
        if not allowed:
            return None  # Rate limited

    # Validar y sanitizar entrada ANTES de usar
    try:
        codigo = validar_codigo_busqueda(codigo)
        nombre = validar_nombre_busqueda(nombre)
    except ValueError:
        return None

    query = f"{codigo} {nombre}".strip()
    if not query:
        return None

    # 1. Caché
    cache_key = f"{codigo}|{nombre}".lower()
    cached = CACHE.get(cache_key)
    if cached:
        return cached

    # 2. Búsqueda
    all_snippets = []
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
            all_snippets = await _buscar_con_reintentos(session, query)
    except Exception:
        return None

    if not all_snippets:
        return None

    # Deduplicar manteniendo orden
    seen = set()
    snippets = []
    for s in all_snippets:
        if s not in seen:
            seen.add(s)
            snippets.append(s)
    snippets = snippets[:10]

    full_text = " | ".join(snippets)

    # 3. Extracción
    marca = _extraer(full_text, PATTERNS["marca"])
    modelo = _extraer(full_text, PATTERNS["modelo"])
    lado = _extraer(full_text, PATTERNS["lado"])
    tipo = _extraer(full_text, PATTERNS["tipo"])
    precio_ec = _extraer_precio_ecuador(full_text)

    lado_norm = _normalizar_lado(lado) if lado else None

    resultado = {
        "codigo": codigo,
        "nombre_busqueda": nombre,
        "marca": marca,
        "modelo": modelo,
        "lado": lado_norm,
        "tipo": tipo,
        "precio_ecuador": precio_ec,  # Solo si detecta Ecuador
        "snippets": snippets[:4],
        "fuente": "DuckDuckGo + Bing + Brave (scraping)",
    }

    # 4. Guardar caché
    CACHE.set(cache_key, resultado)
    return resultado


# ─── Testing ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    async def test():
        casos = [
            ("4121020-BE101", "faro"),
            ("BRK-001", "pastillas freno"),
            ("123456", "filtro aceite"),
        ]
        for codigo, nombre in casos:
            print(f"\n--- {codigo} {nombre} ---")
            r = await buscar_repuesto_web(codigo, nombre)
            print(json.dumps(r, indent=2, ensure_ascii=False))

    asyncio.run(test())