"""
Módulo de Reglas Heurísticas para Derivación de Tickets — Protecta Seguros
Sistema experto (IF/THEN/ELSE) que usa los features reales del JIRA de Protecta.

Mesas reales:
    N1: Service Desk 1, 2, 5, 6, 7  → Solicitudes simples, consultas de usuario
    N2: Squad - Mesa Ongoing         → Incidentes moderados, escalamiento de N1
    N3: soportedigital               → E-commerce, emisión SOAT, digital
        soporteapp                   → Aplicativos internos, planillas, refacturación
        Squad - Mesa Vida Ley        → Producto Vida Ley + error complejo
        Squad - Mesa SCTR            → Producto SCTR + error complejo
"""

# --------------------------------------------------------------------------
# Constantes de mesas
# --------------------------------------------------------------------------

MESAS_N1 = [
    "Service Desk 1",
    "Service Desk 2",
    "Service Desk 5",
    "Service Desk 6",
    "Service Desk 7",
]

MESA_N2 = "Squad - Mesa Ongoing"

MESAS_N3 = {
    "vida_ley":   "Squad - Mesa Vida Ley",
    "sctr":       "Squad - Mesa SCTR",
    "digital":    "soportedigital",
    "app":        "soporteapp",
}

MESA_DEFAULT = "Service Desk 1"

# Palabras clave en tipo_atencion_sd que indican trabajo técnico / aplicativo
KEYWORDS_TECNICO = {
    "error de servidor", "error de servicio", "emisión", "emision",
    "migración", "migracion", "validar emisión", "error de emisión",
    "activación", "activacion", "interfaz", "interfaz de pago",
    "generación de reporte", "reporte", "actualización de datos",
}

KEYWORDS_FACTURACION = {
    "factura", "facturar", "refactura", "refacturar",
    "planilla", "comprobante", "nota de crédito", "nota de credito",
    "anulación de factura", "anulacion de factura",
    "cierre del ticket", "conciliación", "conciliacion",
}

KEYWORDS_SOLICITUD_SIMPLE = {
    "desafiliación de renovación", "desafiliacion de renovacion",
    "actualización de datos de clientes", "actualizacion de datos",
    "reporte", "generación de reporte", "envio de correo",
    "activación o creación de usuarios", "activacion o creacion",
    "inclusión", "inclusion", "retiro correo",
}


# --------------------------------------------------------------------------
# Funciones auxiliares
# --------------------------------------------------------------------------

def _contiene_keywords(texto: str, keywords: set) -> bool:
    """Verifica si el texto (en minúsculas) contiene alguna keyword del set."""
    texto_lower = texto.lower().strip()
    return any(kw in texto_lower for kw in keywords)


def _detectar_producto_n3(producto: str, aplicativo: str) -> str | None:
    """
    Detecta si el ticket corresponde a un producto de N3 específico.
    Retorna el nombre de la mesa N3 o None si no aplica.
    """
    texto = f"{producto} {aplicativo}".lower()

    if "vida ley" in texto or "vida_ley" in texto:
        return MESAS_N3["vida_ley"]

    if "sctr" in texto:
        return MESAS_N3["sctr"]

    if "ecommerce" in texto or "soat" in texto or "digital" in texto:
        return MESAS_N3["digital"]

    return None


# --------------------------------------------------------------------------
# Función principal de evaluación de complejidad (compatible con agentes)
# --------------------------------------------------------------------------

def evaluar_complejidad_base(tipo_error: str, prioridad: str, descripcion: str) -> dict:
    """
    Evalúa la complejidad de un ticket con base en sus atributos.
    Compatible con el agente de complejidad existente.

    Ahora usa 'tipo_error' como el tipo_atencion_sd del CSV de JIRA.
    """
    score = 50.0
    factores = {}

    # Regla 1: Por tipo de atención SD
    if _contiene_keywords(tipo_error, KEYWORDS_TECNICO):
        score += 25
        factores["tipo_atencion"] = "Error técnico / de sistema — alta complejidad"
    elif _contiene_keywords(tipo_error, KEYWORDS_FACTURACION):
        score += 15
        factores["tipo_atencion"] = "Gestión de facturación — complejidad media-alta"
    elif _contiene_keywords(tipo_error, KEYWORDS_SOLICITUD_SIMPLE):
        score -= 15
        factores["tipo_atencion"] = "Solicitud operativa simple"
    else:
        factores["tipo_atencion"] = "Tipo de atención no categorizado"

    # Regla 2: Por urgencia (detectada por el Filtrador)
    if prioridad == "alta":
        score += 20
        factores["urgencia"] = "Urgencia detectada en el resumen — prioridad alta"
    elif prioridad in ("media", "baja"):
        factores["urgencia"] = "Sin urgencia explícita"

    # Regla 3: Palabras clave técnicas en descripción/resumen
    palabras_criticas = [
        "caído", "caido", "crítico", "critico", "no funciona",
        "bloqueado", "sin acceso", "error", "fallo"
    ]
    palabras_tecnicas = [
        "servidor", "base de datos", "sql", "api", "router",
        "emisión", "interfaz", "planilla"
    ]

    desc_lower = descripcion.lower()
    criticas = [p for p in palabras_criticas if p in desc_lower]
    tecnicas = [p for p in palabras_tecnicas if p in desc_lower]

    if criticas:
        score += len(criticas) * 8
        factores["palabras_criticas"] = f"Términos críticos: {', '.join(criticas)}"
    if tecnicas:
        score += len(tecnicas) * 4
        factores["palabras_tecnicas"] = f"Contexto técnico: {', '.join(tecnicas)}"

    # Normalizar
    score = max(0.0, min(100.0, score))

    if score >= 85:
        categoria = "critica"
        recomendacion = "Escalar a N3 inmediatamente"
    elif score >= 60:
        categoria = "alta"
        recomendacion = "Asignar a N2 o N3 según producto"
    elif score >= 40:
        categoria = "media"
        recomendacion = "N1 con posible escalamiento a N2"
    else:
        categoria = "baja"
        recomendacion = "Asignar a N1 (Service Desk)"

    return {
        "score": score,
        "categoria": categoria,
        "factores": factores,
        "recomendacion": recomendacion,
    }


# --------------------------------------------------------------------------
# Función principal de selección de mesa
# --------------------------------------------------------------------------

def determinar_mesa_ideal(tipo_error: str, complejidad: str, **kwargs) -> list[str]:
    """
    Retorna una lista de mesas aptas en orden de preferencia.

    Usa la lógica N1 → N2 → N3 de Protecta Seguros.
    Acepta kwargs para recibir parámetros extra del CSV real:
        - area: Campo personalizado (Área)
        - aplicativo: Campo personalizado (Aplicativo)
        - producto: Campo personalizado (Producto SD)
        - clasificacion: Campo personalizado (Clasificación)
        - urgencia: urgencia_detectada (alta/media/baja)
    """
    area        = kwargs.get("area", "")
    aplicativo  = kwargs.get("aplicativo", "")
    producto    = kwargs.get("producto", "")
    clasificacion = kwargs.get("clasificacion", "")
    urgencia    = kwargs.get("urgencia", "media")

    tipo_lower = tipo_error.lower()

    # ---------------------------------------------------------------
    # REGLA DURA: Urgencia alta → saltar directo a N2
    # ---------------------------------------------------------------
    if urgencia == "alta" and complejidad in ("alta", "critica"):
        mesa_n3 = _detectar_producto_n3(producto, aplicativo)
        if mesa_n3:
            return [mesa_n3, MESA_N2]
        return [MESA_N2, MESAS_N3["digital"]]

    # ---------------------------------------------------------------
    # REGLA: Solicitudes simples → N1
    # ---------------------------------------------------------------
    if clasificacion.lower() in ("solicitud",):
        if _contiene_keywords(tipo_lower, KEYWORDS_SOLICITUD_SIMPLE):
            return [MESA_DEFAULT]
        if complejidad in ("baja", "media"):
            return [MESA_DEFAULT, MESAS_N1[1]]

    # ---------------------------------------------------------------
    # REGLA: Facturación y planillas → soporteapp (N3 especializado)
    # ---------------------------------------------------------------
    if _contiene_keywords(tipo_lower, KEYWORDS_FACTURACION):
        return [MESAS_N3["app"], MESA_N2]

    # ---------------------------------------------------------------
    # REGLA: Error técnico/sistema → según producto
    # ---------------------------------------------------------------
    if _contiene_keywords(tipo_lower, KEYWORDS_TECNICO):
        mesa_n3 = _detectar_producto_n3(producto, aplicativo)
        if mesa_n3 and complejidad in ("alta", "critica"):
            return [mesa_n3, MESA_N2]
        elif mesa_n3:
            return [MESA_N2, mesa_n3]
        # Sin producto específico → N2
        return [MESA_N2]

    # ---------------------------------------------------------------
    # REGLA: Por complejidad (fallback)
    # ---------------------------------------------------------------
    if complejidad == "critica":
        mesa_n3 = _detectar_producto_n3(producto, aplicativo)
        return [mesa_n3 or MESAS_N3["digital"], MESA_N2]

    elif complejidad == "alta":
        return [MESA_N2, MESAS_N3["digital"]]

    else:
        return [MESA_DEFAULT]


# --------------------------------------------------------------------------
# Función de derivación directa (para el agente decisor)
# --------------------------------------------------------------------------

def derivar_ticket(features: dict) -> dict:
    """
    Función de alto nivel: recibe los features de decisión y retorna
    la decisión completa de derivación.

    Args:
        features: Dict con los campos del Agente Filtrador + complejidad evaluada.

    Returns:
        {
            "mesa_asignada": str,
            "nivel": "N1" | "N2" | "N3",
            "alternativas": [str, ...],
            "razonamiento": str,
        }
    """
    tipo_error    = features.get("tipo_atencion_sd") or features.get("tipo_error", "")
    complejidad   = features.get("complejidad", "media")
    descripcion   = features.get("resumen") or features.get("descripcion", "")
    urgencia      = features.get("urgencia_detectada") or features.get("prioridad", "media")

    evaluacion = evaluar_complejidad_base(tipo_error, urgencia, descripcion)

    mesas = determinar_mesa_ideal(
        tipo_error=tipo_error,
        complejidad=evaluacion["categoria"],
        area=features.get("area", ""),
        aplicativo=features.get("aplicativo", ""),
        producto=features.get("producto", ""),
        clasificacion=features.get("clasificacion", ""),
        urgencia=urgencia,
    )

    mesa_asignada = mesas[0] if mesas else MESA_DEFAULT
    alternativas  = mesas[1:] if len(mesas) > 1 else []

    # Determinar nivel
    if mesa_asignada in MESAS_N1:
        nivel = "N1"
    elif mesa_asignada == MESA_N2:
        nivel = "N2"
    else:
        nivel = "N3"

    razonamiento = (
        f"Complejidad '{evaluacion['categoria']}' (score {evaluacion['score']:.0f}). "
        f"{evaluacion['recomendacion']}. "
        f"Mesa seleccionada: {mesa_asignada} ({nivel})."
    )

    return {
        "mesa_asignada": mesa_asignada,
        "nivel":         nivel,
        "alternativas":  alternativas,
        "razonamiento":  razonamiento,
        "score":         evaluacion["score"],
        "evaluacion":    evaluacion,
    }
