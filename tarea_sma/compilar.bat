@echo off
echo Compilando agentes 

javac -cp ".;lib/*" AgenteSensorRed.java
if %errorlevel% neq 0 goto error

javac -cp ".;lib/*" AgenteAnalizadorMalware.java
if %errorlevel% neq 0 goto error

javac -cp ".;lib/*" AgenteCorrelacionEventos.java
if %errorlevel% neq 0 goto error

javac -cp ".;lib/*" AgenteInteligenciaAmenazas.java
if %errorlevel% neq 0 goto error

javac -cp ".;lib/*" AgenteOrquestadorRespuesta.java
if %errorlevel% neq 0 goto error

goto end

:error
echo.
echo ERROR: La compilacion fallo

:end
pause