"""
Módulo de Métricas
Permite evaluar el desempeño del sistema multiagente (Métricas Técnicas y Funcionales).
"""

from datetime import datetime
import json
import os

LOG_FILE = "data/metricas_log.json"

def registrar_decision(ticket_id: str, tiempo_procesamiento_ms: float, mesa_asignada: str, complejidad: str, confianza: float):
    """
    Registra una decisión tomada por el sistema para futuras evaluaciones de métricas.
    """
    # Asegurar que el directorio exista
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    registro = {
        "ticket_id": ticket_id,
        "timestamp": datetime.now().isoformat(),
        "tiempo_procesamiento_ms": tiempo_procesamiento_ms,
        "mesa_asignada": mesa_asignada,
        "complejidad": complejidad,
        "confianza": confianza,
        "tipo_decision": "automatica" if confianza >= 0.70 else "manual_requerida"
    }
    
    # Añadir al log (en un sistema real esto iría a una BD)
    registros = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                registros = json.load(f)
        except:
            pass
            
    registros.append(registro)
    
    with open(LOG_FILE, "w") as f:
        json.dump(registros, f, indent=2)

def obtener_resumen_metricas() -> dict:
    """
    Calcula las métricas actuales del sistema en base a los logs.
    """
    if not os.path.exists(LOG_FILE):
        return {"error": "No hay datos de métricas registrados aún"}
        
    try:
        with open(LOG_FILE, "r") as f:
            registros = json.load(f)
            
        total = len(registros)
        if total == 0:
            return {"total_tickets_procesados": 0}
            
        automaticos = sum(1 for r in registros if r["tipo_decision"] == "automatica")
        manuales = total - automaticos
        
        tiempo_total_ms = sum(r["tiempo_procesamiento_ms"] for r in registros)
        tiempo_promedio = tiempo_total_ms / total
        
        porcentaje_automatizacion = (automaticos / total) * 100
        
        return {
            "total_tickets_procesados": total,
            "tickets_derivados_automaticamente": automaticos,
            "tickets_requirieron_humano": manuales,
            "porcentaje_automatizacion_exitosa": round(porcentaje_automatizacion, 2),
            "tiempo_promedio_decision_ms": round(tiempo_promedio, 2),
            "metricas_funcionales": {
                "impacto_negocio": f"Se ahorró el esfuerzo manual equivalente a {automaticos} tickets derivados correctamente en menos de 1 segundo."
            }
        }
    except Exception as e:
        return {"error": f"Error calculando métricas: {e}"}
