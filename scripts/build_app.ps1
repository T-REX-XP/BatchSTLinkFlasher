#Requires -Version 5.1
<#
.SYNOPSIS
  Step 2/3 - Build the Windows app (PyInstaller onedir EXE).

.DESCRIPTION
  Produces dist\BatchSTLinkFlasher\BatchSTLinkFlasher.exe and supporting files
  (Qt / Python). Does not create Setup.exe — that is step 3 (build_installer.ps1),
  which also bundles OpenOCD and compiles a single installer EXE.

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

Write-Host "==> Step 2/3: build app (onedir EXE)" -ForegroundColor Cyan

if (-not $NoBump) {
    Write-Host "==> Incrementing build version"
    & (Join-Path $PSScriptRoot "bump_version.ps1")
} else {
    $verSync = Read-ProjectVersion
    Sync-VersionArtifacts -Info $verSync
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
$Spec = Join-Path $Root "packaging\batch_stlink_flasher.spec"
if (-not (Test-Path $Spec)) {
    throw "Missing PyInstaller spec: $Spec"
}

New-Item -ItemType Directory -Force -Path $Dist, $Build | Out-Null

Write-Host "==> Running PyInstaller ($Spec)"
& $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath $Dist `
    --workpath $Build `
    $Spec

$payload = Join-Path $Dist "BatchSTLinkFlasher"
$exe = Join-Path $payload "BatchSTLinkFlasher.exe"
if (-not (Test-Path $exe)) {
    throw "PyInstaller did not produce $exe"
}

@{
    AppId   = "BatchSTLinkFlasher"
    Version = $ver.Version
    BuiltAt = (Get-Date).ToString("o")
    Layout  = "onedir"
} | ConvertTo-Json | Set-Content -Path (Join-Path $payload "build-info.json") -Encoding UTF8

Write-Host ""
Write-Host ("App EXE : {0}" -f $exe) -ForegroundColor Green
Write-Host ("Folder  : {0}\" -f $payload)
Write-Host ("Version : {0}" -f $ver.Version)
Write-Host "Next: powershell -File scripts\build_installer.ps1 -ZipPortable"
Write-Host "      (bundles OpenOCD + builds Setup.exe installer)"
Write-Host "See scripts\README.md"
