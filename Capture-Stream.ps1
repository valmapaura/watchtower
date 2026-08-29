# -------------------------------------------------------------
#  Capture-Stream.ps1
# -------------------------------------------------------------
#  Usage:
#    .\Capture-Stream.ps1 -RtspUrl <url> -Duration 30 -OutputDir .\recordings
#
#  Parameters
#    -RtspUrl   : Full RTSP URL (including credentials)
#    -Duration  : Seconds to record (default 30). Omit or set 0 for indefinite recording.
#    -OutputDir : Directory where the MP4 file will be saved (default .\recordings)
# -------------------------------------------------------------

param(
    [Parameter(Mandatory=$true)]
    [string]$RtspUrl,

    [int]$Duration = 30,

    [string]$OutputDir = ".\recordings",

    # Set to $true to include audio. The camera streams PCM_ALAW, which can't be stored in MP4
    # directly, so we re-encode it to AAC (the bundled ffmpeg includes an AAC encoder).
    [bool]$IncludeAudio = $false
)

# Resolve ffmpeg path (bundled with the camera tools) relative to this script, so it
# works regardless of the current working directory.
$root = $PSScriptRoot
if (-not $root) { $root = (Get-Location).Path }
$ffmpegPath = Resolve-Path (Join-Path $root "installation\CAM720VmsTools\ffmpegExe\ffmpeg.exe") -ErrorAction Stop

# Ensure the output directory exists
if (-not (Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir | Out-Null }

# Build timestamp for filename
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputFile = Join-Path $OutputDir "cam_$timestamp.mp4"

# Build ffmpeg arguments
# Video is copied directly (no re‑encoding). Audio handling depends on $IncludeAudio:
#   * $true  – re-encode audio to AAC so it's compatible with the MP4 container.
#   * $false – drop audio with "-an" to produce a valid MP4.
$ffArgs = @(
    "-rtsp_transport", "tcp",
    "-i", $RtspUrl,
    "-c:v", "copy"
)

if ($IncludeAudio) {
    # The camera's PCM_ALAW audio can't go into MP4 as-is, so re-encode to AAC.
    $ffArgs += @("-c:a", "aac", "-b:a", "128k")
} else {
    $ffArgs += "-an"
}

if ($Duration -gt 0) {
    $ffArgs += @("-t", $Duration)
}

$ffArgs += $outputFile

Write-Host "Recording stream to $outputFile"

# Start ffmpeg process
$proc = Start-Process -FilePath $ffmpegPath -ArgumentList $ffArgs -NoNewWindow -Wait -PassThru

if ($proc.ExitCode -eq 0) {
    Write-Host "Recording completed successfully."
} else {
    Write-Error "ffmpeg exited with code $($proc.ExitCode). Check the RTSP URL and network connectivity."
}
