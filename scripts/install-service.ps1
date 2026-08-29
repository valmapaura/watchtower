<#
.SYNOPSIS
    Install Watchtower as a background task using Windows Task Scheduler
    (no third-party software needed — built into Windows).

.DESCRIPTION
    Creates a scheduled task that runs the watchtower motion recorder
    automatically at logon / startup, so it records continuously.

    No NSSM, no service installs, no admin rights beyond what Task Scheduler
    needs to register the task.

.EXAMPLE
    .\scripts\install-service.ps1                  # install + start
    .\scripts\install-service.ps1 -Uninstall        # stop + remove
    .\scripts\install-service.ps1 -Status           # check status
#>
param(
    [string]$TaskName = "WatchtowerRecorder",
    [string]$ConfigPath = "config.json",
    [switch]$Uninstall,
    [switch]$Status
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# Resolve the python executable that runs this project
$python = (Get-Command python).Source
if (-not $python) { Write-Error "python not found on PATH." }

# Working directory + config path
$workDir = Split-Path $root -Parent
$config = Join-Path $workDir $ConfigPath
$pythonArgs = "-m", "watchtower.main", "--config", $config

function Install-Task {
    Write-Host "Creating scheduled task '$TaskName'..." -ForegroundColor Cyan

    $action = New-ScheduledTaskAction -Execute $python -Argument ($pythonArgs -join " ") -WorkingDirectory $workDir

    # Run whether the user is logged on or not, at startup and on logon.
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $trigger2 = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 9999)

    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger, $trigger2 -Settings $settings -Principal $principal -Force | Out-Null
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Task '$TaskName' installed and started." -ForegroundColor Green
    Write-Host "It will run automatically at login/startup." -ForegroundColor DarkCyan
}

function Uninstall-Task {
    Write-Host "Stopping '$TaskName'..." -ForegroundColor Yellow
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Task removed." -ForegroundColor Green
}

function Show-Status {
    Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Select-Object TaskName, State
    Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue | Select-Object LastRunTime, LastTaskResult
}

if ($Uninstall) { Uninstall-Task; exit }
if ($Status)    { Show-Status;    exit }

Install-Task
