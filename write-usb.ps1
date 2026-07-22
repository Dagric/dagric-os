# Dagric OS - write an ISO to a USB stick (raw hybrid-ISO write, bootable).
# MUST run elevated. Launch it via:
#   Start-Process powershell -Verb RunAs -ArgumentList '-ExecutionPolicy Bypass -File "C:\Users\1248n\Downloads\OS\write-usb.ps1" -Edition free'
#
# SAFETY: this script refuses to write to anything that is not a removable
# USB disk, and never to the system or boot disk. It matches the target by
# model + bus + size and aborts on any ambiguity.
param(
    [ValidateSet("free","pro")][string]$Edition = "free",
    [string]$ExpectedModel = "ASolid USB",
    [double]$ExpectedSizeGB = 115.2
)
$ErrorActionPreference = "Stop"
$log = "C:\Users\1248n\Downloads\OS\out\write-usb.log"
function Log($m) { $line = "$(Get-Date -Format HH:mm:ss)  $m"; Write-Host $line; Add-Content $log $line }

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "NOT ELEVATED. Re-launch via Start-Process -Verb RunAs." -ForegroundColor Red; Read-Host "Enter to close"; exit 1
}

$iso = if ($Edition -eq "pro") { "C:\Users\1248n\Downloads\OS\out\dagric-os-pro-1.0-amd64.iso" }
       else { "C:\Users\1248n\Downloads\OS\out\dagric-os-1.0-amd64.iso" }
if (-not (Test-Path $iso)) { Log "ISO not found: $iso"; Read-Host "Enter to close"; exit 1 }
Log "Edition=$Edition  ISO=$iso  ($([math]::Round((Get-Item $iso).Length/1GB,2)) GB)"

# --- Identify the target disk by strict criteria ---
# @(...) forces an array so .Count is reliable even for a single match
# (PowerShell 5.1 returns $null for .Count on a lone object). A ~115 GB
# USB disk uniquely identifies the target here (others are 931/57 GB).
$cand = @(Get-Disk | Where-Object {
    $_.BusType -eq "USB" -and -not $_.IsSystem -and -not $_.IsBoot -and
    ([math]::Abs([math]::Round($_.Size/1GB,1) - $ExpectedSizeGB) -lt 3)
})
if ($cand.Count -ne 1) {
    Log "SAFETY ABORT: expected exactly one USB disk of ~$ExpectedSizeGB GB, found $($cand.Count). Doing nothing."
    Get-Disk | Format-Table Number,FriendlyName,BusType,IsSystem,IsBoot,@{N='GB';E={[math]::Round($_.Size/1GB,1)}}
    Read-Host "Enter to close"; exit 1
}
$disk = $cand[0]
Log "Matched: PhysicalDrive$($disk.Number) '$($disk.FriendlyName)' (expected model '$ExpectedModel')"
if ($disk.IsSystem -or $disk.IsBoot -or $disk.Number -eq 0) { Log "SAFETY ABORT: target looks like a system disk."; Read-Host "Enter to close"; exit 1 }
Log "Target: PhysicalDrive$($disk.Number)  $($disk.FriendlyName)  $([math]::Round($disk.Size/1GB,1)) GB  (currently label '$((Get-Partition -DiskNumber $disk.Number -ErrorAction SilentlyContinue | Get-Volume -ErrorAction SilentlyContinue).FileSystemLabel -join ',')')"

Write-Host ""
Write-Host "This ERASES PhysicalDrive$($disk.Number) ($($disk.FriendlyName), $([math]::Round($disk.Size/1GB,1)) GB) completely." -ForegroundColor Yellow
if ((Read-Host "Type ERASE to proceed") -ne "ERASE") { Log "User declined."; exit 0 }

# --- Clear + raw write ---
Log "Clearing disk $($disk.Number)..."
Clear-Disk -Number $disk.Number -RemoveData -RemoveOEM -Confirm:$false
Start-Sleep 2

Log "Raw-writing ISO to \\.\PhysicalDrive$($disk.Number) ..."
$src = [System.IO.File]::OpenRead($iso)
$dst = New-Object System.IO.FileStream("\\.\PhysicalDrive$($disk.Number)", [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write)
try {
    $buf = New-Object byte[] (8MB); $total = 0; $len = $src.Length
    while (($n = $src.Read($buf, 0, $buf.Length)) -gt 0) {
        $dst.Write($buf, 0, $n); $total += $n
        Write-Progress -Activity "Writing Dagric OS ($Edition)" -Status "$([math]::Round($total/1MB)) / $([math]::Round($len/1MB)) MB" -PercentComplete ($total*100/$len)
    }
    $dst.Flush()
} finally { $src.Close(); $dst.Close() }
Log "Wrote $([math]::Round($total/1MB)) MB. Done."

Write-Host ""
Write-Host "SUCCESS. Dagric OS ($Edition) is on the USB. Safely eject, then boot the target PC from it" -ForegroundColor Green
Write-Host "(boot menu key is usually F12/F10/ESC; pick the USB / UEFI entry)."
Read-Host "Enter to close"
