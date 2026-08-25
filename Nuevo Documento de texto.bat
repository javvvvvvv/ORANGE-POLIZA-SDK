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

rem Restablece la contrasena del SUPERUSUARIO "postgres" cuando se te
rem olvido (distinto de resetear_password.bat, que es para usuarios de
rem Orange Poliza Engine). Truco estandar de PostgreSQL: habilita
rem "trust" (sin password) SOLO para conexiones locales de forma
rem temporal, cambia la contrasena, y deja pg_hba.conf exactamente
rem como estaba. Necesita permisos de administrador porque edita
rem archivos de configuracion de PostgreSQL y reinicia su servicio.

set DIR=%~dp0

echo ============================================
echo   Restablecer contrasena del superusuario "postgres"
echo ============================================
echo.

net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Este script necesita permisos de administrador.
    echo Cierra esta ventana y vuelve a abrirlo con clic derecho -^>
    echo "Ejecutar como administrador".
    pause
    exit /b 1
)

rem --- Localizar psql, carpeta de datos y el servicio ---------------------

set PSQL=
for /f "delims=" %%p in ('where psql 2^>nul') do set PSQL=%%p
if not defined PSQL (
    for /d %%d in ("C:\Program Files\PostgreSQL\*") do (
        if exist "%%d\bin\psql.exe" set PSQL=%%d\bin\psql.exe
    )
)
if not defined PSQL (
    echo No se encontro PostgreSQL instalado en esta computadora.
    pause
    exit /b 1
)

set PGDATA_DIR=
for /d %%d in ("C:\Program Files\PostgreSQL\*") do set PGDATA_DIR=%%d\data
if not exist "%PGDATA_DIR%\pg_hba.conf" (
    echo No se encontro pg_hba.conf en "%PGDATA_DIR%".
    echo Si instalaste PostgreSQL en otra ruta, edita este script o hazlo a mano.
    pause
    exit /b 1
)

set PG_SERVICE=
for /f "delims=" %%s in ('powershell -NoProfile -Command "(Get-Service | Where-Object { $_.Name -like 'postgresql*' } | Select-Object -First 1 -ExpandProperty Name)"') do set PG_SERVICE=%%s
if not defined PG_SERVICE (
    echo No se detecto el servicio de PostgreSQL automaticamente.
    pause
    exit /b 1
)

echo PostgreSQL:  %PSQL%
echo Datos:       %PGDATA_DIR%
echo Servicio:    %PG_SERVICE%
echo.

rem --- Respaldar pg_hba.conf ------------------------------------------------

set BACKUP=%PGDATA_DIR%\pg_hba.conf.antes_de_reset.bak
copy /y "%PGDATA_DIR%\pg_hba.conf" "%BACKUP%" >nul
echo Respaldo guardado en "%BACKUP%".

rem --- Habilitar "trust" solo para conexiones locales ------------------------

echo Habilitando acceso temporal sin contrasena SOLO para esta computadora...
powershell -NoProfile -Command ^
    "$c = Get-Content '%PGDATA_DIR%\pg_hba.conf';" ^
    "$c = $c | ForEach-Object {" ^
    "  if ($_ -match '^local\s+all\s+all\s+\S+\s*$') { $_ -replace '\S+\s*$', 'trust' }" ^
    "  elseif ($_ -match '^host\s+all\s+all\s+127\.0\.0\.1/32\s+\S+\s*$') { $_ -replace '\S+\s*$', 'trust' }" ^
    "  elseif ($_ -match '^host\s+all\s+all\s+::1/128\s+\S+\s*$') { $_ -replace '\S+\s*$', 'trust' }" ^
    "  else { $_ }" ^
    "};" ^
    "Set-Content -Path '%PGDATA_DIR%\pg_hba.conf' -Value $c"

net stop "%PG_SERVICE%" >nul 2>&1
net start "%PG_SERVICE%" >nul 2>&1
timeout /t 2 >nul

rem --- Cambiar la contrasena --------------------------------------------------

set PG_PASS_NUEVA=
set /p PG_PASS_NUEVA=Escribe la contrasena NUEVA para "postgres":
if "%PG_PASS_NUEVA%"=="" (
    echo No puede quedar vacia. Restaurando configuracion original...
    goto :restaurar
)

echo.
echo Aplicando la contrasena nueva...
set PGPASSWORD=
"%PSQL%" -U postgres -h localhost -c "ALTER ROLE postgres WITH PASSWORD '%PG_PASS_NUEVA%';"
if errorlevel 1 (
    echo.
    echo No se pudo cambiar la contrasena. Restaurando configuracion original...
    goto :restaurar
)

echo Contrasena de "postgres" actualizada correctamente.

:restaurar

rem --- Restaurar pg_hba.conf tal como estaba ----------------------------------

echo.
echo Restaurando la configuracion de seguridad original de pg_hba.conf...
copy /y "%BACKUP%" "%PGDATA_DIR%\pg_hba.conf" >nul
net stop "%PG_SERVICE%" >nul 2>&1
net start "%PG_SERVICE%" >nul 2>&1

echo.
echo ============================================
echo   Listo. pg_hba.conf quedo como estaba antes
echo   (ya NO acepta conexiones sin contrasena).
echo ============================================
echo.
echo Si la contrasena se cambio correctamente, ahora puedes correr
echo crear_base_datos.bat y usar esa contrasena nueva para "postgres".
echo.
pause