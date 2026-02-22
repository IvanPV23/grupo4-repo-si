"""
Agente Watcher — Monitorea la carpeta data/inputs/ y extrae tickets pendientes.

Simula la descarga automática de JIRA seleccionando el CSV más reciente
depositado manualmente en la carpeta de ingesta.
"""

import os
import glob
import pandas as pd
from datetime import datetime


# Estados de ticket que se consideran "pendientes de asignar"
ESTADOS_A_PROCESAR = {"Abierto", "En progreso", "Aceptado"}

# Columnas del CSV de JIRA que nos importan
COLUMNAS_ESPERADAS = [
    "Tipo de Incidencia",
    "Clave de incidencia",
    "Resumen",
    "Campo personalizado (Tipo de atención SD)",
    "Informador",
    "Creada",
    "Campo personalizado (Aplicativo)",
    "Campo personalizado (Área)",
    "Estado",
    "Responsable",
    "Campo personalizado (Clasificación)",
    "Campo personalizado (Atendido por)",
    "Campo personalizado (Especialista)",
    "Campo personalizado (Tipo de Cliente)",
    "Campo personalizado (Producto SD)",
]


def _encontrar_csv_mas_reciente(carpeta: str) -> str | None:
    """
    Busca el CSV más reciente en la carpeta dada.
    Ordena por fecha de modificación del archivo (no por nombre).

    Returns:
        Ruta al CSV más reciente, o None si la carpeta está vacía.
    """
    patron = os.path.join(carpeta, "*.csv")
    archivos = glob.glob(patron)

    if not archivos:
        return None

    # Ordenar por fecha de modificación, más reciente primero
    archivos.sort(key=os.path.getmtime, reverse=True)
    return archivos[0]


def cargar_csv_jira(ruta_csv: str) -> pd.DataFrame:
    """
    Carga un CSV exportado de JIRA (separado por ';').
    Intenta múltiples encodings para robustez.

    Returns:
        DataFrame con todas las filas del CSV.
    """
    for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(ruta_csv, sep=";", encoding=encoding)
            print(f"[Watcher] CSV cargado: {os.path.basename(ruta_csv)} "
                  f"({len(df)} filas) con encoding {encoding}")
            return df
        except (UnicodeDecodeError, Exception):
            continue

    raise ValueError(f"No se pudo leer el archivo: {ruta_csv}")


def filtrar_tickets_pendientes(
    df: pd.DataFrame,
    estados_validos: set = None,
    solo_recientes_dias: int = None
) -> pd.DataFrame:
    """
    Filtra el DataFrame para quedarse solo con los tickets que el sistema
    debe procesar.

    Args:
        df: DataFrame completo del CSV de JIRA.
        estados_validos: Conjunto de estados a incluir. Por defecto: {"Abierto"}.
        solo_recientes_dias: Si se indica, solo tickets creados en los últimos N días.

    Returns:
        DataFrame filtrado.
    """
    if estados_validos is None:
        estados_validos = {"Abierto"}

    col_estado = "Estado"
    if col_estado not in df.columns:
        print(f"[Watcher] ADVERTENCIA: columna '{col_estado}' no encontrada. "
              "Retornando todas las filas.")
        return df

    # Filtrar por estado
    df_filtrado = df[df[col_estado].isin(estados_validos)].copy()
    print(f"[Watcher] Tickets con estado {estados_validos}: {len(df_filtrado)}")

    # Filtrar por fecha si se solicita
    if solo_recientes_dias is not None and "Creada" in df_filtrado.columns:
        try:
            df_filtrado["Creada_dt"] = pd.to_datetime(
                df_filtrado["Creada"], dayfirst=True, errors="coerce"
            )
            fecha_corte = pd.Timestamp.now() - pd.Timedelta(days=solo_recientes_dias)
            df_filtrado = df_filtrado[df_filtrado["Creada_dt"] >= fecha_corte]
            print(f"[Watcher] Después de filtro de {solo_recientes_dias} días: "
                  f"{len(df_filtrado)} tickets")
        except Exception as e:
            print(f"[Watcher] No se pudo filtrar por fecha: {e}")

    return df_filtrado


def obtener_tickets_pendientes(
    carpeta: str = "data/inputs/",
    estados_validos: set = None,
    solo_recientes_dias: int = None
) -> list[dict]:
    """
    Función principal del Agente Watcher.

    1. Detecta el CSV más reciente en la carpeta.
    2. Lo carga con el encoding correcto.
    3. Filtra tickets por estado (y opcionalmente por fecha).
    4. Retorna lista de dicts listos para el Agente Filtrador.

    Args:
        carpeta: Ruta a la carpeta de ingesta de CSV.
        estados_validos: Estados a incluir (default: {"Abierto"}).
        solo_recientes_dias: Limitar a tickets de los últimos N días (None = sin límite).

    Returns:
        Lista de diccionarios con los datos de cada ticket pendiente.
        Lista vacía si no hay CSV o no hay tickets en estado válido.
    """
    if estados_validos is None:
        estados_validos = {"Abierto"}

    # 1. Buscar CSV más reciente
    ruta_csv = _encontrar_csv_mas_reciente(carpeta)
    if ruta_csv is None:
        print(f"[Watcher] No se encontraron archivos CSV en: {carpeta}")
        return []

    print(f"[Watcher] Archivo seleccionado: {os.path.basename(ruta_csv)} "
          f"(modificado: {datetime.fromtimestamp(os.path.getmtime(ruta_csv)).strftime('%Y-%m-%d %H:%M')})")

    # 2. Cargar CSV
    df_completo = cargar_csv_jira(ruta_csv)

    # 3. Filtrar tickets pendientes
    df_pendientes = filtrar_tickets_pendientes(
        df_completo,
        estados_validos=estados_validos,
        solo_recientes_dias=solo_recientes_dias
    )

    if df_pendientes.empty:
        print("[Watcher] No hay tickets pendientes con los filtros aplicados.")
        return []

    # 4. Convertir a lista de dicts (reemplazar NaN por None para JSON)
    tickets = df_pendientes.where(pd.notna(df_pendientes), None).to_dict(orient="records")

    print(f"[Watcher] ✅ {len(tickets)} tickets listos para procesar.")
    return tickets


def resumen_archivo(carpeta: str = "data/inputs/") -> dict:
    """
    Retorna un resumen del estado de la carpeta de inputs.
    Útil para el endpoint de estadísticas.
    """
    ruta_csv = _encontrar_csv_mas_reciente(carpeta)
    archivos_total = len(glob.glob(os.path.join(carpeta, "*.csv")))

    if ruta_csv is None:
        return {
            "archivos_csv_disponibles": 0,
            "ultimo_archivo": None,
            "ultima_modificacion": None,
        }

    return {
        "archivos_csv_disponibles": archivos_total,
        "ultimo_archivo": os.path.basename(ruta_csv),
        "ultima_modificacion": datetime.fromtimestamp(
            os.path.getmtime(ruta_csv)
        ).strftime("%Y-%m-%d %H:%M"),
    }
