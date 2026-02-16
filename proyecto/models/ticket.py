"""
Modelo de datos para Tickets de JIRA
Sistema Inteligente de Derivación Automática de Incidencias
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class TipoTicket(Enum):
    """Tipos de ticket disponibles"""
    INCIDENCIA = "incidencia"
    SOLICITUD = "solicitud"


class TipoError(Enum):
    """Categorías de errores/problemas"""
    REDES = "redes"
    SOFTWARE = "software"
    HARDWARE = "hardware"
    INFRAESTRUCTURA = "infraestructura"
    ACCESO = "acceso"
    CONFIGURACION = "configuracion"
    OTRO = "otro"


class EstadoTicket(Enum):
    """Estados posibles del ticket"""
    ABIERTO = "abierto"
    EN_PROCESO = "en_proceso"
    EN_ESPERA_APROBACION = "en_espera_aprobacion"
    CERRADO = "cerrado"
    CANCELADO = "cancelado"


class Area(Enum):
    """Áreas de la organización"""
    OPERACIONES = "operaciones"
    COBRANZAS = "cobranzas"
    FINANZAS = "finanzas"
    RRHH = "rrhh"
    COMERCIAL = "comercial"
    TECNOLOGIA = "tecnologia"


class MesaSoporte(Enum):
    """Mesas de soporte disponibles"""
    MESA_N1 = "mesa_n1"  # Nivel 1 - Soporte básico
    MESA_N2 = "mesa_n2"  # Nivel 2 - Soporte avanzado
    MESA_ESPECIALISTA = "mesa_especialista"  # Especialistas
    MESA_INFRAESTRUCTURA = "mesa_infraestructura"  # Infraestructura
    NO_ASIGNADO = "no_asignado"


class Complejidad(Enum):
    """Nivel de complejidad del ticket"""
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class Prioridad(Enum):
    """Prioridad del ticket"""
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


@dataclass
class Ticket:
    """
    Clase principal que representa un Ticket de JIRA
    
    Atributos:
        ticket_id: Identificador único del ticket (ej: JIRA-1234)
        tipo_ticket: Tipo de ticket (incidencia o solicitud)
        tipo_error: Categoría del problema
        solicitante: Nombre del usuario que reporta
        area: Área organizacional del solicitante
        mesa_asignada: Mesa de soporte asignada actualmente
        estado: Estado actual del ticket
        titulo: Título descriptivo del ticket
        descripcion: Descripción detallada del problema
        complejidad: Nivel de complejidad estimado
        prioridad: Prioridad del ticket
        fecha_creacion: Timestamp de creación
        fecha_actualizacion: Última actualización
        tiempo_estimado_resolucion: Horas estimadas para resolver
        comentarios: Lista de comentarios adicionales
    """
    
    # Campos obligatorios
    ticket_id: str
    tipo_ticket: TipoTicket
    tipo_error: TipoError
    solicitante: str
    area: Area
    titulo: str
    descripcion: str
    
    # Campos con valores por defecto
    mesa_asignada: MesaSoporte = MesaSoporte.NO_ASIGNADO
    estado: EstadoTicket = EstadoTicket.ABIERTO
    complejidad: Optional[Complejidad] = None
    prioridad: Prioridad = Prioridad.MEDIA
    fecha_creacion: datetime = None
    fecha_actualizacion: datetime = None
    tiempo_estimado_resolucion: Optional[float] = None
    comentarios: list = None
    
    def __post_init__(self):
        """Inicialización posterior a la creación del objeto"""
        if self.fecha_creacion is None:
            self.fecha_creacion = datetime.now()
        if self.fecha_actualizacion is None:
            self.fecha_actualizacion = datetime.now()
        if self.comentarios is None:
            self.comentarios = []
    
    def to_dict(self) -> dict:
        """Convierte el ticket a diccionario para JSON/CSV"""
        return {
            'ticket_id': self.ticket_id,
            'tipo_ticket': self.tipo_ticket.value,
            'tipo_error': self.tipo_error.value,
            'solicitante': self.solicitante,
            'area': self.area.value,
            'mesa_asignada': self.mesa_asignada.value,
            'estado': self.estado.value,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'complejidad': self.complejidad.value if self.complejidad else None,
            'prioridad': self.prioridad.value,
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'fecha_actualizacion': self.fecha_actualizacion.isoformat(),
            'tiempo_estimado_resolucion': self.tiempo_estimado_resolucion,
            'comentarios': self.comentarios
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Ticket':
        """Crea un ticket desde un diccionario"""
        return cls(
            ticket_id=data['ticket_id'],
            tipo_ticket=TipoTicket(data['tipo_ticket']),
            tipo_error=TipoError(data['tipo_error']),
            solicitante=data['solicitante'],
            area=Area(data['area']),
            mesa_asignada=MesaSoporte(data.get('mesa_asignada', 'no_asignado')),
            estado=EstadoTicket(data.get('estado', 'abierto')),
            titulo=data['titulo'],
            descripcion=data['descripcion'],
            complejidad=Complejidad(data['complejidad']) if data.get('complejidad') else None,
            prioridad=Prioridad(data.get('prioridad', 'media')),
            tiempo_estimado_resolucion=data.get('tiempo_estimado_resolucion'),
            comentarios=data.get('comentarios', [])
        )
    
    def actualizar_estado(self, nuevo_estado: EstadoTicket, comentario: str = ""):
        """Actualiza el estado del ticket"""
        self.estado = nuevo_estado
        self.fecha_actualizacion = datetime.now()
        if comentario:
            self.comentarios.append({
                'timestamp': datetime.now().isoformat(),
                'accion': f'Estado cambiado a {nuevo_estado.value}',
                'comentario': comentario
            })
    
    def asignar_mesa(self, mesa: MesaSoporte, comentario: str = ""):
        """Asigna el ticket a una mesa específica"""
        self.mesa_asignada = mesa
        self.fecha_actualizacion = datetime.now()
        if comentario:
            self.comentarios.append({
                'timestamp': datetime.now().isoformat(),
                'accion': f'Ticket asignado a {mesa.value}',
                'comentario': comentario
            })
    
    def evaluar_complejidad(self, complejidad: Complejidad, comentario: str = ""):
        """Evalúa y asigna la complejidad del ticket"""
        self.complejidad = complejidad
        self.fecha_actualizacion = datetime.now()
        if comentario:
            self.comentarios.append({
                'timestamp': datetime.now().isoformat(),
                'accion': f'Complejidad evaluada como {complejidad.value}',
                'comentario': comentario
            })
    
    def __str__(self) -> str:
        """Representación en texto del ticket"""
        return (f"Ticket {self.ticket_id} - {self.titulo}\n"
                f"Tipo: {self.tipo_ticket.value} | Error: {self.tipo_error.value}\n"
                f"Solicitante: {self.solicitante} ({self.area.value})\n"
                f"Mesa: {self.mesa_asignada.value} | Estado: {self.estado.value}\n"
                f"Prioridad: {self.prioridad.value} | Complejidad: {self.complejidad.value if self.complejidad else 'No evaluada'}")