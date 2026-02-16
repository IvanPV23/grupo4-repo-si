# Directorio de Datos

## Estructura

```
data/
├── raw/                    # Datos originales sin procesar
│   ├── tickets.csv         # Dataset principal de tickets (a crear por Mellany)
│   ├── tickets_ejemplo.csv # Ejemplo de estructura
│   └── equipos.csv         # Capacidad de equipos (opcional)
├── processed/              # Datos procesados/transformados
│   └── tickets_con_decision.csv
└── logs/                   # Logs del sistema
    ├── api.log
    ├── agentes.log
    └── derivaciones.log
```

## Descripción de Archivos

### tickets.csv
Dataset principal con 100-200 tickets simulados.

**Columnas requeridas:**
- `ticket_id`: Identificador único (ej: JIRA-001)
- `tipo_ticket`: incidencia | solicitud
- `tipo_error`: redes | software | hardware | infraestructura | acceso | configuracion
- `area`: operaciones | cobranzas | finanzas | rrhh | comercial | tecnologia
- `solicitante`: Nombre del usuario
- `titulo`: Título corto del ticket
- `descripcion`: Descripción detallada
- `prioridad`: baja | media | alta | urgente
- `complejidad_real`: baja | media | alta | critica (ground truth)
- `mesa_correcta`: mesa_n1 | mesa_n2 | mesa_especialista | mesa_infraestructura (ground truth)
- `tiempo_resolucion`: Horas estimadas

**Responsable**: Mellany

### equipos.csv (opcional)
Define la capacidad de cada mesa de soporte.

**Columnas:**
- `equipo_id`: Identificador del equipo
- `nombre`: Nombre descriptivo
- `especialidad`: Área de especialización
- `max_tickets`: Capacidad máxima
- `carga_actual`: Tickets actuales (inicial = 0)
- `miembros`: Nombres de los miembros (separados por ;)

### tickets_con_decision.csv
Dataset procesado que incluye las decisiones del sistema.

**Columnas adicionales:**
- `mesa_asignada`: Mesa asignada por el sistema
- `complejidad_evaluada`: Complejidad evaluada por el agente
- `tiempo_procesamiento`: Tiempo que tomó procesar
- `razonamiento`: Explicación de la decisión
- `correcto`: Boolean (mesa_asignada == mesa_correcta)

## Notas

- Los archivos en `raw/` no deben modificarse después de su creación
- Los archivos en `processed/` son generados por el sistema
- Los logs se rotan automáticamente
- **No** subir al repositorio archivos grandes de datos reales (usar .gitignore)