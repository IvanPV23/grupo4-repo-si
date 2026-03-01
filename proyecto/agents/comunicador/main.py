"""
Agente COMUNICADOR — Puerto 8007
Envía correo electrónico al informador con el detalle de la asignación.
Solo envía si el informador tiene un email válido (ya con @ o en el mapeo).
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os

app = FastAPI(
    title="Agente Comunicador",
    description="Envía correo al informador con detalle de asignación",
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


class PayloadComunicador(BaseModel):
    informador: str
    ticket_id: str
    mesa_asignada: str
    nivel_asignado: Optional[str] = ""
    resumen: Optional[str] = ""
    jira_issue_key: Optional[str] = None
    jira_url: Optional[str] = None
    complejidad: Optional[str] = ""
    tiempo_estimado_horas: Optional[float] = None
    area: Optional[str] = ""
    producto: Optional[str] = ""


class RespuestaComunicador(BaseModel):
    enviado: bool
    email_destino: Optional[str] = None
    razon: Optional[str] = None
    timestamp: str

# =====================================================
# Mapeo informador → email (editable)
# =====================================================

MAPEO_PATH = (
    Path(__file__).resolve()
    .parents[2]
    / "data"
    / "informador_emails.json"
)


def _cargar_mapeo() -> dict[str, str]:
    """Carga el mapeo usuario → email desde JSON. Editable sin reiniciar."""
    if not MAPEO_PATH.exists():
        return {}
    try:
        with open(MAPEO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {str(k).strip().lower(): str(v).strip() for k, v in data.items()}
    except (json.JSONDecodeError, IOError):
        return {}


def _resolver_email(informador: str) -> Optional[str]:
    """
    Resuelve el email del informador.
    - Si informador ya contiene @ → es email válido, retornar tal cual.
    - Si no → buscar en mapeo (usuario → email).
    - Si no está en mapeo → retornar None (no enviar).
    """
    if not informador or not str(informador).strip():
        return None
    val = str(informador).strip()
    if "@" in val:
        return val
    mapeo = _cargar_mapeo()
    return mapeo.get(val.lower())


def _enviar_email(destino: str, asunto: str, cuerpo: str) -> bool:
    """Envía email vía SMTP (Gmail)."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    if not user or not password:
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = user
    msg["To"] = destino
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(user, destino, msg.as_string())
        return True
    except Exception:
        return False


# =====================================================
# Endpoints
# =====================================================


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "Comunicador", "timestamp": datetime.now().isoformat()}


@app.post("/enviar", response_model=RespuestaComunicador)
async def enviar_correo(payload: PayloadComunicador):
    """
    Envía correo al informador con el detalle de asignación.
    Solo envía si el informador tiene un email válido.
    """
    email_destino = _resolver_email(payload.informador)
    ts = datetime.now().isoformat()

    if not email_destino:
        return RespuestaComunicador(
            enviado=False,
            razon="Informador sin email válido (no contiene @ ni está en mapeo)",
            timestamp=ts
        )

    asunto = f"Ticket {payload.ticket_id} asignado a mesa {payload.mesa_asignada}"
    lineas = [
        f"Ticket: {payload.ticket_id}",
        f"Mesa asignada: {payload.mesa_asignada}",
        f"Nivel: {payload.nivel_asignado or '-'}",
        f"Resumen: {payload.resumen or '-'}",
        f"Complejidad: {payload.complejidad or '-'}",
        f"Tiempo estimado: {payload.tiempo_estimado_horas or '-'} horas",
        f"Área: {payload.area or '-'}",
        f"Producto: {payload.producto or '-'}",
        "",
    ]
    if payload.jira_issue_key and payload.jira_url:
        lineas.append(f"Issue JIRA: {payload.jira_issue_key}")
        lineas.append(f"URL: {payload.jira_url}")
    cuerpo = "\n".join(lineas)

    ok = _enviar_email(email_destino, asunto, cuerpo)
    if ok:
        return RespuestaComunicador(
            enviado=True,
            email_destino=email_destino,
            razon="Correo enviado correctamente",
            timestamp=ts
        )
    return RespuestaComunicador(
        enviado=False,
        email_destino=email_destino,
        razon="Error al enviar correo (revisar credenciales SMTP)",
        timestamp=ts
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8007, reload=True)
