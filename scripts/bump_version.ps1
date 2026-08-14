#Requires -Version 5.1
<#
.SYNOPSIS
  Increment project version and sync generated artifacts.

.DESCRIPTION
  Default: increment the build number (0.1.0.N -> 0.1.0.N+1).
  Use -Patch / -Minor / -Major for release bumps (resets lower components).

.PARAMETER Patch
  Increment patch, reset build to 0.

.PARAMETER Minor
  Increment minor, reset patch and build to 0.

.PARAMETER Major
  Increment major, reset minor/patch/build to 0.

.PARAMETER Set
  Set an explicit version string like 1.2.3 or 1.2.3.4

.PARAMETER DryRun
  Print the next version without writing files.
#>
[CmdletBinding(DefaultParameterSetName = "BumpBuild")]
param(
    [Parameter(ParameterSetName = "Patch")]
    [switch]$Patch,

    [Parameter(ParameterSetName = "Minor")]
    [switch]$Minor,

    [Parameter(ParameterSetName = "Major")]
    [switch]$Major,

    [Parameter(ParameterSetName = "Set", Mandatory = $true)]
    [string]$Set,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "version.ps1")

$current = Read-ProjectVersion

if ($PSCmdlet.ParameterSetName -eq "Set") {
    $parts = $Set.Trim().Split(".")
    if ($parts.Count -lt 3 -or $parts.Count -gt 4) {
        throw "Version must be MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH.BUILD (got '$Set')"
    }
    $nextMajor = [int]$parts[0]
    $nextMinor = [int]$parts[1]
    $nextPatch = [int]$parts[2]
    $nextBuild = if ($parts.Count -eq 4) { [int]$parts[3] } else { 0 }
} elseif ($Major) {
    $nextMajor = $current.Major + 1
    $nextMinor = 0
    $nextPatch = 0
    $nextBuild = 0
} elseif ($Minor) {
    $nextMajor = $current.Major
    $nextMinor = $current.Minor + 1
    $nextPatch = 0
    $nextBuild = 0
} elseif ($Patch) {
    $nextMajor = $current.Major
    $nextMinor = $current.Minor
    $nextPatch = $current.Patch + 1
    $nextBuild = 0
} else {
    # Default: build increment
    $nextMajor = $current.Major
    $nextMinor = $current.Minor
    $nextPatch = $current.Patch
    $nextBuild = $current.Build + 1
}

$nextVersion = "{0}.{1}.{2}.{3}" -f $nextMajor, $nextMinor, $nextPatch, $nextBuild

Write-Host ("Current : {0}" -f $current.Version)
Write-Host ("Next    : {0}" -f $nextVersion)

if ($DryRun) {
    exit 0
}

Write-ProjectVersion -Major $nextMajor -Minor $nextMinor -Patch $nextPatch -Build $nextBuild
$written = Read-ProjectVersion
Sync-VersionArtifacts -Info $written
Write-Host "Synced version artifacts to $($written.Version)" -ForegroundColor Green
