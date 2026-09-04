$com = New-Object -ComObject SDKCONTPAQNG.TSdkSesion
$com.iniciaConexion()

$com.GetType().InvokeMember($null, [System.Reflection.BindingFlags]::GetType, $null, $com, $null) | Out-Null
[System.Runtime.InteropServices.Marshal]::GetIDispatchForObject($com) | Out-Null
$com.GetType().GetMembers() | Sort-Object Name -Unique | Select-Object Name | Format-Table -AutoSize

$com.finalizaConexion()
