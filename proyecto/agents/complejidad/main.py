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
        # Importar lógica centralizada desde utils
        from utils.reglas_derivacion import evaluar_complejidad_base
        
        # Ejecutar evaluación experta
        resultado = evaluar_complejidad_base(
            tipo_error=ticket.tipo_error,
            prioridad=ticket.prioridad,
            descripcion=ticket.descripcion
        )
        
        return ComplejidadResponse(
            ticket_id=ticket.ticket_id,
            complejidad=resultado["categoria"],
            score=resultado["score"],
            factores=resultado["factores"],
            recomendacion=resultado["recomendacion"],
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