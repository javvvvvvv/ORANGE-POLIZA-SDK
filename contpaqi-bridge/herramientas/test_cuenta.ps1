$com = New-Object -ComObject SDKCONTPAQNG.TSdkSesion
$com.iniciaConexion()
$com.firmaUsuario()
$com.abreEmpresa("ctPRUEBA")

$cuenta = $com.cuentas.buscaPorId(1)
$cuenta.GetType().InvokeMember($null, [System.Reflection.BindingFlags]::GetType, $null, $cuenta, $null) | Out-Null
[System.Runtime.InteropServices.Marshal]::GetIDispatchForObject($cuenta) | Out-Null
$cuenta.GetType().GetMembers() | Sort-Object Name -Unique | Select-Object Name | Format-Table -AutoSize

$com.cierraEmpresa()
$com.finalizaConexion()
