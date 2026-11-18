param(
    [int]$UiPort = 5173,
    [int]$BackendPort = 8765,
    [int]$Threads = 2,
    [switch]$Offline,
    [switch]$OpenBrowser
)

$ErrorActionPreference = 'Stop'
$backendProc = $null
$browserJob = $null
$prevBackendUrl = $env:LAYA_BACKEND_URL
Push-Location $PSScriptRoot
try {

if ($UiPort -lt 1 -or $UiPort -gt 65535 -or $BackendPort -lt 1 -or $BackendPort -gt 65535) {
    throw 'Ports must be between 1 and 65535.'
}
if ($UiPort -eq $BackendPort) {
    throw 'UiPort and BackendPort must be different.'
}
if ($Threads -lt 1 -or $Threads -gt 32) {
    throw 'Threads must be between 1 and 32.'
}

function Assert-Python314Installed {
    $pyCheck = "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)"
    if ($env:LAYA_PYTHON) {
        & $env:LAYA_PYTHON -c $pyCheck 2>$null
        if ($LASTEXITCODE -eq 0) { return }
        throw "LAYA_PYTHON ('$env:LAYA_PYTHON') must be Python 3.14."
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.14 -c $pyCheck 2>$null
        if ($LASTEXITCODE -eq 0) { return }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c $pyCheck 2>$null
        if ($LASTEXITCODE -eq 0) { return }
    }
    throw 'Python 3.14 is required, but was not found. Install Python 3.14 (https://www.python.org/downloads/ or winget install Python.Python.3.14) and run .\setup.ps1.'
}

Assert-Python314Installed

$backendPython = Join-Path $PSScriptRoot 'backend\.venv\Scripts\python.exe'
$uiDir = Join-Path $PSScriptRoot 'ui'
$vinextCmd = Join-Path $uiDir 'node_modules\.bin\vinext.cmd'
$wranglerBin = Join-Path $uiDir 'node_modules\wrangler\bin\wrangler.js'

if (-not (Test-Path $backendPython) -or -not (Test-Path $vinextCmd) -or -not (Test-Path $wranglerBin)) {
    throw 'Missing dependencies. Run .\setup.ps1 first.'
}

& $backendPython -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw 'backend\.venv is not Python 3.14. Run .\setup.ps1 to rebuild the virtual environment with Python 3.14.'
}

function Assert-PortFree([int]$Port, [string]$HintFlag) {
    $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listening) {
        $ownerPid = ($listening | Select-Object -First 1).OwningProcess
        throw "Port $Port is already in use by PID $ownerPid. Stop it or pass $HintFlag <port>."
    }
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Start()
    } catch {
        throw "Port $Port is unavailable. Stop whatever is using it or pass $HintFlag <port>."
    } finally {
        $listener.Stop()
    }
}

Assert-PortFree -Port $BackendPort -HintFlag '-BackendPort'
Assert-PortFree -Port $UiPort -HintFlag '-UiPort'

$backendArgs = @('app.py', '--device', 'cpu', '--port', "$BackendPort", '--threads', "$Threads")
if ($Offline) {
    $backendArgs += '--offline'
}

function Stop-ProcessTree([int]$RootPid) {
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $RootPid" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -RootPid ([int]$child.ProcessId)
    }
    Stop-Process -Id $RootPid -Force -ErrorAction SilentlyContinue
}

    Write-Host "Starting Laya backend (CPU) on http://127.0.0.1:$BackendPort ..."
    $backendProc = Start-Process -FilePath $backendPython `
        -ArgumentList $backendArgs `
        -WorkingDirectory (Join-Path $PSScriptRoot 'backend') `
        -NoNewWindow `
        -PassThru

    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        if ($backendProc.HasExited) {
            throw "Backend exited unexpectedly with code $($backendProc.ExitCode)."
        }
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/api/health" -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if (-not $ready) {
        throw "Backend did not become healthy on http://127.0.0.1:$BackendPort/api/health."
    }

    $env:LAYA_BACKEND_URL = "http://127.0.0.1:$BackendPort"
    Write-Host "Starting Laya UI on http://127.0.0.1:$UiPort (backend: $env:LAYA_BACKEND_URL) ..."
    if ($OpenBrowser) {
        $browserJob = Start-Job -ScriptBlock {
            param($Url)
            for ($i = 0; $i -lt 40; $i++) {
                try {
                    $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
                    if ($r.StatusCode -eq 200) {
                        Start-Process $Url
                        break
                    }
                } catch {
                    Start-Sleep -Milliseconds 500
                }
            }
        } -ArgumentList "http://127.0.0.1:$UiPort"
    }

    Push-Location $uiDir
    try {
        & node .\scripts\run-framework.mjs dev --port "$UiPort"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
} finally {
    if ($browserJob) {
        Stop-Job -Job $browserJob -ErrorAction SilentlyContinue
        Remove-Job -Job $browserJob -Force -ErrorAction SilentlyContinue
    }
    if ($null -eq $prevBackendUrl) {
        Remove-Item Env:LAYA_BACKEND_URL -ErrorAction SilentlyContinue
    } else {
        $env:LAYA_BACKEND_URL = $prevBackendUrl
    }
    if ($backendProc -and -not $backendProc.HasExited) {
        Write-Host "`nStopping Laya backend (PID $($backendProc.Id))..."
        Stop-ProcessTree -RootPid $backendProc.Id
    }
    Pop-Location
}
