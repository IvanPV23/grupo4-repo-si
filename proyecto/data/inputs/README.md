# 📂 Carpeta de Ingesta de Tickets (inputs/)

Aquí depositas manualmente los archivos CSV exportados desde JIRA.

## Cómo usarla

1. Exporta el reporte desde JIRA en formato **CSV** (separado por `;`)
2. Coloca el archivo aquí: `data/inputs/`
3. Llama al endpoint `POST /procesar-csv` para procesar los tickets **Abiertos**

## Formato esperado

El CSV debe tener las siguientes columnas (igual que la exportación estándar):

```
Tipo de Incidencia; Prioridad; Campo personalizado (Prioridad SD); Clave de incidencia;
ID de la incidencia; Resumen; Campo personalizado (Tipo de atención SD); Informador;
Creada; Campo personalizado (Aplicativo); Campo personalizado (Área); Estado;
Responsable; Actualizada; Campo personalizado (Clasificación);
Campo personalizado (Atendido por); Campo personalizado (Especialista);
Resolución; Campo personalizado (Tipo de Cliente); Resuelta;
Campo personalizado (Producto SD)
```

## Notas

- El sistema selecciona automáticamente el **CSV más reciente** de esta carpeta.
- Solo procesa tickets con `Estado == "Abierto"`.
- Los archivos procesados **no se eliminan**, pero se registra cuántos fueron procesados.
