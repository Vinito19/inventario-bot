import math
import os
from datetime import datetime

from fpdf import FPDF
from PIL import Image

from database import get_config

PAGE_W = 210
PAGE_H = 297

# Paleta bicroma: celeste + blanco
CELESTE = (14, 165, 233)
CELESTE_CLARO = (186, 230, 253)
CELESTE_OSCURO = (3, 105, 161)
TEXTO = (55, 65, 81)
BLANCO = (255, 255, 255)


def _safe(text):
    return str(text).encode("latin-1", "replace").decode("latin-1")


def _wave_top(pdf, y_base, amp, wave_len, phase, color):
    pdf.set_fill_color(*color)
    pts = [(0.0, 0.0), (float(PAGE_W), 0.0)]
    x = float(PAGE_W)
    while x >= 0:
        pts.append((x, y_base + amp * math.sin((x / wave_len) * math.tau + phase)))
        x -= 2.0
    pdf.polygon(pts, style="F")


def _wave_bottom(pdf, y_base, amp, wave_len, phase, color):
    pdf.set_fill_color(*color)
    pts = [(0.0, float(PAGE_H)), (float(PAGE_W), float(PAGE_H))]
    x = float(PAGE_W)
    while x >= 0:
        pts.append((x, y_base + amp * math.sin((x / wave_len) * math.tau + phase)))
        x -= 2.0
    pdf.polygon(pts, style="F")


def _rounded_fill(pdf, x, y, w, h, radius=3):
    try:
        pdf.rounded_rectangle(x, y, w, h, style="F", rounding=radius)
    except Exception:
        pdf.rect(x, y, w, h, style="F")


class PDFProforma(FPDF):
    def header(self):
        # Bandas de encabezado con ondas fluidas
        self.set_fill_color(*CELESTE_CLARO)
        self.rect(0, 0, PAGE_W, 52, style="F")
        _wave_top(self, 44, 3, 26, 0.0, CELESTE)
        _wave_top(self, 39, 3.2, 22, 1.3, CELESTE_OSCURO)

        # Logo en recuadro blanco, a la IZQUIERDA (texto va a la derecha, sin solapar)
        logo = get_config("logo_path")
        if logo and os.path.exists(logo):
            self.set_fill_color(*BLANCO)
            _rounded_fill(self, 12, 6, 34, 34, radius=3)
            self.image(logo, x=15, y=8.5, w=29)

        # Datos de la empresa: a la DERECHA del logo
        self.set_text_color(*BLANCO)
        self.set_xy(50, 10)
        self.set_font("helvetica", "B", 14)
        self.cell(0, 7, "REPUESTOS AUTOMOTRICES VCH")

        self.set_font("helvetica", "", 8.5)
        self.set_xy(50, 17.5)
        self.cell(0, 4.5, "PIFO - JOSE RAFAEL DELGADO 310 y GONZALO PIZARRO")
        self.set_xy(50, 22.5)
        self.cell(0, 4.5, "0995390316   |   ve.checa@outlook.com   |   RUC: 1720577129001")

        # Titulo y fecha a la derecha
        self.set_font("helvetica", "B", 20)
        self.set_xy(120, 8)
        self.cell(76, 8, "PROFORMA", align="R")
        self.set_font("helvetica", "", 8)
        self.set_xy(120, 16.5)
        self.cell(76, 5, datetime.now().strftime("Fecha: %d/%m/%Y"), align="R")

    def footer(self):
        # Pie de pagina con ondas fluidas
        self.set_fill_color(*CELESTE_CLARO)
        self.rect(0, 274, PAGE_W, PAGE_H - 274, style="F")
        _wave_bottom(self, 281, 3, 26, 2.1, CELESTE)
        _wave_bottom(self, 287, 3.2, 22, 0.6, CELESTE_OSCURO)

        self.set_text_color(*BLANCO)
        self.set_xy(0, 284)
        self.set_font("helvetica", "I", 8)
        self.cell(PAGE_W, 5, "Documento informativo - precios sujetos a confirmacion", align="C")
        self.set_xy(0, 291)
        self.cell(PAGE_W, 4, f"Pagina {self.page_no()}/{{nb}}", align="C")

    def _seccion(self, y, titulo):
        self.set_xy(14, y)
        self.set_fill_color(*CELESTE)
        self.rect(10, y + 0.5, 2.5, 5.5, style="F")
        self.set_font("helvetica", "B", 12)
        self.set_text_color(*CELESTE_OSCURO)
        self.cell(0, 6, titulo)
        self.set_draw_color(*CELESTE)
        self.set_line_width(0.4)
        self.line(10, y + 8, 200, y + 8)


def _fit_image(pdf, ruta, cx, cy, max_w, max_h):
    with Image.open(ruta) as im:
        iw, ih = im.size
    aspect = iw / ih
    if aspect >= 1:
        w = max_w
        h = w / aspect
        if h > max_h:
            h = max_h
            w = h * aspect
    else:
        h = max_h
        w = h * aspect
        if w > max_w:
            w = max_w
            h = w / aspect
    x = cx + (max_w - w) / 2
    y = cy + (max_h - h) / 2
    pdf.set_draw_color(*CELESTE)
    pdf.set_line_width(0.6)
    pdf.rect(x - 1.5, y - 1.5, w + 3, h + 3, style="D")
    pdf.image(ruta, x=x, y=y, w=w, h=h)


def generar_proforma(repuesto, fotos_paths):
    pdf = PDFProforma()
    pdf.alias_nb_pages()
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    # ---- Seccion: detalle del repuesto ----
    y = 58
    pdf._seccion(y, "DETALLE DEL REPUESTO")
    y += 12

    datos = [
        ("Codigo", repuesto["codigo"]),
        ("Nombre", repuesto["nombre"]),
        ("Categoria", repuesto["categoria_nombre"] or "Sin categoria"),
        ("Descripcion", repuesto["descripcion"]),
    ]

    for etiqueta, valor in datos:
        pdf.set_xy(14, y)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*CELESTE_OSCURO)
        pdf.cell(35, 7, _safe(f"{etiqueta}:"))
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(*TEXTO)
        pdf.multi_cell(147, 7, _safe(valor))
        y = pdf.get_y() + 1.5

    # ---- Precio destacado ----
    y += 2
    pdf.set_fill_color(*CELESTE_CLARO)
    _rounded_fill(pdf, 14, y, 182, 10, radius=2)
    pdf.set_xy(18, y)
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(*CELESTE_OSCURO)
    pdf.cell(60, 10, "PRECIO UNITARIO:")
    pdf.set_font("helvetica", "B", 14)
    pdf.set_xy(18, y)
    pdf.cell(174, 10, f"${repuesto['precio']:.2f}", align="R")

    # Avanzar cursor despues del precio (cell con set_xy no actualiza get_y)
    y_cursor = y + 14

    # ---- Fotos ----
    fotos = [f for f in fotos_paths if f and os.path.exists(f)]

    if fotos:
        # === PAGINA 1: primera foto ocupando todo el espacio ===
        y_seccion1 = y_cursor + 4
        pdf._seccion(y_seccion1, "FOTO DEL REPUESTO")
        y_foto1 = y_seccion1 + 10
        avail_w = 190.0
        avail_h = 265.0 - y_foto1
        if avail_h < 40:
            avail_h = 40
        _fit_image(pdf, fotos[0], 10, y_foto1, avail_w, avail_h)

        if len(fotos) > 1:
            # === PAGINA 2: fotos 2, 3 y 4 ===
            pdf.add_page()
            y_seccion2 = 58
            pdf._seccion(y_seccion2, "FOTOS DEL REPUESTO (continuacion)")
            y2 = y_seccion2 + 12
            restantes = fotos[1:4]
            n = len(restantes)
            gap = 8
            avail_w2 = 190.0
            avail_total_h = 265.0 - y2

            if n == 1:
                _fit_image(pdf, restantes[0], 10, y2, avail_w2, avail_total_h)
            elif n == 2:
                h_each = (avail_total_h - gap) / 2
                _fit_image(pdf, restantes[0], 10, y2, avail_w2, h_each)
                _fit_image(pdf, restantes[1], 10, y2 + h_each + gap, avail_w2, h_each)
            else:
                h_top = avail_total_h * 0.47
                h_bot = avail_total_h * 0.47
                _fit_image(pdf, restantes[0], 10, y2, avail_w2, h_top)
                half_w = (avail_w2 - gap) / 2
                y_bot = y2 + h_top + gap
                _fit_image(pdf, restantes[1], 10, y_bot, half_w, h_bot)
                _fit_image(pdf, restantes[2], 10 + half_w + gap, y_bot, half_w, h_bot)

    # ---- Guardar ----
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"proforma_{repuesto['codigo']}_{timestamp}.pdf"
    ruta_pdf = os.path.join(os.getcwd(), filename)
    pdf.output(ruta_pdf)
    return ruta_pdf
