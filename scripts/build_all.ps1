#Requires -Version 5.1
<#
.SYNOPSIS
  Convenience: run the full packaging pipeline (deps -> app -> installer).

.DESCRIPTION
  Equivalent to:
    1) install_build_deps.ps1
    2) build_app.ps1
    3) build_installer.ps1

.PARAMETER InstallSystemDeps
  Forwarded to install_build_deps.ps1

.PARAMETER NoBump
  Forwarded to build_app.ps1

.PARAMETER SkipInno
  Forwarded to build_installer.ps1 (skip Setup.exe).

.PARAMETER InstallInno
  Forwarded to build_installer.ps1 (auto-install Inno Setup if missing).

.PARAMETER ZipPortable
  Forwarded to build_installer.ps1

.PARAMETER SkipTests
  Forwarded to install_build_deps.ps1
#>
[CmdletBinding()]
param(
    [switch]$InstallSystemDeps,
    [switch]$NoBump,
    [switch]$SkipInno,
    [switch]$InstallInno,
    [switch]$ZipPortable,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> build_all: deps -> app -> Setup.exe" -ForegroundColor Cyan

$depArgs = @()
if ($InstallSystemDeps) { $depArgs += "-InstallSystemDeps" }
if ($SkipTests) { $depArgs += "-SkipTests" }
& (Join-Path $PSScriptRoot "install_build_deps.ps1") @depArgs

$appArgs = @()
if ($NoBump) { $appArgs += "-NoBump" }
& (Join-Path $PSScriptRoot "build_app.ps1") @appArgs

$instArgs = @()
if ($ZipPortable) { $instArgs += "-ZipPortable" }
if ($SkipInno) { $instArgs += "-SkipInno" }
if ($InstallInno) { $instArgs += "-InstallInno" }
& (Join-Path $PSScriptRoot "build_installer.ps1") @instArgs

Write-Host "==> build_all complete" -ForegroundColor Green
