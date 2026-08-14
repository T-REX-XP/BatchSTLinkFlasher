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
  Forwarded to build_installer.ps1

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
    [switch]$ZipPortable,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> build_all: deps -> app -> installer" -ForegroundColor Cyan

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
& (Join-Path $PSScriptRoot "build_installer.ps1") @instArgs

Write-Host "==> build_all complete" -ForegroundColor Green
