$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if ($env:LAYA_PYTHON) {
    & $env:LAYA_PYTHON scripts/install.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.11 scripts/install.py
} else {
    & python scripts/install.py
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
