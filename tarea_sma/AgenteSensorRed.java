/**
 * AgenteSensorRed: Versión INTERACTIVA
 * Recibe eventos manuales desde la GUI de JADE
 */
import jade.core.Agent;
import jade.core.AID;
import jade.core.behaviours.*;
import jade.lang.acl.ACLMessage;
import jade.domain.DFService;
import jade.domain.FIPAException;
import jade.domain.FIPAAgentManagement.DFAgentDescription;
import jade.domain.FIPAAgentManagement.ServiceDescription;

public class AgenteSensorRed extends Agent {
    
    protected void setup() {
        System.out.println("[SENSOR] Agente " + getLocalName() + " iniciado");
        
        // Registrar servicio en páginas amarillas
        registrarServicio();
        
        // Comportamiento: Escuchar eventos manuales
        addBehaviour(new CyclicBehaviour(this) {
            private int contador = 0;
            
            public void action() {
                ACLMessage mensaje = receive();
                if (mensaje != null) {
                    contador++;
                    String evento = mensaje.getContent();
                    
                    System.out.println("[SENSOR] EVENTO RECIBIDO #" + contador + "    ");
                    System.out.println("Contenido: " + evento);
                    System.out.println("Enviado por: " + mensaje.getSender().getLocalName());
                    System.out.println();
                    
                    // Validar que sea un evento válido
                    if (esEventoValido(evento)) {
                        buscarYEnviarEvento(evento);
                    } else {
                        System.out.println("Evento NO valido.");
                    }
                    System.out.println("════════════════════════════════════════════════");
                    System.out.println();
                    
                } else {
                    block();
                }
            }
        });
    }
    
    private boolean esEventoValido(String evento) {
        String[] eventosValidos = {
            "Intento de login fallido desde IP 192.168.1.100",
            "Tráfico sospechoso en puerto 4444",
            "Múltiples conexiones desde IP desconocida 10.0.0.50",
            "Escaneo de puertos detectado desde 172.16.0.20",
            "Actividad anómala en servicio SSH"
        };
        
        for (String valido : eventosValidos) {
            if (evento.equals(valido)) {
                return true;
            }
        }
        return false;
    }
    
    private void registrarServicio() {
        DFAgentDescription dfd = new DFAgentDescription();
        dfd.setName(getAID());
        ServiceDescription sd = new ServiceDescription();
        sd.setType("monitoreo-red");
        sd.setName("sensor-red-principal");
        dfd.addServices(sd);
        try {
            DFService.register(this, dfd);
            System.out.println("[SENSOR] Servicio registrado en páginas amarillas");
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
    
    private void buscarYEnviarEvento(String evento) {
        DFAgentDescription template = new DFAgentDescription();
        ServiceDescription sd = new ServiceDescription();
        sd.setType("correlacion-eventos");
        template.addServices(sd);
        
        try {
            DFAgentDescription[] result = DFService.search(this, template);
            if (result.length > 0) {
                ACLMessage mensaje = new ACLMessage(ACLMessage.INFORM);
                mensaje.addReceiver(result[0].getName());
                mensaje.setContent("EVENTO_RED:" + evento);
                mensaje.setConversationId("deteccion-eventos");
                send(mensaje);
                System.out.println("[SENSOR] Evento enviado al correlacionador");
            } else {
                System.out.println("[SENSOR] No se encontró correlacionador");
            }
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
    
    protected void takeDown() {
        try {
            DFService.deregister(this);
            System.out.println("\n[SENSOR] Agente finalizado y dado de baja de DF");
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
}