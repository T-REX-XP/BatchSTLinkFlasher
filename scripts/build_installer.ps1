#Requires -Version 5.1
<#
.SYNOPSIS
  Step 3/3 - Bundle OpenOCD and build the single Setup.exe installer.

.DESCRIPTION
  Packages dist\BatchSTLinkFlasher\ (from build_app.ps1):
  - Copies OpenOCD from vendor\runtime\openocd
  - Writes bundled-tools.json
  - Compiles Inno Setup → dist\BatchSTLinkFlasher-<version>-Setup.exe
  - Optional portable zip (-ZipPortable)

  Operators distribute the Setup.exe (one file). The installed app is an onedir
  layout with BatchSTLinkFlasher.exe + tools\openocd.

.PARAMETER ZipPortable
  Also create dist\BatchSTLinkFlasher-<version>-portable.zip

.PARAMETER SkipInno
  Do not compile Setup.exe (OpenOCD bundle / zip still run).

.PARAMETER RequireInno
  Fail if ISCC.exe is missing (default: on, unless -SkipInno).

.PARAMETER InstallInno
  Try to install Inno Setup 6 via winget or chocolatey when missing.

.PARAMETER SkipOpenOcd
  Do not bundle OpenOCD (not recommended).
#>
[CmdletBinding()]
param(
    [switch]$ZipPortable,
    [switch]$SkipInno,
    [switch]$RequireInno,
    [switch]$InstallInno,
    [switch]$SkipOpenOcd
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

# Default: require Setup.exe unless explicitly skipped.
if (-not $PSBoundParameters.ContainsKey("RequireInno")) {
    $RequireInno = -not $SkipInno
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

function Install-InnoSetup {
    Write-Host "==> Installing Inno Setup 6..." -ForegroundColor Cyan
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        & winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements --silent
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")
        $found = Find-ISCC
        if ($found) { return $found }
    }
    $choco = Get-Command choco -ErrorAction SilentlyContinue
    if ($choco) {
        & choco install innosetup -y --no-progress
        $found = Find-ISCC
        if ($found) { return $found }
    }
    return $null
}

Write-Host "==> Step 3/3: build installer (Setup.exe)" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $DistApp "BatchSTLinkFlasher.exe"))) {
    throw "Missing dist payload at $DistApp. Run scripts\build_app.ps1 first."
}

$ver = Read-ProjectVersion
Sync-VersionArtifacts -Info $ver
$Version = $ver.Version
Write-Host ("==> Packaging version {0}" -f $Version)

if (-not $SkipOpenOcd) {
    if (-not (Test-Path (Join-Path $VendorOpenOcd "bin\openocd.exe"))) {
        Write-Host "==> OpenOCD not cached; fetching..."
        & (Join-Path $PSScriptRoot "fetch_runtime_deps.ps1")
    }
    if (-not (Test-Path (Join-Path $VendorOpenOcd "bin\openocd.exe"))) {
        throw "OpenOCD not staged at $VendorOpenOcd. Run scripts\fetch_runtime_deps.ps1."
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
            "OpenOCD is bundled under tools\openocd.",
            "Operators should prefer the Setup.exe installer from this step."
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

$setupPath = Join-Path $Root "dist\$AppId-$Version-Setup.exe"

if (-not $SkipInno) {
    $iscc = Find-ISCC
    if (-not $iscc -and $InstallInno) {
        $iscc = Install-InnoSetup
    }
    if (-not $iscc) {
        $hint = @"
Inno Setup (ISCC.exe) not found — cannot build Setup.exe.

Install Inno Setup 6, then re-run this script:
  https://jrsoftware.org/isdl.php
  winget install JRSoftware.InnoSetup
  choco install innosetup

Or re-run with auto-install:
  powershell -File scripts\build_installer.ps1 -InstallInno -ZipPortable

To skip the installer (onedir / zip only):
  powershell -File scripts\build_installer.ps1 -SkipInno -ZipPortable
"@
        if ($RequireInno) {
            throw $hint
        }
        Write-Host $hint -ForegroundColor Yellow
    } else {
        if (-not (Test-Path $Iss)) {
            throw "Missing Inno script: $Iss"
        }
        Write-Host "==> Compiling Setup.exe with $iscc" -ForegroundColor Cyan
        & $iscc $Iss
        if (-not (Test-Path $setupPath)) {
            $alt = Get-ChildItem (Join-Path $Root "dist") -Filter "*Setup*.exe" -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending |
                Select-Object -First 1
            if ($alt) {
                $setupPath = $alt.FullName
            }
        }
        if (-not (Test-Path $setupPath)) {
            throw "ISCC finished but Setup.exe was not found under dist\"
        }
        Write-Host ("Setup.exe: {0}" -f $setupPath) -ForegroundColor Green
    }
} else {
    Write-Host "Skipping Setup.exe (-SkipInno)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done. Artifacts under dist\" -ForegroundColor Green
Write-Host "  App onedir : $DistApp"
if (Test-Path $setupPath) {
    Write-Host "  Installer  : $setupPath" -ForegroundColor Green
}
if ($ZipPortable) {
    Write-Host ("  Portable   : dist\{0}-{1}-portable.zip" -f $AppId, $Version)
}
Write-Host "See scripts\README.md"
