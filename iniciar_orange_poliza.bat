@echo off
setlocal

rem ============================================================================
rem    PROPIEDAD INTELECTUAL Y LICENCIA COMERCIAL CERRADA
rem    ============================================================================
rem    Autor Legal y Titular de Derechos: JAVIER ILLAN GONZALEZ
rem    Organizacion: ORANGE CREW
rem    Contacto: ILLANJAVIER9@GMAIL.COM
rem
rem    ADVERTENCIA LEGAL (MEXICO Y GLOBAL):
rem    Este codigo fuente y su arquitectura son propiedad intelectual exclusiva de
rem    JAVIER ILLAN GONZALEZ. Queda estrictamente prohibida su reproduccion,
rem    distribucion, modificacion, ingenieria inversa, copia o uso comercial sin la
rem    autorizacion expresa y por escrito del autor. Obra protegida conforme a la
rem    Ley Federal del Derecho de Autor y tratados internacionales aplicables.
rem    ============================================================================

set DIR=%~dp0
echo Orange Poliza Engine - Inicializador Docker (SaaS Edition)
echo.

where docker >nul 2>nul
if errorlevel 1 (
    echo No se encontro Docker Desktop instalado.
    echo Es OBLIGATORIO para ejecutar el sistema por las restricciones locales de tu maquina.
    pause
    exit /b 1
)

echo Iniciando Contenedores de Orange Poliza SaaS en segundo plano...
docker-compose up -d

echo.
echo Esperando a que el servidor Gunicorn se levante...
ping 127.0.0.1 -n 6 > nul

echo.
echo Iniciando el servidor...
echo   - En esta computadora:      http://127.0.0.1:8000
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    goto :ip_encontrada
)
:ip_encontrada
set IP=%IP: =%
if defined IP (
    echo   - Desde otras computadoras de tu red: http://%IP%:8000
)
echo.

start "" http://127.0.0.1:8000

echo Presiona cualquier tecla para salir de esta ventana (el servidor seguira corriendo en el fondo mediante Docker).
echo Si deseas detenerlo, puedes abrir Docker Desktop o ejecutar: docker-compose stop
pause
