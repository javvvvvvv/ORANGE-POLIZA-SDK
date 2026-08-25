@echo off
setlocal EnableDelayedExpansion

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

rem Instala (si hace falta) PostgreSQL, crea la base y el usuario de la app,
rem y escribe webapp\.env. Corre esto UNA sola vez, en la computadora que
rem va a actuar como servidor (la misma donde luego corres
rem iniciar_orange_poliza.bat). Las demas computadoras de la red NO
rem necesitan correr este archivo: solo abren el navegador en
rem http://<IP-del-servidor>:5000

set DIR=%~dp0
set PGVERSION=16.4-1
set PGINSTALLER_URL=https://get.enterprisedb.com/postgresql/postgresql-%PGVERSION%-windows-x64.exe
set PGINSTALLER=%TEMP%\postgresql-installer.exe
set ENV_FILE=%DIR%webapp\.env

echo ============================================
echo   Orange Poliza Engine - Instalador de BD
echo ============================================
echo.

net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Este instalador necesita permisos de administrador.
    echo Cierra esta ventana y vuelve a abrir instalar_postgres.bat
    echo con clic derecho -^> "Ejecutar como administrador".
    pause
    exit /b 1
)

rem --- Paso 1: localizar o instalar PostgreSQL --------------------------

set PSQL=
for /f "delims=" %%p in ('where psql 2^>nul') do set PSQL=%%p
if not defined PSQL (
    for /d %%d in ("C:\Program Files\PostgreSQL\*") do (
        if exist "%%d\bin\psql.exe" set PSQL=%%d\bin\psql.exe
    )
)

if defined PSQL (
    echo PostgreSQL ya esta instalado en esta computadora ^(%PSQL%^).
) else (
    echo PostgreSQL no esta instalado. Descargando el instalador oficial...
    echo   %PGINSTALLER_URL%
    powershell -Command "Invoke-WebRequest -Uri '%PGINSTALLER_URL%' -OutFile '%PGINSTALLER%'"
    if not exist "%PGINSTALLER%" (
        echo No se pudo descargar el instalador. Descargalo manualmente desde
        echo https://www.postgresql.org/download/windows/ e instalalo, luego
        echo vuelve a correr este archivo.
        pause
        exit /b 1
    )

    set /p PG_SUPER_PASS=Escribe una contrasena para el superusuario "postgres" de PostgreSQL:
    if "!PG_SUPER_PASS!"=="" (
        echo No puede quedar vacia. Vuelve a correr el instalador.
        pause
        exit /b 1
    )

    echo Instalando PostgreSQL ^(esto tarda unos minutos^)...
    "%PGINSTALLER%" --mode unattended --unattendedmodeui minimal ^
        --superpassword "!PG_SUPER_PASS!" --servicename postgresql ^
        --serverport 5432 --disable-stackbuilder 1

    for /d %%d in ("C:\Program Files\PostgreSQL\*") do (
        if exist "%%d\bin\psql.exe" set PSQL=%%d\bin\psql.exe
    )
    if not defined PSQL (
        echo La instalacion de PostgreSQL no termino correctamente.
        echo Instalalo manualmente y vuelve a correr este archivo.
        pause
        exit /b 1
    )
    echo PostgreSQL instalado correctamente.
)

if not defined PG_SUPER_PASS (
    set /p PG_SUPER_PASS=Contrasena del superusuario "postgres" ^(la que definiste al instalar^):
)

rem --- Paso 2: datos de la base y el usuario de la app -------------------

echo.
set DB_NAME=orange_poliza
set /p DB_NAME_INPUT=Nombre de la base de datos [%DB_NAME%]:
if not "%DB_NAME_INPUT%"=="" set DB_NAME=%DB_NAME_INPUT%

set DB_USER=orange_app
set /p DB_USER_INPUT=Usuario de PostgreSQL para la app [%DB_USER%]:
if not "%DB_USER_INPUT%"=="" set DB_USER=%DB_USER_INPUT%

set DB_PASS=
for /f "delims=" %%p in ('powershell -Command "[System.Web.Security.Membership]::GeneratePassword(20,4)" 2^>nul') do set DB_PASS=%%p
if "%DB_PASS%"=="" set DB_PASS=OrangePoliza_%RANDOM%%RANDOM%
set /p DB_PASS_INPUT=Contrasena para el usuario "%DB_USER%" [generada automaticamente, Enter para usarla]:
if not "%DB_PASS_INPUT%"=="" set DB_PASS=%DB_PASS_INPUT%

echo.
echo Creando rol y base de datos...
set PGPASSWORD=%PG_SUPER_PASS%

"%PSQL%" -U postgres -h localhost -tc "SELECT 1 FROM pg_roles WHERE rolname='%DB_USER%'" > "%TEMP%\rolecheck.txt"
findstr /c:"1" "%TEMP%\rolecheck.txt" >nul
if errorlevel 1 (
    "%PSQL%" -U postgres -h localhost -c "CREATE ROLE %DB_USER% LOGIN PASSWORD '%DB_PASS%';"
) else (
    "%PSQL%" -U postgres -h localhost -c "ALTER ROLE %DB_USER% WITH LOGIN PASSWORD '%DB_PASS%';"
)

"%PSQL%" -U postgres -h localhost -tc "SELECT 1 FROM pg_database WHERE datname='%DB_NAME%'" > "%TEMP%\dbcheck.txt"
findstr /c:"1" "%TEMP%\dbcheck.txt" >nul
if errorlevel 1 (
    "%PSQL%" -U postgres -h localhost -c "CREATE DATABASE %DB_NAME% OWNER %DB_USER%;"
) else (
    echo La base "%DB_NAME%" ya existia; se conserva tal cual.
)

del "%TEMP%\rolecheck.txt" "%TEMP%\dbcheck.txt" >nul 2>&1
set PGPASSWORD=

rem --- Paso 3: permitir conexiones desde otras computadoras de la red ----

echo.
echo Configurando PostgreSQL para aceptar conexiones de la red local...
set PG_SERVICE=
for /f "delims=" %%s in ('powershell -NoProfile -Command "(Get-Service | Where-Object { $_.Name -like 'postgresql*' } | Select-Object -First 1 -ExpandProperty Name)"') do set PG_SERVICE=%%s

for /d %%d in ("C:\Program Files\PostgreSQL\*") do set PGDATA_DIR=%%d\data
if exist "%PGDATA_DIR%\postgresql.conf" (
    powershell -Command ^
        "(Get-Content '%PGDATA_DIR%\postgresql.conf') -replace '^#?listen_addresses.*', \"listen_addresses = '*'\" | Set-Content '%PGDATA_DIR%\postgresql.conf'"
    findstr /c:"host all all samehost trust" "%PGDATA_DIR%\pg_hba.conf" >nul
    if errorlevel 1 (
        echo host    all    all    0.0.0.0/0    scram-sha-256 >> "%PGDATA_DIR%\pg_hba.conf"
    )
    if defined PG_SERVICE (
        net stop "%PG_SERVICE%" >nul 2>&1
        net start "%PG_SERVICE%" >nul 2>&1
        echo Servicio "%PG_SERVICE%" reiniciado.
    ) else (
        echo No se detecto automaticamente el nombre del servicio de PostgreSQL.
        echo Reinicialo a mano desde services.msc para que tome los cambios.
    )
) else (
    echo No se encontro postgresql.conf automaticamente. Si otras computadoras
    echo de tu red necesitan conectarse DIRECTO a este PostgreSQL ^(en vez de
    echo solo abrir el navegador hacia esta maquina^), edita a mano:
    echo   listen_addresses = '*'          en postgresql.conf
    echo   host all all 0.0.0.0/0 scram-sha-256   en pg_hba.conf
)

echo.
echo Recuerda tambien permitir el puerto 5432 en el Firewall de Windows
echo si otras computadoras se conectaran directo a esta base de datos.

rem --- Paso 4: escribir webapp\.env ---------------------------------------

echo.
echo Escribiendo %ENV_FILE% ...
(
    echo ORANGE_DB_HOST=localhost
    echo ORANGE_DB_PORT=5432
    echo ORANGE_DB_NAME=%DB_NAME%
    echo ORANGE_DB_USER=%DB_USER%
    echo ORANGE_DB_PASSWORD=%DB_PASS%
) > "%ENV_FILE%"

echo.
echo ============================================
echo   Listo.
echo   Base de datos: %DB_NAME%
echo   Usuario:       %DB_USER%
echo   Contrasena:    %DB_PASS%
echo   (guardada tambien en webapp\.env)
echo ============================================
echo.
echo Ahora corre iniciar_orange_poliza.bat en ESTA misma computadora.
echo Las demas computadoras de tu red solo necesitan abrir el navegador
echo en http://^<IP-de-esta-computadora^>:5000 - no corren ningun .bat.
echo.
pause
