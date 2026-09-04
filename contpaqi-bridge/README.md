# ContpaqiBridge

Puente HTTP local entre Orange Poliza Engine (Python/Flask) y el SDK COM real
de CONTPAQi (`SDKCONTPAQNG.TSdkSesion`). Vive dentro de este repo en
`contpaqi-bridge/` para que ya no dependa de una ruta personal en una sola
máquina.

## Por qué se reescribió

El bridge anterior no estaba en control de versiones y tenía tres problemas
raíz confirmados:

1. **Host header spoofing**: usaba `HttpListener`, que enruta por el header
   `Host` (restricción de `http.sys`), registrado solo para `localhost`. El
   cliente Python tenía que mandar un `Host: localhost:5005` falso para que
   la petición no fuera rechazada. Este bridge usa Kestrel, que no tiene esa
   restricción — ya no hace falta el truco.
2. **COM STA llamado desde hilos MTA**: causa probable de las fallas
   intermitentes. Aquí todas las llamadas al SDK pasan por un único hilo STA
   dedicado (`Services/StaComDispatcher.cs`).
3. **`abreEmpresa` con el nombre equivocado**: las pruebas (`test_com.ps1`)
   confirmaron que hay que mandar el nombre interno de base de datos
   (`ctNOMBRE_EMPRESA`), no el nombre bonito que ve el usuario. El lado
   Python ahora manda siempre `base_datos_contpaqi` (columna que ya existía
   en la tabla `empresas`), nunca texto libre.

## Pendiente / requiere tu confirmación

- **Propiedades de usuario/contraseña de la sesión**: el código intenta
  `sesion.usuario` / `sesion.contrasena` antes de `firmaUsuario()`. Si el
  nombre real es otro, la excepción del SDK lo va a decir explícitamente.
  Si `firmaUsuario()` abre un diálogo de login cuando no hay credenciales
  fijadas, el bridge se va a quedar colgado esperando un clic que nunca
  llega — corre `herramientas/listar_metodos.ps1` sin `-Propiedad` para ver
  los miembros reales de la sesión y encontrar el nombre correcto.
- **Catálogo de cuentas**: se asume que `sesion.cuentas` expone
  `obtenerCuentas()`, `getCodigo()`, `getNombre()`, `getCodigoAgp()` — esto
  sí está confirmado por `methods.txt`, solo falta confirmar el nombre de
  la propiedad de sesión que lo expone.
- **Creación de pólizas vía SDK en vivo**: NO implementado con métodos
  adivinados a propósito — no hay ninguno confirmado todavía. El endpoint
  `/` responde con éxito=false y explica cómo confirmarlo. Mientras tanto
  usa el exportador de archivo (`.txt`/`.xls`, ya validado) e impórtalo en
  CONTPAQi. Para automatizarlo: usa
  `herramientas/listar_metodos.ps1 -Propiedad polizas` (o el nombre que
  resulte correcto) para descubrir su API real, igual que se hizo aquí.

## Instalación

Requiere .NET 8 SDK y CONTPAQi Contabilidad instalado en la misma máquina
(el SDK COM solo existe donde CONTPAQi está instalado).

```bat
cd contpaqi-bridge
copy appsettings.example.json appsettings.json
:: edita appsettings.json con el usuario/contraseña de CONTPAQi
dotnet run
```

`appsettings.json` está en `.gitignore` — nunca se sube al repo.

## Correr como servicio (recomendado en vez de una ventana de consola)

Una ventana de `dotnet run` se cae si alguien la cierra o la PC reinicia.
Para producción, publica y registra como servicio de Windows:

```bat
dotnet publish -c Release -r win-x86 --self-contained -o publicado
sc create ContpaqiBridge binPath= "C:\ruta\a\publicado\ContpaqiBridge.exe"
sc start ContpaqiBridge
```
