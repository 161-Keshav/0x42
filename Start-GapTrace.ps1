$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$gaptracePython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $gaptracePython)) {
    python -m venv .venv
    & $gaptracePython -m pip install -r requirements-gaptrace.txt
}
& $gaptracePython scripts/run_apps.py
