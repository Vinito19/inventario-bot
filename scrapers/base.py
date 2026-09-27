"""Base común para todos los scrapers de repuestos."""
import asyncio
import random
import re
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

from scrapers.currency import PriceInfo
from scrapers.models import Product

logger = logging.getLogger(__name__)


class ScrapeError(Exception):
    pass


_STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "para", "con", "un", "una",
    "unos", "unas", "and", "the", "of", "en", "y", "a", "por",
}

# Palabras genéricas del rubro: si el único parecido es una de ellas, el
# producto no es el buscado ("Refuerzo Delantero" no es un "faro delantero").
_GENERICOS = {
    "delantero", "delantera", "trasero", "trasera", "izquierdo", "derecho",
    "izquierda", "original", "alternativo", "alternativa", "generico",
    "repuesto", "repuestos", "automotriz", "automoviles", "vehiculo",
    "toyota", "hyundai", "kia", "chevrolet", "nissan", "mazda", "honda",
    "ford", "renault", "chery", "suzuki", "great", "wall", "motors",
    "repuesto", "autoparts", "parts", "originales",
}

# Marcas para extraer compatibilidad (marca + modelo + años).
# "Ranault" está junto a "Renault" a propósito: es el error de tipeo que hay en
# la base de datos y ambos nombres aparecen en las descripciones.
_MARCAS = (
    "Chery", "Toyota", "Honda", "Ford", "Chevrolet", "Hyundai", "Kia",
    "Nissan", "Mazda", "Peugeot", "Suzuki", "Mitsubishi", "Ram",
    "Volkswagen", "Changan", "Great Wall", "Renault", "Ranault", "GWM",
)
_MARCAS_COMPATIBILIDAD = "|".join(re.escape(marca) for marca in _MARCAS)
_MARCAS_PALABRAS = {marca.lower() for marca in _MARCAS} | {"great", "wall", "vw"}

# Categorías de función, en orden de prioridad: gana la primera que coincide.
# El orden importa en dos casos:
#   - "Faro posterior" antes que "faro": un faro no siempre es delantero.
#   - "Moldura de guardafango" antes que "guardafango": la pieza es la moldura.
# Los términos van sin acentos porque `_extract_function` los normaliza antes
# de comparar, así "Alerón" y "Aleron" caen en la misma categoría.
_CATEGORIAS_FUNCION: tuple = (
    (("luz diurna", "daytime running", "drl"), "Luz Diurna (DRL)"),
    (("faro posterior", "faro trasero"), "Faro Trasero"),
    (("optico", "optica", "faro", "headlight"), "Faro Delantero"),
    (("farol", "tail light", "luz de freno", "stop light"), "Farol Trasero"),
    (("moldura", "moño", "monomoldura"), "Moldura"),
    (("guardafango", "fender"), "Guardafango"),
    (("parachoques", "bumper"), "Parachoques"),
    (("mascarilla", "rejilla", "grille"), "Mascarilla"),
    (("espejo", "retrovisor", "mirror"), "Espejo Retrovisor"),
    (("parabrisas", "windshield", "winshield"), "Parabrisas"),
    # Las piezas que se fijan al panel van ANTES que el panel: en "Bisagra
    # Capot" y "Aleron de Compuerta" la función es la bisagra o el alerón.
    (("bisagra", "hinge"), "Bisagra"),
    (("aleron", "spoiler"), "Aleron"),
    (("capot", "hood"), "Capot"),
    (("compuerta", "porton"), "Compuerta"),
    (("estribo", "running board", "side step"), "Estribo"),
    (("guardapolvo", "mudguard", "fender flap"), "Guardapolvos"),
    (("ducto", "conducto", "tuberia de aire"), "Ducto de Aire"),
    (("radiador", "radiator"), "Radiador"),
    (("bomba de agua", "water pump"), "Bomba de Agua"),
    (("amortiguador", "shock", "strut"), "Amortiguador"),
    (("freno", "brake", "pastilla", "caliper", "disco de freno"), "Sistema de Frenos"),
    (("filtro", "filter"), "Filtro"),
    (("buje", "rodamiento", "bearing"), "Rodamiento"),
    (("embrague", "clutch"), "Embrague"),
    (("transmision", "caja de cambios", "gearbox"), "Transmision"),
)

# Palabras que cortan el nombre del modelo: a partir de ahí ya no se está
# hablando del modelo sino del tipo de pieza o de su posición
# ("Kia Soluto Faro delantero derecho año 2021" -> "Soluto").
_CORTE_MODELO = _GENERICOS | {
    "faro", "farol", "mascarilla", "amortiguador", "retrovisor", "espejo",
    "parachoques", "filtro", "pastillas", "freno", "brake", "oil", "año",
    "anio", "luz", "unidad", "kit", "juego", "conjunto", "barra", "molded",
    "foco", "piloto", "terminal", "cable", "bateria", "sensor", "bobina",
    "lado", "lados", "y", "o", "u", "para", "con", "sin",
}


class RateLimitedError(ScrapeError):
    pass


class MaxRetriesError(ScrapeError):
    pass


class BaseScraper(ABC):
    """Clase base para scrapers de sitios de repuestos."""

    SITE_NAME = "Base"
    COUNTRY = ""
    BASE_URL = ""
    currency: str = "USD"
    use_cloudscraper: bool = False
    use_playwright: bool = False
    retries: int = 2
    request_delay: float = 1.0
    timeout: float = 12.0
    wait_for_selector: str = ""
    # "visible" espera a que el elemento se vea; en catálogos con carruseles
    # los productos quedan ocultos tras un slide y la espera se agota siempre.
    # Con "attached" basta con que el nodo esté en el DOM, que es lo que lee
    # el parser. "timeout_selector" acota esa espera: si el catálogo no tiene
    # el repuesto, el selector no aparecerá nunca.
    estado_selector: str = "visible"
    timeout_selector: Optional[float] = None
    settle_ms: int = 3500
    # Si es False, sólo se busca por nombre: útil en catálogos que no indexan
    # el código OEM y donde cada consulta extra cuesta una carga completa.
    buscar_por_codigo: bool = True
    # Catálogos que no indexan la frase completa del repuesto: al buscar
    # "Faro Kia Soluto" no devuelven nada aunque sí tengan el faro. Se
    # reintenta recortando los términos finales (marca, modelo y año).
    degradar_consulta: bool = False
    max_consultas_respaldo: int = 2
    # Sitios que ya devuelven el HTML con los productos y no necesitan el
    # navegador: se pide primero por HTTP y sólo se cae a Playwright si falla.
    aiohttp_primero: bool = False
    viewport: Dict[str, int] = {"width": 1440, "height": 900}
    locale: str = "es-EC"
    headers: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-EC,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, session: Optional[aiohttp.ClientSession] = None,
                 request_delay: Optional[float] = None):
        self._session = session
        self._cloudscraper_instance: Any = None
        self._last_request_at = 0.0
        self._query_codigo = ""
        self._query_nombre = ""
        if request_delay is not None:
            self.request_delay = request_delay

    @property
    def name(self) -> str:
        return self.SITE_NAME.lower()

    @property
    def country(self) -> str:
        return self.COUNTRY

    @property
    def base_url(self) -> str:
        return self.BASE_URL

    @abstractmethod
    def search_url(self, query: str) -> str:
        ...

    @abstractmethod
    def _parse(self, html: str) -> List[Product]:
        ...

    async def search(self, codigo: str, nombre: str = "", limit: int = 5) -> List[Product]:
        """Buscar repuesto por código y nombre.

        Los catálogos de repuestos rara vez indexan el código OEM del
        fabricante, pero sí el nombre descriptivo del repuesto. Por eso se
        consulta primero el nombre y, sólo si no hay resultados, se reintenta
        con el código (normalizado sin guiones, que es como lo indexan varios
        sitios). Los scrapers con `buscar_por_codigo = False` evitan ese
        segundo intento, que en catálogos lentos duplica el tiempo de espera.
        """
        self._query_codigo = (codigo or "").strip()
        self._query_nombre = (nombre or "").strip()

        candidatas: List[str] = [self._query_nombre]
        if self.buscar_por_codigo:
            candidatas += [self._query_codigo,
                           self._query_codigo.replace("-", "").replace(".", "")]

        consultas: List[str] = []
        for consulta in candidatas:
            if consulta and consulta not in consultas:
                consultas.append(consulta)
        if not consultas:
            return []

        resultados: List[Product] = []

        # La primera consulta es la más probable (el nombre descriptivo).
        html = await self._get_html(self.search_url(consultas[0]))
        resultados.extend(p for p in self._parse(html) if self._es_relevante(p, consultas[0]))

        # Si no bastó, el resto se pide en paralelo con un solo navegador:
        # abrir un Chromium por consulta triplicaba el tiempo de espera.
        if len(self._dedupe(resultados)) < limit and len(consultas) > 1:
            await self._throttle()
            for html_extra, consulta in zip(
                await self._get_html_multi([self.search_url(c) for c in consultas[1:]]),
                consultas[1:],
            ):
                if not html_extra:
                    continue
                resultados.extend(
                    p for p in self._parse(html_extra) if self._es_relevante(p, consulta)
                )

        # Catálogos que no indexan la frase completa: se reintenta con el
        # nombre recortado ("Faro Kia Soluto" -> "Faro Kia" -> "Faro"). Los
        # resultados se validan contra la consulta ORIGINAL, no contra la
        # recortada, para no perder precisión al ampliar la búsqueda.
        if self.degradar_consulta and len(self._dedupe(resultados)) < limit:
            respaldos = self._consultas_respaldo(consultas[0])
            if respaldos:
                await self._throttle()
                for html_extra, consulta in zip(
                    await self._get_html_multi([self.search_url(c) for c in respaldos]),
                    respaldos,
                ):
                    if not html_extra:
                        continue
                    resultados.extend(
                        p for p in self._parse(html_extra)
                        if self._es_relevante(p, consultas[0])
                    )
        return self._dedupe(resultados)[:limit]

    def _consultas_respaldo(self, consulta: str) -> List[str]:
        """Versiones más cortas de la consulta, de la más específica a la más amplia.

        Los catálogos indexan descripciones cortas ("faro kia") y no la frase
        completa del inventario ("Faro delantero izquierdo Kia Soluto 1.4
        2019"): al recortar se conserva el tipo de pieza y el lado, que es lo
        que distingue un faro de un ducto de aire, y se pierde el modelo y el
        año, que es donde el catálogo es más exigente.
        """
        palabras = [p for p in re.split(r"\s+", (consulta or "").strip()) if p]
        respaldos: List[str] = []
        for largo in (3, 2, 1):
            if len(palabras) <= largo:
                continue
            candidata = " ".join(palabras[:largo])
            if candidata and candidata not in respaldos:
                respaldos.append(candidata)
            if len(respaldos) >= self.max_consultas_respaldo:
                break
        return respaldos

    def _make_product(self, nombre: str, extra_text: str = "", codigo: str = "",
                      precio_usd: float = 0.0, precio_original: float = 0.0,
                      moneda_original: str = "", url: str = "", imagen_url: str = "") -> Product:
        """Construye un Product aplicando los extractores de función/lado/tecnología.

        Los extractores se alimentan sólo del producto (código, nombre y datos
        del sitio). No se incluye el texto buscado: si no, todos los
        resultados heredarían la función del término consultado.
        """
        codigo = codigo or self._query_codigo
        text = f"{codigo} {nombre} {extra_text}".strip()
        return Product(
            codigo=codigo,
            nombre=nombre.strip(),
            precio_usd=precio_usd,
            moneda_original=moneda_original or self.currency,
            precio_original=precio_original,
            funcion=self._extract_function(text),
            lado=self._extract_side(text, codigo),
            tecnologia=self._extract_technology(text),
            compatibilidad=self._extract_compatibility(text),
            componente_hermano=self._extract_sibling_component(text, codigo),
            sitio=self.name,
            pais=self.country,
            url=url,
            imagen_url=imagen_url,
        )

    def _dedupe(self, results: List[Product]) -> List[Product]:
        seen = set()
        out = []
        for r in results:
            key = (r.url or r.nombre).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(r)
        return out

    def _es_relevante(self, producto: Product, consulta: str) -> bool:
        """Filtra resultados que no corresponden a lo buscado.

        Los catálogos usan búsquedas difusas: al pedir "faro" devuelven
        ductos y molduras, y al pedir un código numérico devuelven la primera
        página de resultados sin relación. Se exige que el producto comparta
        el código OEM (en el nombre o en la URL, que suele incluirlo) o que su
        tipo de pieza coincida con el término principal de la consulta.
        """
        consulta = (consulta or "").strip().lower()
        if not consulta:
            return True

        objetivo = f"{producto.nombre} {producto.url}".lower()
        objetivo_plano = re.sub(r"[^a-z0-9]", "", objetivo)

        codigo_plano = re.sub(r"[^a-z0-9]", "", self._query_codigo.lower())
        if len(codigo_plano) >= 6 and codigo_plano in objetivo_plano:
            return True

        tokens = [t for t in re.split(r"[^a-z0-9]+", consulta)
                  if len(t) >= 4 and t not in _STOPWORDS]
        if not tokens:
            # La consulta es sólo un código ("225.429-02"). Los buscadores
            # difusos devuelven piezas sin relación (el código se parte en
            # "225" + "429" + "02" y casa con cualquier año del título), así
            # que sin coincidencia del código en nombre o URL no se acepta.
            if codigo_plano:
                return codigo_plano in objetivo_plano
            return True

        # La coincidencia debe estar en el tipo de pieza, no en la
        # descripción: "Deposito ... sin Lava Faros" menciona faros pero es
        # un depósito limpiaparabrisas. Se mira el inicio del título.
        tipo_pieza = " ".join((producto.nombre or "").lower().split()[:6])

        def coincide(token: str) -> bool:
            # Límite de palabra: "faro" no debe coincidir dentro de otra
            # palabra; se admite el plural simple.
            return bool(re.search(rf"\b{re.escape(token)}\w{{0,1}}\b", tipo_pieza))

        especificos = [t for t in tokens if t not in _GENERICOS]
        if not especificos:
            return any(coincide(t) for t in tokens)

        # El primer término específico es el tipo de pieza que se pidió
        # ("faro delantero hyundai santa fe" -> "faro"). Si no aparece, el
        # producto es de otra pieza aunque coincida el modelo o la marca.
        return coincide(especificos[0])

    def _extract_function(self, text: str) -> str:
        """Extraer función del repuesto del texto.

        Se busca la primera categoría que coincida, en orden: los términos
        específicos ("luz diurna", "faro posterior") van antes de los generales
        ("faro") y las piezas de carrocería que se nombran junto al tipo
        ("moldura de guardafango") antes que la pieza que las contiene.
        """
        texto = self._sin_acentos((text or "").lower())

        for terminos, categoria in _CATEGORIAS_FUNCION:
            if any(self._contiene_palabra(texto, t) for t in terminos):
                return categoria

        return "Repuesto Automotriz"

    @staticmethod
    def _sin_acentos(texto: str) -> str:
        """'Alerón' y 'Aleron' deben buscar la misma categoría."""
        replacements = (
            ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
            ("ü", "u"),
        )
        for acentuada, simple in replacements:
            texto = texto.replace(acentuada, simple)
        return texto

    @staticmethod
    def _contiene_palabra(texto: str, termino: str) -> bool:
        """Busca un término como palabra completa, admitiendo plural y prefijo.

        Sin límites, "aro" aparece dentro de "parachoques" y "capot" dentro de
        "capotaje"; con límites, "ducto" no debe casar con "producto".
        """
        return bool(re.search(rf"\b{re.escape(termino)}\w{{0,2}}\b", texto))

    def _extract_side(self, text: str, codigo: str) -> str:
        """Extraer lado del repuesto."""
        text_lower = text.lower()
        codigo_lower = codigo.lower()

        # Detectar del código
        if codigo_lower.endswith(("rh", "r")):
            return "Derecho"
        elif codigo_lower.endswith(("lh", "l")):
            return "Izquierdo"

        # Del texto. Se aceptan las formas masculinas y femeninas ("Faro
        # Delantero Derecha") y las abreviaturas con límite de palabra, para
        # que "rh" no case dentro de otra palabra ("Marathi", "Thor"...).
        if re.search(r"\b(derech[oa]|right|rh|passenger)\b", text_lower):
            return "Derecho"
        if re.search(r"\b(izquierd[oa]|left|lh|driver)\b", text_lower):
            return "Izquierdo"

        return "No especificado"

    def _extract_technology(self, text: str) -> str:
        """Extraer tecnología del repuesto."""
        text_lower = text.lower()

        if "led" in text_lower:
            return "LED"
        elif "xenon" in text_lower or "xenón" in text_lower:
            return "Xenón"
        elif "halogen" in text_lower or "halógeno" in text_lower:
            return "Halógeno"

        return "No especificada"

    @staticmethod
    def _recortar_modelo(texto: str) -> str:
        """Limpia el fragmento de modelo: descarta tipo de pieza, posición,
        marcas y años, conservando el nombre del modelo
        ("Soluto Faro delantero Kia Soluto lado derecho año 2021" -> "Soluto")."""
        # El texto viene con nombre + descripción, así que la marca suele
        # repetirse; lo que sigue a la última repetición es el modelo.
        partes = re.split(rf"\b(?:{_MARCAS_COMPATIBILIDAD})\b", texto, re.IGNORECASE)
        if len(partes) > 1:
            texto = partes[-1]

        palabras: List[str] = []
        for palabra in re.split(r"\s+", texto.strip()):
            limpia = palabra.strip(".,:;()[]_-").lower()
            # Cualquier token con un año dentro ("2017", "2017-", "2018-2020")
            # es un año, no parte del modelo.
            if not limpia or re.search(r"(?:19|20)\d{2}", limpia):
                continue
            if limpia in _CORTE_MODELO or limpia in _MARCAS_PALABRAS:
                continue
            if palabras and limpia == palabras[-1].lower():
                continue
            palabras.append(palabra.strip(".,:;()[]_-"))
        return " ".join(palabras[-3:])  # "CX 5", "CR V", "Tiggo 2 pro"

    @staticmethod
    def _recortar_anos(texto: str) -> str:
        """Normaliza el rango de años: "2021 2023" / "2021- 2023" -> "2021-2023"."""
        anios: List[str] = []
        for anio in re.findall(r"(?:19|20)\d{2}", texto):
            if anio not in anios:
                anios.append(anio)
            if len(anios) == 2:
                break
        return "-".join(anios)

    def _extract_compatibility(self, text: str) -> List[str]:
        """Extraer compatibilidad (marca + modelo + años) del texto."""
        compatibilities = []

        # Buscar patrones de marca + modelo + año, en ambos órdenes:
        # "Kia Soluto 2021" y "2021 Kia Soluto". Se toleran comas, guiones y la
        # palabra "año" entre el modelo y el año ("Tiggo 2 pro, año 2021").
        patterns = [
            rf"({_MARCAS_COMPATIBILIDAD})\s+([\w\s\-.]+)[\s,–—-]*"
            r"(?:(?:año|anio|modelo)[\s,–—-]*)?"
            r"(20\d{2}(?:\s*[-,]\s*20\d{2})*)",
            rf"(20\d{{2}})\s+({_MARCAS_COMPATIBILIDAD})\s+([\w\s\-.]+)",
        ]

        for pattern in patterns:
            for match in re.findall(pattern, text, re.IGNORECASE):
                if len(match) != 3:
                    continue
                if match[0].isdigit():  # "2021 Kia Soluto"
                    marca, modelo, anios = match[1], match[2], match[0]
                else:  # "Kia Soluto 2021"
                    marca, modelo, anios = match[0], match[1], match[2]
                # Los años pueden haber quedado dentro del fragmento de modelo
                # ("... año 2021" + "2023"), así que se leen de ambos.
                rango = self._recortar_anos(f"{modelo} {anios}")
                modelo = self._recortar_modelo(modelo)
                compatibilities.append(
                    f"{marca.title()} {modelo} {rango}".strip()
                )

        return sorted(set(compatibilities)) if compatibilities else ["Verificar con vendedor"]

    def _extract_sibling_component(self, text: str, codigo: str) -> Optional[str]:
        """Extraer componente hermano (código similar, difiere en el último carácter)."""
        if len(codigo) <= 1:
            return None

        codigo_base = codigo[:-1]
        pattern = rf"{re.escape(codigo_base)}[A-Z0-9]"
        matches = re.findall(pattern, text, re.IGNORECASE)

        for match in matches:
            if match.upper() != codigo.upper():
                return match.upper()

        return None

    @staticmethod
    def _build_url(url: str, params: Optional[Dict[str, Any]] = None) -> str:
        if not params:
            return url
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}{urlencode(params)}"

    async def _throttle(self) -> None:
        now = time.monotonic()
        wait = max(0.0, self._last_request_at + self.request_delay - now)
        if wait:
            await asyncio.sleep(wait)
        self._last_request_at = time.monotonic()

    async def _get_html(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        last_exc: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            await self._throttle()
            try:
                return await self._fetch_html_layered(url, params)
            except Exception as exc:
                last_exc = exc
            if attempt < self.retries:
                await asyncio.sleep((2 ** attempt) + random.uniform(0, 0.5))
        raise last_exc if last_exc else MaxRetriesError(f"{self.name}: sin respuesta")

    async def _fetch_html_layered(self, url: str,
                                  params: Optional[Dict[str, Any]] = None) -> str:
        fetch_order: List[Any] = []
        if self.aiohttp_primero:
            fetch_order.append(self._get_html_aiohttp)
        if self.use_cloudscraper:
            fetch_order.append(self._get_html_cloudscraper)
        if self.use_playwright:
            fetch_order.append(self._get_html_playwright)
        if not fetch_order:
            return await self._get_html_aiohttp(url, params)

        last_exc: Optional[Exception] = None
        for fetcher in fetch_order:
            try:
                return await fetcher(url, params)
            except Exception as exc:
                last_exc = exc
        return await self._get_html_aiohttp(url, params) if last_exc else ""

    async def _get_html_aiohttp(self, url: str,
                                params: Optional[Dict[str, Any]] = None) -> str:
        full = self._build_url(url, params)
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async def _fetch(session: aiohttp.ClientSession) -> str:
            async with session.get(full, timeout=timeout) as resp:
                if resp.status in (403, 429):
                    raise RateLimitedError(f"[{self.name}] bloqueado ({resp.status}) en {url}")
                if resp.status != 200:
                    raise MaxRetriesError(f"[{self.name}] status {resp.status} en {url}")
                return await resp.text()

        if self._session is not None:
            return await _fetch(self._session)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            return await _fetch(session)

    async def _get_html_cloudscraper(self, url: str,
                                     params: Optional[Dict[str, Any]] = None) -> str:
        import cloudscraper

        full = self._build_url(url, params)
        if self._cloudscraper_instance is None:
            self._cloudscraper_instance = cloudscraper.create_scraper()
        resp = await asyncio.to_thread(
            self._cloudscraper_instance.get, full,
            timeout=self.timeout, headers=self.headers,
        )
        if resp.status_code in (403, 429):
            raise RateLimitedError(f"[{self.name}] bloqueado ({resp.status_code}) en {url}")
        if resp.status_code != 200:
            raise MaxRetriesError(f"[{self.name}] status {resp.status_code} en {url}")
        return resp.text

    async def _get_html_playwright(self, url: str,
                                   params: Optional[Dict[str, Any]] = None) -> str:
        resultados = await self._navegador_html([self._build_url(url, params)])
        return resultados[0] if resultados else ""

    async def _get_html_multi(self, urls: List[str]) -> List[str]:
        """Descarga varias páginas en paralelo con un único navegador.

        Lanzar un Chromium por URL costaba ~20 s extra en cada consulta; con
        un solo contexto y varias pestañas el tiempo total es el de la más
        lenta. Sin Playwright se resuelven en serie con el fetcher normal.
        """
        if not urls:
            return []
        if not self.use_playwright:
            return [await self._get_html(u) for u in urls]

        if self.aiohttp_primero:
            # El sitio ya devuelve el HTML con los productos: se piden todas
            # las páginas por HTTP a la vez y sólo las que fallan necesitan el
            # navegador. Se evita a propósito llamar a `_get_html` aquí para no
            # encadenar el fallback de Playwright con sí mismo.
            resultados = await asyncio.gather(
                *(self._get_html_aiohttp(u) for u in urls),
                return_exceptions=True,
            )
            fallidas = [i for i, r in enumerate(resultados) if isinstance(r, Exception)]
            if not fallidas:
                return [str(r) for r in resultados]
            logger.debug("[%s] %d de %d páginas requieren navegador",
                         self.name, len(fallidas), len(urls))
            for indice, html in zip(
                fallidas,
                await self._navegador_html([urls[i] for i in fallidas]),
            ):
                resultados[indice] = html
            return [
                "" if isinstance(r, Exception) else str(r) for r in resultados
            ]

        return await self._navegador_html(urls)

    async def _navegador_html(self, urls: List[str]) -> List[str]:
        """Carga las URLs con un único navegador de Playwright."""
        if not urls:
            return []
        from playwright.async_api import async_playwright

        wait_ms = int(self.timeout * 1000)
        resultados: List[str] = [""] * len(urls)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            try:
                context = await browser.new_context(
                    user_agent=self.headers["User-Agent"],
                    locale=self.locale,
                    viewport=self.viewport,
                )
                await context.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
                )

                async def cargar(indice: int, url: str) -> None:
                    page = await context.new_page()
                    try:
                        # domcontentloaded + espera explícita: "networkidle"
                        # nunca se estabiliza (long-polling de AliExpress/Shopify).
                        await page.goto(url, timeout=wait_ms, wait_until="domcontentloaded")
                        if self.wait_for_selector:
                            try:
                                await page.wait_for_selector(
                                    self.wait_for_selector,
                                    timeout=int((self.timeout_selector or self.timeout) * 1000),
                                    state=self.estado_selector,
                                )
                            except Exception:
                                logger.debug("[%s] selector %r no apareció en %s",
                                             self.name, self.wait_for_selector, url[:70])
                        await page.wait_for_timeout(self.settle_ms)
                        resultados[indice] = await page.content()
                    except Exception as exc:
                        logger.warning("[%s] no se pudo cargar %s: %s",
                                       self.name, url[:80], type(exc).__name__)
                    finally:
                        await page.close()

                await asyncio.gather(*(cargar(i, u) for i, u in enumerate(urls)))
            finally:
                await browser.close()

        return resultados
