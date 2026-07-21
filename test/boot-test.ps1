# Freehold OS - boot the built ISO in a containerized QEMU VM.
#
#   .\test\boot-test.ps1            # then open http://localhost:6080/vnc.html
#   docker rm -f freehold-boottest  # to stop it
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$iso = "$repo\out\live-image-amd64.hybrid.iso"

if (-not (Test-Path $iso)) { Write-Host "No ISO at $iso - run .\build.ps1 first" -ForegroundColor Red; exit 1 }

docker build -t freehold-boottest "$repo\test"
$existing = docker ps -aq --filter "name=freehold-boottest"
if ($existing) { docker rm -f freehold-boottest | Out-Null }
docker run -d --name freehold-boottest --privileged `
    -p 6080:6080 `
    -v "${iso}:/iso/freehold.iso:ro" `
    freehold-boottest
Write-Host "VM starting. Watch it boot at: http://localhost:6080/vnc.html" -ForegroundColor Green
