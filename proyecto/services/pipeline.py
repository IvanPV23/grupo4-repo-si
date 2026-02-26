"""
Servicios de orquestación del pipeline de derivación.

Este módulo ejecuta el flujo completo:
    Histórico → (si no hay antecedente) Estimador → Complejidad → Orquestador

Está pensado para uso interno (tests, herramientas), mientras que
el pipeline "oficial" para producción se configura en n8n llamando
directamente a cada agente HTTP.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import httpx


def detectar_urgencia(resumen: str, descripcion: str) -> str:
    """
    Heurística simple de urgencia a partir de palabras clave en resumen/descripcion.
    Retorna "alta" o "media".
    """
    import re

    texto = (resumen + " " + descripcion).upper()
    palabras = [
        r"\bURGENTE\b",
        r"\bMUY URGENTE\b",
        r"\bCR[IÍ]TICO\b",
        r"\bCA[IÍ]DO\b",
        r"\bSIN SERVICIO\b",
        r"\bBLOQUEADO\b",
        r"\bNO FUNCIONA\b",
        r"\bEMERGENCIA\b",
    ]
    for patron in palabras:
        if re.search(patron, texto):
            return "alta"
    return "media"


async def ejecutar_pipeline(
    ticket: Dict[str, Any],
    ticket_id: str,
    urls: Dict[str, str],
) -> Dict[str, Any]:
    """
    Ejecuta el pipeline completo contra los agentes HTTP declarados en `urls`.

    - `ticket`: dict compatible con `TicketEntrada` / formulario web.
    - `ticket_id`: identificador interno generado para este pipeline.
    - `urls`: diccionario con las URLs base de agentes:
        {
          "historico":   "http://agente-historico:8004",
          "estimador":   "http://agente-estimador:8005",
          "complejidad": "http://agente-complejidad:8001",
          "orquestador": "http://agente-orquestador:8003",
        }
    """
    resumen = ticket.get("resumen", "") or ""
    desc_det = ticket.get("descripcion_detallada", "") or ""
    urgencia = detectar_urgencia(resumen, desc_det)

    # Resumen enriquecido (impacto al cierre / cantidad afectados)
    resumen_enriquecido = resumen
    if ticket.get("impacta_al_cierre"):
        resumen_enriquecido += " IMPACTA AL CIERRE"
    cant_afectados = ticket.get("cantidad_afectados") or 0
    if cant_afectados and cant_afectados > 10:
        resumen_enriquecido += f" {cant_afectados} usuarios afectados masivo"

    async with httpx.AsyncClient(timeout=12.0) as client:
        # 1. HISTÓRICO
        via_historico = False
        mesa_historico = None
        nivel_historico = None
        hist_razon = ""
        resolucion_ref = None

        try:
            r_hist = await client.post(
                f"{urls['historico']}/consultar",
                json={
                    "ticket_id": ticket_id,
                    "resumen": resumen_enriquecido,
                    "tipo_atencion_sd": ticket.get("tipo_atencion_sd", ""),
                    "area": ticket.get("area", ""),
                    "producto": ticket.get("producto", "") or "",
                },
            )
            h = r_hist.json()
            via_historico = h.get("encontrado", False)
            mesa_historico = h.get("mesa_sugerida")
            nivel_historico = h.get("nivel_sugerido")
            hist_razon = h.get("razonamiento", "")
            resolucion_ref = h.get("resolucion_referencia")
        except Exception as exc:  # pragma: no cover - errores remotos
            hist_razon = f"Histórico no disponible: {exc}"
            resolucion_ref = None

        # 2. ESTIMADOR
        tiempo_horas = None
        categoria_tpo = ""
        factores_est = []
        try:
            r_est = await client.post(
                f"{urls['estimador']}/estimar",
                json={
                    "ticket_id": ticket_id,
                    "tipo_incidencia": ticket.get("tipo_incidencia", ""),
                    "tipo_atencion_sd": ticket.get("tipo_atencion_sd", ""),
                    "area": ticket.get("area", ""),
                    "producto": ticket.get("producto", "") or "",
                    "resumen": resumen_enriquecido,
                    "urgencia_detectada": urgencia,
                },
            )
            e = r_est.json()
            tiempo_horas = e.get("tiempo_estimado_horas")
            categoria_tpo = e.get("categoria_tiempo", "")
            factores_est = e.get("factores_aplicados", [])
        except Exception as exc:  # pragma: no cover
            factores_est = [f"Estimador no disponible: {exc}"]

        # 3. COMPLEJIDAD
        complejidad = "media"
        score_comp = 50.0
        nivel_rec = "N1"
        recom_comp = ""
        try:
            r_comp = await client.post(
                f"{urls['complejidad']}/evaluar",
                json={
                    "ticket_id": ticket_id,
                    "tipo_incidencia": ticket.get("tipo_incidencia", ""),
                    "tipo_atencion_sd": ticket.get("tipo_atencion_sd", ""),
                    "resumen": resumen_enriquecido,
                    "area": ticket.get("area", ""),
                    "producto": ticket.get("producto", "") or "",
                    "urgencia_detectada": urgencia,
                    "tiempo_estimado_horas": tiempo_horas,
                },
            )
            c = r_comp.json()
            complejidad = c.get("complejidad", complejidad)
            score_comp = c.get("score", score_comp)
            nivel_rec = c.get("nivel_recomendado", nivel_rec)
            recom_comp = c.get("recomendacion", "")
        except Exception as exc:  # pragma: no cover
            recom_comp = f"Complejidad no disponible: {exc}"

        # 4. ORQUESTADOR
        try:
            r_orq = await client.post(
                f"{urls['orquestador']}/asignar",
                json={
                    "ticket_id": ticket_id,
                    "tipo_incidencia": ticket.get("tipo_incidencia", ""),
                    "tipo_atencion_sd": ticket.get("tipo_atencion_sd", ""),
                    "area": ticket.get("area", ""),
                    "producto": ticket.get("producto", "") or "",
                    "resumen": resumen_enriquecido,
                    "informador": ticket.get("informador", "") or "",
                    "urgencia_detectada": urgencia,
                    "tiempo_estimado_horas": tiempo_horas,
                    "categoria_tiempo": categoria_tpo,
                    "complejidad": complejidad,
                    "score_complejidad": score_comp,
                    "nivel_recomendado": nivel_rec,
                    "via_historico": via_historico,
                    "mesa_historico": mesa_historico,
                    "resolucion_referencia": resolucion_ref,
                },
            )
            o = r_orq.json()
        except Exception as exc:  # pragma: no cover
            # Fallback si orquestador no disponible
            o = {
                "mesa_asignada": "Service Desk 1",
                "nivel_asignado": "N1",
                "en_cola": False,
                "razonamiento": f"Orquestador no disponible: {exc}",
            }

    razonamiento = (
        f"Histórico: {hist_razon or 'sin antecedentes'} | "
        f"Estimado: {tiempo_horas}h ({categoria_tpo}) | "
        f"Complejidad: {complejidad} (score={score_comp}) | "
        f"{o.get('razonamiento', '')}"
    )

    return {
        "ticket_id": ticket_id,
        "mesa_asignada": o.get("mesa_asignada", "Service Desk 1"),
        "nivel_asignado": o.get("nivel_asignado", "N1"),
        "en_cola": o.get("en_cola", False),
        "complejidad": complejidad,
        "score_complejidad": score_comp,
        "tiempo_estimado_horas": tiempo_horas,
        "categoria_tiempo": categoria_tpo,
        "via_historico": via_historico,
        "razonamiento": razonamiento,
        "timestamp": datetime.now().isoformat(),
        # extras útiles para reportes / Jira
        "resumen": ticket.get("resumen", ""),
        "tipo_incidencia": ticket.get("tipo_incidencia", ""),
        "tipo_atencion_sd": ticket.get("tipo_atencion_sd", ""),
        "area": ticket.get("area", ""),
        "producto": ticket.get("producto", "") or "",
        "aplicativo": ticket.get("aplicativo", "") or "",
        "informador": ticket.get("informador", "") or "",
        "urgencia_detectada": urgencia,
    }

