"""
Agente Filtrador de Features — Transforma filas del CSV de JIRA al
formato interno del sistema de derivación.

Responsabilidades:
    - Mapear columnas JIRA → campos internos.
    - Separar features de DECISIÓN vs features de REPORTE.
    - Detectar urgencia desde el texto del campo "Resumen".
    - Normalizar valores para las reglas de derivación.
"""

import re

# ---------------------------------------------------------------------------
# Mapeo de columnas JIRA → nombre interno
# ---------------------------------------------------------------------------

MAPA_COLUMNAS = {
    "Tipo de Incidencia":                             "tipo_incidencia",
    "Clave de incidencia":                            "ticket_id",
    "Resumen":                                        "resumen",
    "Campo personalizado (Tipo de atención SD)":      "tipo_atencion_sd",
    "Campo personalizado (Área)":                     "area",
    "Campo personalizado (Aplicativo)":               "aplicativo",
    "Campo personalizado (Producto SD)":              "producto",
    "Campo personalizado (Clasificación)":            "clasificacion",
    "Estado":                                         "estado",
    "Informador":                                     "informador",
    "Creada":                                         "fecha_creacion",
    "Actualizada":                                    "fecha_actualizacion",
    "Resuelta":                                       "fecha_resolucion",
    "Campo personalizado (Fecha Cerrado)":            "fecha_cerrado",
    "Campo personalizado (Fecha de Aprobación a Cliente)": "fecha_aprobacion",
    "Responsable":                                    "responsable",
    "Campo personalizado (Atendido por)":             "atendido_por",
    "Campo personalizado (Especialista)":             "especialista",
    "Resolución":                                     "resolucion",
    "Campo personalizado (Tipo de Cliente)":          "tipo_cliente",
    "Prioridad":                                      "prioridad_jira",
    "Campo personalizado (Prioridad SD)":             "prioridad_sd",
}

# Palabras que indican urgencia ALTA en el Resumen
PALABRAS_URGENCIA_ALTA = [
    r"\bMUY URGENTE\b",
    r"\bURGENTE\b",
    r"\bRECONTRA URGENTE\b",
    r"\bCRÍTICO\b",
    r"\bCRITICO\b",
    r"\bCAÍDO\b",
    r"\bCAIDO\b",
    r"\bSIN SERVICIO\b",
    r"\bNO FUNCIONA\b",
    r"\bBLOQUEADO\b",
]

# Features que se usan en la decisión de routing
FEATURES_DECISION = [
    "ticket_id",
    "tipo_incidencia",
    "tipo_atencion_sd",
    "area",
    "aplicativo",
    "producto",
    "clasificacion",
    "urgencia_detectada",
    "resumen",
]

# Features que se guardan solo para reportes/métricas
FEATURES_REPORTE = [
    "ticket_id",
    "informador",
    "fecha_creacion",
    "fecha_actualizacion",
    "fecha_resolucion",
    "fecha_cerrado",
    "fecha_aprobacion",
    "responsable",
    "atendido_por",
    "especialista",
    "resolucion",
    "tipo_cliente",
    "prioridad_jira",
    "prioridad_sd",
    "estado",
]


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------

def _normalizar(valor) -> str:
    """Convierte un valor a string limpio. Maneja None/NaN."""
    if valor is None:
        return ""
    valor_str = str(valor).strip()
    return "" if valor_str.lower() in {"nan", "none", "n/a", "-"} else valor_str


def detectar_urgencia(resumen: str) -> str:
    """
    Analiza el texto del campo 'Resumen' para detectar el nivel de urgencia.

    Returns:
        "alta"   → palabras de urgencia crítica detectadas
        "media"  → no se detecta urgencia explícita
    """
    if not resumen:
        return "media"

    texto = resumen.upper()
    for patron in PALABRAS_URGENCIA_ALTA:
        if re.search(patron, texto):
            return "alta"

    return "media"


def _renombrar_fila(fila: dict) -> dict:
    """
    Renombra las claves de la fila según MAPA_COLUMNAS.
    Las claves no mapeadas se conservan con su nombre original.
    """
    return {
        MAPA_COLUMNAS.get(k, k): _normalizar(v)
        for k, v in fila.items()
    }


# ---------------------------------------------------------------------------
# Funciones principales
# ---------------------------------------------------------------------------

def filtrar_features_decision(fila: dict) -> dict:
    """
    Extrae los features necesarios para el agente decisor.

    Args:
        fila: Diccionario con los datos de una fila del CSV de JIRA.

    Returns:
        Dict con solo los campos relevantes para la decisión de routing,
        incluyendo 'urgencia_detectada' calculada del Resumen.
    """
    fila_renombrada = _renombrar_fila(fila)

    # Calcular urgencia desde el resumen
    fila_renombrada["urgencia_detectada"] = detectar_urgencia(
        fila_renombrada.get("resumen", "")
    )

    # Extraer solo los features de decisión
    resultado = {k: fila_renombrada.get(k, "") for k in FEATURES_DECISION}

    return resultado


def filtrar_features_reporte(fila: dict) -> dict:
    """
    Extrae los features útiles para reportes y métricas.

    Args:
        fila: Diccionario con los datos de una fila del CSV de JIRA.

    Returns:
        Dict con campos de trazabilidad y métricas.
    """
    fila_renombrada = _renombrar_fila(fila)
    resultado = {k: fila_renombrada.get(k, "") for k in FEATURES_REPORTE}
    return resultado


def procesar_fila_completa(fila: dict) -> dict:
    """
    Procesa una fila del CSV y retorna tanto los features de decisión
    como los de reporte en un solo diccionario estructurado.

    Returns:
        {
            "decision": { ... features para routing ... },
            "reporte":  { ... features para métricas ... }
        }
    """
    return {
        "decision": filtrar_features_decision(fila),
        "reporte":  filtrar_features_reporte(fila),
    }


def procesar_lote(tickets: list[dict]) -> list[dict]:
    """
    Procesa una lista de tickets (salida del Watcher) y retorna
    la lista transformada con features separados.

    Args:
        tickets: Lista de dicts del CSV de JIRA (salida de watcher.py).

    Returns:
        Lista de dicts con "decision" y "reporte" por cada ticket.
    """
    resultado = []
    for fila in tickets:
        try:
            resultado.append(procesar_fila_completa(fila))
        except Exception as e:
            ticket_id = fila.get("Clave de incidencia", "DESCONOCIDO")
            print(f"[Filtrador] Error procesando {ticket_id}: {e}")
    return resultado


# ---------------------------------------------------------------------------
# Construcción del payload para n8n (compatible con el modelo interno)
# ---------------------------------------------------------------------------

def construir_payload_n8n(features_decision: dict) -> dict:
    """
    Construye el payload JSON que se enviará al webhook de n8n,
    mapeando los campos del CSV al formato que espera la API.

    Args:
        features_decision: Dict con features de decisión (output de filtrar_features_decision).

    Returns:
        Dict compatible con el modelo TicketCreate de la API.
    """
    ticket_id = features_decision.get("ticket_id") or f"JIRA-{id(features_decision)}"

    # Normalizar tipo de ticket: JIRA usa "Incidente"/"Solicitud"/"Requerimiento"
    tipo_raw = features_decision.get("tipo_incidencia", "").lower()
    if "incident" in tipo_raw:
        tipo_ticket = "incidencia"
    elif "solicitud" in tipo_raw or "requerimiento" in tipo_raw:
        tipo_ticket = "solicitud"
    else:
        tipo_ticket = "incidencia"

    # Mapear tipo_atencion_sd al campo tipo_error interno
    tipo_error = features_decision.get("tipo_atencion_sd", "otro").lower()

    return {
        "ticket_id":  ticket_id,
        "tipo_ticket": tipo_ticket,
        "tipo_error":  tipo_error,
        "solicitante": features_decision.get("informador", ""),
        "area":        features_decision.get("area", ""),
        "titulo":      features_decision.get("resumen", ""),
        "descripcion": features_decision.get("resumen", ""),
        "prioridad":   features_decision.get("urgencia_detectada", "media"),
        # Campos adicionales del CSV real
        "aplicativo":  features_decision.get("aplicativo", ""),
        "producto":    features_decision.get("producto", ""),
        "clasificacion": features_decision.get("clasificacion", ""),
    }
