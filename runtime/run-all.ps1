param(
    [switch]$NoWait,
    [string]$BusinessPack = ""
)

$ErrorActionPreference = "Stop"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$webRoot = Join-Path (Split-Path -Parent $root) "arkaim-web"
$logs = Join-Path $root "logs"

if (-not $BusinessPack -and (Test-Path env:BUSINESS_PACK)) {
    $BusinessPack = $env:BUSINESS_PACK
}
if ($BusinessPack) {
    $env:BUSINESS_PACK = $BusinessPack
    Write-Host "Business pack: $BusinessPack" -ForegroundColor Cyan
}

$coreHost = $env:CORE_HOST; if (-not $coreHost) { $coreHost = "127.0.0.1" }
$corePort = [int]$env:CORE_PORT; if (-not $corePort) { $corePort = 8642 }

New-Item -ItemType Directory -Path $logs -Force | Out-Null

Write-Host "=== Arkaim Runtime :: Start All ===" -ForegroundColor Cyan

# -- Проверка venv --
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Python .venv не найден: $venvPython" -ForegroundColor Red
    Write-Host "  Создай его: cd runtime; python -m venv .venv; .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# -- Проверка node_modules --
$nodeModules = Join-Path $webRoot "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "[ERROR] node_modules не найден: $nodeModules" -ForegroundColor Red
    Write-Host "  Установи: cd arkaim-web; npm install" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/2] Starting Core (port $coreHost`:$corePort)..." -ForegroundColor Yellow
$env:PYTHONPATH = $root
$coreJob = Start-Process -FilePath $venvPython -ArgumentList "-m uvicorn core.main:app --host $coreHost --port $corePort --log-level info" `
    -WorkingDirectory $root -WindowStyle Normal -PassThru
Write-Host "  Core PID: $($coreJob.Id)" -ForegroundColor Green

if (-not $NoWait) {
    $coreReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "http://$coreHost`:$corePort/health" -UseBasicParsing -ErrorAction Stop
            if ($r.StatusCode -eq 200) { $coreReady = $true; break }
        } catch {}
    }
    if ($coreReady) { Write-Host "  Core: READY" -ForegroundColor Green }
    else { Write-Host "  Core: TIMEOUT" -ForegroundColor Red }
}

Write-Host "[2/2] Starting Frontend (Next.js :3000)..." -ForegroundColor Yellow
$npmCommand = if ($IsWindows -or $env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
$feJob = Start-Process -FilePath $npmCommand -ArgumentList "run dev" `
    -WorkingDirectory $webRoot -WindowStyle Normal -PassThru
Write-Host "  Frontend PID: $($feJob.Id)" -ForegroundColor Green

Write-Host "`n=== All components launched ===" -ForegroundColor Cyan
Write-Host "  Backend:  http://$coreHost`:$corePort" -ForegroundColor Gray
Write-Host "  API Docs: http://$coreHost`:$corePort/docs" -ForegroundColor Gray
Write-Host "  Web UI:   http://$coreHost`:$corePort/_ui/book" -ForegroundColor Gray
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Gray
Write-Host "  Logs: $logs" -ForegroundColor Gray