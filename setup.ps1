param(
    [switch]$Force,
    [switch]$SkipUiBuild
)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {

function Require-Node22 {
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        throw 'Node.js 22.13+ is required. Install Node.js from https://nodejs.org/ and rerun .\setup.ps1.'
    }
    $rawVersion = (& node -v).Trim()
    if ($LASTEXITCODE -ne 0 -or -not ($rawVersion -match '^v(\d+)\.(\d+)\.(\d+)')) {
        throw "Could not parse Node.js version: $rawVersion"
    }
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if ($major -lt 22 -or ($major -eq 22 -and $minor -lt 13)) {
        throw "Node.js >= 22.13.0 is required (found $rawVersion)."
    }
    Write-Host "Node.js $rawVersion detected."
}

function Require-Python314 {
    $pyCheck = "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)"
    if ($env:LAYA_PYTHON) {
        & $env:LAYA_PYTHON -c $pyCheck 2>$null
        if ($LASTEXITCODE -eq 0) {
            $ver = (& $env:LAYA_PYTHON --version 2>&1) -join ' '
            Write-Host "$ver detected (via LAYA_PYTHON)."
            return
        }
        throw "LAYA_PYTHON ('$env:LAYA_PYTHON') must be Python 3.14."
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.14 -c $pyCheck 2>$null
        if ($LASTEXITCODE -eq 0) {
            $ver = (& py -3.14 --version 2>&1) -join ' '
            Write-Host "$ver detected."
            return
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c $pyCheck 2>$null
        if ($LASTEXITCODE -eq 0) {
            $ver = (& python --version 2>&1) -join ' '
            Write-Host "$ver detected."
            return
        }
    }
    throw 'Python 3.14 is required, but was not found. Install Python 3.14 (https://www.python.org/downloads/ or winget install Python.Python.3.14) and rerun .\setup.ps1.'
}

Write-Host '=== Laya Playground one-time Windows setup (Python 3.14, CPU mode) ==='
Require-Python314
Require-Node22

Write-Host "`n[1/4] Setting up Python backend (CPU PyTorch)..."
$backendSetup = Join-Path $PSScriptRoot 'backend\setup.ps1'
if ($Force) {
    & $backendSetup --force
} else {
    & $backendSetup
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[2/4] Checking ui/.openai/hosting.json..."
$hostingDir = Join-Path $PSScriptRoot 'ui\.openai'
$hostingFile = Join-Path $hostingDir 'hosting.json'
if (-not (Test-Path $hostingFile)) {
    New-Item -ItemType Directory -Force -Path $hostingDir | Out-Null
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($hostingFile, "{`n  `"d1`": `"DB`",`n  `"r2`": `"`"`n}`n", $utf8NoBom)
    Write-Host 'Created ui/.openai/hosting.json.'
} else {
    Write-Host 'ui/.openai/hosting.json already exists; leaving untouched.'
}

Write-Host "`n[3/4] Checking UI dependencies..."
$uiDir = Join-Path $PSScriptRoot 'ui'
$vinextCmd = Join-Path $uiDir 'node_modules\.bin\vinext.cmd'
$wranglerBin = Join-Path $uiDir 'node_modules\wrangler\bin\wrangler.js'
if (-not $Force -and (Test-Path $vinextCmd) -and (Test-Path $wranglerBin)) {
    Write-Host 'UI dependencies are already installed. Skipping reinstall (pass -Force to reinstall).'
} else {
    Push-Location $uiDir
    try {
        $env:SHARP_IGNORE_GLOBAL_LIBVIPS = '1'
        & npm ci --include=dev --include=optional --prefer-offline --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
    if (-not (Test-Path $vinextCmd) -or -not (Test-Path $wranglerBin)) {
        throw 'UI dependency install finished, but vinext or wrangler is missing under ui/node_modules.'
    }
}

$distManifest = Join-Path $uiDir 'dist\server\wrangler.json'
if ($SkipUiBuild) {
    Write-Host "`n[4/4] Skipping UI build (-SkipUiBuild)."
} elseif (-not $Force -and (Test-Path $distManifest)) {
    Write-Host "`n[4/4] UI build already exists. Skipping rebuild (pass -Force to rebuild)."
} else {
    Write-Host "`n[4/4] Building UI bundle..."
    Push-Location $uiDir
    try {
        & node .\scripts\run-framework.mjs build
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
}

Write-Host "`nSetup complete (CPU mode, no GPU required)."
Write-Host 'Start both backend and UI with: .\run.ps1'
Write-Host 'Note: the first prediction request downloads the selected Laya checkpoint from Hugging Face.'
} finally {
    Pop-Location
}
