$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $pyCheck = "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)"
    $hasPy314 = $false
    if ($env:LAYA_PYTHON) {
        & $env:LAYA_PYTHON -c $pyCheck 2>$null
        $hasPy314 = ($LASTEXITCODE -eq 0)
    } else {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3.14 -c $pyCheck 2>$null
            $hasPy314 = ($LASTEXITCODE -eq 0)
        }
        if (-not $hasPy314 -and (Get-Command python -ErrorAction SilentlyContinue)) {
            & python -c $pyCheck 2>$null
            $hasPy314 = ($LASTEXITCODE -eq 0)
        }
    }
    if (-not $hasPy314) {
        throw 'Python 3.14 is required, but was not found. Install Python 3.14 (https://www.python.org/downloads/ or winget install Python.Python.3.14) and try again.'
    }

    if (-not (Test-Path '.venv/Scripts/python.exe')) {
        throw 'Run .\setup.ps1 first.'
    }
    & .venv/Scripts/python.exe -c $pyCheck 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'backend\.venv is not Python 3.14. Run .\setup.ps1 to rebuild it with Python 3.14.'
    }
    & .venv/Scripts/python.exe app.py @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
