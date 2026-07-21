# Freehold OS - boot the ISO with a blank 20 GB virtual disk attached,
# so the Calamares installer can be exercised end to end.
#   .\test\install-test.ps1           # then open http://localhost:6080/vnc.html
#   .\test\install-test.ps1 -Fresh    # wipe the disk and start over
param([switch]$Fresh)
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$iso = "$repo\out\live-image-amd64.hybrid.iso"

if (-not (Test-Path $iso)) { Write-Host "No ISO - run .\build.ps1 first" -ForegroundColor Red; exit 1 }

docker build -t freehold-boottest "$repo\test"

if ($Fresh) { docker volume rm -f freehold-disk 2>$null | Out-Null }
docker volume create freehold-disk | Out-Null
docker run --rm -v freehold-disk:/disk freehold-boottest sh -c "[ -f /disk/disk.qcow2 ] || qemu-img create -f qcow2 /disk/disk.qcow2 20G"

$existing = docker ps -aq --filter "name=freehold-boottest"
if ($existing) { docker rm -f freehold-boottest | Out-Null }
docker run -d --name freehold-boottest --privileged `
    -p 6080:6080 `
    -v "${iso}:/iso/freehold.iso:ro" `
    -v freehold-disk:/disk `
    freehold-boottest
Write-Host "Install-test VM starting with 20 GB disk. Watch: http://localhost:6080/vnc.html" -ForegroundColor Green
