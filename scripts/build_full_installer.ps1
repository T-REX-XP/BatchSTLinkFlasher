#Requires -Version 5.1
<#
.SYNOPSIS
  Deprecated alias - use scripts\build_all.ps1 (or the 3-step pipeline in scripts\README.md)
#>
[CmdletBinding()]
param(
    [switch]$SkipFetch,
    [switch]$SkipBuild,
    [switch]$NoBump,
    [switch]$SkipInno,
    [switch]$ZipPortable,
    [switch]$InstallSystemDeps,
    [switch]$SkipPythonBootstrap
)

$ErrorActionPreference = "Stop"
Write-Host "NOTE: build_full_installer.ps1 is deprecated; prefer scripts\build_all.ps1" -ForegroundColor Yellow

if ($SkipPythonBootstrap -and -not $SkipFetch -and -not $SkipBuild) {
    # Old flag meant "venv already ready" - still run fetch + app + installer.
}

if (-not $SkipFetch -and -not $SkipBuild -and -not $SkipPythonBootstrap) {
    $all = @()
    if ($InstallSystemDeps) { $all += "-InstallSystemDeps" }
    if ($NoBump) { $all += "-NoBump" }
    if ($SkipInno) { $all += "-SkipInno" }
    if ($ZipPortable) { $all += "-ZipPortable" }
    & (Join-Path $PSScriptRoot "build_all.ps1") @all
    exit $LASTEXITCODE
}

# Partial pipeline for callers that skipped steps.
if (-not $SkipPythonBootstrap -and -not $SkipBuild) {
    $dep = @()
    if ($InstallSystemDeps) { $dep += "-InstallSystemDeps" }
    if ($SkipFetch) { $dep += "-SkipOpenOcd" }
    $dep += "-SkipTests"
    & (Join-Path $PSScriptRoot "install_build_deps.ps1") @dep
}

if (-not $SkipBuild) {
    $app = @()
    if ($NoBump) { $app += "-NoBump" }
    & (Join-Path $PSScriptRoot "build_app.ps1") @app
}

$inst = @()
if ($ZipPortable) { $inst += "-ZipPortable" }
if ($SkipInno) { $inst += "-SkipInno" }
if ($SkipFetch) { $inst += "-SkipOpenOcd" } else { $inst += "-FetchOpenOcd" }
& (Join-Path $PSScriptRoot "build_installer.ps1") @inst
