# Dagric OS - build the ISO from Windows using Docker Desktop.
#
#   .\build.ps1              # free edition
#   .\build.ps1 -Edition pro # Pro edition (creator/developer suite)
#
# Requirements: Docker Desktop running. First build downloads packages
# and takes 30-60+ minutes; later builds are faster because the package
# cache lives in a Docker volume.
param([ValidateSet("free","pro")][string]$Edition = "free")

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot

docker info *> $null
if (-not $?) {
    Write-Host "Docker Desktop is not running. Start it and re-run .\build.ps1" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force "$repo\out" | Out-Null

Write-Host "[1/2] Building the build-environment image..." -ForegroundColor Cyan
docker build -t dagric-builder "$repo\docker"
if (-not $?) { exit 1 }

Write-Host "[2/2] Building the Dagric OS ($Edition) ISO (this takes a while)..." -ForegroundColor Cyan
docker run --rm --privileged `
    -e EDITION=$Edition `
    -v "${repo}:/src:ro" `
    -v "${repo}\out:/out" `
    -v dagric-lb-cache:/build/cache `
    dagric-builder `
    sh /src/docker/container-build.sh

# CHECKED, because it was not. A failed `docker run` merely skipped the "Done."
# line and this script still exited 0 — so any wrapper, scheduled task or CI
# step calling it saw a successful build. The docker BUILD step above is
# checked; the step that actually makes the ISO was not.
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build FAILED (exit $LASTEXITCODE). No ISO was produced." -ForegroundColor Red
    Write-Host "The end of $repo\out\build.log is the place to look."
    exit $LASTEXITCODE
}

Write-Host "Done. ISO is in: $repo\out" -ForegroundColor Green
Write-Host "Test it: .\test\boot-test.ps1 or .\test\install-test.ps1"
