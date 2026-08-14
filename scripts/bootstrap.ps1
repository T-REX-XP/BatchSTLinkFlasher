#Requires -Version 5.1
<#
.SYNOPSIS
  Bootstrap a local Python environment for Batch ST-Link Flasher.

.DESCRIPTION
  Creates .venv (if missing), installs the package with [dev] extras,
  checks for OpenOCD on PATH, and prints next steps / docs links.
#>
[CmdletBinding()]
param(
    [switch]$SkipDev
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Find-Python {
    $uvPy = Join-Path $env:APPDATA "uv\python"
    $candidates = @(
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
        (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    ) | Where-Object { $_ -and $_ -notmatch "WindowsApps\\python" }

    if ($candidates) { return $candidates[0] }

    $uvManaged = Get-ChildItem -Path "$env:APPDATA\uv\python" -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "cpython-3\.(1[1-9]|[2-9]\d)" } |
        Select-Object -First 1 -ExpandProperty FullName
    if ($uvManaged) { return $uvManaged }

    throw "Python 3.11+ not found. Install from https://www.python.org/downloads/ or via uv."
}

Write-Host "==> Batch ST-Link Flasher bootstrap" -ForegroundColor Cyan
$Python = Find-Python
Write-Host "Using Python: $Python"

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "==> Creating .venv"
    & $Python -m venv .venv
}

$PipExtra = if ($SkipDev) { "." } else { ".[dev]" }
Write-Host "==> Installing $PipExtra"
& $VenvPython -m pip install -U pip
& $VenvPython -m pip install -e $PipExtra

Write-Host "==> Running smoke tests"
& $VenvPython -m pytest -q

$OpenOcd = Get-Command openocd -ErrorAction SilentlyContinue
if ($OpenOcd) {
    Write-Host "OpenOCD found: $($OpenOcd.Source)" -ForegroundColor Green
} else {
    Write-Host "OpenOCD not on PATH - install OpenOCD and/or set the path in the UI." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Docs:" -ForegroundColor Cyan
Write-Host "  README.md"
Write-Host "  docs/requirements.md"
Write-Host "  docs/openocd-integration.md"
Write-Host "  docs/packaging.md"
Write-Host ""
Write-Host "Run:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\activate"
Write-Host "  python -m batch_stlink_flasher"
Write-Host "  python -m batch_stlink_flasher.discover"
