# ============================================================================
# PROPIEDAD INTELECTUAL Y LICENCIA COMERCIAL CERRADA
# Autor Legal y Titular de Derechos: JAVIER ILLAN GONZALEZ - ORANGE CREW
# ============================================================================
#
# Descubre en caliente los métodos/propiedades reales de un objeto del SDK
# de CONTPAQi, contra la sesión ya abierta. Úsalo para confirmar el nombre
# real de propiedades como "cuentas" o para encontrar el objeto de pólizas
# antes de automatizarlo (ver el TODO en ContpaqiSdkService.CrearPolizasAsync).
#
# Uso:
#   .\listar_metodos.ps1 -Empresa "ctNOMBRE_INTERNO_EMPRESA" -Propiedad "cuentas"
#
# Si -Propiedad se omite, solo abre la sesión/empresa y lista los miembros
# del propio objeto de sesión (útil para encontrar usuario/contrasena/polizas).

param(
    [Parameter(Mandatory = $true)]
    [string]$Empresa,

    [string]$Propiedad = ""
)

$com = New-Object -ComObject SDKCONTPAQNG.TSdkSesion
$com.iniciaConexion()
$com.firmaUsuario()
$res = $com.abreEmpresa($Empresa)
Write-Host "abreEmpresa($Empresa) -> $res"

if ($Propiedad -ne "") {
    $objetivo = $com.$Propiedad
} else {
    $objetivo = $com
}

$objetivo.GetType().InvokeMember(
    $null, [System.Reflection.BindingFlags]::GetType, $null, $objetivo, $null
) | Out-Null

[System.Runtime.InteropServices.Marshal]::GetIDispatchForObject($objetivo) | Out-Null
$tipo = $objetivo.GetType()
$tipo.GetMembers() | Sort-Object Name -Unique | Select-Object Name | Format-Table -AutoSize

$com.cierraEmpresa()
$com.finalizaConexion()
