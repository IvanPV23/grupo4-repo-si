import csv
import httpx
import asyncio
import time
from utils.metricas import obtener_resumen_metricas
import json

API_URL = "http://localhost:8000/tickets"
CSV_PATH = "data/raw/tickets_completos.csv"

async def procesar_ticket(client, fila):
    ticket_data = {
        "ticket_id": fila["ticket_id"],
        "tipo_ticket": fila["tipo_ticket"],
        "tipo_error": fila["tipo_error"],
        "solicitante": fila["solicitante"],
        "area": fila["area"],
        "titulo": fila["titulo"],
        "descripcion": fila["descripcion"],
        "prioridad": fila["prioridad"]
    }
    try:
        response = await client.post(API_URL, json=ticket_data, timeout=10.0)
        return response.status_code == 200
    except Exception as e:
        print(f"Error procesando {fila['ticket_id']}: {e}")
        return False

async def ejecutar_prueba_estres():
    print("Iniciando Prueba de Estrés del Sistema Inteligente de Derivación...")
    print(f"Leyendo dataset desde {CSV_PATH}")
    
    tickets_a_procesar = []
    try:
        with open(CSV_PATH, "r", encoding='utf-8') as f:
            reader = csv.DictReader(f)
            tickets_a_procesar = list(reader)
    except Exception as e:
        print(f"Error leyendo CSV: {e}")
        return

    total_tickets = len(tickets_a_procesar)
    print(f"[{total_tickets}] tickets cargados listos para inyectar en la API.")
    
    start_time = time.time()
    exitos = 0
    
    # Procesar concurrentemente en lotes para no ahogar el SO local
    lote_size = 20
    
    async with httpx.AsyncClient() as client:
        for i in range(0, total_tickets, lote_size):
            lote = tickets_a_procesar[i:i+lote_size]
            tareas = [procesar_ticket(client, fila) for fila in lote]
            resultados = await asyncio.gather(*tareas)
            exitos += sum(1 for r in resultados if r)
            print(f"Procesando: Lote {i//lote_size + 1} completado ({min(i+lote_size, total_tickets)}/{total_tickets})...")
            # Pequeña pausa para dar tiempo al Orquestador (n8n)
            await asyncio.sleep(0.5)
            
    end_time = time.time()
    tiempo_total = end_time - start_time
    
    print("\n" + "="*50)
    print("🚀 RESULTADOS DE LA PRUEBA DE ESTRÉS 🚀")
    print("="*50)
    print(f"Tickets enviados: {total_tickets}")
    print(f"Envios exitosos (HTTP 200): {exitos}")
    print(f"Tiempo total inyección: {round(tiempo_total, 2)} segundos")
    print(f"Rendimiento de entrada: {round(total_tickets/tiempo_total, 2)} tickets/segundo")
    
    print("\nEsperando 3 segundos a que los Agentes terminen de procesar las colas asíncronas...")
    await asyncio.sleep(3)
    
    print("\n" + "="*50)
    print("📊 MÉTRICAS FUNCIONALES DEL SISTEMA EXPERTO 📊")
    print("="*50)
    metricas = obtener_resumen_metricas()
    print(json.dumps(metricas, indent=2, ensure_ascii=False))
    print("="*50)
    
if __name__ == "__main__":
    asyncio.run(ejecutar_prueba_estres())
