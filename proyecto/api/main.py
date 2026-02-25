"""
API Principal — Sistema de Derivación v3.0
Recibe tickets desde la interfaz web y los procesa por el pipeline de agentes.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from datetime import datetime
import httpx
import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.excel_acumulativo import agregar_fila_reporte, obtener_resumen_reporte

# ── URLs de agentes (internos Docker) ─────────────────────────────────────────
AGENTE_HISTORICO   = os.getenv("AGENTE_HISTORICO_URL",   "http://agente-historico:8004")
AGENTE_ESTIMADOR   = os.getenv("AGENTE_ESTIMADOR_URL",   "http://agente-estimador:8005")
AGENTE_COMPLEJIDAD = os.getenv("AGENTE_COMPLEJIDAD_URL", "http://agente-complejidad:8001")
AGENTE_ORQUESTADOR = os.getenv("AGENTE_ORQUESTADOR_URL", "http://agente-orquestador:8003")

# ── n8n Webhook ────────────────────────────────────────────
N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "http://sistema-tickets-n8n:5678/webhook/derivar"   # Orquestador Central v3
)

# ── Configuración Jira Cloud ───────────────────────────────────────
JIRA_DOMAIN      = os.getenv("JIRA_DOMAIN",      "jhairrmb3.atlassian.net")
JIRA_EMAIL       = os.getenv("JIRA_EMAIL",       "jhairrmb3@gmail.com")
JIRA_API_TOKEN   = os.getenv("JIRA_API_TOKEN",   "")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "SCRUM")
JIRA_ACCOUNT_ID  = os.getenv("JIRA_ACCOUNT_ID",  "712020:4891c296-4785-48fc-8dfe-84c7205f6679")
JIRA_ENABLED     = bool(JIRA_API_TOKEN)  # Se activa solo si hay token

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sistema de Derivación Inteligente v3.0",
    description="Pipeline multiagente: Histórico → Estimador → Complejidad → Orquestador",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir el frontend estático desde /app
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

# ── Modelos ───────────────────────────────────────────────────────────────────

class TicketEntrada(BaseModel):
    """Datos que llegan desde el formulario web."""
    tipo_incidencia: str                   # "Incidente" | "Solicitud"
    resumen: str                           # Descripción corta
    descripcion_detallada: Optional[str] = ""
    tipo_atencion_sd: str                  # "Error de servidor", "Consulta", etc.
    area: str                              # "Siniestros", "Comercial", etc.
    producto: Optional[str] = ""          # "SOAT", "Vida Ley", "SCTR"
    aplicativo: Optional[str] = ""
    informador: Optional[str] = ""
    impacta_al_cierre: Optional[bool] = False
    cantidad_afectados: Optional[int] = 1

class ResultadoDerivacion(BaseModel):
    ticket_id: str
    mesa_asignada: str
    nivel_asignado: str
    en_cola: bool
    complejidad: str
    score_complejidad: float
    tiempo_estimado_horas: Optional[float]
    categoria_tiempo: Optional[str]
    via_historico: bool
    razonamiento: str
    jira_issue_key: Optional[str] = None   # Ej: "SCRUM-7" (None si Jira no disponible)
    jira_url: Optional[str] = None         # URL directa al issue en Jira
    timestamp: str


# ── n8n: delegar orquestación + Jira al workflow central ─────────────────
async def _enviar_a_n8n(ticket_data: dict) -> dict | None:
    """
    Envía el ticket al webhook de n8n (Orquestador Central v3).
    n8n ejecuta el pipeline completo de agentes + crea el issue en Jira.
    Retorna el resultado completo (dict) o None si falla.
    """
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(N8N_WEBHOOK_URL, json=ticket_data)
            if r.status_code in (200, 201):
                data = r.json()
                print(f"[n8n] Pipeline completado → {data.get('jira_issue_key', 'sin Jira')}")
                return data
            else:
                print(f"[n8n] Error {r.status_code}: {r.text[:200]}")
                return None
    except Exception as ex:
        print(f"[n8n] Excepción: {ex}")
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generar_ticket_id() -> str:
    now = datetime.now()
    return f"TK-{now.strftime('%Y%m%d%H%M%S')}"


def _detectar_urgencia(resumen: str, desc: str) -> str:
    import re
    texto = (resumen + " " + desc).upper()
    palabras = [
        r"\bURGENTE\b", r"\bMUY URGENTE\b", r"\bCR[IÍ]TICO\b",
        r"\bCA[IÍ]DO\b", r"\bSIN SERVICIO\b", r"\bBLOQUEADO\b",
        r"\bNO FUNCIONA\b", r"\bEMERGENCIA\b",
    ]
    for p in palabras:
        if re.search(p, texto):
            return "alta"
    return "media"


# ── Pipeline de derivación ────────────────────────────────────────────────────

async def _pipeline_derivacion(ticket: TicketEntrada, ticket_id: str) -> dict:
    """
    Orquesta el pipeline completo:
    HISTÓRICO → (si no hay antecedente) ESTIMADOR → COMPLEJIDAD → ORQUESTADOR
    """
    urgencia = _detectar_urgencia(
        ticket.resumen, ticket.descripcion_detallada or ""
    )

    # Ajustes extra por campos nuevos
    resumen_enriquecido = ticket.resumen
    if ticket.impacta_al_cierre:
        resumen_enriquecido += " IMPACTA AL CIERRE"
    if ticket.cantidad_afectados and ticket.cantidad_afectados > 10:
        resumen_enriquecido += f" {ticket.cantidad_afectados} usuarios afectados masivo"

    async with httpx.AsyncClient(timeout=12.0) as client:

        # ── 1. HISTÓRICO ──────────────────────────────────────────────────
        via_historico  = False
        mesa_historico = None
        nivel_historico= None
        hist_razon     = ""
        try:
            r_hist = await client.post(f"{AGENTE_HISTORICO}/consultar", json={
                "ticket_id":       ticket_id,
                "resumen":         resumen_enriquecido,
                "tipo_atencion_sd": ticket.tipo_atencion_sd,
                "area":            ticket.area,
                "producto":        ticket.producto or "",
            })
            h = r_hist.json()
            via_historico  = h.get("encontrado", False)
            mesa_historico = h.get("mesa_sugerida")
            nivel_historico= h.get("nivel_sugerido")
            hist_razon     = h.get("razonamiento", "")
        except Exception as e:
            hist_razon = f"Histórico no disponible: {e}"

        # ── 2. ESTIMADOR ──────────────────────────────────────────────────
        tiempo_horas   = None
        categoria_tpo  = ""
        factores_est   = []
        try:
            r_est = await client.post(f"{AGENTE_ESTIMADOR}/estimar", json={
                "ticket_id":          ticket_id,
                "tipo_incidencia":    ticket.tipo_incidencia,
                "tipo_atencion_sd":   ticket.tipo_atencion_sd,
                "area":               ticket.area,
                "producto":           ticket.producto or "",
                "resumen":            resumen_enriquecido,
                "urgencia_detectada": urgencia,
            })
            e = r_est.json()
            tiempo_horas  = e.get("tiempo_estimado_horas")
            categoria_tpo = e.get("categoria_tiempo", "")
            factores_est  = e.get("factores_aplicados", [])
        except Exception as ex:
            factores_est = [f"Estimador no disponible: {ex}"]

        # ── 3. COMPLEJIDAD ────────────────────────────────────────────────
        complejidad    = "media"
        score_comp     = 50.0
        nivel_rec      = "N1"
        recom_comp     = ""
        try:
            r_comp = await client.post(f"{AGENTE_COMPLEJIDAD}/evaluar", json={
                "ticket_id":             ticket_id,
                "tipo_incidencia":       ticket.tipo_incidencia,
                "tipo_atencion_sd":      ticket.tipo_atencion_sd,
                "resumen":               resumen_enriquecido,
                "area":                  ticket.area,
                "producto":              ticket.producto or "",
                "urgencia_detectada":    urgencia,
                "tiempo_estimado_horas": tiempo_horas,
            })
            c = r_comp.json()
            complejidad = c.get("complejidad", complejidad)
            score_comp  = c.get("score", score_comp)
            nivel_rec   = c.get("nivel_recomendado", nivel_rec)
            recom_comp  = c.get("recomendacion", "")
        except Exception as ex:
            recom_comp = f"Complejidad no disponible: {ex}"

        # ── 4. ORQUESTADOR ────────────────────────────────────────────────
        try:
            r_orq = await client.post(f"{AGENTE_ORQUESTADOR}/asignar", json={
                "ticket_id":              ticket_id,
                "tipo_incidencia":        ticket.tipo_incidencia,
                "tipo_atencion_sd":       ticket.tipo_atencion_sd,
                "area":                   ticket.area,
                "producto":               ticket.producto or "",
                "resumen":                resumen_enriquecido,
                "informador":             ticket.informador or "",
                "urgencia_detectada":     urgencia,
                "tiempo_estimado_horas":  tiempo_horas,
                "categoria_tiempo":       categoria_tpo,
                "complejidad":            complejidad,
                "score_complejidad":      score_comp,
                "nivel_recomendado":      nivel_rec,
                "via_historico":          via_historico,
                "mesa_historico":         mesa_historico,
            })
            o = r_orq.json()
        except Exception as ex:
            # Fallback si orquestador no disponible
            o = {
                "mesa_asignada":  "Service Desk 1",
                "nivel_asignado": "N1",
                "en_cola":        False,
                "razonamiento":   f"Orquestador no disponible: {ex}",
            }

    razonamiento = (
        f"Histórico: {hist_razon or 'sin antecedentes'} | "
        f"Estimado: {tiempo_horas}h ({categoria_tpo}) | "
        f"Complejidad: {complejidad} (score={score_comp}) | "
        f"{o.get('razonamiento', '')}"
    )

    return {
        "ticket_id":              ticket_id,
        "mesa_asignada":          o.get("mesa_asignada", "Service Desk 1"),
        "nivel_asignado":         o.get("nivel_asignado", "N1"),
        "en_cola":                o.get("en_cola", False),
        "complejidad":            complejidad,
        "score_complejidad":      score_comp,
        "tiempo_estimado_horas":  tiempo_horas,
        "categoria_tiempo":       categoria_tpo,
        "via_historico":          via_historico,
        "razonamiento":           razonamiento,
        "timestamp":              datetime.now().isoformat(),
        # extra para Excel
        "resumen":                ticket.resumen,
        "tipo_incidencia":        ticket.tipo_incidencia,
        "tipo_atencion_sd":       ticket.tipo_atencion_sd,
        "area":                   ticket.area,
        "producto":               ticket.producto or "",
        "aplicativo":             ticket.aplicativo or "",
        "informador":             ticket.informador or "",
        "urgencia_detectada":     urgencia,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/pipeline/ejecutar", tags=["Pipeline"], include_in_schema=True)
async def ejecutar_pipeline(ticket: TicketEntrada):
    """
    Llamado por n8n: ejecuta los 4 agentes y devuelve el resultado crudo.
    """
    ticket_id = _generar_ticket_id()
    resultado = await _pipeline_derivacion(ticket, ticket_id)
    return JSONResponse(content=resultado)


@app.post("/jira/crear", tags=["Pipeline"], include_in_schema=True)
async def crear_jira(resultado: dict):
    """
    Llamado por n8n: recibe el resultado del pipeline y crea el issue en Jira
    usando Python (código probado que funciona). Devuelve {jira_issue_key, jira_url}.
    """
    import base64
    from os import getenv
    domain  = getenv("JIRA_DOMAIN",      "jhairrmb3.atlassian.net")
    email   = getenv("JIRA_EMAIL",       "jhairrmb3@gmail.com")
    token   = getenv("JIRA_API_TOKEN",   "")
    project = getenv("JIRA_PROJECT_KEY", "SCRUM")
    account = getenv("JIRA_ACCOUNT_ID",  "712020:4891c296-4785-48fc-8dfe-84c7205f6679")

    token_b64 = base64.b64encode(f"{email}:{token}".encode()).decode()
    issue_type = "Bug" if "incidente" in (resultado.get("tipo_incidencia") or "").lower() else "Task"
    nivel  = resultado.get("nivel_asignado", "N1")
    mesa   = resultado.get("mesa_asignada", "Service Desk 1")
    comp   = resultado.get("complejidad", "media")
    mesa_l = mesa.replace(" ", "_").replace("-", "_")

    desc = (
        f"Ticket: {resultado.get('ticket_id','')}\n"
        f"Resumen: {resultado.get('resumen','')}\n"
        f"Mesa: {mesa} | Nivel: {nivel}\n"
        f"Complejidad: {comp} (score: {resultado.get('score_complejidad',0)})\n"
        f"Tiempo: {resultado.get('tiempo_estimado_horas','?')}h\n"
        f"Razonamiento: {resultado.get('razonamiento','')}"
    )
    payload = {
        "fields": {
            "project":   {"key": project},
            "summary":   f"[{nivel}] {(resultado.get('resumen') or 'Sin resumen')[:150]}",
            "issuetype": {"name": issue_type},
            "assignee":  {"accountId": account},
            "labels":    [nivel, mesa_l, comp],
            "description": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": desc}]}]
            }
        }
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.post(
                f"https://{domain}/rest/api/3/issue", json=payload,
                headers={"Authorization": f"Basic {token_b64}",
                         "Content-Type": "application/json", "Accept": "application/json"}
            )
            if r.status_code == 201:
                key = r.json().get("key", "")
                url = f"https://{domain}/browse/{key}"
                print(f"[Jira/Python] {key}")
                return JSONResponse(content={"jira_issue_key": key, "jira_url": url})
            else:
                print(f"[Jira/Python] Error {r.status_code}: {r.text[:200]}")
                return JSONResponse(content={"jira_issue_key": None, "jira_url": None})
    except Exception as ex:
        print(f"[Jira/Python] Excepción: {ex}")
        return JSONResponse(content={"jira_issue_key": None, "jira_url": None})


@app.get("/health", tags=["Sistema"])
async def health():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.now().isoformat(),
        "agentes": {
            "historico":    AGENTE_HISTORICO,
            "estimador":    AGENTE_ESTIMADOR,
            "complejidad":  AGENTE_COMPLEJIDAD,
            "orquestador":  AGENTE_ORQUESTADOR,
        }
    }


@app.post("/tickets/nuevo", tags=["Tickets"], response_model=ResultadoDerivacion)
async def crear_ticket(ticket: TicketEntrada):
    """
    Recibe un ticket del formulario y lo envía a n8n para orquestar.
    n8n ejecuta todos los agentes + crea el issue en Jira.
    La API recibe el resultado, guarda en Excel y lo devuelve al frontend.
    """
    # ── 1. Delegar todo a n8n (pipeline + Jira) ────────────────────────
    ticket_dict = ticket.model_dump()
    resultado = await _enviar_a_n8n(ticket_dict)

    if resultado is None:
        # Fallback: si n8n no responde, ejecutar pipeline directo (sin Jira)
        print("[API] n8n no disponible, fallback a pipeline directo")
        ticket_id = _generar_ticket_id()
        resultado = await _pipeline_derivacion(ticket, ticket_id)
        resultado["jira_issue_key"] = None
        resultado["jira_url"] = None

    # ── 2. Guardar en Excel acumulativo ─────────────────────────────
    from utils.excel_acumulativo import agregar_fila_reporte
    agregar_fila_reporte({
        "ticket_id":             resultado.get("ticket_id", ""),
        "resumen":               resultado.get("resumen", ticket.resumen),
        "tipo_incidencia":       resultado.get("tipo_incidencia", ticket.tipo_incidencia),
        "tipo_atencion_sd":      resultado.get("tipo_atencion_sd", ticket.tipo_atencion_sd),
        "area":                  resultado.get("area", ticket.area),
        "producto":              resultado.get("producto", ticket.producto or ""),
        "aplicativo":            resultado.get("aplicativo", ticket.aplicativo or ""),
        "informador":            resultado.get("informador", ticket.informador or ""),
        "urgencia_detectada":    resultado.get("urgencia_detectada", ""),
        "tiempo_estimado_horas": resultado.get("tiempo_estimado_horas"),
        "complejidad":           resultado.get("complejidad", ""),
        "score_complejidad":     resultado.get("score_complejidad", 0),
        "nivel_asignado":        resultado.get("nivel_asignado", ""),
        "mesa_asignada":         resultado.get("mesa_asignada", ""),
        "via_historico":         str(resultado.get("via_historico", False)),
        "resultado":             "EN_COLA" if resultado.get("en_cola") else "DERIVADO_AUTOMATICAMENTE",
        "razonamiento":          resultado.get("razonamiento", ""),
    })

    return ResultadoDerivacion(**{k: resultado.get(k) for k in ResultadoDerivacion.model_fields})


@app.get("/cola", tags=["Tickets"])
async def ver_cola():
    """Tickets actualmente en cola de espera."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{AGENTE_ORQUESTADOR}/cola")
            return r.json()
        except Exception:
            return {"en_cola": 0, "tickets": [], "error": "Orquestador no disponible"}


@app.get("/mesas/estado", tags=["Mesas"])
async def estado_mesas():
    """Estado de carga de todas las mesas de soporte."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{AGENTE_ORQUESTADOR}/mesas/estado")
            return r.json()
        except Exception:
            return {"error": "Orquestador no disponible"}


@app.get("/reporte", tags=["Reportes"])
async def descargar_reporte():
    """Descarga el Excel acumulativo de derivaciones."""
    from utils.excel_acumulativo import RUTA_REPORTE
    if not os.path.exists(RUTA_REPORTE):
        raise HTTPException(status_code=404, detail="No hay reporte generado aún. Envía algún ticket primero.")
    return FileResponse(
        path=RUTA_REPORTE,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="reporte_acumulativo.xlsx"
    )


@app.get("/reporte/resumen", tags=["Reportes"])
async def resumen_reporte():
    """Resumen del reporte acumulativo (cantidad de filas, etc.)."""
    return obtener_resumen_reporte()


@app.get("/metricas", tags=["Sistema"])
async def metricas():
    """Métricas del sistema."""
    resumen = obtener_resumen_reporte()
    return {
        "tickets_procesados": resumen["total"],
        "reporte_excel":      resumen["existe"],
        "timestamp":          datetime.now().isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)