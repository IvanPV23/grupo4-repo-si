"""
Agente HISTÓRICO — Puerto 8004
Busca tickets similares en el historial de CSVs resueltos.
Si encuentra un antecedente, sugiere asignar a N1 directamente.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime

app = FastAPI(
    title="Agente Histórico",
    description="Detecta tickets similares ya resueltos en el historial",
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

class ConsultaHistorico(BaseModel):
    ticket_id: str
    resumen: str
    tipo_atencion_sd: str
    area: str
    producto: Optional[str] = ""


class RespuestaHistorico(BaseModel):
    encontrado: bool
    ticket_id: str
    similares_encontrados: int
    nivel_sugerido: Optional[str] = None        # "N1" o "N2"
    mesa_sugerida: Optional[str] = None
    resolucion_referencia: Optional[str] = None
    confianza_similitud: float = 0.0
    razonamiento: str
    timestamp: str

# =====================================================
# Lógica de búsqueda
# =====================================================

DB_PATH = (
    Path(__file__).resolve()
    .parents[2]  # .../proyecto
    / "data"
    / "historico.db"
)

PALABRAS_STOP = {"de", "la", "el", "los", "las", "un", "una", "en", "y", "a",
                 "por", "con", "del", "al", "que", "se", "no", "es", "son"}


def _palabras_clave(texto: str) -> set:
    """Extrae palabras relevantes de un texto."""
    palabras = re.findall(r'\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{3,}\b', texto.lower())
    return {p for p in palabras if p not in PALABRAS_STOP}


def _init_db():
    """Crea la base SQLite y carga algunos tickets resueltos de ejemplo."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets_resueltos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resumen TEXT NOT NULL,
                tipo_atencion_sd TEXT NOT NULL,
                area TEXT NOT NULL,
                producto TEXT DEFAULT '',
                resolucion_referencia TEXT NOT NULL,
                fecha_resolucion TEXT
            )
            """
        )
        conn.commit()

        # Insertar ejemplos solo si la tabla está vacía
        cur.execute("SELECT COUNT(*) FROM tickets_resueltos")
        (count,) = cur.fetchone()
        if count == 0:
            ejemplos = [
                (
                    "ACTIVACIÓN DE BOT Y REPROCESO SCTR para cliente corporativo",
                    "ACTIVACIÓN DE BOT Y REPROCESO",
                    "Operaciones",
                    "SCTR",
                    "Se revisó el flujo del bot, se corrigió la configuración del webhook en n8n y se reprocesaron las colas pendientes. "
                    "Luego se validó con el usuario informador que las activaciones se completan correctamente.",
                    datetime.now().isoformat(),
                ),
                (
                    "Error de servidor en plataforma de emisión de SOAT (HTTP 500)",
                    "ERROR DE SERVIDOR",
                    "Tecnología",
                    "SOAT",
                    "Se identificó saturación de conexiones en el pool de base de datos, se incrementó el límite de conexiones y se reinició el servicio de aplicación. "
                    "Se agregaron métricas de observabilidad para prevenir recurrencias.",
                    datetime.now().isoformat(),
                ),
                (
                    "Actualización de datos de cliente Vida Ley",
                    "ACTUALIZACIÓN DE DATOS DE CLIENTES",
                    "Comercial",
                    "Vida Ley",
                    "Se actualizaron los datos del cliente en el maestro comercial y se sincronizaron con el core de pólizas. "
                    "Se dejó evidencia en el expediente digital.",
                    datetime.now().isoformat(),
                ),
            ]
            cur.executemany(
                """
                INSERT INTO tickets_resueltos
                    (resumen, tipo_atencion_sd, area, producto, resolucion_referencia, fecha_resolucion)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ejemplos,
            )
            conn.commit()
    finally:
        conn.close()


def _cargar_historico() -> list[dict]:
    """Carga todos los tickets resueltos desde la base SQLite."""
    if not DB_PATH.exists():
        _init_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, resumen, tipo_atencion_sd, area, producto, resolucion_referencia FROM tickets_resueltos"
        )
        filas = cur.fetchall()
        return [dict(f) for f in filas]
    finally:
        conn.close()


def _similitud(consulta: ConsultaHistorico, fila: dict) -> float:
    """
    Calcula score de similitud entre 0.0 y 1.0.
    Criterios:
      - tipo_atencion_sd igual            → +0.40
      - area igual                        → +0.25
      - producto igual                    → +0.15
      - >=2 palabras clave en común       → +0.10 por cada 2 (máx +0.20)
    """
    score = 0.0

    tipo_hist = (fila.get("tipo_atencion_sd") or "").strip().lower()
    area_hist = (fila.get("area") or "").strip().lower()
    prod_hist = (fila.get("producto") or "").strip().lower()
    res_hist = (fila.get("resumen") or "").strip()

    if tipo_hist and consulta.tipo_atencion_sd.lower() == tipo_hist:
        score += 0.40
    if area_hist and consulta.area.lower() == area_hist:
        score += 0.25
    if prod_hist and consulta.producto and consulta.producto.lower() == prod_hist:
        score += 0.15

    # Coincidencia de palabras clave en resumen
    kw_consulta = _palabras_clave(consulta.resumen)
    kw_hist = _palabras_clave(res_hist)
    comunes = len(kw_consulta & kw_hist)
    score += min(0.20, (comunes // 2) * 0.10)

    return round(score, 2)


def _determinar_nivel(fila: dict) -> str:
    """Determina el nivel al que fue asignado el ticket histórico (simple: siempre N1)."""
    return "N1"

# =====================================================
# Endpoints
# =====================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "Histórico", "timestamp": datetime.now().isoformat()}


@app.post("/consultar", response_model=RespuestaHistorico)
async def consultar_historico(consulta: ConsultaHistorico):
    """
    Busca antecedentes de tickets similares ya resueltos.
    Si encuentra uno con similitud >= 0.55, sugiere N1 o N2 directo.
    """
    historico = _cargar_historico()

    if not historico:
        return RespuestaHistorico(
            encontrado=False,
            ticket_id=consulta.ticket_id,
            similares_encontrados=0,
            confianza_similitud=0.0,
            razonamiento="No hay historial disponible en data/inputs/",
            timestamp=datetime.now().isoformat()
        )

    # Calcular similitud con todos los tickets resueltos
    scored = [(fila, _similitud(consulta, fila)) for fila in historico]
    scored.sort(key=lambda x: x[1], reverse=True)

    mejor_fila, mejor_score = scored[0]
    umbral = 0.9

    if mejor_score >= umbral:
        nivel = _determinar_nivel(mejor_fila)
        mesa  = "Service Desk 1" if nivel == "N1" else "Squad - Mesa Ongoing"
        res   = mejor_fila.get("resolucion_referencia", "")
        return RespuestaHistorico(
            encontrado=True,
            ticket_id=consulta.ticket_id,
            similares_encontrados=sum(1 for _, s in scored if s >= umbral),
            nivel_sugerido=nivel,
            mesa_sugerida=mesa,
            resolucion_referencia=res[:300] if res else "Ticket resuelto sin documentación",
            confianza_similitud=mejor_score,
            razonamiento=(
                f"Se encontró ticket similar con similitud={mejor_score}. "
                f"Tipo coincide: '{consulta.tipo_atencion_sd}'. "
                f"Se recomienda asignar directamente a {nivel} ({mesa}) "
                f"siguiendo la resolución anterior."
            ),
            timestamp=datetime.now().isoformat()
        )

    return RespuestaHistorico(
        encontrado=False,
        ticket_id=consulta.ticket_id,
        similares_encontrados=0,
        confianza_similitud=mejor_score,
        razonamiento=(
            f"No se encontraron antecedentes suficientes (mejor similitud={mejor_score}, "
            f"umbral={umbral}). Se requiere evaluación completa."
        ),
        timestamp=datetime.now().isoformat()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
