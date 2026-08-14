#Requires -Version 5.1
<#
.SYNOPSIS
  Install Batch ST-Link Flasher from a built dist folder (or build first).

.DESCRIPTION
  Copies the PyInstaller onedir payload into a stable location, creates Start Menu
  (and optional Desktop) shortcuts, and registers an uninstaller for Add/Remove Programs.

  Default install is per-user (no admin):
    %LOCALAPPDATA%\Programs\BatchSTLinkFlasher

.PARAMETER Build
  Run scripts\build_windows.ps1 before installing.

.PARAMETER SourceDir
  Path to the BatchSTLinkFlasher onedir folder (default: dist\BatchSTLinkFlasher).

.PARAMETER AllUsers
  Install under Program Files (requires elevation).

.PARAMETER DesktopShortcut
  Also create a Desktop shortcut.

.PARAMETER Force
  Overwrite an existing installation without prompting.
#>
[CmdletBinding()]
param(
    [switch]$Build,
    [string]$SourceDir = "",
    [switch]$AllUsers,
    [switch]$DesktopShortcut,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "version.ps1")

$AppName = "Batch ST-Link Flasher"
$AppId = "BatchSTLinkFlasher"
$Publisher = "BatchSTLinkFlasher"
$ExeName = "BatchSTLinkFlasher.exe"

function Resolve-InstallVersion {
    param([string]$Source)
    $buildInfo = Join-Path $Source "build-info.json"
    if (Test-Path $buildInfo) {
        $info = Get-Content -LiteralPath $buildInfo -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($info.Version) { return [string]$info.Version }
    }
    return (Read-ProjectVersion).Version
}

function Get-InstallRoot {
    if ($AllUsers) {
        return Join-Path ${env:ProgramFiles} $AppId
    }
    return Join-Path $env:LOCALAPPDATA "Programs\$AppId"
}

function Ensure-AdminIfNeeded {
    if (-not $AllUsers) { return }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "AllUsers install requires an elevated PowerShell (Run as administrator)."
    }
}

function New-Shortcut {
    param(
        [Parameter(Mandatory = $true)][string]$ShortcutPath,
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [string]$WorkingDirectory = "",
        [string]$Description = $AppName
    )
    $dir = Split-Path -Parent $ShortcutPath
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $wsh = New-Object -ComObject WScript.Shell
    $sc = $wsh.CreateShortcut($ShortcutPath)
    $sc.TargetPath = $TargetPath
    if ($WorkingDirectory) { $sc.WorkingDirectory = $WorkingDirectory }
    $sc.Description = $Description
    $sc.Save()
}

function Register-UninstallEntry {
    param(
        [Parameter(Mandatory = $true)][string]$InstallRoot,
        [Parameter(Mandatory = $true)][string]$UninstallScript
    )
    $regPath = if ($AllUsers) {
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppId"
    } else {
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppId"
    }

    New-Item -Path $regPath -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "DisplayName" -Value $AppName -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "DisplayVersion" -Value $Version -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "Publisher" -Value $Publisher -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "InstallLocation" -Value $InstallRoot -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "DisplayIcon" -Value (Join-Path $InstallRoot $ExeName) -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "UninstallString" -Value ("powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$UninstallScript`"") -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "NoModify" -Value 1 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "NoRepair" -Value 1 -PropertyType DWord -Force | Out-Null
    $sizeKb = [math]::Round(((Get-ChildItem -LiteralPath $InstallRoot -Recurse -File -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum).Sum) / 1KB)
    if ($sizeKb -gt 0) {
        New-ItemProperty -Path $regPath -Name "EstimatedSize" -Value ([int]$sizeKb) -PropertyType DWord -Force | Out-Null
    }
}

Ensure-AdminIfNeeded

if ($Build) {
    Write-Host "==> Building distribution first"
    & (Join-Path $PSScriptRoot "build_windows.ps1")
}

if (-not $SourceDir) {
    $SourceDir = Join-Path $Root "dist\$AppId"
}
if (-not (Test-Path (Join-Path $SourceDir $ExeName))) {
    throw "Missing $ExeName under '$SourceDir'. Run with -Build or scripts\build_windows.ps1 first."
}

$Version = Resolve-InstallVersion -Source $SourceDir
$InstallRoot = Get-InstallRoot
Write-Host "==> $AppName installer v$Version" -ForegroundColor Cyan
Write-Host "Source : $SourceDir"
Write-Host "Target : $InstallRoot"

if ((Test-Path $InstallRoot) -and -not $Force) {
    $answer = Read-Host "Existing install found. Overwrite? [y/N]"
    if ($answer -notmatch '^(y|yes)$') {
        Write-Host "Aborted."
        exit 1
    }
}

if (Test-Path $InstallRoot) {
    Write-Host "==> Removing previous install"
    Remove-Item -LiteralPath $InstallRoot -Recurse -Force
}

Write-Host "==> Copying files"
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
Copy-Item -Path (Join-Path $SourceDir "*") -Destination $InstallRoot -Recurse -Force

# Ship a copy of uninstall.ps1 next to the app for Add/Remove Programs.
$UninstallSrc = Join-Path $PSScriptRoot "uninstall.ps1"
$UninstallDst = Join-Path $InstallRoot "uninstall.ps1"
if (Test-Path $UninstallSrc) {
    Copy-Item -Path $UninstallSrc -Destination $UninstallDst -Force
} else {
    throw "Missing scripts\uninstall.ps1"
}

$ExePath = Join-Path $InstallRoot $ExeName
if (-not (Test-Path $ExePath)) {
    throw "Install copy failed; $ExePath not found."
}

Write-Host "==> Creating shortcuts"
$programsDir = if ($AllUsers) {
    Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\$AppName"
} else {
    Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$AppName"
}
New-Shortcut -ShortcutPath (Join-Path $programsDir "$AppName.lnk") -TargetPath $ExePath -WorkingDirectory $InstallRoot

$wsh = New-Object -ComObject WScript.Shell
$usc = $wsh.CreateShortcut((Join-Path $programsDir "Uninstall $AppName.lnk"))
$usc.TargetPath = "powershell.exe"
$usc.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$UninstallDst`""
$usc.WorkingDirectory = $InstallRoot
$usc.Description = "Uninstall $AppName"
$usc.Save()

if ($DesktopShortcut) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    New-Shortcut -ShortcutPath (Join-Path $desktop "$AppName.lnk") -TargetPath $ExePath -WorkingDirectory $InstallRoot
}

Write-Host "==> Registering uninstaller"
Register-UninstallEntry -InstallRoot $InstallRoot -UninstallScript $UninstallDst

# Marker file used by uninstall.ps1
@{
    AppId       = $AppId
    Version     = $Version
    InstallRoot = $InstallRoot
    AllUsers    = [bool]$AllUsers
    InstalledAt = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content -Path (Join-Path $InstallRoot "install.json") -Encoding UTF8

$OpenOcd = Get-Command openocd -ErrorAction SilentlyContinue
if ($OpenOcd) {
    Write-Host "OpenOCD found: $($OpenOcd.Source)" -ForegroundColor Green
} else {
    Write-Host "NOTE: OpenOCD was not found on PATH." -ForegroundColor Yellow
    Write-Host "      Install OpenOCD separately and set its path in the app settings."
}

Write-Host ""
Write-Host "Installed successfully." -ForegroundColor Green
Write-Host "  App     : $ExePath"
Write-Host "  Start   : Start Menu -> $AppName"
Write-Host "  Remove  : Settings -> Apps, or Start Menu -> Uninstall $AppName"
