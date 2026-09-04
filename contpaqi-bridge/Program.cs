// ============================================================================
// PROPIEDAD INTELECTUAL Y LICENCIA COMERCIAL CERRADA
// ============================================================================
// Autor Legal y Titular de Derechos: JAVIER ILLAN GONZALEZ
// Organización: ORANGE CREW
// Contacto: ILLANJAVIER9@GMAIL.COM
//
// ADVERTENCIA LEGAL (MÉXICO Y GLOBAL):
// Este código fuente y su arquitectura son propiedad intelectual exclusiva de
// JAVIER ILLAN GONZALEZ. Queda estrictamente prohibida su reproducción,
// distribución, modificación, ingeniería inversa, copia o uso comercial sin la
// autorización expresa y por escrito del autor. Obra protegida conforme a la
// Ley Federal del Derecho de Autor y tratados internacionales aplicables.
// ============================================================================
//
// Cambios clave respecto al bridge anterior:
//  - Kestrel en vez de HttpListener: Kestrel no enruta por Host header
//    (http.sys sí), así que ya no hace falta que el cliente Python mande
//    un header "Host: localhost:5005" falso para engañar al bridge.
//  - Escucha en 0.0.0.0, así host.docker.internal (Docker Desktop) llega
//    sin trucos.
//  - Todas las llamadas al SDK COM pasan por un único hilo STA dedicado
//    (StaComDispatcher) — el SDK es STA y Kestrel corre en el thread
//    pool (MTA); llamarlo directo desde ahí es la causa más probable de
//    las fallas intermitentes que había antes.
using ContpaqiBridge.Models;
using ContpaqiBridge.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Configuration
    .AddJsonFile("appsettings.json", optional: true, reloadOnChange: true)
    .AddEnvironmentVariables(prefix: "CONTPAQI_BRIDGE_");

var puerto = builder.Configuration.GetValue("Puerto", 5005);
builder.WebHost.ConfigureKestrel(opciones =>
{
    opciones.ListenAnyIP(puerto);
});

builder.Services.AddSingleton<StaComDispatcher>();
builder.Services.AddSingleton<ContpaqiSdkService>();

var app = builder.Build();

// Empresas: nombre_interno_contpaqi (columna base_datos_contpaqi del lado
// Python) se manda directo desde Flask, así que aquí no se necesita mapeo
// nombre-bonito -> nombre-interno; eso ya se resolvió del lado Python.

app.MapGet("/salud", async (ContpaqiSdkService sdk) =>
{
    var disponible = await sdk.VerificarSdkDisponibleAsync();
    return disponible
        ? Results.Ok(new RespuestaBridge(true, "SDK de CONTPAQi disponible."))
        : Results.StatusCode(StatusCodes.Status503ServiceUnavailable);
});


app.MapGet("/empresas/listar", async (ContpaqiSdkService sdk, ILogger<Program> log) =>
{
    try
    {
        var empresas = await sdk.ListarEmpresasAsync();
        return Results.Ok(new { exito = true, empresas });
    }
    catch (Exception ex)
    {
        log.LogError(ex, "Fallo al listar empresas");
        return Results.Ok(new RespuestaBridge(false, $"Error del SDK: {ex.Message}"));
    }
});

app.MapPost("/cuentas/crear", async (CrearCuentaRequest req, ContpaqiSdkService sdk, ILogger<Program> log) =>
{
    if (string.IsNullOrWhiteSpace(req.Empresa)) return Results.BadRequest(new RespuestaBridge(false, "Falta la empresa."));
    try
    {
        var result = await sdk.CrearCuentaAsync(req.Empresa, req.Cuenta);
        return Results.Ok(result);
    }
    catch (Exception ex)
    {
        log.LogError(ex, "Fallo al crear cuenta en {Empresa}", req.Empresa);
        return Results.Ok(new RespuestaBridge(false, $"Error del SDK al crear cuenta: {ex.Message}"));
    }
});

app.MapPost("/cuentas/listar", async (CuentasRequest req, ContpaqiSdkService sdk, ILogger<Program> log) =>
{
    if (string.IsNullOrWhiteSpace(req.Empresa))
    {
        return Results.BadRequest(new RespuestaBridge(false, "Falta el nombre interno de la empresa."));
    }
    try
    {
        var cuentas = await sdk.ListarCuentasAsync(req.Empresa);
        return Results.Ok(new { exito = true, mensaje = "OK", cuentas });
    }
    catch (Exception ex)
    {
        log.LogError(ex, "Fallo al listar cuentas para {Empresa}", req.Empresa);
        return Results.Ok(new RespuestaBridge(false, $"Error del SDK al listar cuentas: {ex.Message}"));
    }
});

app.MapPost("/", async (ExportarPolizasRequest req, ContpaqiSdkService sdk, ILogger<Program> log) =>
{
    if (string.IsNullOrWhiteSpace(req.Empresa))
    {
        return Results.BadRequest(new RespuestaBridge(false, "Falta el nombre interno de la empresa."));
    }
    try
    {
        var resultado = await sdk.CrearPolizasAsync(req.Empresa, req.Polizas);
        return Results.Ok(resultado);
    }
    catch (Exception ex)
    {
        log.LogError(ex, "Fallo al exportar pólizas para {Empresa}", req.Empresa);
        return Results.Ok(new RespuestaBridge(false, $"Error del SDK al exportar pólizas: {ex.Message}"));
    }
});

app.Logger.LogInformation("ContpaqiBridge escuchando en el puerto {Puerto}", puerto);
app.Run();

