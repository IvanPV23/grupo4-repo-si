"""
API Principal del Sistema de Derivación de Tickets
FastAPI application — v2.0 con soporte para CSV real de JIRA
"""

from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from datetime import datetime
import httpx
import os
import asyncio
import json
import csv
import glob
import sys

# Agregar el path del proyecto para imports relativos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Ticket, TipoTicket, TipoError, Area, MesaSoporte, EstadoTicket
from utils.watcher import obtener_tickets_pendientes, resumen_archivo
from utils.filtrador_features import filtrar_features_decision, construir_payload_n8n

# URL del webhook de n8n en modo producción (se lee del environment de Docker)
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://sistema-tickets-n8n:5678/webhook/ticket")

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
    """Modelo para crear un nuevo ticket (manual o desde CSV de JIRA)"""
    ticket_id: str
    tipo_ticket: str
    tipo_error: str
    solicitante: str
    area: str
    titulo: str
    descripcion: str
    prioridad: Optional[str] = "media"
    # Campos adicionales del CSV real de JIRA (opcionales para compatibilidad)
    aplicativo: Optional[str] = ""
    producto: Optional[str] = ""
    clasificacion: Optional[str] = ""

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
        
        # Construir payload para n8n
        payload_n8n = {
            "ticket_id": ticket_data.ticket_id,
            "tipo_ticket": ticket_data.tipo_ticket,
            "tipo_error": ticket_data.tipo_error,
            "solicitante": ticket_data.solicitante,
            "area": ticket_data.area,
            "titulo": ticket_data.titulo,
            "descripcion": ticket_data.descripcion,
            "prioridad": ticket_data.prioridad,
            "aplicativo": ticket_data.aplicativo or "",
            "producto": ticket_data.producto or "",
            "clasificacion": ticket_data.clasificacion or "",
        }
        
        async def disparar_n8n():
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(N8N_WEBHOOK_URL, json=payload_n8n, timeout=5.0)
                    print(f"Ticket {ticket_data.ticket_id} enviado a n8n correctamente")
                except Exception as e:
                    print(f"Error enviando ticket al webhook de n8n: {e}")
                    
        asyncio.create_task(disparar_n8n())
        
        return TicketResponse(
            ticket_id=ticket.ticket_id,
            tipo_ticket=ticket.tipo_ticket.value,
            tipo_error=ticket.tipo_error.value,
            mesa_asignada=ticket.mesa_asignada.value,
            estado=ticket.estado.value,
            complejidad=ticket.complejidad.value if ticket.complejidad else None,
            mensaje="Ticket creado y flujo en n8n disparado correctamente"
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
# Endpoints de Procesamiento CSV (Agente Watcher)
# =====================================================

@app.post("/procesar-csv", tags=["CSV JIRA"])
async def procesar_csv(estados: Optional[str] = "Abierto"):
    """
    Procesa el CSV más reciente de la carpeta data/inputs/.

    1. Detecta el archivo más nuevo en data/inputs/
    2. Filtra tickets por estado (por defecto: Abierto)
    3. Transforma cada ticket con el Agente Filtrador
    4. Envía cada ticket al webhook de n8n para derivación

    Parámetro:
        estados: Estado(s) a incluir (separados por coma). Default: "Abierto"
    """
    carpeta = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "inputs"
    )

    estados_set = {e.strip() for e in estados.split(",")}

    try:
        tickets_raw = obtener_tickets_pendientes(
            carpeta=carpeta,
            estados_validos=estados_set
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer CSV: {str(e)}")

    if not tickets_raw:
        return {
            "status": "ok",
            "mensaje": "No hay tickets pendientes en la carpeta data/inputs/",
            "procesados": 0,
            "errores": 0,
        }

    procesados = 0
    errores = 0
    detalles = []
    resultados_reporte = []  # Para guardar en CSV

    async with httpx.AsyncClient() as client:
        for fila in tickets_raw:
            try:
                features = filtrar_features_decision(fila)
                payload = construir_payload_n8n(features)

                resp = await client.post(
                    N8N_WEBHOOK_URL,
                    json=payload,
                    timeout=12.0
                )
                procesados += 1

                # Parsear respuesta de n8n (contiene la decisión final)
                try:
                    resp_data = resp.json()
                except Exception:
                    resp_data = {}

                # Extraer campos de la decisión (pueden venir del nodo final de n8n)
                mesa_asignada = (
                    resp_data.get("mesa_asignada")
                    or resp_data.get("mesa_sugerida")
                    or "No determinada"
                )
                nivel         = resp_data.get("nivel", "-")
                confianza     = resp_data.get("confianza", "-")
                razonamiento  = resp_data.get("razonamiento", "-")
                resultado     = resp_data.get("resultado", "PROCESADO")

                detalle = {
                    "ticket_id":     payload["ticket_id"],
                    "status":        "enviado",
                    "n8n_status":    resp.status_code,
                    "mesa_asignada": mesa_asignada,
                    "nivel":         nivel,
                    "confianza":     confianza,
                    "resultado":     resultado,
                }
                detalles.append(detalle)

                # Fila para el reporte CSV
                resultados_reporte.append({
                    "ticket_id":      payload["ticket_id"],
                    "tipo_error":     payload.get("tipo_error", ""),
                    "area":           payload.get("area", ""),
                    "producto":       payload.get("producto", ""),
                    "aplicativo":     payload.get("aplicativo", ""),
                    "clasificacion":  payload.get("clasificacion", ""),
                    "urgencia":       payload.get("prioridad", ""),
                    "mesa_asignada":  mesa_asignada,
                    "nivel":          nivel,
                    "confianza":      confianza,
                    "resultado":      resultado,
                    "razonamiento":   razonamiento,
                    "procesado_en":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

            except Exception as e:
                errores += 1
                ticket_id = fila.get("Clave de incidencia", "DESCONOCIDO")
                print(f"Error procesando {ticket_id}: {e}")
                detalles.append({"ticket_id": ticket_id, "status": "error", "detalle": str(e)})
                resultados_reporte.append({
                    "ticket_id":     ticket_id,
                    "tipo_error":    "", "area": "", "producto": "",
                    "aplicativo":    "", "clasificacion": "", "urgencia": "",
                    "mesa_asignada": "ERROR", "nivel": "-",
                    "confianza":     "-", "resultado": "ERROR",
                    "razonamiento":  str(e),
                    "procesado_en":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

    # ── Guardar reporte CSV ──────────────────────────────────────────────
    ruta_outputs = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "outputs"
    )
    os.makedirs(ruta_outputs, exist_ok=True)
    nombre_reporte = f"reporte_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    ruta_reporte   = os.path.join(ruta_outputs, nombre_reporte)

    columnas = [
        "ticket_id", "tipo_error", "area", "producto", "aplicativo",
        "clasificacion", "urgencia", "mesa_asignada", "nivel",
        "confianza", "resultado", "razonamiento", "procesado_en"
    ]
    with open(ruta_reporte, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columnas, delimiter=";")
        writer.writeheader()
        writer.writerows(resultados_reporte)

    print(f"[API] Reporte guardado: {ruta_reporte}")

    return {
        "status":           "ok",
        "procesados":       procesados,
        "errores":          errores,
        "estados_filtrados": list(estados_set),
        "reporte_csv":      nombre_reporte,
        "detalles":         detalles[:20],
    }


@app.get("/inputs/status", tags=["CSV JIRA"])
async def estado_carpeta_inputs():
    """Muestra el estado de la carpeta data/inputs/ (qué CSV hay disponibles)."""
    carpeta = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "inputs"
    )
    return resumen_archivo(carpeta)


@app.get("/reporte", tags=["CSV JIRA"])
async def descargar_ultimo_reporte():
    """
    Descarga el reporte CSV más reciente generado por /procesar-csv.
    El archivo puede abrirse directamente en Excel.
    """
    ruta_outputs = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "outputs"
    )
    archivos = glob.glob(os.path.join(ruta_outputs, "reporte_*.csv"))
    if not archivos:
        raise HTTPException(
            status_code=404,
            detail="No hay reportes generados aún. Ejecuta POST /procesar-csv primero."
        )
    ultimo = max(archivos, key=os.path.getmtime)
    return FileResponse(
        path=ultimo,
        media_type="text/csv",
        filename=os.path.basename(ultimo)
    )


@app.get("/reporte/lista", tags=["CSV JIRA"])
async def listar_reportes():
    """Lista todos los reportes CSV disponibles en data/outputs/."""
    ruta_outputs = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "outputs"
    )
    archivos = glob.glob(os.path.join(ruta_outputs, "reporte_*.csv"))
    archivos.sort(key=os.path.getmtime, reverse=True)
    return {
        "total": len(archivos),
        "reportes": [os.path.basename(f) for f in archivos]
    }


# =====================================================
# Endpoints de Métricas
# =====================================================

@app.get("/metricas", tags=["Métricas"])
async def obtener_metricas():
    """Retorna métricas reales del sistema desde metricas_log.json."""
    log_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "metricas_log.json"
    )
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "total_tickets": 0,
            "tickets_derivados_automaticamente": 0,
            "tiempo_promedio_procesamiento_ms": 0,
            "distribucion_mesas": {},
            "nota": "Aún no hay métricas registradas. Procesa tickets para ver datos."
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