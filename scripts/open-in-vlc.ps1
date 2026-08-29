<#
.SYNOPSIS
    Opens the cam720 RTSP live stream in VLC.

.DESCRIPTION
    Reads the stream URL from config.json (username/password/host/path)
    and launches VLC pointed at it. VLC handles digest auth automatically.

.EXAMPLE
    .\scripts\open-in-vlc.ps1
#>
$ErrorActionPreference = "Stop"

$configPath = Join-Path $PSScriptRoot "..\config.json"
if (-not (Test-Path $configPath)) {
    Write-Error "config.json not found at $configPath - copy config.example.json to config.json and fill it in."
}

$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
$cam = $cfg.camera
$url = "rtsp://{0}:{1}@{2}:{3}{4}" -f $cam.username, $cam.password, $cam.host, $cam.rtsp_port, $cam.rtsp_path
Write-Host "Opening stream: $url" -ForegroundColor Cyan

# Locate VLC
$vlcPath = $null
$vlcCmd = Get-Command vlc.exe -ErrorAction SilentlyContinue
if ($vlcCmd) {
    $vlcPath = $vlcCmd.Source
}
else {
    $candidates = @(
        "$env:ProgramFiles\VideoLAN\VLC\vlc.exe",
        "${env:ProgramFiles(x86)}\VideoLAN\VLC\vlc.exe",
        "$env:LOCALAPPDATA\Programs\VideoLAN\VLC\vlc.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $vlcPath = $c; break }
    }
}

if (-not $vlcPath) {
    Write-Error "VLC not found. Install it from https://www.videolan.org/vlc/ and try again."
}

Start-Process -FilePath $vlcPath -ArgumentList "`"$url`""
Write-Host "VLC launched. (If no window appeared, check VLC is installed.)" -ForegroundColor Green
