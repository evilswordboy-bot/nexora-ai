<#
.SYNOPSIS
  Builds the NEXORA AI frontend, commits & pushes changes to GitHub (master),
  and immediately updates the 24/7 GitHub Pages Live Demo branch (gh-pages).
  Also ensures detached local background servers are running if needed.
#>
param(
    [string]$CommitMessage = "feat(nexora): update NEXORA AI features and sync live demo"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "1. Building NEXORA AI production frontend..." -ForegroundColor Cyan
Push-Location "$RepoRoot\frontend"
npm.cmd run build
Copy-Item "dist\index.html" -Destination "dist\404.html" -Force
New-Item -ItemType File -Path "dist\.nojekyll" -Force | Out-Null
Pop-Location

Write-Host "2. Committing and pushing source repository to GitHub (master)..." -ForegroundColor Cyan
git add -A
$status = git status --porcelain
if ($status) {
    git commit -m $CommitMessage
}
git push origin master

Write-Host "3. Publishing built bundle directly to gh-pages branch for instant 24/7 GitHub Live Demo..." -ForegroundColor Cyan
$TempPagesDir = Join-Path $env:TEMP "nexora-gh-pages-publish"
if (Test-Path $TempPagesDir) {
    Remove-Item -Recurse -Force $TempPagesDir
}
New-Item -ItemType Directory -Force -Path $TempPagesDir | Out-Null
Copy-Item -Path "$RepoRoot\frontend\dist\*" -Destination $TempPagesDir -Recurse -Force

Push-Location $TempPagesDir
git init
git checkout -b gh-pages
git add -A
git commit -m "deploy(live-demo): $CommitMessage"
git remote add origin https://github.com/evilswordboy-bot/nexora-ai.git
git push -f origin gh-pages
Pop-Location

Write-Host "Done! GitHub Repo: https://github.com/evilswordboy-bot/nexora-ai" -ForegroundColor Green
Write-Host "24/7 GitHub Live Demo: https://evilswordboy-bot.github.io/nexora-ai/" -ForegroundColor Green
