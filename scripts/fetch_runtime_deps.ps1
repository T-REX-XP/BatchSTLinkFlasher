#Requires -Version 5.1
<#
.SYNOPSIS
  Download and stage Windows runtime dependencies (OpenOCD) for packaging.

.DESCRIPTION
  Reads packaging\runtime-deps.json, downloads xPack OpenOCD (unless cached),
  verifies SHA-256, and extracts to vendor\runtime\openocd\ with a stable layout:
    vendor\runtime\openocd\bin\openocd.exe
    vendor\runtime\openocd\share\openocd\scripts\...

.PARAMETER Force
  Re-download even if the cache already looks valid.
#>
[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ManifestPath = Join-Path $Root "packaging\runtime-deps.json"
if (-not (Test-Path $ManifestPath)) {
    throw "Missing $ManifestPath"
}
$manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$dep = $manifest.openocd

$VendorRoot = Join-Path $Root "vendor\runtime"
$CacheDir = Join-Path $VendorRoot "cache"
$OpenOcdRoot = Join-Path $VendorRoot "openocd"
$ZipName = [IO.Path]::GetFileName([uri]$dep.url)
$ZipPath = Join-Path $CacheDir $ZipName
$Marker = Join-Path $OpenOcdRoot ".deps-version"

function Test-OpenOcdStage {
    $exe = Join-Path $OpenOcdRoot $dep.exe_relpath.Replace("/", "\")
    if (-not (Test-Path $exe)) { return $false }
    if (Test-Path $Marker) {
        $have = (Get-Content -LiteralPath $Marker -Raw).Trim()
        if ($have -ne [string]$dep.version) { return $false }
    }
    return $true
}

function Get-FileSha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null

if ((Test-OpenOcdStage) -and -not $Force) {
    Write-Host ("OpenOCD already staged at {0} (v{1})" -f $OpenOcdRoot, $dep.version) -ForegroundColor Green
    exit 0
}

Write-Host ("==> Fetching {0} {1}" -f $dep.name, $dep.version) -ForegroundColor Cyan
Write-Host $dep.url

if ($Force -or -not (Test-Path $ZipPath)) {
    Write-Host "==> Downloading"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $dep.url -OutFile $ZipPath -UseBasicParsing
} else {
    Write-Host "Using cached archive: $ZipPath"
}

$actual = Get-FileSha256 $ZipPath
$expected = ([string]$dep.sha256).ToLowerInvariant()
if ($actual -ne $expected) {
    Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue
    throw "SHA-256 mismatch for $ZipName`nExpected: $expected`nActual:   $actual"
}
Write-Host "SHA-256 OK" -ForegroundColor Green

$ExtractTmp = Join-Path $CacheDir ("extract-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $ExtractTmp | Out-Null
try {
    Write-Host "==> Extracting"
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractTmp -Force

    # xPack zips contain a single top-level folder.
    $inner = Get-ChildItem -LiteralPath $ExtractTmp -Directory | Select-Object -First 1
    if (-not $inner) {
        throw "Unexpected OpenOCD archive layout (no top-level directory)."
    }

    if (Test-Path $OpenOcdRoot) {
        Remove-Item -LiteralPath $OpenOcdRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OpenOcdRoot) | Out-Null
    Move-Item -LiteralPath $inner.FullName -Destination $OpenOcdRoot

    $exe = Join-Path $OpenOcdRoot ($dep.exe_relpath -replace "/", "\")
    if (-not (Test-Path $exe)) {
        throw "openocd.exe missing after extract: $exe"
    }

    Set-Content -LiteralPath $Marker -Value $dep.version -Encoding UTF8
    Write-Host ("Staged OpenOCD -> {0}" -f $exe) -ForegroundColor Green
}
finally {
    if (Test-Path $ExtractTmp) {
        Remove-Item -LiteralPath $ExtractTmp -Recurse -Force -ErrorAction SilentlyContinue
    }
}
