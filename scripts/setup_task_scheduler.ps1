# Registra a execução diária no Windows Task Scheduler.
# Rode este script UMA VEZ, manualmente, num PowerShell comum (não precisa ser admin
# para uma tarefa que roda só com o usuário atual logado).
#
# Uso:
#   .\scripts\setup_task_scheduler.ps1
#   .\scripts\setup_task_scheduler.ps1 -Time "07:00" -Segment "Restaurantes"

param(
    [string]$Time = "06:00",
    [string]$Segment = ""
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Error "Python não encontrado no PATH. Instale o Python (python.org) e rode este script de novo."
    exit 1
}

$ScriptArgs = "`"$ProjectRoot\scripts\run_daily.py`""
if ($Segment -ne "") {
    $ScriptArgs += " `"$Segment`""
}

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument $ScriptArgs -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask -TaskName "ProspectorLeadsLicencas" `
    -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Prospeccao diaria de leads com licencas municipais vencidas/ausentes (Fortaleza-CE)" `
    -Force

Write-Host "Tarefa 'ProspectorLeadsLicencas' registrada: roda todo dia às $Time."
Write-Host "Para testar agora: Start-ScheduledTask -TaskName 'ProspectorLeadsLicencas'"
Write-Host "Para remover: Unregister-ScheduledTask -TaskName 'ProspectorLeadsLicencas' -Confirm:`$false"
