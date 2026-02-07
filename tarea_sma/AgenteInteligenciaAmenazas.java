/**
 * AgenteInteligenciaAmenazas: Enriquece alertas con contexto
 * Consulta base de datos de amenazas conocidas
 */
import jade.core.Agent;
import jade.core.behaviours.*;
import jade.lang.acl.ACLMessage;
import jade.domain.DFService;
import jade.domain.FIPAException;
import jade.domain.FIPAAgentManagement.DFAgentDescription;
import jade.domain.FIPAAgentManagement.ServiceDescription;
import java.util.HashMap;

public class AgenteInteligenciaAmenazas extends Agent {
    private HashMap<String, String> baseDatosAmenazas;
    
    protected void setup() {
        System.out.println("[INTELIGENCIA] Agente " + getLocalName() + " iniciado");
        
        // Inicializar base de datos de amenazas
        inicializarBD();
        
        // Registrar servicio
        registrarServicio();
        
        // Comportamiento: Escuchar alertas y enriquecerlas
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                ACLMessage mensaje = receive();
                if (mensaje != null) {
                    String contenido = mensaje.getContent();
                    System.out.println("[INTELIGENCIA] Alerta recibida: " + contenido);
                    
                    // Enriquecer con información
                    String enriquecido = enriquecerAlerta(contenido);
                    System.out.println("[INTELIGENCIA] Contexto: " + enriquecido);
                    
                    // Enviar a orquestador para respuesta
                    enviarAOrquestador(enriquecido);
                } else {
                    block();
                }
            }
        });
    }
    
    private void inicializarBD() {
        baseDatosAmenazas = new HashMap<String, String>();
        baseDatosAmenazas.put("ATAQUE_RECONOCIMIENTO", "ORIGEN:China|GRUPO:APT28|SEVERIDAD:MEDIA");
        baseDatosAmenazas.put("ATAQUE_FUERZA_BRUTA", "ORIGEN:Rusia|GRUPO:FancyBear|SEVERIDAD:ALTA");
        baseDatosAmenazas.put("POSIBLE_DDOS", "ORIGEN:Botnet|GRUPO:Mirai|SEVERIDAD:CRITICA");
        System.out.println("[INTELIGENCIA] Base de datos de amenazas cargada");
    }
    
    private void registrarServicio() {
        DFAgentDescription dfd = new DFAgentDescription();
        dfd.setName(getAID());
        ServiceDescription sd = new ServiceDescription();
        sd.setType("threat-intelligence");
        sd.setName("inteligencia-amenazas");
        dfd.addServices(sd);
        try {
            DFService.register(this, dfd);
            System.out.println("[INTELIGENCIA] Servicio registrado");
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
    
    private String enriquecerAlerta(String alerta) {
        String patron = alerta.replace("ALERTA:", "");
        String contexto = baseDatosAmenazas.get(patron);
        if (contexto != null) {
            return patron + "|" + contexto + "|PREDICCION:Escalada a compromiso total";
        }
        return patron + "|ORIGEN:Desconocido|SEVERIDAD:BAJA";
    }
    
    private void enviarAOrquestador(String alertaEnriquecida) {
        DFAgentDescription template = new DFAgentDescription();
        ServiceDescription sd = new ServiceDescription();
        sd.setType("orquestacion-respuesta");
        template.addServices(sd);
        
        try {
            DFAgentDescription[] result = DFService.search(this, template);
            if (result.length > 0) {
                ACLMessage mensaje = new ACLMessage(ACLMessage.INFORM);
                mensaje.addReceiver(result[0].getName());
                mensaje.setContent("AMENAZA_ENRIQUECIDA:" + alertaEnriquecida);
                mensaje.setConversationId("respuesta-incidente");
                send(mensaje);
                System.out.println("[INTELIGENCIA] Amenaza enriquecida enviada a orquestador");
            }
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
    
    protected void takeDown() {
        try {
            DFService.deregister(this);
            System.out.println("[INTELIGENCIA] Agente finalizado");
        } catch (FIPAException fe) {
            fe.printStackTrace();
        }
    }
}