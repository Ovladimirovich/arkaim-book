Write-Host "Stopping Arkaim Runtime processes..." -ForegroundColor Yellow

# -- Остановка Core (uvicorn core.main:app) --
Get-Process | Where-Object { $_.ProcessName -eq "python" } | ForEach-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    if ($cmdLine -match "core\.main:app") {
        Write-Host "  Killing Core PID $($_.Id): $($cmdLine.Substring(0, [Math]::Min(80, $cmdLine.Length)))" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force
    }
}

# -- Остановка Frontend (npm run dev / next) --
Get-Process | Where-Object { $_.ProcessName -in @("node", "next") } | ForEach-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    if ($cmdLine -match "arkaim-web|next dev|npm run dev") {
        Write-Host "  Killing Frontend PID $($_.Id): $($cmdLine.Substring(0, [Math]::Min(80, $cmdLine.Length)))" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force
    }
}

# -- Освобождение портов 8642, 3000 --
foreach ($port in @(8642, 3000)) {
    $conns = netstat -ano | Select-String ":$port " | Select-String "LISTENING"
    foreach ($line in $conns) {
        $procId = ($line -split '\s+')[-1].Trim()
        if ($procId -and $procId -ne "0") {
            Write-Host "  Freeing port $port (PID $procId)" -ForegroundColor Gray
            taskkill /f /pid $procId 2>$null | Out-Null
        }
    }
}

Write-Host "Done." -ForegroundColor Green