# Sistema Inteligente de Derivación Automática de Tickets

Sistema basado en arquitectura multiagente para la derivación automática e inteligente de tickets de incidencias usando n8n como orquestador.

## 📋 Descripción

Este proyecto implementa un sistema inteligente que automatiza la asignación de tickets de soporte técnico a las mesas especializadas correspondientes, considerando:

- Complejidad de la incidencia
- Capacidad de los equipos
- Tipo de error reportado
- Área organizacional
- Prioridad del ticket

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                      n8n Orchestrator                    │
│              (Coordinación de Flujos)                    │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Agente     │ │   Agente     │ │   Agente     │
│ Complejidad  │ │  Capacidad   │ │   Decisor    │
└──────────────┘ └──────────────┘ └──────────────┘
        │               │               │
        └───────────────┼───────────────┘
                        ▼
                ┌──────────────┐
                │   Ticket     │
                │   Asignado   │
                └──────────────┘
```

## 📁 Estructura del Proyecto

```
proyecto-tickets-ia/
├── agents/                     # Agentes inteligentes
│   ├── complejidad/           # Agente evaluador de complejidad
│   ├── capacidad/             # Agente evaluador de capacidad
│   └── decisor/               # Agente decisor final
├── api/                       # API REST (FastAPI)
├── config/                    # Archivos de configuración
├── data/                      # Datos del sistema
│   ├── raw/                   # Datos crudos
│   ├── processed/             # Datos procesados
│   └── logs/                  # Logs del sistema
├── docs/                      # Documentación
├── models/                    # Modelos de datos
├── n8n/                       # Configuración de n8n
│   ├── workflows/             # Workflows exportados
│   └── credentials/           # Credenciales (gitignored)
├── tests/                     # Tests automatizados
│   ├── unit/                  # Tests unitarios
│   └── integration/           # Tests de integración
└── utils/                     # Utilidades y helpers
```

## 🚀 Instalación

### Prerrequisitos

- Docker y Docker Compose
- Python 3.9+
- Git

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/proyecto-tickets-ia.git
cd proyecto-tickets-ia
```

2. **Crear entorno virtual de Python**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

5. **Levantar servicios con Docker**
```bash
docker-compose up -d
```

6. **Acceder a n8n**
- URL: http://localhost:5678
- Importar workflows desde `n8n/workflows/`

## 🛠️ Tecnologías Utilizadas

- **n8n**: Orquestador de workflows
- **Python 3.9+**: Backend y agentes
- **FastAPI**: API REST
- **Docker**: Contenerización
- **Pandas**: Procesamiento de datos
- **scikit-learn**: Machine Learning (opcional)
- **SQLite/PostgreSQL**: Persistencia de datos

## 👥 Equipo y Responsabilidades

### 👤 Mellany - Procesamiento de Datos y Lógica de Negocio
- Diseño y manipulación del dataset de tickets
- Implementación de reglas de negocio
- Optimización de procesos de decisión
- Métricas y evaluación del sistema

**Tareas asignadas:**
- [ ] Crear dataset de tickets simulados (`data/raw/tickets.csv`)
- [ ] Implementar reglas heurísticas de derivación
- [ ] Desarrollar módulo de métricas y evaluación
- [ ] Documentar proceso de decisión

### 👤 Mauricio - Modelado de Datos y ML
- Definición de modelos de datos
- Implementación de clasificadores (opcional)
- Análisis de patrones en tickets
- Validación de modelos

**Tareas asignadas:**
- [ ] Refinar modelo de Ticket (ya está base en `models/ticket.py`)
- [ ] Crear modelo de datos para equipos/mesas
- [ ] Implementar clasificador de complejidad (opcional)
- [ ] Análisis exploratorio de datos

### 👤 Jhair - Infraestructura y Conectividad
- Configuración de Docker y servicios
- API REST con FastAPI
- Integración entre componentes
- Configuración de n8n

**Tareas asignadas:**
- [ ] Configurar Docker Compose completo
- [ ] Implementar API REST base
- [ ] Configurar endpoints para agentes
- [ ] Integración con n8n

### 👤 [Tu nombre] - Arquitectura y Coordinación
- Diseño general del sistema
- Implementación de agentes
- Coordinación de workflows en n8n
- Documentación técnica

**Tareas asignadas:**
- [ ] Implementar los 3 agentes (complejidad, capacidad, decisor)
- [ ] Diseñar workflows de n8n
- [ ] Documentación de arquitectura
- [ ] Integración final del sistema

## 🧪 Testing

```bash
# Ejecutar tests unitarios
pytest tests/unit/

# Ejecutar tests de integración
pytest tests/integration/

# Coverage
pytest --cov=. tests/
```

## 📊 Dataset

El proyecto incluye un dataset simulado de tickets con las siguientes características:

- **Volumen**: ~100-200 tickets
- **Atributos**: tipo_ticket, tipo_error, área, complejidad, prioridad
- **Objetivo**: Validar reglas de derivación automática

Ver `data/raw/README.md` para más detalles.

## 🔄 Flujo de Trabajo en n8n

1. **Trigger**: Webhook recibe nuevo ticket
2. **Extracción**: Se extraen atributos del ticket
3. **Agente Complejidad**: Evalúa complejidad técnica
4. **Agente Capacidad**: Verifica disponibilidad de mesas
5. **Agente Decisor**: Toma decisión final
6. **Ejecución**: Se asigna ticket a mesa correspondiente
7. **Registro**: Se almacena decisión y métricas

## 📈 Métricas del Sistema

- Tiempo promedio de procesamiento
- Tasa de derivación automática
- Precisión de asignación (vs ground truth)
- Carga balanceada entre mesas

## 🤝 Contribución

1. Fork el proyecto
2. Crea tu rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto es parte del curso **Sistemas Inteligentes** y está desarrollado con fines académicos.

## 📧 Contacto

Para preguntas o sugerencias, contactar al equipo del proyecto.

---

**Última actualización**: Febrero 2026