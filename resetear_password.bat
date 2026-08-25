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

rem Restablece la contrasena de un usuario sin necesitar la contrasena
rem anterior. Corre esto EN EL SERVIDOR (la computadora que tiene
rem webapp\.env apuntando a la base de datos real).

set DIR=%~dp0
set VENV=%DIR%webapp\.venv

if not exist "%VENV%\Scripts\python.exe" (
    echo No se encontro el entorno virtual de la app.
    echo Corre primero iniciar_orange_poliza.bat al menos una vez.
    pause
    exit /b 1
)

if not exist "%DIR%webapp\.env" (
    echo No se encontro webapp\.env. Corre primero instalar_postgres.bat
    echo en esta computadora, o copia el .env del servidor real aqui.
    pause
    exit /b 1
)

echo ============================================
echo   Orange Poliza Engine - Restablecer contrasena
echo ============================================
echo.

set /p ORANGE_USUARIO=Nombre de usuario a restablecer:
if "%ORANGE_USUARIO%"=="" (
    echo No escribiste ningun usuario.
    pause
    exit /b 1
)

set /p ORANGE_PASS_NUEVA=Contrasena nueva (minimo 4 caracteres):
if "%ORANGE_PASS_NUEVA%"=="" (
    echo No escribiste ninguna contrasena.
    pause
    exit /b 1
)

cd /d "%DIR%webapp"
call "%VENV%\Scripts\activate.bat"
python resetear_password.py "%ORANGE_USUARIO%" "%ORANGE_PASS_NUEVA%"

pause
