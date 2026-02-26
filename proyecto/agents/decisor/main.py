"""
Agente ORQUESTADOR — Puerto 8003
Reemplaza al Decisor + Capacidad.
Asigna la mesa final, verifica disponibilidad y maneja la cola.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import os

app = FastAPI(
    title="Agente Orquestador",
    description="Asigna la mesa final, verifica carga y gestiona cola de espera",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# Estado de mesas (nombres reales de Protecta)
# =====================================================

ESTADO_MESAS = {
    # N1 — Soporte general
    "Service Desk 1": {"nivel": "N1", "especialidad": "Soporte general",        "max": 20, "actual": 12},
    "Service Desk 2": {"nivel": "N1", "especialidad": "Soporte general",        "max": 20, "actual":  8},
    # N2 — Soporte avanzado
    "Squad - Mesa Ongoing":   {"nivel": "N2", "especialidad": "Escalamiento",    "max": 15, "actual": 10},
    # N3 — Especialistas (evitar asignar a menos que sea necesario)
    "soportedigital":         {"nivel": "N3", "especialidad": "Ecommerce/Digital","max": 10, "actual":  5},
    "soporteapp":             {"nivel": "N3", "especialidad": "Facturación/Apps", "max": 10, "actual":  7},
    "Squad - Mesa Vida Ley":  {"nivel": "N3", "especialidad": "Vida Ley",         "max":  8, "actual":  3},
    "Squad - Mesa SCTR":      {"nivel": "N3", "especialidad": "SCTR",             "max":  8, "actual":  6},
    "Squad - Mesa SOAT":      {"nivel": "N3", "especialidad": "SOAT",             "max":  8, "actual":  4},
}

# Cola de espera (en memoria — se pierde al reiniciar; persistencia futura)
_COLA: List[dict] = []

# =====================================================
# Reglas de asignación de mesa
# =====================================================

def _porcentaje(mesa: str) -> float:
    m = ESTADO_MESAS[mesa]
    return (m["actual"] / m["max"]) * 100

def _disponible(mesa: str) -> bool:
    return _porcentaje(mesa) < 90

def _candidatas_por_nivel(nivel: str) -> List[str]:
    """Retorna mesas del nivel solicitado, ordenadas por menor carga."""
    mesas = [m for m, d in ESTADO_MESAS.items() if d["nivel"] == nivel]
    mesas.sort(key=_porcentaje)
    return mesas

def _mesa_por_producto(producto: str, tipo_sd: str) -> Optional[str]:
    """Reglas específicas por producto para ir directo a la mesa N3 correcta."""
    prod = producto.lower()
    tipo = tipo_sd.lower()
    if "vida ley" in prod or "vida ley" in tipo:
        return "Squad - Mesa Vida Ley"
    if "sctr" in prod or "sctr" in tipo:
        return "Squad - Mesa SCTR"
    if "soat" in prod or "soat" in tipo and "ecommerce" in tipo:
        return "Squad - Mesa SOAT"
    if "ecommerce" in tipo or "digital" in tipo or "web" in tipo:
        return "soportedigital"
    if "factura" in tipo or "planilla" in tipo or "conciliacion" in tipo:
        return "soporteapp"
    return None


def asignar_mesa(
    nivel_recomendado: str,
    complejidad: str,
    tipo_atencion_sd: str,
    producto: str,
    via_historico: bool,
) -> dict:
    """
    Lógica de asignación de mesa:
    1. Si vía histórico → forzar N1 o N2 (nunca N3)
    2. Si N3 recomendado → revisar regla por producto
    3. Verificar disponibilidad; si saturada → siguiente nivel o cola
    """
    # Histórico siempre N1/N2
    if via_historico:
        for nivel in ("N1", "N2"):
            for mesa in _candidatas_por_nivel(nivel):
                if _disponible(mesa):
                    return {"mesa": mesa, "nivel": nivel, "en_cola": False,
                            "razon": f"Histórico detectado → forzado a {nivel}"}
        # Si ambos N1 y N2 están llenos (extremo), poner en cola
        return {"mesa": "Service Desk 1", "nivel": "N1", "en_cola": True,
                "razon": "Histórico: N1/N2 saturados → cola"}

    # N3 solo si muy_alta complejidad
    if nivel_recomendado == "N3" and complejidad == "muy_alta":
        mesa_n3 = _mesa_por_producto(producto, tipo_atencion_sd)
        if mesa_n3 and _disponible(mesa_n3):
            return {"mesa": mesa_n3, "nivel": "N3", "en_cola": False,
                    "razon": f"Complejidad MUY_ALTA → N3 ({mesa_n3})"}
        # N3 saturada → escalar a N2
        for mesa in _candidatas_por_nivel("N2"):
            if _disponible(mesa):
                return {"mesa": mesa, "nivel": "N2", "en_cola": False,
                        "razon": f"N3 saturada → escalado a N2"}

    # Caso normal: N1 o N2
    niveles = ["N1"] if nivel_recomendado in ("N1", "baja", "media") else ["N2", "N1"]
    for nivel in niveles:
        for mesa in _candidatas_por_nivel(nivel):
            if _disponible(mesa):
                return {"mesa": mesa, "nivel": nivel, "en_cola": False,
                        "razon": f"Complejidad {complejidad} → {nivel} ({mesa}, "
                                 f"carga {round(_porcentaje(mesa),1)}%)"}

    # Todas saturadas → cola en N1
    mesa_fallback = _candidatas_por_nivel("N1")[0]
    return {"mesa": mesa_fallback, "nivel": "N1", "en_cola": True,
            "razon": "Todas las mesas N1/N2 saturadas → en cola de espera"}

# =====================================================
# Modelos
# =====================================================

class SolicitudOrquestador(BaseModel):
    ticket_id: str
    tipo_incidencia: str
    tipo_atencion_sd: str
    area: Optional[str] = ""
    producto: Optional[str] = ""
    resumen: Optional[str] = ""
    informador: Optional[str] = ""
    urgencia_detectada: Optional[str] = "media"
    # Del Estimador
    tiempo_estimado_horas: Optional[float] = None
    categoria_tiempo: Optional[str] = ""
    # Del Complejidad
    complejidad: Optional[str] = "media"
    score_complejidad: Optional[float] = 50.0
    nivel_recomendado: Optional[str] = "N1"
    # Del Histórico
    via_historico: Optional[bool] = False
    mesa_historico: Optional[str] = None
    resolucion_referencia: Optional[str] = None

class RespuestaOrquestador(BaseModel):
    ticket_id: str
    mesa_asignada: str
    nivel_asignado: str
    en_cola: bool
    complejidad: str
    score_complejidad: float
    tiempo_estimado_horas: Optional[float]
    categoria_tiempo: Optional[str]
    via_historico: bool
    resolucion_referencia: Optional[str] = None
    razonamiento: str
    timestamp: str

# =====================================================
# Endpoints
# =====================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "Orquestador", "timestamp": datetime.now().isoformat()}


@app.get("/mesas/estado")
async def estado_mesas():
    """Estado de carga de todas las mesas."""
    return {
        mesa: {
            **datos,
            "porcentaje": round(_porcentaje(mesa), 1),
            "disponible": _disponible(mesa),
        }
        for mesa, datos in ESTADO_MESAS.items()
    }


@app.get("/cola")
async def ver_cola():
    """Tickets actualmente en cola de espera."""
    return {"en_cola": len(_COLA), "tickets": _COLA}


@app.post("/asignar", response_model=RespuestaOrquestador)
async def asignar(solicitud: SolicitudOrquestador):
    """
    Asigna la mesa final combinando todos los resultados previos.
    Si la mesa está saturada, pone el ticket en cola de espera.
    """
    try:
        # Si el histórico ya determinó la mesa, usarla directamente
        if solicitud.via_historico and solicitud.mesa_historico:
            mesa_final = solicitud.mesa_historico
            nivel_final = ESTADO_MESAS.get(mesa_final, {}).get("nivel", "N1")
            en_cola = not _disponible(mesa_final)
            razon = f"Histórico → directamente a {mesa_final}"
        else:
            resultado = asignar_mesa(
                nivel_recomendado=solicitud.nivel_recomendado or "N1",
                complejidad=solicitud.complejidad or "media",
                tipo_atencion_sd=solicitud.tipo_atencion_sd,
                producto=solicitud.producto or "",
                via_historico=solicitud.via_historico or False,
            )
            mesa_final  = resultado["mesa"]
            nivel_final = resultado["nivel"]
            en_cola     = resultado["en_cola"]
            razon       = resultado["razon"]

        # Actualizar carga (simulado)
        if mesa_final in ESTADO_MESAS and not en_cola:
            ESTADO_MESAS[mesa_final]["actual"] = min(
                ESTADO_MESAS[mesa_final]["actual"] + 1,
                ESTADO_MESAS[mesa_final]["max"]
            )

        # Registrar en cola si aplica
        if en_cola:
            _COLA.append({
                "ticket_id": solicitud.ticket_id,
                "mesa_objetivo": mesa_final,
                "timestamp": datetime.now().isoformat()
            })

        return RespuestaOrquestador(
            ticket_id=solicitud.ticket_id,
            mesa_asignada=mesa_final,
            nivel_asignado=nivel_final,
            en_cola=en_cola,
            complejidad=solicitud.complejidad or "media",
            score_complejidad=solicitud.score_complejidad or 50.0,
            tiempo_estimado_horas=solicitud.tiempo_estimado_horas,
            categoria_tiempo=solicitud.categoria_tiempo,
            via_historico=solicitud.via_historico or False,
            resolucion_referencia=solicitud.resolucion_referencia,
            razonamiento=(
                (
                    f"Ticket similar en histórico → Asignar a {nivel_final} ({mesa_final}) | "
                    f"Cómo se resolvió antes: {solicitud.resolucion_referencia}"
                )
                if solicitud.via_historico and solicitud.resolucion_referencia
                else (
                    f"Complejidad: {solicitud.complejidad or 'media'} (score={solicitud.score_complejidad or 50.0}) | "
                    f"Tiempo est.: {solicitud.tiempo_estimado_horas}h ({solicitud.categoria_tiempo}) | "
                    f"{razon}"
                )
            ),
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)