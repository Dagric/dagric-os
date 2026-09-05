# Dagric OS - boot the built ISO in a containerized QEMU VM.
#
#   .\test\boot-test.ps1            # then open http://localhost:6080/vnc.html
#   docker rm -f dagric-boottest  # to stop it
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

# Test against a COPY so a later build.ps1 can't corrupt the running VM's
# mounted CD-ROM (same protection as install-test.ps1).
$testIso = "$repo\out\_testing.iso"
Copy-Item $iso $testIso -Force
$iso = $testIso

docker build -t dagric-boottest "$repo\test"
$kvmReady = & "$PSScriptRoot\enable-kvm.ps1"
if (-not $kvmReady) {
    Write-Warning "KVM is unavailable; boot remains valid but will be much slower."
}
$existing = docker ps -aq --filter "name=dagric-boottest"
if ($existing) { docker rm -f dagric-boottest | Out-Null }
# promo/capture-real-vm.py records the framebuffer through VNC. Bind that
# unauthenticated test display to loopback only so it is never exposed to LAN.
$runtimeSecurity = @("--cap-drop=ALL", "--security-opt=no-new-privileges:true", "--pids-limit=512")
if ($kvmReady) { $runtimeSecurity += "--device=/dev/kvm" }
docker run -d --name dagric-boottest @runtimeSecurity `
    --read-only --tmpfs /tmp:rw,nosuid,nodev,size=64m `
    -p 127.0.0.1:6080:6080 `
    -p 127.0.0.1:5914:5900 `
    -v "${iso}:/iso/dagric.iso:ro" `
    dagric-boottest
Write-Host "VM starting. Watch it boot at: http://localhost:6080/vnc.html" -ForegroundColor Green
