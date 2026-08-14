#Requires -Version 5.1
<#
.SYNOPSIS
  Deprecated alias — use scripts\install_build_deps.ps1

.DESCRIPTION
  Developer-oriented wrapper around install_build_deps.ps1 (runs tests, installs OpenOCD cache).
#>
[CmdletBinding()]
param(
    [switch]$SkipDev
)

$ErrorActionPreference = "Stop"
Write-Host "NOTE: bootstrap.ps1 is deprecated; prefer scripts\install_build_deps.ps1" -ForegroundColor Yellow

$args = @()
if ($SkipDev) { $args += "-DevOnly" }
& (Join-Path $PSScriptRoot "install_build_deps.ps1") @args
