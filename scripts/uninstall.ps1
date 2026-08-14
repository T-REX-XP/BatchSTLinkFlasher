#Requires -Version 5.1
<#
.SYNOPSIS
  Uninstall Batch ST-Link Flasher.

.DESCRIPTION
  Removes the application files, Start Menu / Desktop shortcuts, and the
  Add/Remove Programs registry entry. Safe to run from the installed copy
  or from the repo scripts folder.
#>
[CmdletBinding()]
param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$AppName = "Batch ST-Link Flasher"
$AppId = "BatchSTLinkFlasher"

function Get-InstallInfo {
    $candidates = @(
        (Join-Path $PSScriptRoot "install.json"),
        (Join-Path $env:LOCALAPPDATA "Programs\$AppId\install.json"),
        (Join-Path ${env:ProgramFiles} "$AppId\install.json")
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) {
            return Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
        }
    }
    return $null
}

function Remove-ShortcutDir {
    param([string]$Path)
    if ($Path -and (Test-Path $Path)) {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$info = Get-InstallInfo
$installRoot = $null
$allUsers = $false

if ($info) {
    $installRoot = [string]$info.InstallRoot
    $allUsers = [bool]$info.AllUsers
} else {
    $perUser = Join-Path $env:LOCALAPPDATA "Programs\$AppId"
    $perMachine = Join-Path ${env:ProgramFiles} $AppId
    if (Test-Path $perUser) { $installRoot = $perUser }
    elseif (Test-Path $perMachine) {
        $installRoot = $perMachine
        $allUsers = $true
    }
}

if (-not $installRoot -or -not (Test-Path $installRoot)) {
    if (-not $Quiet) {
        Write-Host "No $AppName installation found." -ForegroundColor Yellow
    }
    exit 0
}

if ($allUsers) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "This install was for all users. Re-run uninstall from an elevated PowerShell."
    }
}

if (-not $Quiet) {
    Write-Host "==> Uninstalling $AppName from $installRoot" -ForegroundColor Cyan
}

# Remove shortcuts
$programsUser = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$AppName"
$programsMachine = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\$AppName"
Remove-ShortcutDir $programsUser
Remove-ShortcutDir $programsMachine

$desktopLnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "$AppName.lnk"
if (Test-Path $desktopLnk) {
    Remove-Item -LiteralPath $desktopLnk -Force -ErrorAction SilentlyContinue
}

# Registry uninstall keys
foreach ($regPath in @(
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppId",
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppId"
    )) {
    if (Test-Path $regPath) {
        Remove-Item -LiteralPath $regPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# App files last (this script may live inside InstallRoot)
$tempUninstall = Join-Path $env:TEMP ("uninstall-" + $AppId + ".ps1")
Copy-Item -LiteralPath $PSCommandPath -Destination $tempUninstall -Force
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command",
    "Start-Sleep -Seconds 1; Remove-Item -LiteralPath `"$installRoot`" -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath `"$tempUninstall`" -Force -ErrorAction SilentlyContinue"
) -WindowStyle Hidden

if (-not $Quiet) {
    Write-Host "Uninstall scheduled. $AppName will be removed momentarily." -ForegroundColor Green
}
