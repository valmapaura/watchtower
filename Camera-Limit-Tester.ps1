# -------------------------------------------------------------
#  Camera‑Limit‑Tester.ps1
# -------------------------------------------------------------
#  Usage:
#    .\Camera-Limit-Tester.ps1 -RtspUrl <url> -Streams 4 -Duration 10
#
#  Parameters
#    -RtspUrl   : Full RTSP URL (username/password included)
#    -Streams   : Number of concurrent streams to open
#    -Duration  : Seconds each stream records (default 10)
#    -LogDir    : Directory to write logs (default .\logs)
# -------------------------------------------------------------

param(
    [Parameter(Mandatory=$true)]
    [string]$RtspUrl,

    [int]$Streams = 4,

    [int]$Duration = 10,

    [string]$LogDir = ".\logs"
)

# Resolve ffmpeg path (bundled with the camera tools) relative to this script, so it
# works regardless of the current working directory.
$root = $PSScriptRoot
if (-not $root) { $root = (Get-Location).Path }
$ffmpegPath = Resolve-Path (Join-Path $root "installation\CAM720VmsTools\ffmpegExe\ffmpeg.exe") -ErrorAction Stop

# Ensure the log directory exists
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

# Helper function: launch a single ffmpeg instance that reads the RTSP stream
function Start-Stream {
    param(
        [int]$Id,
        [string]$Rtsp,
        [int]$Dur,
        [string]$LogFile
    )
    $args = @(
        "-i", $Rtsp,
        "-t", $Dur,
        "-c", "copy",
        "-f", "null",
        "-"
    )
    $proc = Start-Process -FilePath $ffmpegPath -ArgumentList $args `
        -RedirectStandardError $LogFile -NoNewWindow -PassThru
    return $proc
}

# Launch the requested number of concurrent streams
$processes = @()
for ($i = 1; $i -le $Streams; $i++) {
    $logFile = Join-Path $LogDir "stream_$i.log"
    $proc = Start-Stream -Id $i -Rtsp $RtspUrl -Dur $Duration -LogFile $logFile
    $processes += [PSCustomObject]@{ Id = $i; Process = $proc; LogFile = $logFile }
    Write-Host "Started stream $i (PID $($proc.Id))"
}

# Wait for all ffmpeg processes to finish
$processes | ForEach-Object { $_.Process.WaitForExit() }

# Summarise results – exit code, CPU time, and any error lines reported by ffmpeg
$summary = @()
foreach ($p in $processes) {
    $log = Get-Content $p.LogFile
    $errors = ($log | Select-String -Pattern "error|failed|packet loss|timeout" -CaseSensitive).Line
    $cpu = (Get-Process -Id $p.Process.Id).CPU
    $summary += [PSCustomObject]@{
        Stream   = $p.Id
        ExitCode = $p.Process.ExitCode
        CPUsec   = [math]::Round($cpu,2)
        Errors   = ($errors -join "`n") -replace "`r",""
    }
}

$summary | Format-Table -AutoSize
$summary | Export-Csv -Path (Join-Path $LogDir "summary.csv") -NoTypeInformation

Write-Host "`nTest complete. Logs written to $LogDir"
