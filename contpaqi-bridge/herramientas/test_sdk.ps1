$com = New-Object -ComObject SDKCONTPAQNG.TSdkSesion
$com.iniciaConexion()
$com.firmaUsuario()

$miembros = $com.GetType().GetMembers() | Select-Object Name -Unique
$miembros | Format-Table -AutoSize

$com.finalizaConexion()
