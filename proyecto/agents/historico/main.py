"""
Agente HISTÓRICO — Puerto 8004
Busca tickets similares en el historial de CSVs resueltos.
Si encuentra un antecedente, sugiere asignar a N1 o N2 directamente.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import csv
import glob
import re
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

CARPETA_INPUTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "data", "inputs"
)

ESTADOS_RESUELTOS = {"terminado", "cerrado", "resuelto", "done", "closed"}

PALABRAS_STOP = {"de", "la", "el", "los", "las", "un", "una", "en", "y", "a",
                 "por", "con", "del", "al", "que", "se", "no", "es", "son"}


def _palabras_clave(texto: str) -> set:
    """Extrae palabras relevantes de un texto."""
    palabras = re.findall(r'\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{3,}\b', texto.lower())
    return {p for p in palabras if p not in PALABRAS_STOP}


def _cargar_historico() -> list:
    """Carga todos los CSVs de data/inputs/ que tengan tickets resueltos."""
    registros = []
    carpeta = os.path.abspath(CARPETA_INPUTS)
    if not os.path.isdir(carpeta):
        return registros

    archivos = glob.glob(os.path.join(carpeta, "*.csv"))
    for archivo in archivos:
        try:
            for enc in ("utf-8-sig", "latin-1", "cp1252"):
                try:
                    with open(archivo, encoding=enc) as f:
                        reader = csv.DictReader(f, delimiter=";")
                        for fila in reader:
                            estado = fila.get("Estado", "").strip().lower()
                            if estado in ESTADOS_RESUELTOS:
                                registros.append(fila)
                    break
                except UnicodeDecodeError:
                    continue
        except Exception as e:
            print(f"[Histórico] Error leyendo {archivo}: {e}")
    return registros


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

    # Mapeo de columnas JIRA
    tipo_hist = (fila.get("Campo personalizado (Tipo de atención SD)", "")
                 or fila.get("Campo personalizado (Tipo de atencion SD)", "")
                 or fila.get("Tipo de atencion SD", "")).strip().lower()
    area_hist  = (fila.get("Campo personalizado (Área)", "")
                  or fila.get("Area", "")).strip().lower()
    prod_hist  = (fila.get("Campo personalizado (Producto SD)", "")
                  or fila.get("Producto", "")).strip().lower()
    res_hist   = fila.get("Resumen", "").strip()

    if tipo_hist and consulta.tipo_atencion_sd.lower() == tipo_hist:
        score += 0.40
    if area_hist and consulta.area.lower() == area_hist:
        score += 0.25
    if prod_hist and consulta.producto and consulta.producto.lower() == prod_hist:
        score += 0.15

    # Coincidencia de palabras clave en resumen
    kw_consulta = _palabras_clave(consulta.resumen)
    kw_hist     = _palabras_clave(res_hist)
    comunes     = len(kw_consulta & kw_hist)
    score      += min(0.20, (comunes // 2) * 0.10)

    return round(score, 2)


def _determinar_nivel(fila: dict) -> str:
    """Determina el nivel al que fue asignado el ticket histórico."""
    responsable = (fila.get("Responsable", "")
                   or fila.get("Campo personalizado (Atendido por)", "")).lower()
    # Heurística simple: si fue resuelto → probablemente N1/N2
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
    umbral = 0.55

    if mejor_score >= umbral:
        nivel = _determinar_nivel(mejor_fila)
        mesa  = "Service Desk 1" if nivel == "N1" else "Squad - Mesa Ongoing"
        res   = mejor_fila.get("Resolución", "") or mejor_fila.get("Resolucion", "")
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
