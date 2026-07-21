# Dagric OS - build the dagric-* config packages and generate the
# signed APT repository in out\repo.
#   .\repo.ps1
$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot

docker build -t dagric-builder "$repo\docker"
New-Item -ItemType Directory -Force "$repo\out" | Out-Null
docker volume create dagric-repo-keys | Out-Null

docker run --rm `
    -v "${repo}:/src:ro" `
    -v "${repo}\out:/out" `
    -v dagric-repo-keys:/keys `
    dagric-builder sh -c "sh /src/packages/build-packages.sh && sh /src/packages/make-repo.sh"

Write-Host "Done. Signed repo: $repo\out\repo (signing key kept in Docker volume dagric-repo-keys)" -ForegroundColor Green
