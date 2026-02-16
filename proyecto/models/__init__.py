"""
Modelos de datos del sistema
"""

from .ticket import (
    Ticket,
    TipoTicket,
    TipoError,
    EstadoTicket,
    Area,
    MesaSoporte,
    Complejidad,
    Prioridad
)

__all__ = [
    'Ticket',
    'TipoTicket',
    'TipoError',
    'EstadoTicket',
    'Area',
    'MesaSoporte',
    'Complejidad',
    'Prioridad'
]