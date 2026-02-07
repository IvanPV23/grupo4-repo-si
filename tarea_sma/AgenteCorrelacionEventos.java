/**
 * AgenteCorrelacionEventos: Recibe eventos y los correlaciona
 * Busca patrones de ataque y solicita análisis de malware
 */
import jade.core.Agent;
import jade.core.behaviours.*;
import jade.lang.acl.ACLMessage;
import jade.domain.DFService;
import jade.domain.FIPAException;
import jade.domain.FIPAAgentManagement.DFAgentDescription;
import jade.domain.FIPAAgentManagement.ServiceDescription;
import java.util.ArrayList;

public class AgenteCorrelacionEventos extends Agent {
    private ArrayList<String> eventosRecibidos = new ArrayList<String>();
    
    protected void setup() {
        System.out.println("[CORRELACION] Agente " + getLocalName() + " iniciado");
        
        // Registrar servicio
        registrarServicio();
        
        // Comportamiento: Recibir eventos y correlacionar
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                ACLMessage mensaje = receive();
                if (mensaje != null) {
                    String contenido = mensaje.getContent();
                    System.out.println("[CORRELACION] Evento recibido: " + contenido);
                    
                    eventosRecibidos.add(contenido);
                    
                    // Correlacionar eventos
                    String patron = detectarPatron();
                    if (!patron.equals("NORMAL")) {
                        System.out.println("[CORRELACION] ¡PATRÓN DETECTADO! " + patron);
                        
                        // Solicitar análisis de malware
                        solicitarAnalisisMalware(patron);
                        
                        // Enviar alerta a inteligencia de amenazas
                        enviarAInteligencia(patron);
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
        sd.setType("correlacion-eventos");
        sd.setName("correlacionador-principal");
        dfd.addServices(sd);
        try {
            DFService.register(this, dfd);
            System.out.println("[CORRELACION] Servicio registrado");
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
    
    private String detectarPatron() {
        if (eventosRecibidos.size() >= 2) {
            // Simulación simple de detección de patrones
            String ultimo = eventosRecibidos.get(eventosRecibidos.size() - 1);
            if (ultimo.contains("puerto") || ultimo.contains("escaneo")) {
                return "ATAQUE_RECONOCIMIENTO";
            } else if (ultimo.contains("login") || ultimo.contains("SSH")) {
                return "ATAQUE_FUERZA_BRUTA";
            } else if (ultimo.contains("conexiones")) {
                return "POSIBLE_DDOS";
            }
        }
        return "NORMAL";
    }
    
    private void solicitarAnalisisMalware(String patron) {
        DFAgentDescription template = new DFAgentDescription();
        ServiceDescription sd = new ServiceDescription();
        sd.setType("analisis-malware");
        template.addServices(sd);
        
        try {
            DFAgentDescription[] result = DFService.search(this, template);
            if (result.length > 0) {
                ACLMessage solicitud = new ACLMessage(ACLMessage.REQUEST);
                solicitud.addReceiver(result[0].getName());
                solicitud.setContent("ANALIZAR_ARCHIVO:sospechoso_" + patron + ".exe");
                solicitud.setConversationId("analisis-malware");
                send(solicitud);
                System.out.println("[CORRELACION] Solicitud de análisis enviada");
            }
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
    
    private void enviarAInteligencia(String patron) {
        DFAgentDescription template = new DFAgentDescription();
        ServiceDescription sd = new ServiceDescription();
        sd.setType("threat-intelligence");
        template.addServices(sd);
        
        try {
            DFAgentDescription[] result = DFService.search(this, template);
            if (result.length > 0) {
                ACLMessage mensaje = new ACLMessage(ACLMessage.INFORM);
                mensaje.addReceiver(result[0].getName());
                mensaje.setContent("ALERTA:" + patron);
                mensaje.setConversationId("amenazas");
                send(mensaje);
                System.out.println("[CORRELACION] Alerta enviada a inteligencia");
            }
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
    
    protected void takeDown() {
        try {
            DFService.deregister(this);
            System.out.println("[CORRELACION] Agente finalizado");
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
}