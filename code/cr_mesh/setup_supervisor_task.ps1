# Persist the Two Rocks supervisors across reboots (non-admin).
#
# A full Scheduled Task needs elevation on this box, so we use HKCU logon
# entries instead — each launches its supervisor (windowless, via pythonw) at
# every user logon. Each supervisor holds its own named mutex, so a double-logon
# can't spawn two. Linux nodes are already systemd services.
#
# Two SEPARATE, non-overlapping supervisors:
#   CadenceTwoRocksMesh  -> cr_supervisor.py      (mesh: worker, bridges, governor, windings)
#   CadenceApiSupervisor -> cr_api_supervisor.py  (API services: compute, lattice, resolver,
#                                                  llm-conduit, compute-v1 :8099)
#
# Run:  powershell -ExecutionPolicy Bypass -File setup_supervisor_task.ps1
$ErrorActionPreference = "Stop"
$py   = (Get-Command python -ErrorAction SilentlyContinue).Source
$pyw  = if ($py) { Join-Path (Split-Path $py) "pythonw.exe" } else { "$env:LOCALAPPDATA\Programs\Python\Python314\pythonw.exe" }
$HERE = "C:\Users\affor\egt_repo_rebuild\current_repo\code\cr_mesh"
if (-not (Test-Path $pyw)) { throw "pythonw.exe not found at $pyw" }

$supervisors = @{
    "CadenceTwoRocksMesh"  = "$HERE\cr_supervisor.py"
    "CadenceApiSupervisor" = "$HERE\cr_api_supervisor.py"
}
foreach ($Name in $supervisors.Keys) {
    $sup = $supervisors[$Name]
    $val = "`"$pyw`" `"$sup`""
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name $Name -Value $val
    Write-Output "Registered logon autostart '$Name':"
    Write-Output "  $val"
    Write-Output "  start now:  Start-Process -FilePath `"$pyw`" -ArgumentList `"$sup`""
    Write-Output ""
}
