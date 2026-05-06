param(
    [string]$LoHost = "127.0.0.1",
    [int]$Port = 2002
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

$repoRoot = Split-Path -Parent $PSScriptRoot
$loPy = "C:\Program Files\LibreOffice\program\python.exe"
$outputFile = Join-Path $PSScriptRoot "smoke_running_lo_output.json"

if (-not (Test-Path $loPy)) {
    throw "LibreOffice Python bulunamadi: $loPy"
}

$env:LO_TEST_HOST = $LoHost
$env:LO_TEST_PORT = "$Port"

& $loPy (Join-Path $PSScriptRoot "libreoffice_smoke_test.py") | Tee-Object -FilePath $outputFile
exit $LASTEXITCODE
