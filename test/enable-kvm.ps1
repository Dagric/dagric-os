# Dagric OS - make Docker Desktop expose its existing WSL2 KVM device.
#
# Docker Desktop's VM already ships the KVM modules, but it does not load them
# after a restart.  Without this small setup step the QEMU test container falls
# back to TCG and a three-minute install takes well over an hour.  Failure is
# deliberately non-fatal: callers can still run the slower compatibility path.
$ErrorActionPreference = "Continue"

function Test-DockerKvm {
    & docker run --rm --privileged -v /dev:/hostdev alpine `
        sh -c "test -e /hostdev/kvm" 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

if (Test-DockerKvm) {
    Write-Host "Docker KVM is already available." -ForegroundColor Green
    $true
    return
}

$vendor = (& docker run --rm --privileged alpine sh -c `
    'grep -oE "\bvmx\b|\bsvm\b" /proc/cpuinfo 2>/dev/null | head -1' `
    2>$null | Select-Object -First 1)
$vendor = "$vendor".Trim()
$module = switch ($vendor) {
    "svm" { "kvm_amd" }
    "vmx" { "kvm_intel" }
    default { $null }
}

if (-not $module) {
    Write-Warning "Docker's WSL VM exposes neither svm nor vmx; QEMU will use software emulation."
    $false
    return
}

& docker run --rm --privileged -v /lib/modules:/lib/modules alpine sh -c `
    "apk add -q kmod 2>/dev/null && modprobe $module" | Out-Null
if ($LASTEXITCODE -ne 0 -or -not (Test-DockerKvm)) {
    Write-Warning "Could not load $module in Docker Desktop; QEMU will use software emulation."
    $false
    return
}

Write-Host "Docker KVM enabled ($module)." -ForegroundColor Green
$true
