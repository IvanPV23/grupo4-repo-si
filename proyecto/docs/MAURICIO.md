# Guía de Tareas - Mauricio
## Modelado de Datos y Machine Learning

### 🎯 Responsabilidad Principal
Refinar los modelos de datos, crear estructura para equipos/mesas, implementar clasificadores ML opcionales, y realizar análisis de patrones en tickets.

---

## 📋 Tareas Asignadas

### 1. Refinar Modelo de Ticket
**Prioridad: ALTA**  
**Archivo**: `models/ticket.py` (ya existe, revisar y extender)

#### Descripción
El modelo base ya está creado. Tu tarea es:
- Revisarlo y agregar validaciones adicionales
- Crear métodos helper útiles
- Agregar serialización/deserialización optimizada

#### Mejoras sugeridas

```python
# En models/ticket.py, agregar:

from typing import List
import json

class Ticket:
    # ... código existente ...
    
    def validar_consistencia(self) -> tuple[bool, str]:
        """
        Valida la consistencia lógica del ticket
        Retorna: (es_valido, mensaje_error)
        """
        # Verificar que prioridad y complejidad sean consistentes
        if self.prioridad == 'urgente' and self.complejidad == 'baja':
            return False, "Inconsistencia: prioridad urgente con complejidad baja"
        
        # Verificar que descripción no esté vacía
        if not self.descripcion or len(self.descripcion) < 10:
            return False, "Descripción muy corta o vacía"
        
        # Verificar tipos de error según área
        if self.area == 'tecnologia' and self.tipo_error == 'acceso':
            return False, "Área de tecnología no debería tener problemas de acceso"
        
        return True, "Ticket válido"
    
    def extraer_palabras_clave(self) -> List[str]:
        """
        Extrae palabras clave técnicas de la descripción
        Útil para clasificación
        """
        palabras_tecnicas = [
            'servidor', 'base de datos', 'red', 'wifi', 'internet',
            'aplicación', 'sistema', 'error', 'caído', 'lento',
            'conexión', 'acceso', 'contraseña', 'usuario', 'permiso'
        ]
        
        desc_lower = self.descripcion.lower()
        encontradas = [p for p in palabras_tecnicas if p in desc_lower]
        return encontradas
    
    def calcular_score_urgencia(self) -> float:
        """
        Calcula un score de urgencia (0-100)
        Combina prioridad, complejidad y palabras clave
        """
        score = 0
        
        # Base por prioridad
        prioridad_scores = {
            'baja': 10,
            'media': 30,
            'alta': 60,
            'urgente': 90
        }
        score += prioridad_scores.get(self.prioridad.value, 30)
        
        # Ajuste por complejidad
        if self.complejidad:
            complejidad_scores = {
                'baja': 0,
                'media': 10,
                'alta': 20,
                'critica': 30
            }
            score += complejidad_scores.get(self.complejidad.value, 0)
        
        # Ajuste por palabras clave críticas
        palabras_criticas = ['caído', 'crítico', 'urgente', 'bloqueado']
        desc_lower = self.descripcion.lower()
        for palabra in palabras_criticas:
            if palabra in desc_lower:
                score += 5
        
        return min(score, 100)
    
    @classmethod
    def from_csv_row(cls, row: dict) -> 'Ticket':
        """Crea ticket desde fila de CSV"""
        return cls(
            ticket_id=row['ticket_id'],
            tipo_ticket=TipoTicket(row['tipo_ticket']),
            tipo_error=TipoError(row['tipo_error']),
            solicitante=row['solicitante'],
            area=Area(row['area']),
            titulo=row['titulo'],
            descripcion=row['descripcion'],
            prioridad=Prioridad(row.get('prioridad', 'media'))
        )
```

---

### 2. Crear Modelo de Datos para Equipos/Mesas
**Prioridad: ALTA**  
**Archivo**: `models/equipo.py`

#### Descripción
Crear el modelo que representa los equipos de soporte y su capacidad.

```python
"""
Modelo de Equipo de Soporte
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from enum import Enum


class EspecialidadEquipo(Enum):
    """Especialidades de los equipos"""
    SOPORTE_GENERAL = "soporte_general"
    SOPORTE_AVANZADO = "soporte_avanzado"
    INFRAESTRUCTURA = "infraestructura"
    REDES = "redes"
    APLICACIONES = "aplicaciones"


@dataclass
class Equipo:
    """
    Representa un equipo/mesa de soporte
    """
    equipo_id: str
    nombre: str
    especialidad: EspecialidadEquipo
    max_tickets: int
    carga_actual: int = 0
    miembros: List[str] = None
    horario_disponible: str = "24/7"
    
    def __post_init__(self):
        if self.miembros is None:
            self.miembros = []
    
    def porcentaje_uso(self) -> float:
        """Calcula el porcentaje de uso actual"""
        if self.max_tickets == 0:
            return 100.0
        return (self.carga_actual / self.max_tickets) * 100
    
    def esta_disponible(self, umbral: float = 90.0) -> bool:
        """Verifica si el equipo está disponible (bajo el umbral)"""
        return self.porcentaje_uso() < umbral
    
    def capacidad_restante(self) -> int:
        """Retorna cuántos tickets más puede recibir"""
        return max(0, self.max_tickets - self.carga_actual)
    
    def asignar_ticket(self) -> bool:
        """
        Intenta asignar un ticket al equipo
        Retorna True si fue exitoso, False si está lleno
        """
        if self.carga_actual < self.max_tickets:
            self.carga_actual += 1
            return True
        return False
    
    def liberar_ticket(self) -> bool:
        """
        Libera un ticket del equipo
        Retorna True si fue exitoso
        """
        if self.carga_actual > 0:
            self.carga_actual -= 1
            return True
        return False
    
    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            'equipo_id': self.equipo_id,
            'nombre': self.nombre,
            'especialidad': self.especialidad.value,
            'max_tickets': self.max_tickets,
            'carga_actual': self.carga_actual,
            'porcentaje_uso': self.porcentaje_uso(),
            'capacidad_restante': self.capacidad_restante(),
            'miembros': self.miembros,
            'horario_disponible': self.horario_disponible
        }
    
    def __str__(self) -> str:
        return (f"Equipo {self.nombre} - {self.especialidad.value}\n"
                f"Carga: {self.carga_actual}/{self.max_tickets} "
                f"({self.porcentaje_uso():.1f}%)")


# Dataset de equipos (puede ir en config/equipos.py)
EQUIPOS_DEFAULT = [
    Equipo(
        equipo_id="mesa_n1",
        nombre="Mesa N1 - Soporte General",
        especialidad=EspecialidadEquipo.SOPORTE_GENERAL,
        max_tickets=20,
        miembros=["Juan P.", "María L.", "Carlos R."]
    ),
    Equipo(
        equipo_id="mesa_n2",
        nombre="Mesa N2 - Soporte Avanzado",
        especialidad=EspecialidadEquipo.SOPORTE_AVANZADO,
        max_tickets=15,
        miembros=["Ana G.", "Luis M."]
    ),
    Equipo(
        equipo_id="mesa_especialista",
        nombre="Mesa Especialista",
        especialidad=EspecialidadEquipo.INFRAESTRUCTURA,
        max_tickets=10,
        miembros=["Pedro S."]
    ),
    Equipo(
        equipo_id="mesa_infraestructura",
        nombre="Mesa Infraestructura",
        especialidad=EspecialidadEquipo.INFRAESTRUCTURA,
        max_tickets=8,
        miembros=["Jorge T.", "Diana V."]
    )
]
```

---

### 3. Implementar Clasificador de Complejidad (Opcional)
**Prioridad: MEDIA**  
**Archivos**: 
- `models/clasificador.py`
- `notebooks/entrenamiento_modelo.ipynb`

#### Descripción
Crear un modelo de ML que prediga la complejidad de un ticket basándose en sus atributos.

```python
"""
Clasificador de Complejidad de Tickets
Usando Machine Learning
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
import joblib


class ClasificadorComplejidad:
    """
    Clasifica tickets en niveles de complejidad:
    - baja
    - media  
    - alta
    - critica
    """
    
    def __init__(self):
        self.modelo = None
        self.label_encoder = LabelEncoder()
        
    def entrenar(self, df: pd.DataFrame):
        """
        Entrena el modelo con dataset de tickets
        
        Args:
            df: DataFrame con columnas:
                - descripcion
                - tipo_error
                - prioridad
                - area
                - complejidad (target)
        """
        # Features
        X = df[['descripcion', 'tipo_error', 'prioridad', 'area']]
        y = df['complejidad']
        
        # Codificar target
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Crear pipeline
        self.modelo = Pipeline([
            ('features', ColumnTransformer([
                ('texto', TfidfVectorizer(max_features=100), 'descripcion'),
                ('categoricas', 'passthrough', ['tipo_error', 'prioridad', 'area'])
            ])),
            ('clasificador', RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            ))
        ])
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42
        )
        
        # Entrenar
        self.modelo.fit(X_train, y_train)
        
        # Evaluar
        score = self.modelo.score(X_test, y_test)
        print(f"Precisión del modelo: {score:.2%}")
        
        return score
    
    def predecir(self, ticket_data: dict) -> tuple[str, float]:
        """
        Predice la complejidad de un ticket
        
        Args:
            ticket_data: Dict con descripcion, tipo_error, prioridad, area
            
        Returns:
            (complejidad_predicha, confianza)
        """
        if self.modelo is None:
            raise ValueError("Modelo no entrenado")
        
        # Crear DataFrame con un registro
        df = pd.DataFrame([ticket_data])
        
        # Predecir
        prediccion_encoded = self.modelo.predict(df)[0]
        complejidad = self.label_encoder.inverse_transform([prediccion_encoded])[0]
        
        # Obtener probabilidades (confianza)
        probabilidades = self.modelo.predict_proba(df)[0]
        confianza = probabilidades.max()
        
        return complejidad, confianza
    
    def guardar(self, ruta: str):
        """Guarda el modelo entrenado"""
        joblib.dump({
            'modelo': self.modelo,
            'label_encoder': self.label_encoder
        }, ruta)
    
    @classmethod
    def cargar(cls, ruta: str):
        """Carga un modelo previamente entrenado"""
        datos = joblib.load(ruta)
        clasificador = cls()
        clasificador.modelo = datos['modelo']
        clasificador.label_encoder = datos['label_encoder']
        return clasificador


# Ejemplo de uso
if __name__ == "__main__":
    # Cargar dataset
    df = pd.read_csv('../data/raw/tickets.csv')
    
    # Entrenar
    clf = ClasificadorComplejidad()
    clf.entrenar(df)
    
    # Guardar
    clf.guardar('../models/clasificador_complejidad.pkl')
    
    # Probar predicción
    ticket_test = {
        'descripcion': 'Servidor web no responde',
        'tipo_error': 'infraestructura',
        'prioridad': 'urgente',
        'area': 'tecnologia'
    }
    
    complejidad, confianza = clf.predecir(ticket_test)
    print(f"Complejidad predicha: {complejidad} (confianza: {confianza:.2%})")
```

---

### 4. Análisis Exploratorio de Datos
**Prioridad: MEDIA**  
**Archivo**: `notebooks/analisis_exploratorio.ipynb`

#### Contenido sugerido

```python
# Jupyter Notebook - Análisis Exploratorio

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)

# 1. Cargar datos
df = pd.read_csv('../data/raw/tickets.csv')

# 2. Análisis descriptivo
print("=" * 50)
print("ANÁLISIS DESCRIPTIVO")
print("=" * 50)
print(f"\nTotal de tickets: {len(df)}")
print(f"\nColumnas: {df.columns.tolist()}")
print(f"\nValores nulos:\n{df.isnull().sum()}")

# 3. Distribuciones
fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# Distribución de tipos de error
df['tipo_error'].value_counts().plot(kind='bar', ax=axes[0,0])
axes[0,0].set_title('Distribución de Tipos de Error')

# Distribución de complejidad
df['complejidad'].value_counts().plot(kind='bar', ax=axes[0,1])
axes[0,1].set_title('Distribución de Complejidad')

# Distribución de áreas
df['area'].value_counts().plot(kind='bar', ax=axes[1,0])
axes[1,0].set_title('Tickets por Área')

# Distribución de prioridad
df['prioridad'].value_counts().plot(kind='bar', ax=axes[1,1])
axes[1,1].set_title('Distribución de Prioridad')

plt.tight_layout()
plt.savefig('../docs/distribucion_tickets.png')

# 4. Análisis de correlaciones
# Crear matriz de correlación para variables categóricas
from scipy.stats import chi2_contingency

def cramers_v(x, y):
    confusion_matrix = pd.crosstab(x,y)
    chi2 = chi2_contingency(confusion_matrix)[0]
    n = confusion_matrix.sum().sum()
    return np.sqrt(chi2 / (n * (min(confusion_matrix.shape) - 1)))

# Calcular Cramer's V entre variables
variables = ['tipo_error', 'complejidad', 'area', 'prioridad']
correlaciones = pd.DataFrame(index=variables, columns=variables)

for var1 in variables:
    for var2 in variables:
        if var1 == var2:
            correlaciones.loc[var1, var2] = 1.0
        else:
            correlaciones.loc[var1, var2] = cramers_v(df[var1], df[var2])

# Heatmap
plt.figure(figsize=(8, 6))
sns.heatmap(correlaciones.astype(float), annot=True, cmap='coolwarm')
plt.title('Correlaciones entre Variables Categóricas')
plt.savefig('../docs/correlaciones.png')

# 5. Análisis de mesa correcta vs características
mesa_por_tipo = pd.crosstab(df['tipo_error'], df['mesa_correcta'], normalize='index') * 100
print("\n% de asignación de mesa por tipo de error:")
print(mesa_por_tipo)
```

---

## 🛠️ Herramientas Recomendadas

```bash
pip install pandas numpy scikit-learn joblib matplotlib seaborn scipy jupyter
```

---

## 📊 Entregables

1. ✅ `models/equipo.py` - Modelo de equipos
2. ✅ `models/ticket.py` - Modelo refinado con nuevos métodos
3. ✅ `models/clasificador.py` - Clasificador ML (opcional)
4. ✅ `notebooks/analisis_exploratorio.ipynb` - Análisis
5. ✅ `notebooks/entrenamiento_modelo.ipynb` - Entrenamiento ML
6. ✅ `docs/modelo_datos.md` - Documentación de modelos

---

## 🤝 Coordinación con Equipo

- **Con Mellany**: Recibir dataset para entrenar modelos
- **Con Jhair**: Definir formato de API para modelos
- **Con Ivan**: Integrar clasificador en agentes

---

## 🚀 Cómo Empezar

1. Revisar modelo de Ticket existente
2. Crear modelo de Equipo
3. Esperar dataset de Mellany
4. Realizar análisis exploratorio
5. Entrenar clasificador (opcional)

**¡Éxito!**