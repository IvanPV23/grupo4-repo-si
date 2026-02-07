/**
 * AgenteOrquestadorRespuesta: Toma decisiones y ejecuta contramedidas
 * Recibe amenazas enriquecidas y genera respuesta automática
 */
import jade.core.Agent;
import jade.core.behaviours.*;
import jade.lang.acl.ACLMessage;
import jade.domain.DFService;
import jade.domain.FIPAException;
import jade.domain.FIPAAgentManagement.DFAgentDescription;
import jade.domain.FIPAAgentManagement.ServiceDescription;

public class AgenteOrquestadorRespuesta extends Agent {
    private int incidentesAtendidos = 0;
    
    protected void setup() {
        System.out.println("[ORQUESTADOR] Agente " + getLocalName() + " iniciado");
        
        // Registrar servicio
        registrarServicio();
        
        // Comportamiento: Recibir amenazas y ejecutar respuesta
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                ACLMessage mensaje = receive();
                if (mensaje != null) {
                    String contenido = mensaje.getContent();
                    System.out.println("\n[ORQUESTADOR] ========================================");
                    System.out.println("[ORQUESTADOR] AMENAZA RECIBIDA: " + contenido);
                    
                    incidentesAtendidos++;
                    
                    // Analizar severidad y tomar decisión
                    String decision = tomarDecision(contenido);
                    System.out.println("[ORQUESTADOR] DECISIÓN: " + decision);
                    
                    // Ejecutar contramedidas
                    ejecutarContramedidas(decision);
                    
                    // Generar reporte
                    generarReporte(contenido, decision);
                    
                    System.out.println("[ORQUESTADOR] ========================================\n");
                    
                    // Finalizar después de 3 incidentes
                    if (incidentesAtendidos >= 3) {
                        System.out.println("[ORQUESTADOR] 3 incidentes atendidos. Finalizando sistema...");
                        myAgent.doDelete();
                    }
                } else {
                    block();
                }
            }
        });
    }
    
    private void registrarServicio() {
        DFAgentDescription dfd = new DFAgentDescription();
        dfd.setName(getAID());
        ServiceDescription sd = new ServiceDescription();
        sd.setType("orquestacion-respuesta");
        sd.setName("orquestador-soc");
        dfd.addServices(sd);
        try {
            DFService.register(this, dfd);
            System.out.println("[ORQUESTADOR] Servicio registrado");
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
    
    private String tomarDecision(String amenaza) {
        if (amenaza.contains("CRITICA")) {
            return "RESPUESTA_AUTOMATICA:Bloquear IP origen + Aislar segmento de red + Notificar CSIRT";
        } else if (amenaza.contains("ALTA")) {
            return "RESPUESTA_AUTOMATICA:Bloquear IP origen + Activar monitoreo intensivo";
        } else if (amenaza.contains("MEDIA")) {
            return "RESPUESTA_MANUAL:Alertar administrador + Incrementar logging";
        } else {
            return "MONITOREAR:Sin acción automática + Registro en SIEM";
        }
    }
    
    private void ejecutarContramedidas(String decision) {
        System.out.println("[ORQUESTADOR] Ejecutando contramedidas...");
        
        if (decision.contains("Bloquear IP")) {
            System.out.println("  ✓ Regla de firewall aplicada: IP bloqueada");
        }
        if (decision.contains("Aislar")) {
            System.out.println("  ✓ VLAN aislada: Segmento de red en cuarentena");
        }
        if (decision.contains("Notificar")) {
            System.out.println("  ✓ Email enviado a equipo CSIRT");
        }
        if (decision.contains("Alertar")) {
            System.out.println("  ✓ Alerta enviada a administrador");
        }
        
        System.out.println("[ORQUESTADOR] Contramedidas ejecutadas exitosamente");
    }
    
    private void generarReporte(String amenaza, String decision) {
        System.out.println("\n--- REPORTE DE INCIDENTE #" + incidentesAtendidos + " ---");
        System.out.println("Amenaza: " + amenaza);
        System.out.println("Acción tomada: " + decision);
        System.out.println("Estado: MITIGADO");
        System.out.println("Timestamp: " + new java.util.Date());
        System.out.println("-------------------------------\n");
    }
    
    protected void takeDown() {
        try {
            DFService.deregister(this);
            System.out.println("[ORQUESTADOR] Sistema SOC finalizado");
            System.out.println("[ORQUESTADOR] Total incidentes atendidos: " + incidentesAtendidos);
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
}