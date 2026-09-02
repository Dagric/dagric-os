# Dagric OS - boot the ISO with a blank 50 GB sparse virtual disk attached,
# so the Calamares installer can be exercised end to end.
#   .\test\install-test.ps1           # BIOS mode, then open http://localhost:6080/vnc.html
#   .\test\install-test.ps1 -Uefi     # UEFI firmware (OVMF) - modern-PC simulation
#   .\test\install-test.ps1 -Fresh    # wipe the disk and start over
param([switch]$Fresh, [switch]$Uefi)
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
# Take the most recently built edition-named ISO instead of hard-coding
# live-build's own live-image-amd64.hybrid.iso. build.sh has always named its
# output per edition and container-build.sh does now, so that literal matches
# nothing and this aborted with "No ISO" on a tree holding two of them.
$iso = (Get-ChildItem "$repo\out\dagric-os-*-amd64.iso" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
if (-not $iso) { Write-Host "No ISO in $repo\out - run .\build.ps1 first" -ForegroundColor Red; exit 1 }
Write-Host "Testing $(Split-Path $iso -Leaf)" -ForegroundColor Cyan

# Test against a COPY so a later build.ps1 (which overwrites the working
# ISO) can't corrupt the running VM's mounted CD-ROM. Learned the hard way.
$testIso = "$repo\out\_testing.iso"
Copy-Item $iso $testIso -Force
$iso = $testIso

docker build -t dagric-boottest "$repo\test"
$kvmReady = & "$PSScriptRoot\enable-kvm.ps1"
if (-not $kvmReady) {
    Write-Warning "KVM is unavailable; install remains valid but will be much slower."
}

# Stop the previous VM before trying to remove its disk.  The old order asked
# Docker to delete dagric-disk while dagric-boottest still had the volume open;
# Docker correctly kept the volume, but the error was hidden and -Fresh then
# reused a partially installed disk.  That can turn an install test into a
# convincing false pass, so freshness is now verified rather than assumed.
$existing = docker ps -aq --filter "name=dagric-boottest"
if ($existing) { docker rm -f dagric-boottest | Out-Null }

if ($Fresh) {
    docker volume rm -f dagric-disk 2>$null | Out-Null
    if (docker volume ls -q --filter "name=^dagric-disk$") {
        throw "Could not remove the previous dagric-disk volume; refusing a non-fresh install test."
    }
}
docker volume create dagric-disk | Out-Null
docker run --rm -v dagric-disk:/disk dagric-boottest sh -c "[ -f /disk/disk.qcow2 ] || qemu-img create -f qcow2 /disk/disk.qcow2 50G"

$uefiEnv = "0"; if ($Uefi) { $uefiEnv = "1" }
docker run -d --name dagric-boottest --privileged `
    -e UEFI=$uefiEnv `
    -p 6080:6080 `
    -v "${iso}:/iso/dagric.iso:ro" `
    -v dagric-disk:/disk `
    dagric-boottest
Write-Host "Install-test VM starting ($(if ($Uefi) {'UEFI'} else {'BIOS'})) with 50 GB sparse disk. Watch: http://localhost:6080/vnc.html" -ForegroundColor Green
