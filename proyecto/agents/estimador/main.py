"""
Agente ESTIMADOR — Puerto 8005
Estima el tiempo de resolución de un ticket (en horas)
usando exclusivamente un modelo de ML entrenado (linear_regression.pkl).
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from io import BytesIO
import cloudpickle
import sys
import time
import os
import logging

import pandas as pd

logger = logging.getLogger("estimador")

# ── MLflow tracking (no-op si el servidor no está disponible) ───────────────
_MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "")
_MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT_NAME", "estimador-inferencias")
_mlflow_ready = False

def _init_mlflow():
    """Inicializa MLflow una sola vez al arrancar el servicio."""
    global _mlflow_ready
    if not _MLFLOW_URI:
        return
    try:
        import mlflow
        mlflow.set_tracking_uri(_MLFLOW_URI)
        mlflow.set_experiment(_MLFLOW_EXPERIMENT)
        _mlflow_ready = True
        logger.info(f"[MLflow] Conectado a {_MLFLOW_URI}, experimento '{_MLFLOW_EXPERIMENT}'")
    except Exception as e:
        logger.warning(f"[MLflow] No disponible al arrancar ({e}). El tracking se omitirá.")

app = FastAPI(
    title="Agente Estimador",
    description="Estima tiempo de resolución de tickets en horas",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    _init_mlflow()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# Modelos
# =====================================================

class ConsultaEstimador(BaseModel):
    ticket_id: str

    # --- Payload "legacy" (reglas) ---
    tipo_incidencia: Optional[str] = None          # "Incidente" | "Solicitud"
    tipo_atencion_sd: Optional[str] = None
    area: Optional[str] = ""
    producto: Optional[str] = ""
    resumen: Optional[str] = ""
    urgencia_detectada: Optional[str] = "media"   # "alta" | "media"

    # --- Payload del modelo entrenado (según el ejemplo del usuario) ---
    tipoIncidencia: Optional[str] = Field(default=None)
    tipoAtencionSD: Optional[str] = Field(default=None)
    clasificacion: Optional[str] = Field(default=None)
    productoSD: Optional[str] = Field(default=None)
    impactaCierre: Optional[str] = Field(default=None)
    informador: Optional[str] = Field(default=None)
    aplicativo: Optional[str] = Field(default=None)
    hora_creacion: Optional[int] = Field(default=None, ge=0, le=23)
    dia_semana: Optional[int] = Field(default=None, ge=0, le=6)  # lunes=0 ... domingo=6
    mes_creacion: Optional[int] = Field(default=None, ge=1, le=12)
    anio_creacion: Optional[int] = Field(default=None, ge=2000, le=2100)
    fecha_creacion: Optional[datetime] = Field(default=None)

    def to_ml_features(self) -> dict[str, Any]:
        """
        Normaliza el request al esquema esperado por el modelo entrenado.

        - Acepta campos camelCase (ejemplo) y completa campos temporales si faltan.
        - El modelo espera los nombres EXACTOS de columnas del training.
        """
        now = datetime.now()
        dt = self.fecha_creacion or now

        hora_creacion = self.hora_creacion if self.hora_creacion is not None else dt.hour
        dia_semana = self.dia_semana if self.dia_semana is not None else dt.weekday()  # lunes=0
        mes_creacion = self.mes_creacion if self.mes_creacion is not None else dt.month
        anio_creacion = self.anio_creacion if self.anio_creacion is not None else dt.year

        return {
            "tipoIncidencia": self.tipoIncidencia or (self.tipo_incidencia or ""),
            "tipoAtencionSD": self.tipoAtencionSD or (self.tipo_atencion_sd or ""),
            "area": self.area or "",
            "clasificacion": self.clasificacion or "",
            "productoSD": self.productoSD or (self.producto or ""),
            "impactaCierre": self.impactaCierre or "",
            "informador": self.informador or "",
            "aplicativo": self.aplicativo or "",
            "hora_creacion": int(hora_creacion),
            "dia_semana": int(dia_semana),
            "mes_creacion": int(mes_creacion),
            "anio_creacion": int(anio_creacion),
        }

class RespuestaEstimador(BaseModel):
    ticket_id: str
    tiempo_estimado_horas: float
    rango_minimo_horas: float
    rango_maximo_horas: float
    categoria_tiempo: str         # "rapido" | "normal" | "lento" | "muy_lento"
    factores_aplicados: list
    timestamp: str

# =====================================================
# Carga de modelo (pickle) + predicción
# =====================================================

def _model_path() -> Path:
    # .../proyecto/agents/estimador/main.py -> .../proyecto/models/modelo.pkl
    return Path(__file__).resolve().parents[2] / "models" / "modelo.pkl"



@lru_cache(maxsize=1)
def _load_artefact() -> dict[str, Any]:
    path = _model_path()
    if not path.exists():
        raise FileNotFoundError(f"No existe el modelo: {path}")

    artefact = cloudpickle.loads(path.read_bytes())
    if not isinstance(artefact, dict) or "pipeline" not in artefact:
        raise ValueError("Artefacto inválido: se esperaba dict con key 'pipeline'.")

    pipeline = artefact["pipeline"]
    target_inverse_fn = artefact.get("target_inverse_fn")
    features_cat = artefact.get("features_cat") or []
    features_num = artefact.get("features_num") or []
    features_all = artefact.get("features_all") or []
    dummy_columns = artefact.get("dummy_columns") or []
    model_name = artefact.get("model_name", "linear_regression.pkl")

    def predict(payload: Any):
        if isinstance(payload, dict):
            df = pd.DataFrame([payload])
            single = True
        elif isinstance(payload, pd.DataFrame):
            df = payload
            single = False
        else:
            raise TypeError("payload debe ser dict o pandas.DataFrame")

        # El pipeline del artefacto contiene solo el modelo; el encoding se hace aquí
        # usando las columnas dummy del entrenamiento.
        if features_all:
            for col in features_all:
                if col not in df.columns:
                    df[col] = "" if col in features_cat else 0
            df = df[features_all]

        if features_cat:
            df_cat = df[features_cat].fillna("").astype(str)
        else:
            df_cat = pd.DataFrame(index=df.index)

        if features_num:
            df_num = df[features_num].apply(pd.to_numeric, errors="coerce").fillna(0)
        else:
            df_num = pd.DataFrame(index=df.index)

        df_base = pd.concat([df_cat, df_num], axis=1)
        X = pd.get_dummies(df_base, columns=features_cat) if features_cat else df_base
        if dummy_columns:
            X = X.reindex(columns=dummy_columns, fill_value=0)

        y = pipeline.predict(X)
        if target_inverse_fn is not None:
            y = target_inverse_fn(y)

        if single:
            return float(y[0])
        return [float(v) for v in y]

    artefact["predict"] = predict
    artefact["model_name"] = model_name
    return artefact


def _categoria_tiempo(horas: float) -> str:
    if horas < 24:
        return "rapido"
    if horas < 72:
        return "normal"
    if horas < 168:
        return "lento"
    return "muy_lento"

# =====================================================
# Endpoints
# =====================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "Estimador", "timestamp": datetime.now().isoformat()}


def _log_mlflow_inferencia(
    ticket_id: str,
    features: dict,
    horas_final: float,
    categoria: str,
    latencia_ms: float,
    model_name: str,
):
    """
    Registra un run de inferencia en MLflow.
    Se llama de forma best-effort: si falla, no interrumpe la respuesta.
    """
    if not _mlflow_ready:
        return
    try:
        import mlflow
        with mlflow.start_run(run_name=f"inf-{ticket_id}"):
            # Params: features de entrada (strings y números)
            mlflow.log_params({
                "tipoIncidencia": str(features.get("tipoIncidencia", ""))[:250],
                "tipoAtencionSD": str(features.get("tipoAtencionSD", ""))[:250],
                "area":           str(features.get("area", ""))[:250],
                "productoSD":     str(features.get("productoSD", ""))[:250],
                "hora_creacion":  features.get("hora_creacion", 0),
                "dia_semana":     features.get("dia_semana", 0),
                "mes_creacion":   features.get("mes_creacion", 1),
            })
            # Métricas: predicción + latencia
            mlflow.log_metrics({
                "tiempo_estimado_horas": horas_final,
                "latencia_ms":           round(latencia_ms, 2),
            })
            # Tags: contexto del run
            mlflow.set_tags({
                "ticket_id":     ticket_id,
                "categoria":     categoria,
                "model_version": model_name,
                "servicio":      "agente-estimador",
            })
    except Exception as e:
        logger.warning(f"[MLflow] Error al loguear inferencia {ticket_id}: {e}")


@app.post("/estimar", response_model=RespuestaEstimador)
async def estimar(consulta: ConsultaEstimador):
    """
    Estima el tiempo de resolución del ticket en horas.
    Basado exclusivamente en el modelo de ML entrenado (linear_regression.pkl).
    Cada inferencia queda trackeada en MLflow (si el servidor está disponible).
    """
    t0 = time.perf_counter()
    try:
        artefact = _load_artefact()
        features = consulta.to_ml_features()
        pred_horas = float(artefact["predict"](features))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo estimar con el modelo de ML: {e}",
        )
    latencia_ms = (time.perf_counter() - t0) * 1000

    horas_final = round(pred_horas, 2)
    rango_min = round(horas_final * 0.75, 2)
    rango_max = round(horas_final * 1.25, 2)
    categoria = _categoria_tiempo(horas_final)
    model_name = artefact.get("model_name", "modelo.pkl")

    # Tracking MLflow (best-effort, no bloquea la respuesta)
    _log_mlflow_inferencia(
        ticket_id=consulta.ticket_id,
        features=features,
        horas_final=horas_final,
        categoria=categoria,
        latencia_ms=latencia_ms,
        model_name=model_name,
    )

    resultado = {
        "tiempo_estimado_horas": horas_final,
        "rango_minimo_horas": rango_min,
        "rango_maximo_horas": rango_max,
        "categoria_tiempo": categoria,
        "factores_aplicados": [
            f"ML: {model_name}",
            f"latencia: {round(latencia_ms, 1)}ms",
        ],
    }

    return RespuestaEstimador(
        ticket_id=consulta.ticket_id,
        **resultado,
        timestamp=datetime.now().isoformat()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
