"""
Agente de Evaluación de Complejidad
Analiza tickets y determina su nivel de complejidad
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from datetime import datetime

app = FastAPI(
    title="Agente de Complejidad",
    description="Evalúa la complejidad técnica de tickets",
    version="1.0.0"
)

# =====================================================
# Modelos
# =====================================================

class TicketEvaluacion(BaseModel):
    """Datos del ticket para evaluación"""
    ticket_id: str
    tipo_error: str
    descripcion: str
    area: str
    prioridad: str

class ComplejidadResponse(BaseModel):
    """Respuesta de evaluación de complejidad"""
    ticket_id: str
    complejidad: str  # baja, media, alta, critica
    score: float  # 0-100
    factores: dict
    recomendacion: str
    timestamp: str

# =====================================================
# Endpoints
# =====================================================

@app.get("/health")
async def health_check():
    """Health check del agente"""
    return {
        "status": "healthy",
        "agent": "Complejidad",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/evaluar", response_model=ComplejidadResponse)
async def evaluar_complejidad(ticket: TicketEvaluacion):
    """
    Evalúa la complejidad de un ticket
    
    Criterios considerados:
    - Tipo de error
    - Descripción del problema
    - Área afectada
    - Prioridad
    - Palabras clave técnicas
    """
    try:
        # TODO: Implementar lógica de evaluación
        # Por ahora, lógica simple basada en reglas
        
        score = 50.0  # Base
        factores = {}
        
        # Evaluar por tipo de error
        if ticket.tipo_error in ["infraestructura", "redes"]:
            score += 20
            factores["tipo_error"] = "Alta complejidad técnica"
        elif ticket.tipo_error == "software":
            score += 10
            factores["tipo_error"] = "Complejidad media"
        
        # Evaluar por prioridad
        if ticket.prioridad == "urgente":
            score += 15
            factores["prioridad"] = "Requiere atención inmediata"
        elif ticket.prioridad == "alta":
            score += 10
            factores["prioridad"] = "Alta prioridad"
        
        # Palabras clave en descripción
        palabras_complejas = ["servidor", "caído", "crítico", "datos", "seguridad"]
        descripcion_lower = ticket.descripcion.lower()
        palabras_encontradas = [p for p in palabras_complejas if p in descripcion_lower]
        
        if palabras_encontradas:
            score += len(palabras_encontradas) * 5
            factores["palabras_clave"] = f"Términos técnicos: {', '.join(palabras_encontradas)}"
        
        # Determinar nivel de complejidad
        if score >= 80:
            complejidad = "critica"
            recomendacion = "Asignar a mesa especialista inmediatamente"
        elif score >= 60:
            complejidad = "alta"
            recomendacion = "Asignar a mesa N2 o especialista"
        elif score >= 40:
            complejidad = "media"
            recomendacion = "Puede ser manejado por mesa N1 o N2"
        else:
            complejidad = "baja"
            recomendacion = "Asignar a mesa N1"
        
        return ComplejidadResponse(
            ticket_id=ticket.ticket_id,
            complejidad=complejidad,
            score=min(score, 100),
            factores=factores,
            recomendacion=recomendacion,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# Main
# =====================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )