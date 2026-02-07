@echo off
echo Compilando agentes 

javac -cp ".;jade.jar" AgenteSensorRed.java
if %errorlevel% neq 0 goto error

javac -cp ".;jade.jar" AgenteAnalizadorMalware.java
if %errorlevel% neq 0 goto error

javac -cp ".;jade.jar" AgenteCorrelacionEventos.java
if %errorlevel% neq 0 goto error

javac -cp ".;jade.jar" AgenteInteligenciaAmenazas.java
if %errorlevel% neq 0 goto error

javac -cp ".;jade.jar" AgenteOrquestadorRespuesta.java
if %errorlevel% neq 0 goto error

goto end

:error
echo.
echo ERROR: La compilacion fallo

:end
pause