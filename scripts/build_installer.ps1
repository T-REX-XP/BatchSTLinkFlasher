#Requires -Version 5.1
<#
.SYNOPSIS
  Step 3/3 - Build the Windows installer that embeds the app (+ OpenOCD).

.DESCRIPTION
  Takes an existing dist\BatchSTLinkFlasher\ payload (from build_app.ps1) and:

  1. Bundles OpenOCD from vendor\runtime\openocd into tools\openocd
  2. Writes bundled-tools.json / build-info.json
  3. Optionally creates a portable zip
  4. Compiles Setup.exe with Inno Setup when ISCC is available

  Does not rebuild the PyInstaller app unless -BuildApp is passed.

.PARAMETER BuildApp
  Run build_app.ps1 first.

.PARAMETER NoBump
  Passed to build_app.ps1 when -BuildApp is used.

.PARAMETER SkipOpenOcd
  Do not copy OpenOCD into the payload (not recommended for operator installs).

.PARAMETER FetchOpenOcd
  Run fetch_runtime_deps.ps1 before bundling.

.PARAMETER ZipPortable
  Create dist\BatchSTLinkFlasher-<version>-portable.zip

.PARAMETER SkipInno
  Do not compile Setup.exe.
#>
[CmdletBinding()]
param(
    [switch]$BuildApp,
    [switch]$NoBump,
    [switch]$SkipOpenOcd,
    [switch]$FetchOpenOcd,
    [switch]$ZipPortable,
    [switch]$SkipInno
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "version.ps1")

$AppId = "BatchSTLinkFlasher"
$DistApp = Join-Path $Root "dist\$AppId"
$VendorOpenOcd = Join-Path $Root "vendor\runtime\openocd"
$ManifestPath = Join-Path $Root "packaging\runtime-deps.json"
$Iss = Join-Path $Root "packaging\installer.iss"

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

Write-Host "==> Step 3/3: build EXE installer" -ForegroundColor Cyan

if ($BuildApp) {
    $args = @()
    if ($NoBump) { $args += "-NoBump" }
    & (Join-Path $PSScriptRoot "build_app.ps1") @args
}

if (-not (Test-Path (Join-Path $DistApp "BatchSTLinkFlasher.exe"))) {
    throw "Missing dist payload at $DistApp. Run scripts\build_app.ps1 first (or pass -BuildApp)."
}

if ($FetchOpenOcd) {
    & (Join-Path $PSScriptRoot "fetch_runtime_deps.ps1")
}

$ver = Read-ProjectVersion
$Version = $ver.Version
Write-Host ("==> Packaging version {0}" -f $Version)

if (-not $SkipOpenOcd) {
    if (-not (Test-Path (Join-Path $VendorOpenOcd "bin\openocd.exe"))) {
        throw "OpenOCD not staged at $VendorOpenOcd. Run scripts\install_build_deps.ps1 or scripts\fetch_runtime_deps.ps1 (or pass -FetchOpenOcd)."
    }
    Write-Host "==> Bundling OpenOCD into dist\tools\openocd"
    $toolsOpenOcd = Join-Path $DistApp "tools\openocd"
    if (Test-Path $toolsOpenOcd) {
        Remove-Item -LiteralPath $toolsOpenOcd -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $toolsOpenOcd) | Out-Null
    Copy-Item -Path $VendorOpenOcd -Destination $toolsOpenOcd -Recurse -Force

    $manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    @{
        AppId          = $AppId
        Version        = $Version
        BuiltAt        = (Get-Date).ToString("o")
        OpenOcdExe     = "tools/openocd/bin/openocd.exe"
        OpenOcdScripts = "tools/openocd/share/openocd/scripts"
        OpenOcdVersion = [string]$manifest.openocd.version
        OpenOcdName    = [string]$manifest.openocd.name
        Notes          = @(
            "Python runtime is embedded in BatchSTLinkFlasher.exe (no system Python required).",
            "OpenOCD is bundled under tools\openocd."
        )
    } | ConvertTo-Json | Set-Content -Path (Join-Path $DistApp "bundled-tools.json") -Encoding UTF8
} else {
    Write-Host "Skipping OpenOCD bundle (-SkipOpenOcd)" -ForegroundColor Yellow
}

@{
    AppId   = $AppId
    Version = $Version
    BuiltAt = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content -Path (Join-Path $DistApp "build-info.json") -Encoding UTF8

Copy-Item -Path (Join-Path $PSScriptRoot "uninstall.ps1") -Destination (Join-Path $DistApp "uninstall.ps1") -Force

if ($ZipPortable) {
    $zip = Join-Path $Root "dist\$AppId-$Version-portable.zip"
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Write-Host "==> Creating portable zip: $zip"
    Compress-Archive -Path (Join-Path $DistApp "*") -DestinationPath $zip -Force
}

if (-not $SkipInno) {
    $iscc = Find-ISCC
    if (-not $iscc) {
        Write-Host "Inno Setup (ISCC.exe) not found - Setup.exe skipped." -ForegroundColor Yellow
        Write-Host "Install from https://jrsoftware.org/isinfo.php then re-run this script."
    } else {
        Write-Host "==> Compiling Inno Setup installer with $iscc" -ForegroundColor Cyan
        & $iscc $Iss
        $setup = Join-Path $Root "dist\$AppId-$Version-Setup.exe"
        if (Test-Path $setup) {
            Write-Host "Setup.exe: $setup" -ForegroundColor Green
        } else {
            Get-ChildItem (Join-Path $Root "dist") -Filter "*Setup*.exe" | ForEach-Object {
                Write-Host "Setup.exe: $($_.FullName)" -ForegroundColor Green
            }
        }
    }
}

Write-Host ""
Write-Host "Installer artifacts:" -ForegroundColor Green
Write-Host "  Version : $Version"
Write-Host "  Onedir  : $DistApp"
Write-Host "  Install : powershell -File scripts\install.ps1 -DesktopShortcut -Force"
Write-Host "  Uninstall: powershell -File scripts\uninstall.ps1"
Write-Host "See scripts\README.md"
