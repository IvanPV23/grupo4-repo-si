"""
Agente DASHBOARD — Puerto 8006
Expone endpoints con datos de gráficos calculados desde:
  - data/outputs/reporte_acumulativo.xlsx  (derivaciones acumuladas)
  - data/historico.db                      (tickets resueltos en SQLite)
  - MLflow runs vía MLFLOW_TRACKING_URI    (métricas de inferencia)

Los datos se retornan como JSON puro; el frontend los renderiza con Chart.js.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pathlib import Path
from collections import Counter
import os
import sqlite3
import logging

logger = logging.getLogger("dashboard")

app = FastAPI(
    title="Agente Dashboard",
    description="Datos de gráficos desde SQLite, Excel y MLflow",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rutas de datos ──────────────────────────────────────────────────────────
_BASE = Path(__file__).resolve().parents[2]
RUTA_EXCEL = _BASE / "data" / "outputs" / "reporte_acumulativo.xlsx"
RUTA_DB    = _BASE / "data" / "historico.db"
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://agente-mlflow:5000")


# ── Helpers ────────────────────────────────────────────────────────────────

def _leer_excel() -> list[dict]:
    """Lee el Excel acumulativo y retorna lista de dicts. Vacío si no existe."""
    if not RUTA_EXCEL.exists():
        return []
    try:
        import openpyxl
        wb = openpyxl.load_workbook(RUTA_EXCEL, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(rows[0])]
        return [dict(zip(headers, row)) for row in rows[1:]]
    except Exception as e:
        logger.warning(f"No se pudo leer Excel: {e}")
        return []


def _leer_historico_db() -> list[dict]:
    """Lee todos los tickets resueltos del SQLite histórico."""
    if not RUTA_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(RUTA_DB))
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM tickets_resueltos")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"No se pudo leer SQLite: {e}")
        return []


def _mlflow_ultimas_inferencias(n: int = 50) -> list[dict]:
    """
    Obtiene los últimos N runs del experimento de inferencias desde MLflow.
    Retorna lista de dicts con tiempo_estimado_horas y latencia_ms.
    Retorna [] si MLflow no está disponible.
    """
    try:
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_URI)
        client = mlflow.tracking.MlflowClient()
        experiments = client.search_experiments(filter_string="name = 'estimador-inferencias'")
        if not experiments:
            return []
        exp_id = experiments[0].experiment_id
        runs = client.search_runs(
            experiment_ids=[exp_id],
            max_results=n,
            order_by=["start_time DESC"],
        )
        result = []
        for r in runs:
            metrics = r.data.metrics
            result.append({
                "tiempo_estimado_horas": metrics.get("tiempo_estimado_horas"),
                "latencia_ms":           metrics.get("latencia_ms"),
                "run_id":                r.info.run_id,
                "start_time":            r.info.start_time,
            })
        return result
    except Exception as e:
        logger.warning(f"MLflow no disponible: {e}")
        return []


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent": "Dashboard",
        "timestamp": datetime.now().isoformat(),
        "excel_existe": RUTA_EXCEL.exists(),
        "db_existe":    RUTA_DB.exists(),
        "mlflow_uri":   MLFLOW_URI,
    }


@app.get("/charts/resumen")
async def resumen():
    """Estadísticas generales: total tickets, automatización %, distribución complejidad."""
    filas = _leer_excel()
    total = len(filas)
    if total == 0:
        return {"total": 0, "automatizados": 0, "en_cola": 0, "via_historico": 0}

    automatizados = sum(
        1 for f in filas
        if str(f.get("resultado", "")).upper() == "DERIVADO_AUTOMATICAMENTE"
    )
    en_cola = sum(1 for f in filas if str(f.get("resultado", "")).upper() == "EN_COLA")
    via_historico = sum(1 for f in filas if str(f.get("via_historico", "")).upper() == "TRUE")

    return {
        "total":           total,
        "automatizados":   automatizados,
        "en_cola":         en_cola,
        "via_historico":   via_historico,
        "pct_automatizado": round(automatizados / total * 100, 1) if total else 0,
    }


@app.get("/charts/mesas")
async def distribucion_mesas():
    """
    Distribución de tickets por mesa asignada.
    Retorna formato Chart.js: {labels: [...], data: [...]}.
    """
    filas = _leer_excel()
    conteo = Counter(
        str(f.get("mesa_asignada", "Desconocida")) for f in filas if f.get("mesa_asignada")
    )
    labels = list(conteo.keys())
    data   = list(conteo.values())
    return {"labels": labels, "data": data, "total": len(filas)}


@app.get("/charts/complejidad")
async def distribucion_complejidad():
    """
    Distribución de tickets por nivel de complejidad.
    Retorna formato Chart.js: {labels: [...], data: [...]}.
    """
    filas = _leer_excel()
    conteo = Counter(
        str(f.get("complejidad", "desconocida")).lower() for f in filas if f.get("complejidad")
    )
    # Orden canónico
    orden = ["baja", "media", "alta", "muy_alta"]
    labels = [c for c in orden if c in conteo] + [c for c in conteo if c not in orden]
    data   = [conteo[l] for l in labels]
    return {"labels": labels, "data": data, "total": len(filas)}


@app.get("/charts/tiempo")
async def distribucion_tiempo():
    """
    Distribución de tickets por categoría de tiempo estimado.
    También incluye los últimos N puntos de latencia desde MLflow.
    """
    filas = _leer_excel()
    conteo_cat = Counter(
        str(f.get("categoria_tiempo", "sin_datos")).lower()
        for f in filas if f.get("categoria_tiempo")
    )
    orden = ["rapido", "normal", "lento", "muy_lento"]
    labels = [c for c in orden if c in conteo_cat] + [c for c in conteo_cat if c not in orden]
    data   = [conteo_cat[l] for l in labels]

    # Promedio de tiempo estimado desde Excel
    tiempos = [
        float(f["tiempo_estimado_horas"])
        for f in filas
        if f.get("tiempo_estimado_horas") is not None
        and str(f["tiempo_estimado_horas"]).replace(".", "", 1).isdigit()
    ]
    promedio_horas = round(sum(tiempos) / len(tiempos), 2) if tiempos else None

    # Latencias desde MLflow
    mlflow_runs = _mlflow_ultimas_inferencias(50)
    latencias = [r["latencia_ms"] for r in mlflow_runs if r.get("latencia_ms") is not None]
    promedio_latencia_ms = round(sum(latencias) / len(latencias), 1) if latencias else None

    return {
        "labels":               labels,
        "data":                 data,
        "total":                len(filas),
        "promedio_horas":       promedio_horas,
        "promedio_latencia_ms": promedio_latencia_ms,
        "mlflow_runs_analizados": len(mlflow_runs),
    }


@app.get("/charts/niveles")
async def distribucion_niveles():
    """Distribución de tickets por nivel asignado (N1, N2, N3)."""
    filas = _leer_excel()
    conteo = Counter(
        str(f.get("nivel_asignado", "Desconocido")) for f in filas if f.get("nivel_asignado")
    )
    orden = ["N1", "N2", "N3"]
    labels = [n for n in orden if n in conteo] + [n for n in conteo if n not in orden]
    data   = [conteo[l] for l in labels]
    return {"labels": labels, "data": data, "total": len(filas)}


@app.get("/charts/mlflow-inferencias")
async def mlflow_inferencias():
    """
    Últimas 50 inferencias desde MLflow: tiempo estimado y latencia.
    Útil para ver drift o degradación del modelo.
    """
    runs = _mlflow_ultimas_inferencias(50)
    return {
        "runs":  runs,
        "total": len(runs),
        "mlflow_uri": MLFLOW_URI,
    }


@app.get("/charts/historico-db")
async def historico_db():
    """Resumen del historial SQLite: total tickets resueltos, distribución por área."""
    tickets = _leer_historico_db()
    total = len(tickets)
    areas = Counter(t.get("area", "Desconocida") for t in tickets)
    return {
        "total":          total,
        "areas":          dict(areas.most_common(10)),
        "campos_ejemplo": list(tickets[0].keys()) if tickets else [],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=True)
