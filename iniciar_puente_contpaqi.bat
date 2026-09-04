@echo off
REM Ya no depende de una ruta de usuario fija: usa la carpeta donde vive
REM este .bat, asi funciona igual en cualquier maquina que tenga el repo.
cd /d "%~dp0contpaqi-bridge"
if not exist appsettings.json (
    echo Falta contpaqi-bridge\appsettings.json
    echo Copia appsettings.example.json a appsettings.json y pon tu usuario/contrasena de CONTPAQi.
    pause
    exit /b 1
)
echo Iniciando ContpaqiBridge...
dotnet run
pause
