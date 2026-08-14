#Requires -Version 5.1
<#
.SYNOPSIS
  Build a Windows onedir distribution with PyInstaller.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Missing .venv. Run scripts\bootstrap.ps1 first."
}

Write-Host "==> Ensuring PyInstaller"
& $VenvPython -m pip install -U "pyinstaller>=6.0"

$Dist = Join-Path $Root "dist"
$Build = Join-Path $Root "build"
New-Item -ItemType Directory -Force -Path $Dist, $Build | Out-Null

Write-Host "==> Building BatchSTLinkFlasher (onedir)"
& $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name BatchSTLinkFlasher `
    --paths (Join-Path $Root "src") `
    --distpath $Dist `
    --workpath $Build `
    --collect-all PySide6 `
    (Join-Path $Root "src\batch_stlink_flasher\__main__.py")

Write-Host ""
Write-Host "Output: $Dist\BatchSTLinkFlasher\" -ForegroundColor Green
Write-Host "Ship that folder with OpenOCD installed separately on the operator PC."
Write-Host "See docs\packaging.md"
