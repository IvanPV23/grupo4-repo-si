# Guía de Tareas - Mellany
## Procesamiento de Datos y Lógica de Negocio

### 🎯 Responsabilidad Principal
Diseñar y crear el dataset de tickets, implementar las reglas de negocio para la derivación, y desarrollar el sistema de métricas para evaluar el desempeño del sistema.

---

## 📋 Tareas Asignadas

### 1. Crear Dataset de Tickets Simulados
**Prioridad: ALTA**  
**Archivo**: `data/raw/tickets.csv`

#### Descripción
Crear un dataset simulado de 100-200 tickets que represente casos reales de un entorno empresarial.

#### Columnas requeridas
```csv
ticket_id,tipo_ticket,tipo_error,area,solicitante,titulo,descripcion,prioridad,complejidad_real,mesa_correcta,tiempo_resolucion
```

#### Ejemplo de registros
```csv
JIRA-001,incidencia,redes,operaciones,Juan Perez,Internet lento en piso 3,Usuarios reportan lentitud en conexión desde las 9am,alta,media,mesa_n2,4
JIRA-002,solicitud,software,finanzas,Maria Lopez,Instalación de Excel,Necesito Microsoft Excel en mi laptop nueva,media,baja,mesa_n1,1
JIRA-003,incidencia,infraestructura,tecnologia,Carlos Ruiz,Servidor web caído,Servidor web no responde desde las 8am,urgente,critica,mesa_especialista,8
```

#### Distribución sugerida
- **Tipos de ticket**: 70% incidencias, 30% solicitudes
- **Tipos de error**: 
  - 20% redes
  - 25% software
  - 15% hardware
  - 20% infraestructura
  - 10% acceso
  - 10% configuración
- **Áreas**: Distribuir entre operaciones, cobranzas, finanzas, rrhh, comercial, tecnologia
- **Complejidad**: 30% baja, 40% media, 25% alta, 5% crítica

#### Herramientas
```python
import pandas as pd
import random
from faker import Faker

# Código de ejemplo para generar tickets
fake = Faker('es_MX')

def generar_tickets(n=100):
    tickets = []
    for i in range(1, n+1):
        ticket = {
            'ticket_id': f'JIRA-{i:03d}',
            'tipo_ticket': random.choice(['incidencia', 'solicitud']),
            'tipo_error': random.choice(['redes', 'software', 'hardware', 'infraestructura']),
            # ... completar
        }
        tickets.append(ticket)
    return pd.DataFrame(tickets)
```

---

### 2. Implementar Reglas Heurísticas de Derivación
**Prioridad: ALTA**  
**Archivo**: `utils/reglas_derivacion.py`

#### Descripción
Crear el conjunto de reglas de negocio que determinan a qué mesa debe ir cada tipo de ticket.

#### Reglas sugeridas

```python
"""
Reglas de Derivación de Tickets
"""

class ReglasDerivacion:
    
    @staticmethod
    def evaluar_por_tipo_error(tipo_error: str, complejidad: str) -> list:
        """Determina mesas candidatas según tipo de error"""
        reglas = {
            'infraestructura': ['mesa_especialista', 'mesa_infraestructura'],
            'redes': ['mesa_n2', 'mesa_especialista'] if complejidad in ['alta', 'critica'] 
                     else ['mesa_n1', 'mesa_n2'],
            'software': ['mesa_n1', 'mesa_n2'],
            'hardware': ['mesa_n2', 'mesa_especialista'],
            'acceso': ['mesa_n1'],
            'configuracion': ['mesa_n1']
        }
        return reglas.get(tipo_error, ['mesa_n1'])
    
    @staticmethod
    def evaluar_por_area(area: str, tipo_error: str) -> str:
        """Ajusta prioridad según área crítica"""
        areas_criticas = ['operaciones', 'cobranzas', 'finanzas']
        if area in areas_criticas and tipo_error == 'infraestructura':
            return 'priorizar'
        return 'normal'
    
    @staticmethod
    def evaluar_escalamiento(complejidad: str, mesa_actual: str) -> str:
        """Determina si debe escalarse a mesa superior"""
        if complejidad in ['alta', 'critica'] and mesa_actual == 'mesa_n1':
            return 'mesa_n2'
        if complejidad == 'critica' and mesa_actual in ['mesa_n1', 'mesa_n2']:
            return 'mesa_especialista'
        return mesa_actual
```

#### Casos especiales a considerar
- Tickets de áreas críticas (operaciones, cobranzas)
- Tickets con palabras clave urgentes
- Histórico de tickets similares
- Horario del reporte (horas laborales vs fuera de horario)

---

### 3. Desarrollar Módulo de Métricas y Evaluación
**Prioridad: MEDIA**  
**Archivo**: `utils/metricas.py`

#### Descripción
Implementar el sistema que evalúa el desempeño del sistema de derivación.

#### Métricas a calcular

```python
"""
Sistema de Métricas para Evaluación
"""
import pandas as pd
from typing import Dict

class Metricas:
    
    def __init__(self, df_tickets: pd.DataFrame):
        self.df = df_tickets
    
    def precision_asignacion(self) -> float:
        """
        Calcula precisión: % de tickets correctamente asignados
        Compara mesa_asignada vs mesa_correcta (ground truth)
        """
        correctos = (self.df['mesa_asignada'] == self.df['mesa_correcta']).sum()
        total = len(self.df)
        return (correctos / total) * 100
    
    def tiempo_promedio_procesamiento(self) -> float:
        """Tiempo promedio en procesar cada ticket (segundos)"""
        return self.df['tiempo_procesamiento'].mean()
    
    def tasa_derivacion_automatica(self) -> float:
        """% de tickets derivados sin intervención manual"""
        automaticos = (self.df['derivacion_automatica'] == True).sum()
        return (automaticos / len(self.df)) * 100
    
    def distribucion_por_mesa(self) -> Dict:
        """Distribución de tickets por mesa"""
        return self.df['mesa_asignada'].value_counts().to_dict()
    
    def precision_por_complejidad(self) -> Dict:
        """Precisión segmentada por nivel de complejidad"""
        resultados = {}
        for complejidad in ['baja', 'media', 'alta', 'critica']:
            df_seg = self.df[self.df['complejidad'] == complejidad]
            if len(df_seg) > 0:
                correctos = (df_seg['mesa_asignada'] == df_seg['mesa_correcta']).sum()
                resultados[complejidad] = (correctos / len(df_seg)) * 100
        return resultados
    
    def generar_reporte(self) -> Dict:
        """Genera reporte completo de métricas"""
        return {
            'precision_global': self.precision_asignacion(),
            'tiempo_promedio': self.tiempo_promedio_procesamiento(),
            'tasa_automatizacion': self.tasa_derivacion_automatica(),
            'distribucion_mesas': self.distribucion_por_mesa(),
            'precision_por_complejidad': self.precision_por_complejidad()
        }
```

---

### 4. Documentar Proceso de Decisión
**Prioridad: MEDIA**  
**Archivo**: `docs/proceso_decision.md`

#### Contenido sugerido
- Diagrama de flujo del proceso
- Explicación de cada regla
- Casos de uso y ejemplos
- Justificación de las decisiones de diseño

---

## 🛠️ Herramientas Recomendadas

```bash
# Instalar librerías para análisis
pip install pandas numpy faker matplotlib seaborn
```

### Ejemplo de análisis exploratorio

```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Cargar datos
df = pd.read_csv('data/raw/tickets.csv')

# Análisis descriptivo
print(df.describe())
print(df['tipo_error'].value_counts())

# Visualizaciones
df['tipo_error'].value_counts().plot(kind='bar')
plt.title('Distribución de Tipos de Error')
plt.savefig('docs/dist_tipos_error.png')
```

---

## 📊 Entregables

1. ✅ `data/raw/tickets.csv` - Dataset completo
2. ✅ `data/raw/equipos.csv` - Capacidad de mesas (opcional)
3. ✅ `utils/reglas_derivacion.py` - Reglas implementadas
4. ✅ `utils/metricas.py` - Sistema de métricas
5. ✅ `docs/proceso_decision.md` - Documentación
6. ✅ `notebooks/analisis_exploratorio.ipynb` - Análisis (opcional)

---

## 🤝 Coordinación con Equipo

- **Con Mauricio**: Compartir dataset para que entrene modelos ML
- **Con Jhair**: Definir formato de respuesta de métricas para API
- **Con Ivan**: Validar que reglas se integren bien con agentes

---

## 📝 Notas Importantes

1. El dataset debe ser **realista** pero no necesita ser perfecto
2. Las reglas deben ser **explícitas y documentadas**
3. Las métricas deben permitir **evaluar mejoras** del sistema
4. Mantén el código **simple y legible**

---

## 🚀 Cómo Empezar

1. Revisar el modelo de Ticket en `models/ticket.py`
2. Crear el dataset en `data/raw/tickets.csv`
3. Implementar reglas en `utils/reglas_derivacion.py`
4. Desarrollar métricas en `utils/metricas.py`
5. Documentar en `docs/proceso_decision.md`

**¡Éxito en tu trabajo!**