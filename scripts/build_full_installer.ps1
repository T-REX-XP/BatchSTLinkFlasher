#Requires -Version 5.1
<#
.SYNOPSIS
  Build a full Windows installer that ships the app + runtime tools (OpenOCD).

.DESCRIPTION
  End-to-end packaging for operators:

  1. Ensure Python 3.11+ is available on the *build* machine (optional winget install)
  2. Ensure venv + packaging extras (PyInstaller)
  3. Download/stage OpenOCD into vendor\runtime\openocd
  4. Optionally install system deps via winget (VC++ redistributable)
  5. Build PyInstaller onedir (scripts\build_windows.ps1)
  6. Copy OpenOCD into dist\BatchSTLinkFlasher\tools\openocd
  7. Write bundled-tools.json so the app auto-selects OpenOCD
  8. Compile Setup.exe (Inno Setup) and/or produce a portable zip

  Operators do NOT need a system Python — it is embedded by PyInstaller.
  OpenOCD IS bundled under tools\openocd.

.PARAMETER SkipFetch
  Skip OpenOCD download (require existing vendor\runtime\openocd).

.PARAMETER SkipBuild
  Skip PyInstaller; reuse dist\BatchSTLinkFlasher.

.PARAMETER NoBump
  Do not increment build number.

.PARAMETER SkipInno
  Do not compile Inno Setup.

.PARAMETER ZipPortable
  Also create a portable zip including tools.

.PARAMETER InstallSystemDeps
  Use winget to install VC++ redistributable (and Python if missing for the build).

.PARAMETER SkipPythonBootstrap
  Do not create/update .venv (assume already ready).
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
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "version.ps1")

$AppId = "BatchSTLinkFlasher"
$DistApp = Join-Path $Root "dist\$AppId"
$VendorOpenOcd = Join-Path $Root "vendor\runtime\openocd"
$ManifestPath = Join-Path $Root "packaging\runtime-deps.json"

function Find-Python {
    $candidates = @(
        (Join-Path $Root ".venv\Scripts\python.exe"),
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
        (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    ) | Where-Object { $_ -and (Test-Path $_) -and $_ -notmatch "WindowsApps\\python" }
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

Write-Host "==> Full installer build" -ForegroundColor Cyan

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
        throw "Python 3.11+ required to *build* the installer. Install Python or pass -InstallSystemDeps."
    }
}
Write-Host "Build Python: $python"

if (-not $SkipPythonBootstrap) {
    $venvPy = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) {
        Write-Host "==> Creating .venv"
        & $python -m venv .venv
    }
    Write-Host "==> Ensuring packaging extras"
    & $venvPy -m pip install -U pip
    & $venvPy -m pip install -e ".[dev,packaging]"
}

if (-not $SkipFetch) {
    & (Join-Path $PSScriptRoot "fetch_runtime_deps.ps1")
} elseif (-not (Test-Path (Join-Path $VendorOpenOcd "bin\openocd.exe"))) {
    throw "OpenOCD not staged at $VendorOpenOcd. Run scripts\fetch_runtime_deps.ps1 first."
}

if (-not $SkipBuild) {
    $buildArgs = @()
    if ($NoBump) { $buildArgs += "-NoBump" }
    & (Join-Path $PSScriptRoot "build_windows.ps1") @buildArgs
}

if (-not (Test-Path (Join-Path $DistApp "BatchSTLinkFlasher.exe"))) {
    throw "Missing dist payload at $DistApp"
}

Write-Host "==> Bundling OpenOCD into dist\tools\openocd" -ForegroundColor Cyan
$toolsOpenOcd = Join-Path $DistApp "tools\openocd"
if (Test-Path $toolsOpenOcd) {
    Remove-Item -LiteralPath $toolsOpenOcd -Recurse -Force
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $toolsOpenOcd) | Out-Null
Copy-Item -Path $VendorOpenOcd -Destination $toolsOpenOcd -Recurse -Force

$manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$ver = Read-ProjectVersion
$bundled = [ordered]@{
    AppId            = $AppId
    Version          = $ver.Version
    BuiltAt          = (Get-Date).ToString("o")
    OpenOcdExe       = "tools/openocd/bin/openocd.exe"
    OpenOcdScripts   = "tools/openocd/share/openocd/scripts"
    OpenOcdVersion   = [string]$manifest.openocd.version
    OpenOcdName      = [string]$manifest.openocd.name
    Notes            = @(
        "Python runtime is embedded in BatchSTLinkFlasher.exe (no system Python required).",
        "OpenOCD is bundled under tools\openocd."
    )
}
$bundled | ConvertTo-Json | Set-Content -Path (Join-Path $DistApp "bundled-tools.json") -Encoding UTF8

# Keep build-info in sync
@{
    AppId   = $AppId
    Version = $ver.Version
    BuiltAt = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content -Path (Join-Path $DistApp "build-info.json") -Encoding UTF8

Copy-Item -Path (Join-Path $PSScriptRoot "uninstall.ps1") -Destination (Join-Path $DistApp "uninstall.ps1") -Force

$installerArgs = @("-SkipBuild", "-NoBump")
if ($SkipInno) { $installerArgs += "-SkipInno" }
if ($ZipPortable) { $installerArgs += "-ZipPortable" }
& (Join-Path $PSScriptRoot "build_installer.ps1") @installerArgs

Write-Host ""
Write-Host "Full installer artifacts:" -ForegroundColor Green
Write-Host ("  Version : {0}" -f $ver.Version)
Write-Host ("  Onedir  : {0}  (includes tools\openocd)" -f $DistApp)
Write-Host "  Install : powershell -File scripts\install.ps1 -DesktopShortcut -Force"
Write-Host "  Or run  : dist\BatchSTLinkFlasher-<ver>-Setup.exe  (if Inno Setup was available)"
Write-Host "See docs\packaging.md"
