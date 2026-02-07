@echo off
echo ========================================
echo   SISTEMA DE CIBERSEGURIDAD - JADE
echo ========================================
echo.
echo Iniciando agentes...
echo.

java -cp ".;jade.jar" jade.Boot -gui -agents sensor:AgenteSensorRed;malware:AgenteAnalizadorMalware;correlacion:AgenteCorrelacionEventos;inteligencia:AgenteInteligenciaAmenazas;orquestador:AgenteOrquestadorRespuesta

echo.
echo Sistema finalizado
pause