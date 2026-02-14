# Sistema Multiagente de Monitoreo de Ataques de Red (JADE)

Este proyecto implementa un **sistema multiagente** en JADE para simular la detección, análisis y respuesta ante eventos de seguridad en una red.  
El objetivo del taller es **observar el flujo de comunicación entre agentes**.

---

## Requisitos previos

- Java JDK instalado  

---

## Pasos para ejecutar el sistema

### 1. Compilar el proyecto
```bash
.\compilar.bat
```

---

### 2. Ejecutar la plataforma JADE
```bash
.\ejecutar.bat
```

Al iniciar, en consola deberías observar:
- Inicialización del contenedor JADE  
- Registro de los agentes en las **páginas amarillas (DF)**  
- Mensajes de arranque de cada agente  

---

## Prueba del sistema 

⚠ **Se debe enviar al menos DOS mensajes para iniciar el flujo completo.**  

### 4. Enviar un mensaje desde la GUI del agente `sensor`

Desde la **interfaz gráfica del agente sensor**, envía **algunos** de los siguientes mensajes:

- `Intento de login fallido desde IP 192.168.1.100`
- `Tráfico sospechoso en puerto 4444`
- `Múltiples conexiones desde IP desconocida 10.0.0.50`
- `Escaneo de puertos detectado desde 172.16.0.20`
- `Actividad anómala en servicio SSH`

---

## Observación del flujo

Una vez enviado el mensaje:

- Puedes activar los **Sniffers de JADE** que mostrarán el flujo completo de mensajes ACL
- Se visualizarán performativas como `INFORM` y `REQUEST`
- La consola mostrará nuevamente mensajes de procesamiento y respuesta
- No se requiere interacción adicional

---

## Notas finales

- El sistema está diseñado para ser **reactivo y autónomo**
- No existe control centralizado
- Toda la coordinación ocurre mediante mensajes ACL
- El objetivo es **observar el comportamiento de un SMA**, no la exactitud del ataque


---


