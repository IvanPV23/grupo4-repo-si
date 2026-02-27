"""
Agente COMPLEJIDAD v2 — Puerto 8001
Determina la complejidad de un ticket basándose en:
  - Tipo de incidencia
  - Palabras clave en el Resumen
  - Tiempo estimado de resolución
  - Urgencia detectada
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import re
from datetime import datetime

app = FastAPI(
    title="Agente de Complejidad v2",
    description="Evalúa complejidad técnica considerando tiempo estimado y palabras clave",
    version="2.0.0"
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

class TicketEvaluacion(BaseModel):
    ticket_id: str
    tipo_incidencia: str                       # "Incidente" | "Solicitud"
    tipo_atencion_sd: str
    resumen: Optional[str] = ""
    area: Optional[str] = ""
    producto: Optional[str] = ""
    urgencia_detectada: Optional[str] = "media"
    tiempo_estimado_horas: Optional[float] = None  # viene del Estimador

class ComplejidadResponse(BaseModel):
    ticket_id: str
    complejidad: str        # baja | media | alta | muy_alta
    score: float            # 0 – 100
    nivel_recomendado: str  # N1 | N2 | N3
    factores: dict
    recomendacion: str
    timestamp: str

# =====================================================
# Tablas de puntuación
# =====================================================

# Tipos de atención → puntaje base (incidentes técnicos puntúan más alto)
PUNTAJE_TIPO_ATENCION = {
    "consulta":              10,
    "solicitud de info":     10,
    "actualizacion":         15,
    "desafiliacion":         15,
    "alta de corredor":      20,
    "acceso":                20,
    "emision":               30,
    "endoso":                30,
    "anulacion":             30,
    "reembolso":             40,
    "siniestro":             45,
    "error de aplicacion":   50,
    "error de sistema":      60,
    "error de servidor":     65,
    "integracion":           70,
    "configuracion":         35,
}

# Palabras en resumen → puntaje adicional
PALABRAS_ALTA_COMPLEJIDAD = [
    (r"\b(masivo|todos los usuarios|100%)\b",            30, "impacto masivo"),
    (r"\b(ca[ií]do|sin servicio|no funciona)\b",         25, "servicio caído"),
    (r"\b(producci[oó]n|productivo|en vivo)\b",          20, "ambiente producción"),
    (r"\b(cr[ií]tico|emergencia|urgente)\b",             15, "urgencia crítica"),
    (r"\b(bloqueado|paralizado|detenido)\b",             15, "bloqueo operativo"),
    (r"\b(integraci[oó]n|api|servicio externo)\b",       15, "integración técnica"),
    (r"\b(base de datos|bd|sql|timeout)\b",              20, "problema de datos"),
    (r"\b(error 5\d\d|500|503|504)\b",                   20, "error HTTP crítico"),
]

PALABRAS_BAJA_COMPLEJIDAD = [
    (r"\b(consulta|pregunta|c[oó]mo)\b",                -10, "consulta simple"),
    (r"\b(actualizar? datos|cambiar? correo)\b",         -10, "actualización simple"),
]


def evaluar_complejidad(ticket: TicketEvaluacion) -> dict:
    """Calcula score de complejidad 0-100 y categoría."""
    score = 30.0  # base neutral
    factores = {}

    # 1. Tipo de incidencia
    tipo_inc = ticket.tipo_incidencia.strip().lower()
    if "incidente" in tipo_inc:
        score += 15
        factores["tipo_incidencia"] = "+15 (Incidente > Solicitud)"
    else:
        score -= 5
        factores["tipo_incidencia"] = "-5 (Solicitud)"

    # 2. Tipo de atención SD
    tipo_sd = ticket.tipo_atencion_sd.strip().lower()
    pts_tipo = 0
    for key, pts in PUNTAJE_TIPO_ATENCION.items():
        if key in tipo_sd:
            pts_tipo = pts
            break
    if pts_tipo:
        score += pts_tipo - 30  # relativo al base 30
        factores["tipo_atencion_sd"] = f"{pts_tipo - 30:+d} ('{tipo_sd}')"

    # 3. Palabras clave en resumen
    resumen = (ticket.resumen or "").lower()
    for patron, puntos, etiqueta in PALABRAS_ALTA_COMPLEJIDAD:
        if re.search(patron, resumen):
            score += puntos
            factores[etiqueta] = f"+{puntos}"
    for patron, puntos, etiqueta in PALABRAS_BAJA_COMPLEJIDAD:
        if re.search(patron, resumen):
            score += puntos
            factores[etiqueta] = f"{puntos}"

    # 4. Urgencia
    if ticket.urgencia_detectada == "alta":
        score += 10
        factores["urgencia"] = "+10 (urgencia alta detectada)"

    # 5. Tiempo estimado (viene del Estimador)
    if ticket.tiempo_estimado_horas is not None:
        th = ticket.tiempo_estimado_horas
        if th >= 168:    # > 1 semana
            score += 20
            factores["tiempo_estimado"] = f"+20 (>{th}h estimado)"
        elif th >= 72:   # 3-7 días
            score += 10
            factores["tiempo_estimado"] = f"+10 ({th}h estimado)"
        elif th < 24:    # mismo día
            score -= 10
            factores["tiempo_estimado"] = f"-10 ({th}h estimado, rápido)"

    # 6. Producto de alta complejidad técnica
    prod = (ticket.producto or "").lower()
    if any(p in prod for p in ["sctr", "vida ley", "vida individual"]):
        score += 10
        factores["producto"] = f"+10 (producto complejo: {prod})"

    # Clamp 0–100
    score = max(0.0, min(100.0, round(score, 1)))

    # Categorizar
    if score <= 35:
        categoria = "baja"
        nivel = "N1"
        recomendacion = "Puede resolver N1 (Service Desk). Baja complejidad técnica."
    elif score <= 60:
        categoria = "media"
        nivel = "N1"
        recomendacion = "N1 con posible escalamiento a N2 si no resuelve en plazo."
    elif score <= 80:
        categoria = "alta"
        nivel = "N2"
        recomendacion = "Requiere N2 (Squad Ongoing). Complejidad técnica significativa."
    else:
        categoria = "muy_alta"
        nivel = "N3"
        recomendacion = "N3 solo si no hay antecedente histórico. Complejidad máxima."

    return {
        "complejidad": categoria,
        "score": score,
        "nivel_recomendado": nivel,
        "factores": factores,
        "recomendacion": recomendacion,
    }

# =====================================================
# Endpoints
# =====================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "Complejidad v2", "timestamp": datetime.now().isoformat()}


@app.post("/evaluar", response_model=ComplejidadResponse)
async def evaluar(ticket: TicketEvaluacion):
    """Evalúa la complejidad del ticket. Incorpora tiempo_estimado_horas del Estimador."""
    try:
        resultado = evaluar_complejidad(ticket)
        return ComplejidadResponse(
            ticket_id=ticket.ticket_id,
            **resultado,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)