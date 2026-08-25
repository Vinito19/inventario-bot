import os
import sys
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest


def _nuevo_repuesto():
    return {
        "codigo": "TEST-001",
        "nombre": "Pastillas de freno",
        "descripcion": "Ceramicas universales",
        "cantidad": 10,
        "precio": 25.50,
        "categoria_nombre": "Frenos",
        "categoria_id": None,
    }


def _es_pdf(path):
    with open(path, "rb") as f:
        return f.read(5) == b"%PDF-"


def test_generar_proforma_sin_fotos():
    from pdf_proforma import generar_proforma

    ruta = generar_proforma(_nuevo_repuesto(), [])
    try:
        assert ruta and os.path.exists(ruta)
        assert _es_pdf(ruta)
    finally:
        if os.path.exists(ruta):
            os.remove(ruta)


def test_generar_proforma_con_1_foto(tmp_img):
    from pdf_proforma import generar_proforma

    ruta = generar_proforma(_nuevo_repuesto(), [tmp_img])
    try:
        assert os.path.exists(ruta)
        assert _es_pdf(ruta)
    finally:
        if os.path.exists(ruta):
            os.remove(ruta)


def test_generar_proforma_con_4_fotos(tmp_img, tmp_img_vertical):
    from pdf_proforma import generar_proforma

    fotos = [tmp_img, tmp_img_vertical, tmp_img, tmp_img_vertical]
    ruta = generar_proforma(_nuevo_repuesto(), fotos)
    try:
        assert os.path.exists(ruta)
        assert _es_pdf(ruta)
    finally:
        if os.path.exists(ruta):
            os.remove(ruta)


def test_generar_proforma_rutas_inexistentes():
    from pdf_proforma import generar_proforma

    ruta = generar_proforma(_nuevo_repuesto(), ["/no/existe/1.jpg", "/no/existe/2.jpg"])
    try:
        assert os.path.exists(ruta)
        assert _es_pdf(ruta)
    finally:
        if os.path.exists(ruta):
            os.remove(ruta)


def test_generar_proforma_2_paginas_con_4_fotos(tmp_img, tmp_img_vertical):
    """Con 4 fotos debe generar al menos 2 paginas (foto principal + resto)."""
    from pdf_proforma import generar_proforma

    fotos = [tmp_img, tmp_img_vertical, tmp_img, tmp_img_vertical]
    ruta = generar_proforma(_nuevo_repuesto(), fotos)
    try:
        with open(ruta, "rb") as f:
            contenido = f.read()
        n_pages = len(re.findall(rb"/Type\s*/Page\b", contenido))
        assert n_pages >= 2
    finally:
        if os.path.exists(ruta):
            os.remove(ruta)