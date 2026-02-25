"""
utils/excel_acumulativo.py
Gestiona el reporte Excel persistente del sistema.
Agrega nuevas filas sin sobreescribir el histórico.
"""

import os
from datetime import datetime

# openpyxl es la librería estándar para .xlsx
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    OPENPYXL_OK = True
except ImportError:
    OPENPYXL_OK = False

# Ruta del reporte acumulativo
RUTA_REPORTE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "outputs", "reporte_acumulativo.xlsx"
)

COLUMNAS = [
    "ticket_id",
    "resumen",
    "tipo_incidencia",
    "tipo_atencion_sd",
    "area",
    "producto",
    "aplicativo",
    "informador",
    "urgencia_detectada",
    "tiempo_estimado_horas",
    "complejidad",
    "score_complejidad",
    "nivel_asignado",
    "mesa_asignada",
    "via_historico",
    "resultado",
    "razonamiento",
    "procesado_en",
]


def _crear_libro_nuevo(ruta: str):
    """Crea un Excel nuevo con el encabezado formateado."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Derivaciones"

    # Estilo de encabezado
    fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    font = Font(color="FFFFFF", bold=True)

    for col_idx, col_name in enumerate(COLUMNAS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center")

    # Anchos de columna razonables
    anchos = {
        "ticket_id": 14, "resumen": 45, "tipo_incidencia": 16,
        "tipo_atencion_sd": 28, "area": 18, "producto": 14,
        "aplicativo": 18, "informador": 22, "urgencia_detectada": 18,
        "tiempo_estimado_horas": 22, "complejidad": 14, "score_complejidad": 18,
        "nivel_asignado": 14, "mesa_asignada": 28, "via_historico": 14,
        "resultado": 28, "razonamiento": 60, "procesado_en": 20,
    }
    for col_idx, col_name in enumerate(COLUMNAS, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = anchos.get(col_name, 18)

    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    wb.save(ruta)
    return wb


def agregar_fila_reporte(datos: dict) -> str:
    """
    Agrega una nueva fila al reporte acumulativo Excel.

    Args:
        datos: dict con claves iguales a COLUMNAS (campos faltantes quedan vacíos).

    Returns:
        Ruta del archivo Excel.
    """
    if not OPENPYXL_OK:
        print("[Excel] openpyxl no disponible — saltando escritura")
        return RUTA_REPORTE

    # Cargar o crear el libro
    if os.path.exists(RUTA_REPORTE):
        wb = openpyxl.load_workbook(RUTA_REPORTE)
        ws = wb.active
    else:
        wb = _crear_libro_nuevo(RUTA_REPORTE)
        ws = wb.active

    # Agregar datos en la siguiente fila disponible
    fila = ws.max_row + 1
    datos.setdefault("procesado_en", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    for col_idx, col_name in enumerate(COLUMNAS, start=1):
        valor = datos.get(col_name, "")
        ws.cell(row=fila, column=col_idx, value=valor)

    wb.save(RUTA_REPORTE)
    print(f"[Excel] Fila {fila} agregada → {RUTA_REPORTE}")
    return RUTA_REPORTE


def obtener_resumen_reporte() -> dict:
    """Retorna estadísticas básicas del reporte acumulativo."""
    if not OPENPYXL_OK or not os.path.exists(RUTA_REPORTE):
        return {"total": 0, "archivo": RUTA_REPORTE, "existe": False}

    wb = openpyxl.load_workbook(RUTA_REPORTE, read_only=True)
    ws = wb.active
    total = ws.max_row - 1  # -1 por el encabezado
    wb.close()

    return {
        "total": max(0, total),
        "archivo": RUTA_REPORTE,
        "existe": True,
    }
