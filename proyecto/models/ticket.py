"""
Modelos de datos para Tickets
Sistema Inteligente de Derivación Automática de Incidencias

Se alinean dos vistas principales:
- El payload que llega desde JIRA / dataset histórico (campos tipoIncidencia, tipoAtencionSD, etc.)
- El ticket de entrada desde la web (campos tipo_incidencia, resumen, etc.) que se mapea a esa vista.
"""

from datetime import datetime
from typing import Optional

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