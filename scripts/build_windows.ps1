#Requires -Version 5.1
<#
.SYNOPSIS
  Deprecated alias - use scripts\build_app.ps1
#>
[CmdletBinding()]
param(
    [switch]$NoBump
)

$ErrorActionPreference = "Stop"
Write-Host "NOTE: build_windows.ps1 is deprecated; prefer scripts\build_app.ps1" -ForegroundColor Yellow
$args = @()
if ($NoBump) { $args += "-NoBump" }
& (Join-Path $PSScriptRoot "build_app.ps1") @args
