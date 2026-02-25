"""
Agente ESTIMADOR — Puerto 8005
Estima el tiempo de resolución de un ticket (en horas) usando
patrones históricos (rule-based por ahora, ML después).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

app = FastAPI(
    title="Agente Estimador",
    description="Estima tiempo de resolución de tickets en horas",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# Modelos
# =====================================================

class ConsultaEstimador(BaseModel):
    ticket_id: str
    tipo_incidencia: str          # "Incidente" | "Solicitud"
    tipo_atencion_sd: str
    area: Optional[str] = ""
    producto: Optional[str] = ""
    resumen: Optional[str] = ""
    urgencia_detectada: Optional[str] = "media"   # "alta" | "media"

class RespuestaEstimador(BaseModel):
    ticket_id: str
    tiempo_estimado_horas: float
    rango_minimo_horas: float
    rango_maximo_horas: float
    categoria_tiempo: str         # "rapido" | "normal" | "lento" | "muy_lento"
    factores_aplicados: list
    timestamp: str

# =====================================================
# Tablas de tiempos base (calculados de DATA2 histórico)
# Promedio general histórico: ~87h, pero por tipo:
# =====================================================

# Tiempos base en horas según tipo de atención (estimados del historial)
TIEMPOS_BASE_TIPO = {
    "desafiliacion":             24.0,
    "actualizacion de datos":    18.0,
    "alta de corredor":          36.0,
    "consulta":                  12.0,
    "solicitud de informacion":  16.0,
    "emision":                   48.0,
    "endoso":                    56.0,
    "anulacion":                 40.0,
    "reembolso":                 72.0,
    "siniestro":                 96.0,
    "error de servidor":        120.0,
    "error de sistema":         110.0,
    "error de aplicacion":       90.0,
    "acceso":                    20.0,
    "instalacion":               30.0,
    "configuracion":             48.0,
    "integracion":              144.0,
    "reporte":                   36.0,
    "factura":                   48.0,
    "planilla":                  60.0,
    "conciliacion":              72.0,
    "default":                   87.0,   # promedio histórico general
}

# Multiplicadores por tipo de incidencia
MULT_TIPO_INCIDENCIA = {
    "incidente":  1.3,   # Incidentes suelen ser más complejos/urgentes
    "solicitud":  0.85,
    "default":    1.0,
}

# Palabras críticas en resumen que aumentan el tiempo estimado
PALABRAS_CRITIC = [
    "masivo", "todos", "100%", "caido", "caído", "sin servicio",
    "produccion", "producción", "bloqueado", "critico", "crítico"
]

# =====================================================
# Lógica de estimación
# =====================================================

def _tiempo_base(tipo_sd: str) -> tuple:
    """Retorna (horas_base, descripcion)."""
    t = tipo_sd.strip().lower()
    for key, horas in TIEMPOS_BASE_TIPO.items():
        if key in t:
            return horas, key
    return TIEMPOS_BASE_TIPO["default"], "default"


def estimar_tiempo(consulta: ConsultaEstimador) -> dict:
    """
    Calcula el tiempo estimado de resolución con factores ajustadores.

    Factores:
      1. Tiempo base del tipo de atención SD
      2. Tipo de incidencia (Incidente → +30%)
      3. Urgencia alta (detectada en resumen → -20%, se resuelve más rápido por prioridad)
      4. Palabras críticas en resumen (afectan a más personas → +40%)
      5. Producto de alta complejidad (SCTR, Vida Ley → +25%)
    """
    horas_base, tipo_usado = _tiempo_base(consulta.tipo_atencion_sd)
    factores = [f"Tipo '{tipo_usado}' → base {horas_base}h"]

    multiplicador = 1.0

    # Factor 1: tipo de incidencia
    tipo_inc = consulta.tipo_incidencia.strip().lower()
    mult_inc = MULT_TIPO_INCIDENCIA.get(tipo_inc, MULT_TIPO_INCIDENCIA["default"])
    if mult_inc != 1.0:
        multiplicador *= mult_inc
        factores.append(f"Tipo incidencia '{tipo_inc}' → ×{mult_inc}")

    # Factor 2: urgencia alta → se prioriza, se resuelve antes
    if consulta.urgencia_detectada == "alta":
        multiplicador *= 0.80
        factores.append("Urgencia alta detectada → ×0.80 (mayor prioridad)")

    # Factor 3: palabras críticas en resumen
    resumen_lower = (consulta.resumen or "").lower()
    palabras_crit_encontradas = [p for p in PALABRAS_CRITIC if p in resumen_lower]
    if palabras_crit_encontradas:
        multiplicador *= 1.40
        factores.append(f"Palabras críticas: {palabras_crit_encontradas} → ×1.40")

    # Factor 4: productos de alta complejidad técnica
    prod = (consulta.producto or "").lower()
    if any(p in prod for p in ["sctr", "vida ley", "vida individual"]):
        multiplicador *= 1.25
        factores.append(f"Producto '{prod}' alta complejidad → ×1.25")

    horas_final = round(horas_base * multiplicador, 1)

    # Rango de incertidumbre ±25%
    rango_min = round(horas_final * 0.75, 1)
    rango_max = round(horas_final * 1.25, 1)

    # Categoría
    if horas_final < 24:
        categoria = "rapido"
    elif horas_final < 72:
        categoria = "normal"
    elif horas_final < 168:
        categoria = "lento"
    else:
        categoria = "muy_lento"

    return {
        "tiempo_estimado_horas": horas_final,
        "rango_minimo_horas":    rango_min,
        "rango_maximo_horas":    rango_max,
        "categoria_tiempo":      categoria,
        "factores_aplicados":    factores,
    }

# =====================================================
# Endpoints
# =====================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "Estimador", "timestamp": datetime.now().isoformat()}


@app.post("/estimar", response_model=RespuestaEstimador)
async def estimar(consulta: ConsultaEstimador):
    """
    Estima el tiempo de resolución del ticket en horas.
    Basado en patrones históricos del CSV de JIRA (reglas por ahora, ML pendiente).
    """
    resultado = estimar_tiempo(consulta)
    return RespuestaEstimador(
        ticket_id=consulta.ticket_id,
        **resultado,
        timestamp=datetime.now().isoformat()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
