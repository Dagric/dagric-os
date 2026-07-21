# Dagric OS - boot the ISO with a blank 20 GB virtual disk attached,
# so the Calamares installer can be exercised end to end.
#   .\test\install-test.ps1           # BIOS mode, then open http://localhost:6080/vnc.html
#   .\test\install-test.ps1 -Uefi     # UEFI firmware (OVMF) - modern-PC simulation
#   .\test\install-test.ps1 -Fresh    # wipe the disk and start over
param([switch]$Fresh, [switch]$Uefi)
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$iso = "$repo\out\live-image-amd64.hybrid.iso"

if (-not (Test-Path $iso)) { Write-Host "No ISO - run .\build.ps1 first" -ForegroundColor Red; exit 1 }

docker build -t dagric-boottest "$repo\test"

if ($Fresh) { docker volume rm -f dagric-disk 2>$null | Out-Null }
docker volume create dagric-disk | Out-Null
docker run --rm -v dagric-disk:/disk dagric-boottest sh -c "[ -f /disk/disk.qcow2 ] || qemu-img create -f qcow2 /disk/disk.qcow2 20G"

$uefiEnv = "0"; if ($Uefi) { $uefiEnv = "1" }
$existing = docker ps -aq --filter "name=dagric-boottest"
if ($existing) { docker rm -f dagric-boottest | Out-Null }
docker run -d --name dagric-boottest --privileged `
    -e UEFI=$uefiEnv `
    -p 6080:6080 `
    -v "${iso}:/iso/dagric.iso:ro" `
    -v dagric-disk:/disk `
    dagric-boottest
Write-Host "Install-test VM starting ($(if ($Uefi) {'UEFI'} else {'BIOS'})) with 20 GB disk. Watch: http://localhost:6080/vnc.html" -ForegroundColor Green
