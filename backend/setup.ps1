$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $pyCheck = "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)"
    if ($env:LAYA_PYTHON) {
        & $env:LAYA_PYTHON -c $pyCheck 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "LAYA_PYTHON ('$env:LAYA_PYTHON') must be Python 3.14."
        }
        & $env:LAYA_PYTHON scripts/install.py @args
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.14 -c $pyCheck 2>$null
        if ($LASTEXITCODE -eq 0) {
            & py -3.14 scripts/install.py @args
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -c $pyCheck 2>$null
            if ($LASTEXITCODE -ne 0) {
                throw 'Python 3.14 is required, but was not found. Install Python 3.14 (https://www.python.org/downloads/ or winget install Python.Python.3.14) and try again.'
            }
            & python scripts/install.py @args
        } else {
            throw 'Python 3.14 is required, but was not found. Install Python 3.14 (https://www.python.org/downloads/ or winget install Python.Python.3.14) and try again.'
        }
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c $pyCheck 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw 'Python 3.14 is required, but was not found. Install Python 3.14 (https://www.python.org/downloads/ or winget install Python.Python.3.14) and try again.'
        }
        & python scripts/install.py @args
    } else {
        throw 'Python 3.14 is required, but Python is not installed. Install Python 3.14 (https://www.python.org/downloads/ or winget install Python.Python.3.14) and try again.'
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}
