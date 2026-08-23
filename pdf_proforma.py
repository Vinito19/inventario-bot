import os
from datetime import datetime
from fpdf import FPDF
from database import get_config


class PDFProforma(FPDF):
    def header(self):
        logo_path = get_config("logo_path")
        if logo_path and os.path.exists(logo_path):
            self.image(logo_path, x=10, y=8, w=30)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "PROFORMA", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

        # Datos de la empresa
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, "Repuesto Automotrices VCH", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "Barrio: PIFO  Calle: JOSE RAFAEL DELGADO  Numero: 310  Interseccion: GONZALO PIZARRO", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, "Tel: 0995390316  Email: ve.checa@outlook.com  RUC: 1720577129001", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_draw_color(0, 0, 0)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}", align="C")


def generar_proforma(repuesto, fotos_file_ids):
    pdf = PDFProforma()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Tabla de datos del repuesto
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "DETALLE DEL REPUESTO", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    datos = [
        ("Código", repuesto["codigo"]),
        ("Nombre", repuesto["nombre"]),
        ("Categoría", repuesto["categoria_nombre"] or "Sin categoría"),
        ("Descripción", repuesto["descripcion"]),
        ("Precio unitario", f"${repuesto['precio']:.2f}"),
    ]

    pdf.set_font("Helvetica", "B", 10)
    col_w1 = 45
    col_w2 = 145

    for etiqueta, valor in datos:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(col_w1, 7, f"{etiqueta}:", border=0)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(col_w2, 7, str(valor), border=0, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    # Fotos
    from database import get_connection
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for i, file_id in enumerate(fotos_file_ids, 1):
            cursor.execute("SELECT file_id_1, file_id_2, file_id_3, file_id_4 FROM repuestos WHERE codigo = ?", (repuesto["codigo"],))
            row = cursor.fetchone()
            if row and row[f"file_id_{i}"]:
                file_id = row[f"file_id_{i}"]
    finally:
        conn.close()

    # Nota: las fotos se envían aparte como documentos adjuntos, no incrustadas en el PDF
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "FOTOS DEL REPUESTO", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Se adjuntan {len(fotos_file_ids)} fotos del repuesto como documentos separados.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Footer info
    pdf.set_draw_color(0, 0, 0)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, "Este documento es una proforma informativa. Los precios y disponibilidad pueden variar. Consulte condiciones finales al momento de la compra.")

    # Guardar
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"proforma_{repuesto['codigo']}_{timestamp}.pdf"
    ruta = os.path.join(os.getcwd(), filename)
    pdf.output(ruta)
    return ruta