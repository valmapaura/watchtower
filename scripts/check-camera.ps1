<#
.SYNOPSIS
    cam720 - camera health check: ping, open ports, RTSP server status.

.DESCRIPTION
    A quick diagnostic for the APCam WiFi camera. No credentials required.

.EXAMPLE
    .\scripts\check-camera.ps1
    .\scripts\check-camera.ps1 -CameraHost 192.168.1.247
#>
param(
    [string]$CameraHost = ""
)

$ErrorActionPreference = "Continue"

# If no host was passed, try to read it from config.json (if present).
if (-not $CameraHost) {
    $configPath = Join-Path $PSScriptRoot "..\config.json"
    if (Test-Path $configPath) {
        $cam = (Get-Content $configPath -Raw | ConvertFrom-Json).camera
        if ($cam.host) { $CameraHost = $cam.host }
    }
}
if (-not $CameraHost) { $CameraHost = "192.168.1.247" }

Write-Host "== cam720 health check: $CameraHost ==" -ForegroundColor Cyan

# 1. Ping
$ping = Test-Connection -ComputerName $CameraHost -Count 2 -ErrorAction SilentlyContinue
if ($ping) {
    $avg = [int](($ping | Measure-Object -Property ResponseTime -Average).Average)
    Write-Host "[OK]     Ping: alive (${avg} ms avg)" -ForegroundColor Green
}
else {
    Write-Host "[FAIL]   Ping: no response" -ForegroundColor Red
    Write-Host "        Are you on the same LAN (192.168.1.0/24)?" -ForegroundColor DarkYellow
    exit 1
}

# 2. Ports
$ports = @(
    @{ Port = 80;   Name = "Web UI (HTTP)" },
    @{ Port = 443;  Name = "Web UI (HTTPS)" },
    @{ Port = 554;  Name = "RTSP stream" },
    @{ Port = 8899; Name = "Camera SDK" }
)
foreach ($p in $ports) {
    $open = Test-NetConnection -ComputerName $CameraHost -Port $p.Port -WarningAction SilentlyContinue -InformationLevel Quiet
    $state = if ($open) { "[OK]     " } else { "[CLOSED] " }
    $color = if ($open) { "Green" } else { "DarkGray" }
    Write-Host ("{0} Port {1,-5} {2}" -f $state, $p.Port, $p.Name) -ForegroundColor $color
}

# 3. RTSP server responds to OPTIONS?
try {
    $client = New-Object System.Net.Sockets.TcpClient
    $client.Connect($CameraHost, 554)
    $stream = $client.GetStream()
    $stream.ReadTimeout = 4000
    $req = "OPTIONS rtsp://${CameraHost}:554/ RTSP/1.0`r`nCSeq: 1`r`nUser-Agent: cam720`r`n`r`n"
    $bytes = [System.Text.Encoding]::ASCII.GetBytes($req)
    $stream.Write($bytes, 0, $bytes.Length)
    $buf = New-Object byte[] 2048
    $n = $stream.Read($buf, 0, 2048)
    $resp = [System.Text.Encoding]::ASCII.GetString($buf, 0, $n)
    if ($resp -match "200 OK") {
        Write-Host "[OK]     RTSP server: responding (200 OK)" -ForegroundColor Green
    }
    else {
        Write-Host "[WARN]   RTSP server: unexpected response: $(($resp -split "`r`n")[0])" -ForegroundColor Yellow
    }
    $client.Close()
}
catch {
    Write-Host "[FAIL]   RTSP server: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Tip: stream at rtsp://<user>:<pass>@${CameraHost}:554/live/ch0  (see config.json)" -ForegroundColor DarkCyan
