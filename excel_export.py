import os
from datetime import datetime

from openpyxl import Workbook

from database import get_connection


def generar_excel():
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT r.codigo, r.nombre, r.descripcion, r.cantidad, r.precio,
                   r.ubicacion, r.fecha, c.nombre as categoria
            FROM repuestos r
            LEFT JOIN categorias c ON r.categoria_id = c.id
            ORDER BY r.codigo
        """)

        repuestos = cursor.fetchall()
    finally:
        conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventario"

    headers = ["Código", "Nombre", "Descripción", "Categoría", "Cantidad", "Precio", "Ubicación", "Fecha"]

    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    for row_num, r in enumerate(repuestos, 2):
        ws.cell(row=row_num, column=1, value=r["codigo"]).border = thin_border
        ws.cell(row=row_num, column=2, value=r["nombre"]).border = thin_border
        ws.cell(row=row_num, column=3, value=r["descripcion"]).border = thin_border
        ws.cell(row=row_num, column=4, value=r["categoria"] or "Sin categoría").border = thin_border
        ws.cell(row=row_num, column=5, value=r["cantidad"]).border = thin_border
        ws.cell(row=row_num, column=6, value=r["precio"]).border = thin_border
        ws.cell(row=row_num, column=7, value=r["ubicacion"]).border = thin_border
        ws.cell(row=row_num, column=8, value=r["fecha"]).border = thin_border

        ws.cell(row=row_num, column=5).alignment = Alignment(horizontal="center")
        ws.cell(row=row_num, column=6).number_format = '#,##0.00'
        ws.cell(row=row_num, column=6).alignment = Alignment(horizontal="right")

        if r["cantidad"] == 0:
            red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
            for col in range(1, 9):
                ws.cell(row=row_num, column=col).fill = red_fill
        elif r["cantidad"] < 5:
            yellow_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
            for col in range(1, 9):
                ws.cell(row=row_num, column=col).fill = yellow_fill

    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 15
    ws.column_dimensions["G"].width = 20
    ws.column_dimensions["H"].width = 20

    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"

    fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo = f"inventario_{fecha_str}.xlsx"
    ruta = os.path.join(os.getcwd(), archivo)
    wb.save(ruta)

    return ruta