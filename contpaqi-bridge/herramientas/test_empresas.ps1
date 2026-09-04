$com = New-Object -ComObject SDKCONTPAQNG.TSdkSesion
$com.iniciaConexion()
$com.firmaUsuario()

try {
    Write-Host "Trying .empresas"
    $emps = $com.empresas
    Write-Host "Success: $emps"
} catch {
    Write-Host "Failed .empresas"
}

try {
    Write-Host "Trying .obtenerEmpresas()"
    $emps = $com.obtenerEmpresas()
    Write-Host "Success: $emps"
} catch {
    Write-Host "Failed .obtenerEmpresas()"
}

$com.finalizaConexion()
