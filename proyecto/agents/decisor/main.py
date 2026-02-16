"""
Agente Decisor
Integra las evaluaciones de complejidad y capacidad para tomar la decisión final
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import uvicorn
import httpx
from datetime import datetime
import os

app = FastAPI(
    title="Agente Decisor",
    description="Toma la decisión final de asignación de tickets",
    version="1.0.0"
)

# =====================================================
# Configuración
# =====================================================

AGENTE_COMPLEJIDAD_URL = os.getenv("AGENTE_COMPLEJIDAD_URL", "http://localhost:8001")
AGENTE_CAPACIDAD_URL = os.getenv("AGENTE_CAPACIDAD_URL", "http://localhost:8002")

# =====================================================
# Modelos
# =====================================================

class TicketDecision(BaseModel):
    """Datos del ticket para decisión"""
    ticket_id: str
    tipo_error: str
    descripcion: str
    area: str
    prioridad: str

class DecisionResponse(BaseModel):
    """Respuesta de la decisión final"""
    ticket_id: str
    mesa_asignada: str
    complejidad_evaluada: str
    score_complejidad: float
    capacidad_mesa: float
    razonamiento: str
    factores_decision: Dict
    timestamp: str
    confianza: float  # 0-1

# =====================================================
# Funciones auxiliares
# =====================================================

async def consultar_agente_complejidad(ticket: TicketDecision) -> Dict:
    """Consulta al agente de complejidad"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AGENTE_COMPLEJIDAD_URL}/evaluar",
                json={
                    "ticket_id": ticket.ticket_id,
                    "tipo_error": ticket.tipo_error,
                    "descripcion": ticket.descripcion,
                    "area": ticket.area,
                    "prioridad": ticket.prioridad
                },
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Error al consultar agente de complejidad: {str(e)}"
            )

async def consultar_agente_capacidad(tipo_error: str, complejidad: str) -> Dict:
    """Consulta al agente de capacidad"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AGENTE_CAPACIDAD_URL}/evaluar",
                json={
                    "tipo_error": tipo_error,
                    "complejidad": complejidad
                },
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Error al consultar agente de capacidad: {str(e)}"
            )

def calcular_confianza(complejidad_score: float, mesas_disponibles: int) -> float:
    """
    Calcula el nivel de confianza de la decisión
    Basado en:
    - Claridad de la evaluación de complejidad
    - Disponibilidad de mesas apropiadas
    """
    # Factor de complejidad (score cercano a umbrales = menos confianza)
    if complejidad_score < 40 or complejidad_score > 80:
        factor_complejidad = 0.9
    elif 45 < complejidad_score < 75:
        factor_complejidad = 0.7
    else:
        factor_complejidad = 0.5
    
    # Factor de disponibilidad
    factor_disponibilidad = min(mesas_disponibles / 3, 1.0)
    
    # Confianza combinada
    confianza = (factor_complejidad + factor_disponibilidad) / 2
    
    return round(confianza, 2)

# =====================================================
# Endpoints
# =====================================================

@app.get("/health")
async def health_check():
    """Health check del agente"""
    return {
        "status": "healthy",
        "agent": "Decisor",
        "timestamp": datetime.now().isoformat(),
        "dependencies": {
            "agente_complejidad": AGENTE_COMPLEJIDAD_URL,
            "agente_capacidad": AGENTE_CAPACIDAD_URL
        }
    }

@app.post("/decidir", response_model=DecisionResponse)
async def tomar_decision(ticket: TicketDecision):
    """
    Toma la decisión final de asignación
    
    Proceso:
    1. Consulta al agente de complejidad
    2. Consulta al agente de capacidad
    3. Integra ambas evaluaciones
    4. Aplica reglas de decisión
    5. Retorna mesa asignada con razonamiento
    """
    try:
        # Paso 1: Evaluar complejidad
        eval_complejidad = await consultar_agente_complejidad(ticket)
        
        # Paso 2: Evaluar capacidad
        eval_capacidad = await consultar_agente_capacidad(
            tipo_error=ticket.tipo_error,
            complejidad=eval_complejidad["complejidad"]
        )
        
        # Paso 3: Integrar evaluaciones y tomar decisión
        mesa_asignada = eval_capacidad["mesa_recomendada"]
        
        # Construir razonamiento
        razonamiento_partes = [
            f"Complejidad evaluada: {eval_complejidad['complejidad']} (score: {eval_complejidad['score']})",
            f"Recomendación de complejidad: {eval_complejidad['recomendacion']}",
            f"Evaluación de capacidad: {eval_capacidad['razonamiento']}",
            f"Decisión final: Asignar a {mesa_asignada}"
        ]
        
        razonamiento = " | ".join(razonamiento_partes)
        
        # Factores de decisión
        factores_decision = {
            "complejidad": eval_complejidad["factores"],
            "mesas_disponibles": eval_capacidad["mesas_disponibles"],
            "capacidades": [
                {
                    "mesa": cap["mesa"],
                    "uso": cap["porcentaje_uso"]
                }
                for cap in eval_capacidad["capacidades"]
            ]
        }
        
        # Calcular confianza
        confianza = calcular_confianza(
            eval_complejidad["score"],
            len(eval_capacidad["mesas_disponibles"])
        )
        
        # Obtener capacidad de la mesa asignada
        capacidad_mesa = next(
            (cap["porcentaje_uso"] for cap in eval_capacidad["capacidades"]
             if cap["mesa"] == mesa_asignada),
            0.0
        )
        
        return DecisionResponse(
            ticket_id=ticket.ticket_id,
            mesa_asignada=mesa_asignada,
            complejidad_evaluada=eval_complejidad["complejidad"],
            score_complejidad=eval_complejidad["score"],
            capacidad_mesa=capacidad_mesa,
            razonamiento=razonamiento,
            factores_decision=factores_decision,
            timestamp=datetime.now().isoformat(),
            confianza=confianza
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en el proceso de decisión: {str(e)}"
        )

@app.get("/status")
async def verificar_estado_agentes():
    """Verifica el estado de los agentes dependientes"""
    estados = {}
    
    async with httpx.AsyncClient() as client:
        # Verificar agente de complejidad
        try:
            resp = await client.get(f"{AGENTE_COMPLEJIDAD_URL}/health", timeout=5.0)
            estados["agente_complejidad"] = "online" if resp.status_code == 200 else "error"
        except:
            estados["agente_complejidad"] = "offline"
        
        # Verificar agente de capacidad
        try:
            resp = await client.get(f"{AGENTE_CAPACIDAD_URL}/health", timeout=5.0)
            estados["agente_capacidad"] = "online" if resp.status_code == 200 else "error"
        except:
            estados["agente_capacidad"] = "offline"
    
    todos_online = all(estado == "online" for estado in estados.values())
    
    return {
        "status": "ready" if todos_online else "degraded",
        "agentes": estados,
        "timestamp": datetime.now().isoformat()
    }

# =====================================================
# Main
# =====================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    )