#Requires -Version 5.1
<#
.SYNOPSIS
  Prepare and create a release tag in the form vMAJOR.MINOR.PATCH (e.g. v0.1.0).

.DESCRIPTION
  1. Sets packaging/version.json to MAJOR.MINOR.PATCH.0 and syncs artifacts
  2. Optionally commits the version bump
  3. Creates an annotated git tag vMAJOR.MINOR.PATCH
  4. Optionally pushes the tag (triggers .github/workflows/release.yml)

.PARAMETER Version
  Semver without leading v, e.g. 0.1.0

.PARAMETER Commit
  git add + commit version files before tagging

.PARAMETER Push
  git push origin HEAD and the new tag

.PARAMETER DryRun
  Print actions without writing git objects
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Version,

    [switch]$Commit,
    [switch]$Push,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $PSScriptRoot "version.ps1")

$raw = $Version.Trim().TrimStart("v", "V")
if ($raw -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version must look like 0.1.0 (got '$Version'). Tag will be vMAJOR.MINOR.PATCH."
}

$tag = "v$raw"
$four = "$raw.0"

Write-Host "==> Release tag pipeline" -ForegroundColor Cyan
Write-Host "Version : $raw"
Write-Host "Tag     : $tag"
Write-Host "Internal: $four"

if ($DryRun) {
    Write-Host "[DryRun] Would set version to $four, create tag $tag" -ForegroundColor Yellow
    exit 0
}

Write-Host "==> Syncing version artifacts"
& (Join-Path $PSScriptRoot "bump_version.ps1") -Set $four

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    throw "git is required to create tags"
}

$existing = & git tag -l $tag
if ($existing) {
    throw "Tag $tag already exists. Delete it first or choose another version."
}

$status = & git status --porcelain
if ($Commit) {
    Write-Host "==> Committing version bump"
    & git add -- packaging/version.json packaging/installer.iss pyproject.toml src/batch_stlink_flasher/_version.py
    if ($LASTEXITCODE -ne 0) { throw "git add failed" }
    $msg = "chore: release $tag"
    & git commit -m $msg
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Nothing to commit (version files may already match)." -ForegroundColor Yellow
    }
} elseif ($status) {
    Write-Host "Working tree has changes. Pass -Commit to include the version bump, or commit manually." -ForegroundColor Yellow
}

Write-Host "==> Creating annotated tag $tag"
& git tag -a $tag -m "Release $tag"
if ($LASTEXITCODE -ne 0) { throw "git tag failed" }

if ($Push) {
    Write-Host "==> Pushing commit + tag (triggers GitHub Release workflow)"
    & git push origin HEAD
    if ($LASTEXITCODE -ne 0) { throw "git push failed" }
    & git push origin $tag
    if ($LASTEXITCODE -ne 0) { throw "git push tag failed" }
    Write-Host "Release workflow should start for $tag" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Tag created locally. Publish with:" -ForegroundColor Cyan
    Write-Host "  git push origin HEAD"
    Write-Host "  git push origin $tag"
    Write-Host "Or re-run with -Push"
}

Write-Host "Done." -ForegroundColor Green
