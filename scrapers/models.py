"""Modelos de datos para los resultados de scraping de repuestos."""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Product:
    """Modelo unificado para resultados de búsqueda."""
    codigo: str
    nombre: str
    precio_usd: float
    moneda_original: str
    precio_original: float
    funcion: str
    lado: str
    tecnologia: str
    compatibilidad: List[str]
    componente_hermano: Optional[str] = None
    sitio: str = ""
    pais: str = ""
    url: str = ""
    imagen_url: str = ""
    fecha_busqueda: str = ""

    def __post_init__(self):
        if not self.fecha_busqueda:
            self.fecha_busqueda = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        """Convertir a diccionario para JSON."""
        return {
            "codigo": self.codigo,
            "nombre": self.nombre,
            "precio_usd": self.precio_usd,
            "moneda_original": self.moneda_original,
            "precio_original": self.precio_original,
            "funcion": self.funcion,
            "lado": self.lado,
            "tecnologia": self.tecnologia,
            "compatibilidad": self.compatibilidad,
            "componente_hermano": self.componente_hermano,
            "sitio": self.sitio,
            "pais": self.pais,
            "url": self.url,
            "imagen_url": self.imagen_url,
            "fecha_busqueda": self.fecha_busqueda,
        }