@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Orange Poliza Engine - Emitir licencia

rem ============================================================================
rem   Emisor de licencias - Orange Crew
rem   USO EXCLUSIVO DE JAVIER ILLAN GONZALEZ. No compartir este archivo ni la
rem   contrasena con clientes.
rem
rem   Esto NO es un candado de seguridad fuerte (la contrasena queda a la
rem   vista si alguien abre este .bat con el Bloc de notas): es solo para
rem   que no lo corra por accidente alguien mas en tu computadora. La
rem   proteccion real esta en la firma del archivo orange.lic.
rem
rem   PARA CAMBIAR LA CONTRASENA: busca la linea que dice
rem       set "CLAVE_ESPERADA=OrangeCrew2026"
rem   mas abajo, y cambia el texto entre comillas por la tuya.
rem ============================================================================
set "CLAVE_ESPERADA=OrangeCrew2026"

echo ============================================================
echo   ORANGE POLIZA ENGINE - Emitir licencia (orange.lic)
echo ============================================================
echo.

set /p "CLAVE=Escribe la contrasena para continuar: "

if "%CLAVE%"=="%CLAVE_ESPERADA%" goto clave_ok

echo.
echo Contrasena incorrecta. No se hizo nada.
echo.
pause
exit /b 1

:clave_ok
echo.
echo Contrasena correcta.
echo.

set "PY="
where python >nul 2>&1
if not errorlevel 1 set "PY=python"
if not defined PY (
    where python3 >nul 2>&1
    if not errorlevel 1 set "PY=python3"
)
if not defined PY (
    where py >nul 2>&1
    if not errorlevel 1 set "PY=py"
)
if not defined PY (
    echo No se encontro Python instalado en esta computadora.
    echo Instalalo desde https://www.python.org/downloads/
    echo y marca la casilla "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

echo Usando: %PY%
echo Abriendo el emisor de licencias...
echo.
"%PY%" "%~dp0herramientas\generar_licencia.py"
set "CODIGO_SALIDA=%errorlevel%"

echo.
if not "%CODIGO_SALIDA%"=="0" (
    echo El script termino con un error ^(codigo %CODIGO_SALIDA%^). Revisa el mensaje de arriba.
)

echo.
pause
