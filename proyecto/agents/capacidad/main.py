"""
Agente de Evaluación de Capacidad
Analiza la disponibilidad y carga de las mesas de soporte
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
from datetime import datetime

app = FastAPI(
    title="Agente de Capacidad",
    description="Evalúa la capacidad y disponibilidad de mesas de soporte",
    version="1.0.0"
)

# =====================================================
# Modelos
# =====================================================

class CapacidadMesa(BaseModel):
    """Estado de capacidad de una mesa"""
    mesa: str
    especialidad: str
    max_tickets: int
    carga_actual: int
    porcentaje_uso: float
    disponible: bool

class ConsultaCapacidad(BaseModel):
    """Consulta de capacidad para tipo de ticket"""
    tipo_error: str
    complejidad: Optional[str] = None

class CapacidadResponse(BaseModel):
    """Respuesta de evaluación de capacidad"""
    mesas_disponibles: List[str]
    mesa_recomendada: str
    capacidades: List[CapacidadMesa]
    razonamiento: str
    timestamp: str

# =====================================================
# Estado del sistema (En producción vendría de BD)
# =====================================================

# Estado simulado de las mesas reales de Protecta Seguros
ESTADO_MESAS = {
    "Service Desk 1": {
        "especialidad": "N1 - Soporte General",
        "max_tickets": 20,
        "carga_actual": 12
    },
    "Service Desk 2": {
        "especialidad": "N1 - Soporte General",
        "max_tickets": 20,
        "carga_actual": 8
    },
    "Squad - Mesa Ongoing": {
        "especialidad": "N2 - Soporte Avanzado",
        "max_tickets": 15,
        "carga_actual": 10
    },
    "soportedigital": {
        "especialidad": "N3 - Digital y E-commerce",
        "max_tickets": 10,
        "carga_actual": 5
    },
    "soporteapp": {
        "especialidad": "N3 - Aplicativos y Facturación",
        "max_tickets": 10,
        "carga_actual": 4
    },
    "Squad - Mesa Vida Ley": {
        "especialidad": "N3 - Producto Vida Ley",
        "max_tickets": 8,
        "carga_actual": 3
    },
    "Squad - Mesa SCTR": {
        "especialidad": "N3 - Producto SCTR",
        "max_tickets": 8,
        "carga_actual": 2
    }
}

# Mapeo de keywords de tipo_atencion_sd a mesas (basado en data real de JIRA)
ESPECIALIZACION_MESAS = {
    # Solicitudes simples → N1
    "desafiliacion": ["Service Desk 1", "Service Desk 2"],
    "actualizacion de datos": ["Service Desk 1"],
    "envio de correo": ["Service Desk 1"],
    "activacion": ["Service Desk 1", "Service Desk 2"],
    "inclusion": ["Service Desk 1"],
    # Errores moderados → N2
    "error de servicio": ["Squad - Mesa Ongoing", "soportedigital"],
    "error de servidor": ["Squad - Mesa Ongoing", "soportedigital"],
    "emision": ["soportedigital", "Squad - Mesa Ongoing"],
    "migracion": ["Squad - Mesa Ongoing", "soporteapp"],
    # Facturación → soporteapp
    "factura": ["soporteapp", "Squad - Mesa Ongoing"],
    "planilla": ["soporteapp"],
    "refactura": ["soporteapp"],
    "conciliacion": ["soporteapp"],
    # Default
    "default": ["Service Desk 1", "Squad - Mesa Ongoing"]
}

# =====================================================
# Funciones auxiliares
# =====================================================

def calcular_capacidad_mesa(mesa_id: str) -> CapacidadMesa:
    """Calcula el estado de capacidad de una mesa"""
    estado = ESTADO_MESAS[mesa_id]
    porcentaje = (estado["carga_actual"] / estado["max_tickets"]) * 100
    
    return CapacidadMesa(
        mesa=mesa_id,
        especialidad=estado["especialidad"],
        max_tickets=estado["max_tickets"],
        carga_actual=estado["carga_actual"],
        porcentaje_uso=round(porcentaje, 2),
        disponible=porcentaje < 90  # Disponible si está bajo 90%
    )

def obtener_mesas_especializadas(tipo_error: str, complejidad: str = "media") -> List[str]:
    """Retorna las mesas especializadas para un tipo de error usando reglas centralizadas"""
    from utils.reglas_derivacion import determinar_mesa_ideal
    return determinar_mesa_ideal(tipo_error, complejidad)

# =====================================================
# Endpoints
# =====================================================

@app.get("/health")
async def health_check():
    """Health check del agente"""
    return {
        "status": "healthy",
        "agent": "Capacidad",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/capacidad/todas")
async def obtener_todas_capacidades():
    """Retorna el estado de capacidad de todas las mesas"""
    capacidades = [calcular_capacidad_mesa(mesa_id) for mesa_id in ESTADO_MESAS.keys()]
    return {
        "timestamp": datetime.now().isoformat(),
        "capacidades": capacidades
    }

@app.post("/evaluar", response_model=CapacidadResponse)
async def evaluar_capacidad(consulta: ConsultaCapacidad):
    """
    Evalúa qué mesa tiene capacidad para recibir el ticket
    
    Criterios:
    - Especialización de la mesa
    - Carga actual vs capacidad máxima
    - Complejidad del ticket (si se proporciona)
    """
    try:
        # Obtener mesas especializadas usando la lógica centralizada
        mesas_especializadas = obtener_mesas_especializadas(consulta.tipo_error, consulta.complejidad)
        
        # Calcular capacidad de mesas relevantes
        capacidades = [calcular_capacidad_mesa(mesa) for mesa in mesas_especializadas]
        
        # Filtrar mesas disponibles
        mesas_disponibles = [
            cap.mesa for cap in capacidades 
            if cap.disponible
        ]
        
        # Si no hay mesas disponibles, buscar la menos cargada
        if not mesas_disponibles:
            capacidades.sort(key=lambda x: x.porcentaje_uso)
            mesa_recomendada = capacidades[0].mesa
            razonamiento = f"No hay mesas disponibles. Se asigna a {mesa_recomendada} (menos cargada: {capacidades[0].porcentaje_uso}%)"
        else:
            # Seleccionar mesa basándose en complejidad
            if consulta.complejidad in ["alta", "critica"]:
                # Buscar mesa especialista disponible
                mesas_especialistas = [m for m in mesas_disponibles if "especialista" in m or "infraestructura" in m]
                if mesas_especialistas:
                    mesa_recomendada = mesas_especialistas[0]
                    razonamiento = f"Alta complejidad: asignado a mesa especializada {mesa_recomendada}"
                else:
                    mesa_recomendada = mesas_disponibles[0]
                    razonamiento = f"Alta complejidad pero no hay especialistas disponibles: asignado a {mesa_recomendada}"
            else:
                # Para complejidad media/baja, asignar a la menos cargada disponible
                caps_disponibles = [c for c in capacidades if c.disponible]
                caps_disponibles.sort(key=lambda x: x.porcentaje_uso)
                mesa_recomendada = caps_disponibles[0].mesa
                razonamiento = f"Asignado a {mesa_recomendada} (carga: {caps_disponibles[0].porcentaje_uso}%)"
        
        return CapacidadResponse(
            mesas_disponibles=mesas_disponibles,
            mesa_recomendada=mesa_recomendada,
            capacidades=capacidades,
            razonamiento=razonamiento,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/actualizar/{mesa_id}")
async def actualizar_carga_mesa(mesa_id: str, incremento: int = 1):
    """Actualiza la carga actual de una mesa (cuando se asigna un ticket)"""
    if mesa_id not in ESTADO_MESAS:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    
    ESTADO_MESAS[mesa_id]["carga_actual"] += incremento
    
    return {
        "mesa": mesa_id,
        "nueva_carga": ESTADO_MESAS[mesa_id]["carga_actual"],
        "max_tickets": ESTADO_MESAS[mesa_id]["max_tickets"]
    }

# =====================================================
# Main
# =====================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )