# 🧪 Guía de Validación del Proyecto

Esta guía te ayudará a verificar que el proyecto funciona correctamente después de clonarlo.

## ⚡ Pre-requisitos

- **Python 3.9+** instalado
- **Docker Desktop** instalado y corriendo
- **Git** instalado
- **PowerShell** (Windows) o Terminal (Mac/Linux)

---

## 🚀 Validación Paso a Paso

### 1️⃣ Clonar el Repositorio

```bash
git clone https://github.com/USUARIO/sistema-inteligente-derivacion-tickets.git
cd sistema-inteligente-derivacion-tickets
```

---

### 2️⃣ Configurar Entorno Python

#### **Windows (PowerShell):**
```powershell
# Crear entorno virtual
python -m venv venv

# Activar (si falla, ejecuta primero el comando de abajo)
.\venv\Scripts\Activate.ps1

# Si sale error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Verificar
python -c "from models.ticket import Ticket; print('✓ Python OK')"
```

#### **Mac/Linux:**
```bash
# Crear entorno virtual
python3 -m venv venv

# Activar
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Verificar
python -c "from models.ticket import Ticket; print('✓ Python OK')"
```

**✅ Checkpoint:** Debes ver `✓ Python OK`

---

### 3️⃣ Validar Docker

```bash
# Verificar Docker está corriendo
docker --version
docker-compose --version

# Construir imágenes (5-10 minutos primera vez)
docker-compose build

# Levantar servicios
docker-compose up -d

# Esperar 30 segundos para que inicien
# Windows PowerShell:
Start-Sleep -Seconds 30
# Mac/Linux:
sleep 30

# Ver estado
docker-compose ps
```

**Resultado esperado:**
```
NAME                        STATUS
sistema-tickets-api         Up
agente-complejidad          Up
agente-capacidad            Up
agente-decisor              Up
sistema-tickets-n8n         Up
```

**✅ Checkpoint:** Todos los servicios deben mostrar "Up"

---

### 4️⃣ Probar Endpoints

#### **Windows PowerShell:**
```powershell
# API Principal
Invoke-RestMethod http://localhost:8000/health

# Agentes
Invoke-RestMethod http://localhost:8001/health  # Complejidad
Invoke-RestMethod http://localhost:8002/health  # Capacidad
Invoke-RestMethod http://localhost:8003/health  # Decisor

# Abrir en navegador
start http://localhost:8000/docs  # Swagger UI
start http://localhost:5678       # n8n
```

#### **Mac/Linux:**
```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health

# Abrir en navegador
open http://localhost:8000/docs   # Mac
xdg-open http://localhost:8000/docs  # Linux
```

**✅ Checkpoint:** Todos deben responder con status "healthy"

---

### 5️⃣ Test Funcional Completo

#### **Windows PowerShell:**
```powershell
$ticket = @{
    ticket_id = "TEST-001"
    tipo_ticket = "incidencia"
    tipo_error = "redes"
    solicitante = "Usuario Test"
    area = "operaciones"
    titulo = "Test de validacion"
    descripcion = "Probando el sistema"
    prioridad = "media"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/tickets" `
    -Method POST `
    -Body $ticket `
    -ContentType "application/json"
```

#### **Mac/Linux:**
```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TEST-001",
    "tipo_ticket": "incidencia",
    "tipo_error": "redes",
    "solicitante": "Usuario Test",
    "area": "operaciones",
    "titulo": "Test de validacion",
    "descripcion": "Probando el sistema",
    "prioridad": "media"
  }'
```

**✅ Checkpoint:** Debe retornar un JSON con el ticket creado

---

## 🌐 URLs Importantes

Con los servicios corriendo:

| Servicio | URL | Descripción |
|----------|-----|-------------|
| API Docs | http://localhost:8000/docs | Swagger UI interactivo |
| API Health | http://localhost:8000/health | Health check |
| n8n | http://localhost:5678 | Orquestador (admin/admin123) |
| Agente Complejidad | http://localhost:8001/health | Health check |
| Agente Capacidad | http://localhost:8002/health | Health check |
| Agente Decisor | http://localhost:8003/health | Health check |

---

## ✅ Checklist de Validación

- [ ] Python 3.9+ instalado y funcionando
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas (`pip list` muestra fastapi, pandas, etc.)
- [ ] Modelo de Ticket se importa sin error
- [ ] Docker Desktop corriendo
- [ ] `docker-compose build` completa sin errores
- [ ] `docker-compose up -d` levanta todos los servicios
- [ ] `docker-compose ps` muestra todos "Up"
- [ ] http://localhost:8000/docs se abre en navegador
- [ ] Todos los health checks responden
- [ ] Puedes crear un ticket de prueba
- [ ] n8n es accesible en http://localhost:5678

---

## 🐛 Troubleshooting

### Error: "Python no encontrado"
```bash
# Verificar instalación
python --version
# o
python3 --version
```

### Error: "Docker no está corriendo"
- Abrir Docker Desktop
- Esperar a que aparezca "Docker Desktop is running"

### Error: "Puerto en uso"
```bash
# Ver qué usa el puerto
# Windows:
netstat -ano | findstr :8000
# Mac/Linux:
lsof -i :8000

# Matar proceso o cambiar puerto en docker-compose.yml
```

### Error: "Módulo no encontrado"
```bash
# Asegurarse de estar en el venv
# Debe verse (venv) al inicio de la línea

# Reinstalar
pip install -r requirements.txt --force-reinstall
```

### Servicios no inician
```bash
# Ver logs detallados
docker-compose logs

# Ver logs de un servicio específico
docker-compose logs api
docker-compose logs agente-complejidad

# Reconstruir desde cero
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## 🧹 Limpiar Después de Validar

```bash
# Detener servicios
docker-compose down

# Desactivar venv
deactivate  # Windows PowerShell/Linux/Mac

# Opcional: Eliminar venv (se puede recrear después)
# Windows:
Remove-Item -Recurse -Force venv
# Mac/Linux:
rm -rf venv
```

---

## 🎯 ¿Qué Significa "Validación Exitosa"?

Si todos estos puntos funcionan:

✅ Entorno Python configurado  
✅ Dependencias instaladas  
✅ Modelo de Ticket importable  
✅ Docker levanta 5 servicios  
✅ Todos los health checks responden  
✅ Puedes crear tickets vía API  
✅ Swagger UI accesible  
✅ n8n accesible  

→ **¡El proyecto está listo para trabajar!** 🚀

---

## 📞 Soporte

Si algo no funciona:

1. Revisar la sección de Troubleshooting arriba
2. Ver logs: `docker-compose logs`
3. Consultar documentación en `docs/`
4. Reportar issue en GitHub
5. Contactar al equipo

---

**Última actualización:** Febrero 2026  
**Versión:** 1.0