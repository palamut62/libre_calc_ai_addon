param(
    [int]$Count = 3
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$singleRun = Join-Path $scriptDir "run_lo_smoke.ps1"
$jsonOut = Join-Path $scriptDir "smoke_last_output.json"

if (-not (Test-Path $singleRun)) {
    throw "Bulunamadi: $singleRun"
}

$allOk = $true
for ($i = 1; $i -le $Count; $i++) {
    Write-Host "=== Smoke Run $i/$Count ==="
    powershell -ExecutionPolicy Bypass -File $singleRun
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Run $i FAILED (exit=$LASTEXITCODE)" -ForegroundColor Red
        $allOk = $false
        break
    }

    if (-not (Test-Path $jsonOut)) {
        Write-Host "Run $i FAILED (json output missing)" -ForegroundColor Red
        $allOk = $false
        break
    }

    $obj = Get-Content $jsonOut -Raw | ConvertFrom-Json
    Write-Host ("pass={0}, fail={1}" -f $obj.pass_count, $obj.fail_count)
    if ($obj.fail_count -ne 0) {
        Write-Host "Run $i FAILED (fail_count != 0)" -ForegroundColor Red
        $allOk = $false
        break
    }
}

if (-not $allOk) {
    exit 1
}

Write-Host "All $Count runs passed." -ForegroundColor Green
exit 0
