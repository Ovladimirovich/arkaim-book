# Требует админ-прав: запусти правой кнопкой → "Run with PowerShell" 
# или из админ-PowerShell: .\stop-arkaim-services.ps1

$services = @("ArkaimCore", "ArkaimGateway")

foreach ($name in $services) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if ($null -eq $svc) {
        Write-Host "[$name] не найден" -ForegroundColor Yellow
        continue
    }

    if ($svc.Status -eq 'Running') {
        Write-Host "[$name] останавливаю..." -ForegroundColor Cyan
        Stop-Service -Name $name -Force -ErrorAction Stop
        Write-Host "[$name] остановлен" -ForegroundColor Green
    } else {
        Write-Host "[$name] уже остановлен" -ForegroundColor Gray
    }

    if ($svc.StartType -ne 'Disabled') {
        Write-Host "[$name] ставлю Disabled..." -ForegroundColor Cyan
        Set-Service -Name $name -StartupType Disabled -ErrorAction Stop
        Write-Host "[$name] тип запуска: Disabled" -ForegroundColor Green
    }
}

Write-Host "`nПроверка порта 8080:" -ForegroundColor Cyan
$port = netstat -ano | findstr ":8080 .*LISTEN"
if ($port) { Write-Host "  Порт занят: $port" -ForegroundColor Red }
else { Write-Host "  Порт 8080 свободен" -ForegroundColor Green }

Read-Host "Нажми Enter для выхода"