"""
API Principal del Sistema de Derivación de Tickets
FastAPI application
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from datetime import datetime

from models import Ticket, TipoTicket, TipoError, Area, MesaSoporte, EstadoTicket

# Configuración de la aplicación
app = FastAPI(
    title="Sistema de Derivación Inteligente de Tickets",
    description="API para gestión automática de tickets de soporte",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# Modelos de Request/Response
# =====================================================

class TicketCreate(BaseModel):
    """Modelo para crear un nuevo ticket"""
    ticket_id: str
    tipo_ticket: str
    tipo_error: str
    solicitante: str
    area: str
    titulo: str
    descripcion: str
    prioridad: Optional[str] = "media"

class TicketResponse(BaseModel):
    """Modelo de respuesta de ticket"""
    ticket_id: str
    tipo_ticket: str
    tipo_error: str
    mesa_asignada: str
    estado: str
    complejidad: Optional[str]
    mensaje: str

class HealthResponse(BaseModel):
    """Modelo de respuesta de health check"""
    status: str
    timestamp: str
    service: str
    version: str

# =====================================================
# Endpoints de Health Check
# =====================================================

@app.get("/", tags=["Health"])
async def root():
    """Endpoint raíz"""
    return {
        "message": "Sistema de Derivación Inteligente de Tickets",
        "status": "active",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check del servicio"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        service="API Principal",
        version="1.0.0"
    )

# =====================================================
# Endpoints de Tickets
# =====================================================

@app.post("/tickets", response_model=TicketResponse, tags=["Tickets"])
async def crear_ticket(ticket_data: TicketCreate):
    """
    Crea un nuevo ticket y lo procesa para derivación automática
    
    Este endpoint:
    1. Valida los datos del ticket
    2. Crea el objeto Ticket
    3. Dispara el flujo de derivación automática
    4. Retorna el resultado de la asignación
    """
    try:
        # Validar y crear ticket
        ticket = Ticket(
            ticket_id=ticket_data.ticket_id,
            tipo_ticket=TipoTicket(ticket_data.tipo_ticket),
            tipo_error=TipoError(ticket_data.tipo_error),
            solicitante=ticket_data.solicitante,
            area=Area(ticket_data.area),
            titulo=ticket_data.titulo,
            descripcion=ticket_data.descripcion
        )
        
        # TODO: Aquí se dispara el flujo de derivación
        # Por ahora, asignación simple como placeholder
        
        return TicketResponse(
            ticket_id=ticket.ticket_id,
            tipo_ticket=ticket.tipo_ticket.value,
            tipo_error=ticket.tipo_error.value,
            mesa_asignada=ticket.mesa_asignada.value,
            estado=ticket.estado.value,
            complejidad=ticket.complejidad.value if ticket.complejidad else None,
            mensaje="Ticket creado y en proceso de derivación"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Datos inválidos: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar ticket: {str(e)}"
        )

@app.get("/tickets/{ticket_id}", tags=["Tickets"])
async def obtener_ticket(ticket_id: str):
    """Obtiene información de un ticket específico"""
    # TODO: Implementar consulta a base de datos
    return {
        "ticket_id": ticket_id,
        "mensaje": "Endpoint en desarrollo"
    }

@app.get("/tickets", tags=["Tickets"])
async def listar_tickets(
    skip: int = 0,
    limit: int = 100,
    mesa: Optional[str] = None,
    estado: Optional[str] = None
):
    """Lista todos los tickets con filtros opcionales"""
    # TODO: Implementar consulta con filtros
    return {
        "total": 0,
        "tickets": [],
        "mensaje": "Endpoint en desarrollo"
    }

# =====================================================
# Endpoints de Derivación (para n8n)
# =====================================================

@app.post("/derivar/{ticket_id}", tags=["Derivación"])
async def derivar_ticket(ticket_id: str):
    """
    Endpoint que dispara el proceso de derivación automática
    Llamado por n8n webhook
    """
    # TODO: Implementar lógica de derivación
    return {
        "ticket_id": ticket_id,
        "estado": "En proceso de derivación",
        "mensaje": "Flujo de derivación iniciado"
    }

# =====================================================
# Endpoints de Métricas
# =====================================================

@app.get("/metricas", tags=["Métricas"])
async def obtener_metricas():
    """Retorna métricas del sistema"""
    # TODO: Implementar cálculo de métricas
    return {
        "total_tickets": 0,
        "tickets_derivados_automaticamente": 0,
        "tiempo_promedio_procesamiento": 0,
        "tasa_precision": 0
    }

# =====================================================
# Main
# =====================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )