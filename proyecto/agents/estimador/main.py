"""
Agente ESTIMADOR — Puerto 8005
Estima el tiempo de resolución de un ticket (en horas)
usando exclusivamente un modelo de ML entrenado (LightGBM, modelo.pkl).
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import cloudpickle
import time

import html
import re
import unicodedata
import numpy as np
import ftfy
import scipy.sparse as sp
import pandas as pd

def _limpiar_resumen(texto: str) -> str:
    """Limpieza de texto para TF-IDF. Réplica exacta de la función del notebook."""
    if not texto or not str(texto).strip():
        return ""
    try:
        texto = ftfy.fix_text(str(texto))
    except Exception:
        texto = str(texto)
    texto = html.unescape(texto)
    texto = texto.lower()
    texto = re.sub(r"\b\d+[_/\-]\d+\b", "", texto)
    texto = re.sub(r"\b\d+\b", "", texto)
    texto = re.sub(r"[\/\\:;\-><\=\+#@!?\.,\(\)\[\]\{\}\"'*&%$~`|_]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()

app = FastAPI(
    title="Agente Estimador",
    description="Estima tiempo de resolución de tickets en horas",
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

class ConsultaEstimador(BaseModel):
    ticket_id: str

    # --- Payload "legacy" (snake_case) ---
    tipo_incidencia: Optional[str] = None          # "Incidente" | "Solicitud"
    tipo_atencion_sd: Optional[str] = None
    area: Optional[str] = ""
    producto: Optional[str] = ""
    resumen: Optional[str] = ""

    # --- Payload del modelo entrenado (camelCase) ---
    tipoIncidencia: Optional[str] = Field(default=None)
    tipoAtencionSD: Optional[str] = Field(default=None)
    clasificacion: Optional[str] = Field(default=None)
    productoSD: Optional[str] = Field(default=None)
    impactaCierre: Optional[str] = Field(default=None)
    informador: Optional[str] = Field(default=None)
    aplicativo: Optional[str] = Field(default=None)

    def to_ml_features(self) -> dict[str, Any]:
        """
        Normaliza el request al esquema esperado por el modelo entrenado (v4).
        Acepta campos camelCase y snake_case; el modelo espera los nombres EXACTOS del training.
        """
        return {
            "tipoIncidencia": self.tipoIncidencia or (self.tipo_incidencia or ""),
            "tipoAtencionSD": self.tipoAtencionSD or (self.tipo_atencion_sd or ""),
            "area": self.area or "",
            "clasificacion": self.clasificacion or "",
            "productoSD": self.productoSD or (self.producto or ""),
            "impactaCierre": self.impactaCierre or "",
            "informador": self.informador or "",
            "aplicativo": self.aplicativo or "",
            "resumen": self.resumen or "",
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
    features_cat = artefact.get("features_cat") or []
    features_num = artefact.get("features_num") or []
    dummy_columns = artefact.get("dummy_columns") or []
    features_cyclic_raw = artefact.get("features_cyclic_raw") or {}
    tfidf_vectorizer = artefact.get("tfidf_vectorizer")
    target_max_h = float(artefact.get("target_max_h", 720))
    model_name = artefact.get("model_name", "modelo.pkl")

    # Inverse transform: prefer callable stored in artefact; fall back to string lookup
    target_inverse_fn = artefact.get("target_inverse_fn")
    if target_inverse_fn is None:
        _t = artefact.get("target_transform", "log1p")
        _inv_map = {
            "log1p":      lambda z: np.maximum(np.expm1(z), 0.0),
            "sqrt":       np.square,
            "log1p_sqrt": lambda z: np.square(np.maximum(np.expm1(z), 0.0)),
            "log":        np.exp,
        }
        target_inverse_fn = _inv_map.get(_t)

    def predict(payload: Any):
        if isinstance(payload, dict):
            df = pd.DataFrame([payload])
            single = True
        elif isinstance(payload, pd.DataFrame):
            df = payload.copy()
            single = False
        else:
            raise TypeError("payload debe ser dict o pandas.DataFrame")

        # 1. ftfy encoding fix + NFC normalization on categorical text fields
        # NFC ensures tildes/accents match training data (e.g. 'ACTIVACIÓN' == 'ACTIVACIÓN')
        _ftfy_cols = ["tipoAtencionSD", "tipoIncidencia", "area",
                      "clasificacion", "productoSD", "aplicativo", "impactaCierre"]
        for col in _ftfy_cols:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: unicodedata.normalize("NFC", ftfy.fix_text(str(x)))
                    if pd.notna(x) and str(x).strip() else (x if pd.notna(x) else "")
                )

        # 2. Cyclic sin/cos encoding from raw temporal features
        for feat, period in features_cyclic_raw.items():
            if feat in df.columns:
                vals = pd.to_numeric(df[feat], errors="coerce").fillna(0)
                df[f"{feat}_sin"] = np.sin(2 * np.pi * vals / period)
                df[f"{feat}_cos"] = np.cos(2 * np.pi * vals / period)
            else:
                df[f"{feat}_sin"] = 0.0
                df[f"{feat}_cos"] = 1.0

        # 3. Categorical dummies
        X_cat_in = pd.get_dummies(
            df.reindex(columns=features_cat, fill_value=""), dtype=int
        )

        # 4. Numerical features (cyclic sin/cos + anio_creacion)
        X_num_in = (
            df.reindex(columns=features_num, fill_value=0)
            .apply(pd.to_numeric, errors="coerce")
            .fillna(0.0)
        )

        # 5. TF-IDF on resumen
        if tfidf_vectorizer is not None:
            if "resumen" in df.columns:
                textos = df["resumen"].fillna("").astype(str)
            else:
                textos = pd.Series([""] * len(df), index=df.index)
            textos_limpios = [_limpiar_resumen(t) for t in textos]
            X_tfidf_in = tfidf_vectorizer.transform(textos_limpios)
            tfidf_cols = [f"tfidf_{w}" for w in tfidf_vectorizer.get_feature_names_out()]
        else:
            n_tfidf = sum(1 for c in (dummy_columns or []) if c.startswith("tfidf_"))
            X_tfidf_in = sp.csr_matrix((len(df), n_tfidf))
            tfidf_cols = [c for c in (dummy_columns or []) if c.startswith("tfidf_")]

        # 6. Assemble sparse matrix and align to training column order
        X_sp_in = sp.hstack([
            sp.csr_matrix(X_cat_in.values),
            sp.csr_matrix(X_num_in.values),
            X_tfidf_in,
        ])
        in_cols = list(X_cat_in.columns) + list(X_num_in.columns) + tfidf_cols
        X_final = (
            pd.DataFrame(X_sp_in.toarray(), columns=in_cols)
            .reindex(columns=dummy_columns, fill_value=0)
            .astype(np.float32)
            .values
        )

        # 7. Predict → inverse transform → clip
        y = pipeline.predict(X_final)
        if target_inverse_fn is not None:
            y = target_inverse_fn(y)
        y = np.clip(y, 0.25, target_max_h)

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


@app.post("/estimar", response_model=RespuestaEstimador)
async def estimar(consulta: ConsultaEstimador):
    """Estima el tiempo de resolución del ticket en horas (LightGBM, modelo.pkl)."""
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
