#Requires -Version 5.1
<#
.SYNOPSIS
  Step 1/3 — Install build-time dependencies for Batch ST-Link Flasher.

.DESCRIPTION
  Prepares the machine to *build* the app (not to run the operator EXE):

  - Locate or optionally install Python 3.11+
  - Create .venv and install package extras [dev,packaging]
  - Optionally install VC++ redistributable via winget
  - Download OpenOCD into vendor\runtime\openocd (for bundling later)
  - Report whether Inno Setup (ISCC) is available for Setup.exe builds

.PARAMETER InstallSystemDeps
  Use winget to install Python (if missing) and VC++ redistributable.

.PARAMETER SkipOpenOcd
  Do not download OpenOCD (build_installer.ps1 will require it later).

.PARAMETER SkipTests
  Skip the pytest smoke run after installing deps.

.PARAMETER DevOnly
  Install .[dev] only (no PyInstaller packaging extra).
#>
[CmdletBinding()]
param(
    [switch]$InstallSystemDeps,
    [switch]$SkipOpenOcd,
    [switch]$SkipTests,
    [switch]$DevOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Find-Python {
    $candidates = @(
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
        (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    ) | Where-Object { $_ -and $_ -notmatch "WindowsApps\\python" }
    if ($candidates) { return $candidates[0] }

    $uvManaged = Get-ChildItem -Path "$env:APPDATA\uv\python" -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "cpython-3\.(1[1-9]|[2-9]\d)" } |
        Select-Object -First 1 -ExpandProperty FullName
    if ($uvManaged) { return $uvManaged }
    return $null
}

function Install-WingetPackage([string]$Id) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Host "winget not available; skip $Id" -ForegroundColor Yellow
        return
    }
    Write-Host "==> winget install $Id"
    & winget install --id $Id -e --accept-package-agreements --accept-source-agreements --silent
}

function Find-ISCC {
    foreach ($path in @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
            "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
        )) {
        if ($path -and (Test-Path $path)) { return $path }
    }
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

Write-Host "==> Step 1/3: install build dependencies" -ForegroundColor Cyan

if ($InstallSystemDeps) {
    Install-WingetPackage "Microsoft.VCRedist.2015+.x64"
}

$python = Find-Python
if (-not $python) {
    if ($InstallSystemDeps) {
        Install-WingetPackage "Python.Python.3.12"
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")
        $python = Find-Python
    }
    if (-not $python) {
        throw "Python 3.11+ not found. Install from https://www.python.org/downloads/ or re-run with -InstallSystemDeps."
    }
}
Write-Host "Python: $python"

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "==> Creating .venv"
    & $python -m venv .venv
}

$extra = if ($DevOnly) { ".[dev]" } else { ".[dev,packaging]" }
Write-Host "==> Installing $extra"
& $venvPy -m pip install -U pip
& $venvPy -m pip install -e $extra

if (-not $SkipTests) {
    Write-Host "==> Running tests"
    $env:QT_QPA_PLATFORM = "offscreen"
    & $venvPy -m pytest -q
}

if (-not $SkipOpenOcd) {
    & (Join-Path $PSScriptRoot "fetch_runtime_deps.ps1")
} else {
    Write-Host "Skipping OpenOCD fetch (-SkipOpenOcd)" -ForegroundColor Yellow
}

$iscc = Find-ISCC
if ($iscc) {
    Write-Host "Inno Setup found: $iscc" -ForegroundColor Green
} else {
    Write-Host "Inno Setup (ISCC) not found — Setup.exe builds will be skipped until installed." -ForegroundColor Yellow
    Write-Host "  https://jrsoftware.org/isinfo.php  or: choco install innosetup"
}

Write-Host ""
Write-Host "Build deps ready. Next:" -ForegroundColor Green
Write-Host "  powershell -File scripts\build_app.ps1"
Write-Host "  powershell -File scripts\build_installer.ps1 -ZipPortable"
Write-Host "See scripts\README.md"
