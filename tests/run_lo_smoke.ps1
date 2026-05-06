$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

$repoRoot = Split-Path -Parent $PSScriptRoot
$soffice = "C:\Program Files\LibreOffice\program\soffice.exe"
$loPy = "C:\Program Files\LibreOffice\program\python.exe"
$profileDir = Join-Path $repoRoot ".tmp_lo_profile"
$outputFile = Join-Path $PSScriptRoot "smoke_last_output.json"

if (-not (Test-Path $soffice)) {
    throw "LibreOffice bulunamadi: $soffice"
}
if (-not (Test-Path $loPy)) {
    throw "LibreOffice Python bulunamadi: $loPy"
}

New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
$profileUri = "file:///" + ($profileDir -replace "\\", "/")
$accept = "socket,host=127.0.0.1,port=2003;urp;"

$proc = Start-Process -FilePath $soffice -ArgumentList @(
    "--headless",
    "--nologo",
    "--norestore",
    "--nolockcheck",
    "-env:UserInstallation=$profileUri",
    "--accept=$accept",
    "--calc"
) -PassThru -WindowStyle Hidden

try {
    Start-Sleep -Seconds 8
    $env:LO_TEST_HOST = "127.0.0.1"
    $env:LO_TEST_PORT = "2003"
    & $loPy (Join-Path $PSScriptRoot "libreoffice_smoke_test.py") | Tee-Object -FilePath $outputFile
    exit $LASTEXITCODE
}
finally {
    if ($proc) {
        cmd /c "taskkill /PID $($proc.Id) /T /F" | Out-Null
    }
    if (Test-Path $profileDir) {
        Remove-Item -Recurse -Force $profileDir
    }
}
