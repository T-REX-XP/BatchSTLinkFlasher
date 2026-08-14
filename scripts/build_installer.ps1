#Requires -Version 5.1
<#
.SYNOPSIS
  Build PyInstaller dist and compile a Windows Setup.exe (Inno Setup).

.DESCRIPTION
  1. Runs scripts\build_windows.ps1
  2. Compiles packaging\installer.iss with ISCC.exe if Inno Setup is installed
  3. Always leaves the onedir payload under dist\BatchSTLinkFlasher\
  4. Optionally zips the onedir payload for portable distribution

.PARAMETER SkipBuild
  Skip PyInstaller rebuild (use existing dist\BatchSTLinkFlasher).

.PARAMETER ZipPortable
  Also create dist\BatchSTLinkFlasher-<version>-portable.zip

.PARAMETER SkipInno
  Do not attempt Inno Setup compilation.
#>
[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$ZipPortable,
    [switch]$SkipInno
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Version = "0.1.0"
$AppId = "BatchSTLinkFlasher"
$DistApp = Join-Path $Root "dist\$AppId"
$Iss = Join-Path $Root "packaging\installer.iss"

function Find-ISCC {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) { return $path }
    }
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

if (-not $SkipBuild) {
    Write-Host "==> Building onedir payload" -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot "build_windows.ps1")
}

if (-not (Test-Path (Join-Path $DistApp "BatchSTLinkFlasher.exe"))) {
    throw "Missing dist payload at $DistApp. Build failed or -SkipBuild used without a prior build."
}

# Write install.json template into dist so PowerShell installer has version metadata after copy.
@{
    AppId       = $AppId
    Version     = $Version
    BuiltAt     = (Get-Date).ToString("o")
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
        Write-Host "Inno Setup (ISCC.exe) not found." -ForegroundColor Yellow
        Write-Host "Install from https://jrsoftware.org/isinfo.php then re-run, or use:"
        Write-Host "  powershell -File scripts\install.ps1 -Build"
    } else {
        Write-Host "==> Compiling Inno Setup installer with $iscc" -ForegroundColor Cyan
        & $iscc $Iss
        $setup = Join-Path $Root "dist\$AppId-$Version-Setup.exe"
        if (Test-Path $setup) {
            Write-Host "Setup.exe: $setup" -ForegroundColor Green
        } else {
            # Inno OutputBaseFilename may land here; list matching artifacts
            Get-ChildItem (Join-Path $Root "dist") -Filter "*Setup*.exe" | ForEach-Object {
                Write-Host "Setup.exe: $($_.FullName)" -ForegroundColor Green
            }
        }
    }
}

Write-Host ""
Write-Host "Artifacts:" -ForegroundColor Cyan
Write-Host "  Onedir   : $DistApp"
Write-Host "  Install  : powershell -File scripts\install.ps1 [-Build] [-DesktopShortcut]"
Write-Host "  Uninstall: powershell -File scripts\uninstall.ps1"
Write-Host "See docs\packaging.md"
