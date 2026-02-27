"""
Modelos de datos para Tickets
Sistema Inteligente de Derivación Automática de Incidencias

Se alinean dos vistas principales:
- El payload que llega desde JIRA / dataset histórico (campos tipoIncidencia, tipoAtencionSD, etc.)
- El ticket de entrada desde la web (campos tipo_incidencia, resumen, etc.) que se mapea a esa vista.

Objeto unificado de pipeline: un mismo tipo de dato (ticket) circula desde el front,
se enriquece en Histórico → Estimador → Complejidad y llega al Orquestador con todos los campos.
"""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


class TicketJiraFeatures(BaseModel):
    """
    Representa el formato de ticket con el que se entrenó el modelo de ML
    y el que se extrae desde JIRA / dataset histórico.

    Este es el mismo esquema que consume el artefacto linear_regression.pkl:

        {
          "tipoIncidencia": "Incidente",
          "tipoAtencionSD": "ACTIVACIÓN DE BOT Y REPROCESO",
          "area": "Operaciones",
          "clasificacion": "Solicitud",
          "productoSD": "SCTR",
          "impactaCierre": "SI",
          "informador": "nportugal",
          "aplicativo": "Plataforma Digital -> PD - SCTR",
          "hora_creacion": 9,
          "dia_semana": 3,
          "mes_creacion": 8,
          "anio_creacion": 2025
        }
    """

    tipoIncidencia: str
    tipoAtencionSD: str
    area: str
    clasificacion: str
    productoSD: str
    impactaCierre: str
    informador: str
    aplicativo: str
    hora_creacion: int = Field(ge=0, le=23)
    dia_semana: int = Field(ge=0, le=6)  # lunes=0
    mes_creacion: int = Field(ge=1, le=12)
    anio_creacion: int = Field(ge=2000, le=2100)


class TicketWeb(BaseModel):
    """
    Ticket tal como llega desde el formulario web de reportes.
    Este modelo se usa en la API principal y puede mapearse a TicketJiraFeatures
    para alimentar al modelo histórico/ML.
    """

    # Campos del formulario actual
    tipo_incidencia: str                   # "Incidente" | "Solicitud"
    resumen: str                           # Descripción corta
    descripcion_detallada: Optional[str] = ""
    tipo_atencion_sd: str                  # "Error de servidor", "Consulta", etc.
    area: str                              # "Siniestros", "Comercial", etc.
    producto: Optional[str] = ""
    aplicativo: Optional[str] = ""
    informador: Optional[str] = ""
    impacta_al_cierre: Optional[bool] = False
    cantidad_afectados: Optional[int] = 1

    # Metadatos de tiempo opcionales (si vienen desde otra fuente, por ejemplo JIRA)
    hora_creacion: Optional[int] = Field(default=None, ge=0, le=23)
    dia_semana: Optional[int] = Field(default=None, ge=0, le=6)
    mes_creacion: Optional[int] = Field(default=None, ge=1, le=12)
    anio_creacion: Optional[int] = Field(default=None, ge=2000, le=2100)
    fecha_creacion: Optional[datetime] = None

    def to_jira_features(self) -> TicketJiraFeatures:
        """Mapea el ticket web al formato de features del modelo JIRA/ML."""
        now = datetime.now()
        dt = self.fecha_creacion or now

        hora = self.hora_creacion if self.hora_creacion is not None else dt.hour
        dia = self.dia_semana if self.dia_semana is not None else dt.weekday()
        mes = self.mes_creacion if self.mes_creacion is not None else dt.month
        anio = self.anio_creacion if self.anio_creacion is not None else dt.year

        return TicketJiraFeatures(
            tipoIncidencia=self.tipo_incidencia,
            tipoAtencionSD=self.tipo_atencion_sd,
            area=self.area,
            clasificacion="Solicitud" if self.tipo_incidencia.lower().startswith("solic") else "Incidente",
            productoSD=self.producto or "",
            impactaCierre="SI" if self.impacta_al_cierre else "NO",
            informador=self.informador or "",
            aplicativo=self.aplicativo or "",
            hora_creacion=int(hora),
            dia_semana=int(dia),
            mes_creacion=int(mes),
            anio_creacion=int(anio),
        )


class TicketPipeline(BaseModel):
    """
    Ticket unificado que circula por el pipeline (n8n y agentes).
    Base (desde front) + campos que van llenando Histórico, Estimador, Complejidad, Orquestador.
    """
    ticket_id: str = ""
    tipo_incidencia: str = ""
    resumen: str = ""
    descripcion_detallada: Optional[str] = ""
    tipo_atencion_sd: str = ""
    area: str = ""
    producto: Optional[str] = ""
    aplicativo: Optional[str] = ""
    informador: Optional[str] = ""
    impacta_al_cierre: Optional[bool] = False
    cantidad_afectados: Optional[int] = 1
    urgencia_detectada: str = "media"
    via_historico: bool = False
    mesa_historico: Optional[str] = None
    resolucion_referencia: Optional[str] = None
    tiempo_estimado_horas: Optional[float] = None
    categoria_tiempo: Optional[str] = ""
    complejidad: str = "media"
    score_complejidad: float = 50.0
    nivel_recomendado: str = "N1"
    mesa_asignada: Optional[str] = None
    nivel_asignado: Optional[str] = None
    en_cola: Optional[bool] = None
    razonamiento: Optional[str] = None

    def to_orquestador_payload(self) -> dict[str, Any]:
        """Payload para POST /asignar."""
        return {
            "ticket_id": self.ticket_id,
            "tipo_incidencia": self.tipo_incidencia,
            "tipo_atencion_sd": self.tipo_atencion_sd,
            "area": self.area,
            "producto": self.producto or "",
            "resumen": self.resumen,
            "informador": self.informador or "",
            "urgencia_detectada": self.urgencia_detectada,
            "tiempo_estimado_horas": self.tiempo_estimado_horas,
            "categoria_tiempo": self.categoria_tiempo or "",
            "complejidad": self.complejidad,
            "score_complejidad": self.score_complejidad,
            "nivel_recomendado": self.nivel_recomendado,
            "via_historico": self.via_historico,
            "mesa_historico": self.mesa_historico,
            "resolucion_referencia": self.resolucion_referencia,
        }