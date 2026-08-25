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

rem Crea (o repara) el rol y la base de datos de la app en un PostgreSQL
rem que YA esta instalado, y deja webapp\.env con exactamente esas
rem credenciales -- para que nunca queden desalineadas. Uso tipico:
rem   - Primera vez: crea el rol y la base.
rem   - "Usuario o contrasena incorrectos" / error de autenticacion:
rem     vuelve a correr este archivo, te deja credenciales frescas y
rem     consistentes con el .env, y prueba la conexion al final.
rem
rem Si PostgreSQL todavia NO esta instalado en esta computadora, corre
rem primero instalar_postgres.bat (ese si lo instala desde cero).

set DIR=%~dp0
set ENV_FILE=%DIR%webapp\.env

echo ============================================
echo   Orange Poliza Engine - Crear/reparar base de datos
echo ============================================
echo.

rem --- Paso 1: localizar psql ---------------------------------------------

set PSQL=
for /f "delims=" %%p in ('where psql 2^>nul') do set PSQL=%%p
if not defined PSQL (
    for /d %%d in ("C:\Program Files\PostgreSQL\*") do (
        if exist "%%d\bin\psql.exe" set PSQL=%%d\bin\psql.exe
    )
)
if not defined PSQL (
    echo No se encontro PostgreSQL instalado en esta computadora.
    echo Corre primero instalar_postgres.bat ^(que si lo instala desde cero^).
    pause
    exit /b 1
)
echo PostgreSQL encontrado: %PSQL%

rem --- Paso 2: confirmar que el servicio este corriendo -------------------

set PG_SERVICE=
for /f "delims=" %%s in ('powershell -NoProfile -Command "(Get-Service | Where-Object { $_.Name -like 'postgresql*' } | Select-Object -First 1 -ExpandProperty Name)"') do set PG_SERVICE=%%s
if defined PG_SERVICE (
    for /f "delims=" %%e in ('powershell -NoProfile -Command "(Get-Service -Name '%PG_SERVICE%').Status"') do set PG_STATUS=%%e
    if not "!PG_STATUS!"=="Running" (
        echo El servicio "%PG_SERVICE%" no esta corriendo. Iniciandolo...
        net start "%PG_SERVICE%" >nul 2>&1
    )
    echo Servicio de PostgreSQL: %PG_SERVICE% ^(!PG_STATUS!^)
) else (
    echo AVISO: no se detecto el servicio de PostgreSQL automaticamente.
    echo Verifica en services.msc que este corriendo antes de continuar.
)

rem --- Paso 3: datos de conexion -------------------------------------------

echo.
set /p PG_SUPER_PASS=Contrasena del superusuario "postgres" de PostgreSQL:
if "%PG_SUPER_PASS%"=="" (
    echo No puede quedar vacia.
    pause
    exit /b 1
)

set DB_NAME=orange_poliza
set /p DB_NAME_INPUT=Nombre de la base de datos [%DB_NAME%]:
if not "%DB_NAME_INPUT%"=="" set DB_NAME=%DB_NAME_INPUT%

set DB_USER=orange_app
set /p DB_USER_INPUT=Usuario de PostgreSQL para la app [%DB_USER%]:
if not "%DB_USER_INPUT%"=="" set DB_USER=%DB_USER_INPUT%

set DB_PASS=
for /f "delims=" %%p in ('powershell -Command "Add-Type -AssemblyName System.Web; [System.Web.Security.Membership]::GeneratePassword(20,4)" 2^>nul') do set DB_PASS=%%p
if "%DB_PASS%"=="" set DB_PASS=OrangePoliza_%RANDOM%%RANDOM%
set /p DB_PASS_INPUT=Contrasena para "%DB_USER%" [Enter para usar una generada automaticamente]:
if not "%DB_PASS_INPUT%"=="" set DB_PASS=%DB_PASS_INPUT%

rem --- Paso 4: crear/actualizar rol y base ---------------------------------

echo.
echo Verificando conexion con el superusuario...
set PGPASSWORD=%PG_SUPER_PASS%
"%PSQL%" -U postgres -h localhost -c "SELECT 1;" >nul 2>&1
if errorlevel 1 (
    echo No se pudo conectar como "postgres" con esa contrasena. Verifica que
    echo sea correcta y que el servicio de PostgreSQL este corriendo.
    set PGPASSWORD=
    pause
    exit /b 1
)

echo Creando/actualizando el rol "%DB_USER%"...
"%PSQL%" -U postgres -h localhost -tc "SELECT 1 FROM pg_roles WHERE rolname='%DB_USER%'" > "%TEMP%\rolecheck.txt"
findstr /c:"1" "%TEMP%\rolecheck.txt" >nul
if errorlevel 1 (
    "%PSQL%" -U postgres -h localhost -c "CREATE ROLE %DB_USER% LOGIN PASSWORD '%DB_PASS%';"
) else (
    "%PSQL%" -U postgres -h localhost -c "ALTER ROLE %DB_USER% WITH LOGIN PASSWORD '%DB_PASS%';"
)

echo Creando la base "%DB_NAME%" si no existe...
"%PSQL%" -U postgres -h localhost -tc "SELECT 1 FROM pg_database WHERE datname='%DB_NAME%'" > "%TEMP%\dbcheck.txt"
findstr /c:"1" "%TEMP%\dbcheck.txt" >nul
if errorlevel 1 (
    "%PSQL%" -U postgres -h localhost -c "CREATE DATABASE %DB_NAME% OWNER %DB_USER%;"
) else (
    "%PSQL%" -U postgres -h localhost -c "ALTER DATABASE %DB_NAME% OWNER TO %DB_USER%;"
    echo La base "%DB_NAME%" ya existia; se dejo con "%DB_USER%" como dueno.
)

del "%TEMP%\rolecheck.txt" "%TEMP%\dbcheck.txt" >nul 2>&1
set PGPASSWORD=

rem --- Paso 5: escribir webapp\.env ----------------------------------------

echo.
echo Escribiendo %ENV_FILE% ...
(
    echo ORANGE_DB_HOST=localhost
    echo ORANGE_DB_PORT=5432
    echo ORANGE_DB_NAME=%DB_NAME%
    echo ORANGE_DB_USER=%DB_USER%
    echo ORANGE_DB_PASSWORD=%DB_PASS%
) > "%ENV_FILE%"

rem --- Paso 6: probar la conexion con las credenciales de la app ----------

echo.
echo Probando conexion con las credenciales de la app...
set PGPASSWORD=%DB_PASS%
"%PSQL%" -U %DB_USER% -h localhost -d %DB_NAME% -c "SELECT 1;" >nul 2>&1
if errorlevel 1 (
    set PGPASSWORD=
    echo.
    echo No se pudo validar la conexion con el usuario "%DB_USER%". Revisa que
    echo no haya otra regla de pg_hba.conf bloqueando conexiones locales por
    echo password, y vuelve a correr este archivo.
    pause
    exit /b 1
)
set PGPASSWORD=

echo.
echo ============================================
echo   Listo. Conexion verificada correctamente.
echo   Base de datos: %DB_NAME%
echo   Usuario:       %DB_USER%
echo   (credenciales guardadas en webapp\.env)
echo ============================================
echo.
echo Ahora corre iniciar_orange_poliza.bat.
echo.
pause
