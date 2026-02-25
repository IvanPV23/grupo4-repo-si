# 🎫 Sistema Inteligente de Derivación Automática de Tickets v3.0

> **Proyecto académico** — Curso de Sistemas Inteligentes, Febrero 2026.  
> Arquitectura multiagente para la clasificación y enrutamiento automático de tickets de soporte técnico, con integración a Jira Cloud y orquestación via n8n.

---

## 🏗️ Arquitectura del Sistema v3.0

```
👤 Usuario rellena el formulario web
        http://localhost:8000/app
               │
               ▼
    ┌──────────────────────┐
    │  API Principal       │  Python + FastAPI (puerto 8000)
    │  POST /tickets/nuevo │  Recibe ticket → llama a n8n
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  n8n Orquestador     │  Puerto 5678 — Workflow: "Orquestador Central v3"
    │  /webhook/derivar    │
    │  ┌─ Nodo 1 ─────────┤  Recibir Ticket (Webhook)
    │  ├─ Nodo 2 ─────────┤  Ejecutar Pipeline Agentes → /pipeline/ejecutar
    │  ├─ Nodo 3 ─────────┤  Crear Issue JIRA (Python) → /jira/crear
    │  └─ Nodo 4 ─────────┤  Armar Respuesta Final
    └──────────┬───────────┘
               │ resultado completo
               ▼
    ┌──────────────────────┐    ┌──────────────────────┐
    │  API guarda en Excel │    │  Jira Cloud          │
    │  reporte_acum.xlsx   │    │  Issue SCRUM-X creado│
    └──────────────────────┘    └──────────────────────┘
```

### Pipeline de Agentes (llamado por n8n en /pipeline/ejecutar)

```
Ticket
  ├─ Agente HISTÓRICO   (8004) ← ¿Ticket similar antes? → bypass directo
  ├─ Agente ESTIMADOR   (8005) ← ¿Cuántas horas tomará?
  ├─ Agente COMPLEJIDAD (8001) ← Score 0-100 → baja/media/alta/muy_alta
  └─ Agente ORQUESTADOR (8003) ← ¿Qué mesa tiene capacidad? → asigna
```

### Mesas de Soporte

| Nivel | Mesa | Especialidad |
|---|---|---|
| N1 | Service Desk 1 / 2 | Solicitudes simples, consultas |
| N2 | Squad - Mesa Ongoing | Incidentes moderados |
| N3 | Squad - Mesa SOAT | Incidencias producto SOAT |
| N3 | Squad - Mesa SCTR | Incidencias producto SCTR |
| N3 | Squad - Mesa Vida Ley | Incidencias producto Vida Ley |
| N3 | soportedigital | Ecommerce, emisión digital |

---

## 📁 Estructura del Proyecto

```
proyecto/
├── agents/
│   ├── historico/main.py      ← Agente histórico (puerto 8004)
│   ├── estimador/main.py      ← Agente estimador (puerto 8005)
│   ├── complejidad/main.py    ← Agente complejidad (puerto 8001)
│   └── decisor/main.py        ← Agente orquestador (puerto 8003)
│
├── api/
│   └── main.py                ← API principal (puerto 8000)
│                                 Endpoints: /tickets/nuevo, /pipeline/ejecutar,
│                                            /jira/crear, /reporte, /mesas/estado
│
├── data/
│   ├── inputs/                ← ⚠️ NO subir al repo (datos sensibles Protecta)
│   │   └── *.csv              ← Exportaciones JIRA (excluidas por .gitignore)
│   └── outputs/               ← Excel acumulativo generado por el sistema
│
├── frontend/
│   └── index.html             ← Formulario web del sistema
│
├── utils/
│   ├── excel_acumulativo.py   ← Generador de reporte Excel
│   ├── reglas_derivacion.py   ← Lógica de mesas y niveles
│   └── metricas.py            ← Métricas del sistema
│
├── n8n_orquestador_v3.json    ← Workflow n8n (importar en la UI)
├── docker-compose.yml         ← Orquestación de todos los servicios
├── Dockerfile                 ← Imagen de la API
└── Dockerfile.agent           ← Imagen de los agentes
```

---

## 🚀 Instalación y Puesta en Marcha

### Prerrequisitos

- **Docker Desktop** instalado y corriendo
- **Git** instalado
- Cuenta en **Jira Cloud** (para integración automática de issues)

### 1. Clonar el repositorio

```bash
git clone https://github.com/IvanPV23/grupo4-repo-si.git
cd grupo4-repo-si/proyecto
```

### 2. Levantar todos los servicios

```bash
docker-compose up -d --build
```

**Servicios que se levantan:**

| Servicio | Puerto | Rol |
|---|---|---|
| `sistema-tickets-api` | 8000 | API principal + frontend |
| `sistema-tickets-n8n` | 5678 | Orquestador de flujos |
| `agente-historico` | 8004 | Búsqueda en historial |
| `agente-estimador` | 8005 | Estimación de tiempo |
| `agente-complejidad` | 8001 | Evaluación de complejidad |
| `agente-orquestador` | 8003 | Asignación de mesas |

### 3. Configurar n8n

1. Abre **http://localhost:5678**
2. Menú `☰` → **Import from file**
3. Selecciona `n8n_orquestador_v3.json`
4. Activa el workflow (toggle **Inactive → Active**)

### 4. Usar el sistema

Abre **http://localhost:8000/app** → rellena el formulario → el sistema:
- Ejecuta el pipeline de 4 agentes
- Crea automáticamente un issue en Jira Cloud
- Guarda el resultado en el Excel acumulativo

---

## 🌐 Endpoints Disponibles

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Estado del sistema y agentes |
| `POST` | `/tickets/nuevo` | Procesar ticket (llama a n8n) |
| `POST` | `/pipeline/ejecutar` | Solo ejecutar agentes (sin Jira/Excel) |
| `POST` | `/jira/crear` | Solo crear issue en Jira |
| `GET` | `/cola` | Tickets en cola de espera |
| `GET` | `/mesas/estado` | Carga de cada mesa |
| `GET` | `/reporte` | Descargar Excel acumulativo |
| `GET` | `/metricas` | Métricas del sistema |
| `GET` | `/docs` | Documentación Swagger |

---

## 🧪 Prueba rápida

```powershell
# PowerShell — enviar un ticket de prueba
$body = @{
    tipo_incidencia    = "Incidente"
    resumen            = "SOAT caido masivo, no se puede emitir"
    tipo_atencion_sd   = "Error de sistema"
    area               = "Siniestros"
    producto           = "SOAT"
    informador         = "usuario@empresa.com"
    cantidad_afectados = 10
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/tickets/nuevo" -Method POST `
    -ContentType "application/json" -Body $body
```

Respuesta esperada:
```json
{
  "ticket_id": "TK-20260225XXXXXX",
  "mesa_asignada": "Squad - Mesa SOAT",
  "nivel_asignado": "N3",
  "complejidad": "muy_alta",
  "jira_issue_key": "SCRUM-X",
  "jira_url": "https://jhairrmb3.atlassian.net/browse/SCRUM-X"
}
```

---

## 🛠️ Tecnologías Utilizadas

| Tecnología | Rol |
|---|---|
| **Python 3.12 + FastAPI** | API REST y lógica de agentes |
| **n8n** | Orquestador visual de flujos (webhook → agentes → Jira) |
| **Jira Cloud REST API** | Creación automática de issues por ticket |
| **Docker + Docker Compose** | Contenerización de todos los servicios |
| **httpx** | Comunicación asíncrona entre agentes |
| **openpyxl** | Generación del reporte Excel acumulativo |
| **Pydantic** | Validación de modelos de datos |

---

## ⚠️ Sobre los Datos — Aviso de Privacidad

> Los archivos CSV en `data/inputs/` provienen de exportaciones reales de JIRA de una empresa peruana de seguros (**Protecta**). Por razones de privacidad y seguridad, **estos archivos están excluidos del repositorio** mediante `.gitignore`. Para ejecutar el sistema, coloca manualmente los CSVs en esa carpeta.
>
> El sistema fue validado sobre estos datos únicamente con fines académicos en el contexto del Curso de **Sistemas Inteligentes**, Febrero 2026.

---

## 👥 Equipo — Grupo 4

Proyecto desarrollado para el Curso de **Sistemas Inteligentes**, Febrero 2026.

---

## 📝 Licencia

Uso académico exclusivo. No apto para producción sin adaptaciones de seguridad.