# Freehold OS - package a release: versioned ISO name + SHA256 checksums.
#   .\release.ps1 [-Version 1.0]
param([string]$Version = "1.0")
$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$iso = "$repo\out\live-image-amd64.hybrid.iso"
if (-not (Test-Path $iso)) { Write-Host "No ISO - run .\build.ps1 first" -ForegroundColor Red; exit 1 }

$name = "freehold-os-$Version-amd64.iso"
Copy-Item $iso "$repo\out\$name" -Force
$hash = (Get-FileHash "$repo\out\$name" -Algorithm SHA256).Hash.ToLower()
"$hash  $name" | Out-File "$repo\out\SHA256SUMS" -Encoding ascii
Write-Host "Release ready:" -ForegroundColor Green
Write-Host "  out\$name"
Write-Host "  out\SHA256SUMS  ($hash)"
Write-Host "Publish both files together so buyers can verify their download."
