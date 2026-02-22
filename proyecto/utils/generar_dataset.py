"""
Generador de Dataset Simulado para el Sistema de Derivación de Tickets
Genera un archivo CSV con 100 tickets de prueba.
"""

import csv
import random
import os

def generar_dataset(cantidad: int = 100, filepath: str = "data/raw/tickets_completos.csv"):
    """
    Genera un dataset sintético realista de tickets.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    tipos_error = ["software", "hardware", "redes", "infraestructura", "acceso", "configuracion"]
    areas = ["ventas", "finanzas", "rrhh", "operaciones", "tecnologia", "marketing"]
    prioridades = ["baja", "media", "alta", "urgente"]
    
    descripciones_base = {
        "software": [
            "El sistema de nóminasarroja error 500",
            "Mi excel no abre",
            "La aplicación web está muy lenta",
            "Error al guardar los datos del cliente en el CRM"
        ],
        "hardware": [
            "El monitor no enciende",
            "La laptop hace un ruido extraño",
            "Impresora atascada",
            "Teclado tiene teclas rotas"
        ],
        "redes": [
            "No hay WiFi en el piso 3",
            "Pérdida de paquetes en la red VPN",
            "El router principal se reinicia solo",
            "Lentitud generalizada en la conexión a internet"
        ],
        "infraestructura": [
            "Servidor de base de datos caído, datos críticos inaccesibles",
            "Fallo en el disco duro del servidor principal",
            "Alerta de temperatura alta en el data center",
            "Fallo de energía en el rack secundario"
        ],
        "acceso": [
            "Olvidé mi contraseña de Windows",
            "Cuenta bloqueada por múltiples intentos",
            "No puedo ingresar al correo corporativo",
            "Necesito acceso a la carpeta compartida"
        ],
        "configuracion": [
            "Configurar correo en mi nuevo iPhone",
            "Instalar y configurar VPN en mi laptop",
            "Actualizar permisos del sistema",
            "Mapear unidad de red compartida"
        ]
    }
    
    nombres = ["Ana", "Carlos", "Luis", "Maria", "Juan", "Pedro", "Sofia", "Jorge", "Laura"]
    apellidos = ["Perez", "Gomez", "Ruiz", "Torres", "Martinez", "Diaz", "Sanchez"]
    
    mesas_correctas_logica = {
        "acceso": "mesa_n1",
        "configuracion": "mesa_n1",
        "software": "mesa_n1",  # Simplificado, N2 si es complejo
        "hardware": "mesa_n1",
        "redes": "mesa_n2",
        "infraestructura": "mesa_especialista"
    }

    with open(filepath, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ticket_id", "tipo_ticket", "tipo_error", "area", "solicitante", "titulo", "descripcion", "prioridad", "complejidad_real", "mesa_correcta", "tiempo_resolucion"])
        
        for i in range(1, cantidad + 1):
            ticket_id = f"TICK-{str(i).zfill(4)}"
            tipo_error = random.choice(tipos_error)
            area = random.choice(areas)
            
            # Ajustar probabilidad de prioridad según tipo de error
            weights = [0.4, 0.4, 0.15, 0.05]
            if tipo_error in ["infraestructura", "redes"]:
                weights = [0.05, 0.15, 0.5, 0.3]
            prioridad = random.choices(prioridades, weights=weights)[0]
            
            descripcion = random.choice(descripciones_base[tipo_error])
            if prioridad == "urgente":
                descripcion = "URGENTE: " + descripcion
                
            solicitante = f"{random.choice(nombres)} {random.choice(apellidos)}"
            titulo = f"Problema de {tipo_error} en {area}"
            
            # Asignar una complejidad razonable
            complejidad_real = "baja"
            if tipo_error in ["infraestructura", "redes"] or prioridad in ["alta", "urgente"]:
                complejidad_real = random.choice(["alta", "critica"])
            elif tipo_error in ["software", "hardware"] and prioridad == "media":
                complejidad_real = "media"
                
            mesa_correcta = mesas_correctas_logica.get(tipo_error, "mesa_n1")
            # Ajuste por complejidad
            if complejidad_real == "critica" and mesa_correcta != "mesa_especialista":
                mesa_correcta = "mesa_n2" if mesa_correcta == "mesa_n1" else "mesa_especialista"
                
            tiempo_resolucion = round(random.uniform(0.5, 8.0) if complejidad_real in ["baja", "media"] else random.uniform(4.0, 24.0), 1)
            
            # Introducir un 10% de "ruido" donde la mesa correcta no coincida exactamente con la heurística básica 
            # (Útil si deciden usar Machine Learning después)
            if random.random() < 0.10:
                mesa_correcta = random.choice(["mesa_n1", "mesa_n2", "mesa_especialista", "mesa_infraestructura"])
            
            writer.writerow([
                ticket_id, 
                random.choice(["incidencia", "solicitud"]), 
                tipo_error, 
                area, 
                solicitante, 
                titulo, 
                descripcion, 
                prioridad, 
                complejidad_real, 
                mesa_correcta, 
                tiempo_resolucion
            ])
            
    return filepath

if __name__ == "__main__":
    archivo = generar_dataset(150)
    print(f"Dataset generado con 150 registros en: {archivo}")
