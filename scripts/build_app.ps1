#Requires -Version 5.1
<#
.SYNOPSIS
  Step 2/3 — Build the Windows app (PyInstaller onedir).

.DESCRIPTION
  Produces dist\BatchSTLinkFlasher\BatchSTLinkFlasher.exe and supporting files.
  Does not create Setup.exe (that is step 3: build_installer.ps1).

  Requires step 1: scripts\install_build_deps.ps1

.PARAMETER NoBump
  Do not increment the build number in packaging\version.json.
#>
[CmdletBinding()]
param(
    [switch]$NoBump
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "version.ps1")

Write-Host "==> Step 2/3: build app" -ForegroundColor Cyan

if (-not $NoBump) {
    Write-Host "==> Incrementing build version"
    & (Join-Path $PSScriptRoot "bump_version.ps1")
}

$ver = Read-ProjectVersion
Write-Host ("==> Building BatchSTLinkFlasher {0}" -f $ver.Version)

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Missing .venv. Run scripts\install_build_deps.ps1 first."
}

Write-Host "==> Ensuring PyInstaller"
& $VenvPython -m pip install -U "pyinstaller>=6.0"

$Dist = Join-Path $Root "dist"
$Build = Join-Path $Root "build"
New-Item -ItemType Directory -Force -Path $Dist, $Build | Out-Null

Write-Host "==> Running PyInstaller"
& $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name BatchSTLinkFlasher `
    --icon (Join-Path $Root "src\batch_stlink_flasher\assets\app_icon.ico") `
    --paths (Join-Path $Root "src") `
    --distpath $Dist `
    --workpath $Build `
    --collect-all PySide6 `
    --add-data ((Join-Path $Root "src\batch_stlink_flasher\assets") + ";batch_stlink_flasher/assets") `
    (Join-Path $Root "src\batch_stlink_flasher\__main__.py")

$payload = Join-Path $Dist "BatchSTLinkFlasher"
if (-not (Test-Path (Join-Path $payload "BatchSTLinkFlasher.exe"))) {
    throw "PyInstaller did not produce BatchSTLinkFlasher.exe"
}

@{
    AppId   = "BatchSTLinkFlasher"
    Version = $ver.Version
    BuiltAt = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content -Path (Join-Path $payload "build-info.json") -Encoding UTF8

Write-Host ""
Write-Host ("App built: {0}\" -f $payload) -ForegroundColor Green
Write-Host ("Version  : {0}" -f $ver.Version)
Write-Host "Next: powershell -File scripts\build_installer.ps1 -ZipPortable"
Write-Host "See scripts\README.md"
