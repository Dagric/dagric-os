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
$sourceCommit = (git -C "$repo" rev-parse HEAD).Trim()
if ($sourceCommit -notmatch '^[0-9a-fA-F]{40}$') {
    throw "Could not resolve the Dagric source commit. Build from a Git checkout."
}

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
$buildToken = [guid]::NewGuid().ToString('N').Substring(0, 12)
$outputVolume = "dagric-build-output-$buildToken-$Edition"
$exportContainer = "dagric-build-export-$buildToken-$Edition"
docker volume create $outputVolume *> $null
if ($LASTEXITCODE -ne 0) { throw "Could not create the Docker output volume." }

try {
    # Keep the multi-gigabyte ISO on Docker's Linux filesystem while it is
    # built. Direct writes through a Windows bind mount have failed at 1-4 GB
    # with ENOMEM and left plausible-looking truncated files behind.
    docker run --rm --privileged `
        -e EDITION=$Edition `
        -e DAGRIC_SOURCE_COMMIT=$sourceCommit `
        -v "${repo}:/src:ro" `
        -v "${outputVolume}:/out" `
        -v dagric-lb-cache:/build/cache `
        dagric-builder `
        sh /src/docker/container-build.sh
    $buildExit = $LASTEXITCODE

    # docker cp streams through the engine instead of the fragile bind-mount
    # bridge. Export the log on failure too, then verify the successful copy by
    # hashing the exact host file against SHA256SUMS from the output volume.
    docker create --name $exportContainer -v "${outputVolume}:/release:ro" dagric-builder true *> $null
    if ($LASTEXITCODE -ne 0) { throw "Could not create the ISO export helper." }
    docker cp "${exportContainer}:/release/." "$repo\out"
    if ($LASTEXITCODE -ne 0) { throw "Could not export the Docker build output." }

    if ($buildExit -ne 0) {
        throw "Build failed inside Docker (exit $buildExit). See $repo\out\build.log."
    }

    $isoName = if ($Edition -eq 'pro') { 'dagric-os-pro-1.0-amd64.iso' } else { 'dagric-os-1.0-amd64.iso' }
    $isoPath = Join-Path "$repo\out" $isoName
    $expectedLine = Get-Content "$repo\out\SHA256SUMS" | Where-Object { $_ -match "  $([regex]::Escape($isoName))$" }
    if (-not $expectedLine) { throw "SHA256SUMS does not contain $isoName." }
    $expectedHash = ($expectedLine -split '\s+')[0].ToLowerInvariant()
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $isoPath).Hash.ToLowerInvariant()
    if ($actualHash -ne $expectedHash) {
        throw "Exported ISO checksum mismatch. Expected $expectedHash, got $actualHash."
    }
}
finally {
    docker rm -f $exportContainer *> $null
    docker volume rm -f $outputVolume *> $null
}

Write-Host "Done. ISO is in: $repo\out" -ForegroundColor Green
Write-Host "Test it: .\test\boot-test.ps1 or .\test\install-test.ps1"
