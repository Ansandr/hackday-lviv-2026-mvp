$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (Test-Path -LiteralPath '.venv/Scripts/python.exe') {
    & ./.venv/Scripts/python.exe -m src.support.run
} else {
    & python -m src.support.run
}
