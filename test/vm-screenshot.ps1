# Capture a screenshot of the running boot-test VM to test\screen.png
$ErrorActionPreference = "Stop"
docker exec dagric-boottest sh -c "printf 'screendump /tmp/screen.ppm\n' | socat - UNIX-CONNECT:/tmp/monitor.sock > /dev/null; sleep 1; convert /tmp/screen.ppm /tmp/screen.png"
docker cp dagric-boottest:/tmp/screen.png "$PSScriptRoot\screen.png"
Write-Host "Saved: $PSScriptRoot\screen.png"
