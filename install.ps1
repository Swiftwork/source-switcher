# Windows startup installer for source-switcher
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$usbId = Read-Host "USB VID:PID to watch (run 'python -m source_switcher list-usb' to find it)"
$onConnect = Read-Host "Source on connect [dp2]"
if (-not $onConnect) { $onConnect = "dp2" }
$onDisconnect = Read-Host "Source on disconnect [dp1]"
if (-not $onDisconnect) { $onDisconnect = "dp1" }
$displayIdx = Read-Host "Display index, 0-based [0]"
if (-not $displayIdx) { $displayIdx = "0" }

$python = (Get-Command python).Source
$startupDir = [Environment]::GetFolderPath("Startup")
$vbsPath = Join-Path $startupDir "source-switcher.vbs"

# VBScript wrapper to run without a visible console window
$vbs = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """$python"" -m source_switcher watch --display $displayIdx --usb $usbId --on-connect $onConnect --on-disconnect $onDisconnect", 0, False
"@

# Set PYTHONPATH in user environment
[Environment]::SetEnvironmentVariable("PYTHONPATH", "$scriptDir\src", "User")

Set-Content -Path $vbsPath -Value $vbs

Write-Host ""
Write-Host "Installed to: $vbsPath"
Write-Host "Will start automatically on next login."
Write-Host "To start now, run: wscript '$vbsPath'"
Write-Host "To remove: delete '$vbsPath'"
