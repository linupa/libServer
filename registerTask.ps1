$a = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File `"c:\clib\libServer\startUp.ps1`" -WindowStyle Hidden -ExecutionPolicy Bypass"
$t = New-ScheduledTaskTrigger -AtLogon
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$p = New-ScheduledTaskPrincipal -GroupId "BUILTIN\Administrators" -RunLevel Highest
Register-ScheduledTask -TaskName "LibServerPrep" -Action $a -Trigger $t -Settings $s -Principal $p

# Delete
# schtasks /Delete /TN "LibServerPrep"
