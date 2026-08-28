$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$url = 'http://127.0.0.1:4173/?view=workspace'

[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Text.UTF8Encoding]::new($false)

$listeners = Get-NetTCPConnection -LocalPort 4173 -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $listeners) {
    Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
}

$env:VITE_RUNTIME_MODE = 'api'
Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev' -WorkingDirectory $projectPath -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds(30)
do {
    try {
        Invoke-WebRequest -Uri 'http://127.0.0.1:4173/local-admin/model-config' -UseBasicParsing -TimeoutSec 2 | Out-Null
        Start-Process $url
        exit 0
    }
    catch {
        Start-Sleep -Milliseconds 500
    }
} while ((Get-Date) -lt $deadline)

Add-Type -AssemblyName PresentationFramework
[System.Windows.MessageBox]::Show('Demo1 did not start. Check Node.js and port 4173.', '1Cat Demo1') | Out-Null
exit 1
