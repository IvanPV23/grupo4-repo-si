# Guía de Tareas - Jhair
## Infraestructura y Conectividad

### 🎯 Responsabilidad Principal
Configurar Docker y servicios, implementar la API REST completa, configurar endpoints para agentes, y realizar la integración con n8n.

---

## 📋 Tareas Asignadas

### 1. Configurar Docker Compose Completo
**Prioridad: CRÍTICA**  
**Archivo**: `docker-compose.yml` (ya existe, revisar y ajustar)

#### Descripción
El archivo `docker-compose.yml` ya tiene la estructura base. Tu tarea es:
- Verificar que todos los servicios estén correctamente configurados
- Ajustar variables de entorno según necesidades
- Configurar volúmenes y networking
- Asegurar que los servicios puedan comunicarse entre sí

#### Pasos de verificación

```bash
# 1. Verificar sintaxis del docker-compose
docker-compose config

# 2. Construir imágenes
docker-compose build

# 3. Levantar servicios
docker-compose up -d

# 4. Verificar que todos estén corriendo
docker-compose ps

# 5. Ver logs
docker-compose logs -f

# 6. Probar conectividad entre servicios
docker exec sistema-tickets-api curl http://agente-complejidad:8001/health
docker exec sistema-tickets-api curl http://agente-capacidad:8002/health
docker exec sistema-tickets-api curl http://agente-decisor:8003/health
```

#### Troubleshooting común

```bash
# Si hay problemas de red
docker network ls
docker network inspect proyecto-tickets-ia_tickets-network

# Si los contenedores no inician
docker-compose logs nombre-servicio

# Reiniciar todo
docker-compose down -v
docker-compose up -d --build

# Limpiar sistema
docker system prune -a
```

#### Configuración adicional

```yaml
# Agregar healthchecks robustos
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

# Configurar restart policy
restart: unless-stopped

# Límites de recursos (opcional)
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
```

---

### 2. Implementar API REST Base Completa
**Prioridad: CRÍTICA**  
**Archivo**: `api/main.py` (ya existe, extender funcionalidad)

#### Endpoints adicionales a implementar

```python
"""
Extensiones para API Principal
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from typing import List
import httpx

# =====================================================
# Integración con Agentes
# =====================================================

@app.post("/webhook/nuevo-ticket", tags=["Webhooks"])
async def webhook_nuevo_ticket(ticket_data: TicketCreate, background_tasks: BackgroundTasks):
    """
    Webhook que recibe notificaciones de nuevos tickets
    Dispara el flujo completo de derivación
    """
    try:
        # 1. Crear ticket
        ticket = Ticket(
            ticket_id=ticket_data.ticket_id,
            tipo_ticket=TipoTicket(ticket_data.tipo_ticket),
            tipo_error=TipoError(ticket_data.tipo_error),
            solicitante=ticket_data.solicitante,
            area=Area(ticket_data.area),
            titulo=ticket_data.titulo,
            descripcion=ticket_data.descripcion
        )
        
        # 2. Guardar en base de datos (implementar)
        # await guardar_ticket(ticket)
        
        # 3. Disparar proceso de derivación en background
        background_tasks.add_task(procesar_derivacion, ticket)
        
        return {
            "status": "accepted",
            "ticket_id": ticket.ticket_id,
            "mensaje": "Ticket recibido, procesando derivación"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def procesar_derivacion(ticket: Ticket):
    """
    Proceso completo de derivación (ejecutado en background)
    """
    async with httpx.AsyncClient() as client:
        try:
            # Llamar al agente decisor
            response = await client.post(
                "http://agente-decisor:8003/decidir",
                json={
                    "ticket_id": ticket.ticket_id,
                    "tipo_error": ticket.tipo_error.value,
                    "descripcion": ticket.descripcion,
                    "area": ticket.area.value,
                    "prioridad": ticket.prioridad.value
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                decision = response.json()
                
                # Actualizar ticket con decisión
                ticket.asignar_mesa(
                    MesaSoporte(decision["mesa_asignada"]),
                    comentario=decision["razonamiento"]
                )
                
                # Guardar en BD (implementar)
                # await actualizar_ticket(ticket)
                
                # Notificar a n8n (implementar)
                # await notificar_n8n(ticket, decision)
                
                print(f"Ticket {ticket.ticket_id} asignado a {decision['mesa_asignada']}")
            
        except Exception as e:
            print(f"Error en derivación de {ticket.ticket_id}: {str(e)}")


# =====================================================
# Endpoints de Consulta
# =====================================================

@app.get("/tickets/estadisticas", tags=["Estadísticas"])
async def obtener_estadisticas():
    """Estadísticas generales del sistema"""
    # TODO: Implementar consultas reales
    return {
        "total_tickets": 0,
        "tickets_pendientes": 0,
        "tickets_en_proceso": 0,
        "tickets_cerrados": 0,
        "distribucion_mesas": {},
        "tiempo_promedio_resolucion": 0
    }


@app.get("/equipos/estado", tags=["Equipos"])
async def obtener_estado_equipos():
    """Estado actual de todos los equipos"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://agente-capacidad:8002/capacidad/todas",
                timeout=10.0
            )
            return response.json()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail="Error al consultar estado de equipos"
            )


# =====================================================
# Endpoints de Testing
# =====================================================

@app.post("/test/derivacion", tags=["Testing"])
async def test_derivacion_completa(ticket_data: TicketCreate):
    """
    Endpoint de testing para probar el flujo completo
    """
    async with httpx.AsyncClient() as client:
        # 1. Evaluar complejidad
        resp_complejidad = await client.post(
            "http://agente-complejidad:8001/evaluar",
            json={
                "ticket_id": ticket_data.ticket_id,
                "tipo_error": ticket_data.tipo_error,
                "descripcion": ticket_data.descripcion,
                "area": ticket_data.area,
                "prioridad": ticket_data.prioridad
            }
        )
        
        # 2. Evaluar capacidad
        complejidad_data = resp_complejidad.json()
        resp_capacidad = await client.post(
            "http://agente-capacidad:8002/evaluar",
            json={
                "tipo_error": ticket_data.tipo_error,
                "complejidad": complejidad_data["complejidad"]
            }
        )
        
        # 3. Decisión final
        resp_decision = await client.post(
            "http://agente-decisor:8003/decidir",
            json={
                "ticket_id": ticket_data.ticket_id,
                "tipo_error": ticket_data.tipo_error,
                "descripcion": ticket_data.descripcion,
                "area": ticket_data.area,
                "prioridad": ticket_data.prioridad
            }
        )
        
        return {
            "complejidad": resp_complejidad.json(),
            "capacidad": resp_capacidad.json(),
            "decision": resp_decision.json()
        }
```

---

### 3. Configurar Endpoints para Agentes
**Prioridad: ALTA**  
**Archivos**: 
- `agents/complejidad/main.py` (revisar)
- `agents/capacidad/main.py` (revisar)
- `agents/decisor/main.py` (revisar)

#### Verificaciones necesarias

```bash
# Script de verificación de endpoints
#!/bin/bash

echo "=== Verificación de Endpoints de Agentes ==="

# Health checks
echo "\n1. Health Check - Agente Complejidad"
curl http://localhost:8001/health

echo "\n2. Health Check - Agente Capacidad"
curl http://localhost:8002/health

echo "\n3. Health Check - Agente Decisor"
curl http://localhost:8003/health

# Test funcional
echo "\n4. Test Evaluación Complejidad"
curl -X POST http://localhost:8001/evaluar \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TEST-001",
    "tipo_error": "infraestructura",
    "descripcion": "Servidor caído en producción",
    "area": "operaciones",
    "prioridad": "urgente"
  }'

echo "\n5. Test Evaluación Capacidad"
curl -X POST http://localhost:8002/evaluar \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_error": "infraestructura",
    "complejidad": "alta"
  }'

echo "\n6. Test Decisión Final"
curl -X POST http://localhost:8003/decidir \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TEST-001",
    "tipo_error": "infraestructura",
    "descripcion": "Servidor caído",
    "area": "operaciones",
    "prioridad": "urgente"
  }'
```

#### Mejoras de networking

```python
# Agregar retry logic y circuit breaker

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def llamar_agente_con_retry(url: str, datos: dict):
    """Llama a un agente con reintentos automáticos"""
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=datos, timeout=10.0)
        response.raise_for_status()
        return response.json()
```

---

### 4. Integración con n8n
**Prioridad: ALTA**  
**Archivos**: 
- `n8n/workflows/flujo_derivacion.json`
- `config/n8n_config.json`

#### Configuración inicial de n8n

```bash
# 1. Acceder a n8n
open http://localhost:5678

# 2. Credenciales por defecto (cambiar después)
# Usuario: admin
# Contraseña: admin123

# 3. Crear credenciales HTTP para API
# Settings > Credentials > New Credential > HTTP Header Auth
```

#### Workflow básico en n8n

1. **Trigger**: Webhook
   - Method: POST
   - Path: `webhook/nuevo-ticket`

2. **HTTP Request**: Llamar API Principal
   - URL: `http://api:8000/webhook/nuevo-ticket`
   - Method: POST
   - Body: JSON del ticket

3. **HTTP Request**: Obtener decisión
   - URL: `http://agente-decisor:8003/decidir`
   - Method: POST

4. **Conditional**: Evaluar resultado
   - If mesa_asignada != "no_asignado": continuar
   - Else: notificar error

5. **HTTP Request**: Actualizar ticket en sistema
   - URL del sistema de tickets (Jira o mock)
   - Asignar a equipo correspondiente

#### Exportar workflow

```bash
# Desde n8n UI:
# Workflows > Your Workflow > ... > Download

# Guardar en:
# n8n/workflows/flujo_derivacion.json
```

---

## 🛠️ Herramientas Recomendadas

```bash
# Herramientas de networking
sudo apt-get install curl jq httpie

# Para debugging
pip install httpx tenacity

# Docker tools
docker-compose
docker ps
docker logs
docker network inspect
```

### Scripts útiles

```bash
# scripts/test_conectividad.sh
#!/bin/bash

echo "=== Test de Conectividad ==="

# Verificar que todos los servicios estén up
services=("api" "agente-complejidad" "agente-capacidad" "agente-decisor" "n8n")

for service in "${services[@]}"; do
    if docker-compose ps | grep -q "$service.*Up"; then
        echo "✓ $service está corriendo"
    else
        echo "✗ $service NO está corriendo"
    fi
done

# Test de endpoints
echo "\n=== Test de Endpoints ==="

# API Principal
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✓ API Principal responde"
else
    echo "✗ API Principal no responde"
fi

# Agentes
for port in 8001 8002 8003; do
    if curl -s http://localhost:$port/health > /dev/null; then
        echo "✓ Agente en puerto $port responde"
    else
        echo "✗ Agente en puerto $port no responde"
    fi
done

# n8n
if curl -s http://localhost:5678 > /dev/null; then
    echo "✓ n8n responde"
else
    echo "✗ n8n no responde"
fi
```

---

## 📊 Entregables

1. ✅ `docker-compose.yml` - Configuración completa y funcional
2. ✅ `api/main.py` - API con todos los endpoints implementados
3. ✅ Verificación de conectividad entre servicios
4. ✅ `n8n/workflows/flujo_derivacion.json` - Workflow exportado
5. ✅ `scripts/test_conectividad.sh` - Script de verificación
6. ✅ `docs/arquitectura_infraestructura.md` - Documentación

---

## 🤝 Coordinación con Equipo

- **Con Mellany**: Definir formato de métricas en API
- **Con Mauricio**: Definir endpoints para modelos
- **Con Ivan**: Verificar integración con agentes y n8n

---

## 📝 Checklist de Infraestructura

- [ ] Docker Compose levanta todos los servicios
- [ ] Servicios pueden comunicarse entre sí
- [ ] Health checks funcionan correctamente
- [ ] API responde a requests básicos
- [ ] Agentes responden a evaluaciones
- [ ] n8n puede llamar a la API
- [ ] Logs se guardan correctamente
- [ ] Variables de entorno configuradas
- [ ] Documentación de arquitectura completa

---

## 🚀 Cómo Empezar

1. Revisar `docker-compose.yml` existente
2. Levantar servicios: `docker-compose up -d`
3. Verificar logs: `docker-compose logs -f`
4. Probar endpoints con curl
5. Configurar n8n y crear workflow
6. Documentar arquitectura

**¡Éxito!**