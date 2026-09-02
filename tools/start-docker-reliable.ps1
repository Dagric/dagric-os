[CmdletBinding()]
param(
    [int]$ReadyTimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'

$dockerDesktopExe = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
$dockerCliExe = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
$dockerLocalRoot = Join-Path $env:LOCALAPPDATA 'Docker'
$dockerRunRoot = Join-Path $dockerLocalRoot 'run'
$dockerSecretsRoot = Join-Path $env:LOCALAPPDATA 'docker-secrets-engine'
$dockerPipe = '\\.\pipe\dockerDesktopLinuxEngine'

function Test-DockerEnginePipe {
    try {
        return Test-Path -LiteralPath $dockerPipe
    }
    catch {
        return $false
    }
}

function Get-DockerServerVersion {
    param(
        [int]$TimeoutMilliseconds = 2500
    )

    if (-not (Test-DockerEnginePipe)) {
        return $null
    }

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $dockerCliExe
    $startInfo.Arguments = 'version --format "{{.Server.Version}}"'
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    try {
        $null = $process.Start()
        if (-not $process.WaitForExit($TimeoutMilliseconds)) {
            $process.Kill()
            return $null
        }
        $output = $process.StandardOutput.ReadToEnd().Trim()
        if ($process.ExitCode -ne 0 -or -not $output) {
            return $null
        }
        return $output
    }
    finally {
        $process.Dispose()
    }
}

function Stop-BrokenDockerProcesses {
    $processes = @(
        Get-Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.ProcessName -match '^com\.docker\.backend$|^Docker Desktop$|^DockerCli$|^docker-desktop$|^docker$'
            }
    )
    if ($processes.Count -eq 0) {
        return
    }

    $processes | Stop-Process -Force -ErrorAction SilentlyContinue
    $deadline = (Get-Date).AddSeconds(10)
    do {
        Start-Sleep -Milliseconds 250
        $remaining = @(
            Get-Process -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.ProcessName -match '^com\.docker\.backend$|^Docker Desktop$|^DockerCli$|^docker-desktop$|^docker$'
                }
        )
    } while ($remaining.Count -gt 0 -and (Get-Date) -lt $deadline)

    if ($remaining.Count -gt 0) {
        throw "Could not stop stale Docker processes: $($remaining.ProcessName -join ', ')"
    }
}

function Move-RuntimeDirectory {
    param(
        [Parameter(Mandatory)]
        [string]$LiteralPath,

        [Parameter(Mandatory)]
        [string]$ExpectedParent,

        [Parameter(Mandatory)]
        [string]$ExpectedName
    )

    if (-not (Test-Path -LiteralPath $LiteralPath)) {
        New-Item -ItemType Directory -Path $LiteralPath | Out-Null
        return $null
    }

    $item = Get-Item -LiteralPath $LiteralPath -Force
    if (-not $item.PSIsContainer -or $item.Parent.FullName -ne $ExpectedParent -or $item.Name -ne $ExpectedName) {
        throw "Refusing to move an unexpected runtime path: $LiteralPath"
    }

    $entries = @(Get-ChildItem -LiteralPath $LiteralPath -Force -ErrorAction SilentlyContinue)
    if ($entries.Count -eq 0) {
        return $null
    }

    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $quarantineName = "$ExpectedName.stale-$stamp"
    $quarantinePath = Join-Path $ExpectedParent $quarantineName
    $suffix = 1
    while (Test-Path -LiteralPath $quarantinePath) {
        $quarantineName = "$ExpectedName.stale-$stamp-$suffix"
        $quarantinePath = Join-Path $ExpectedParent $quarantineName
        $suffix++
    }

    Rename-Item -LiteralPath $LiteralPath -NewName $quarantineName
    New-Item -ItemType Directory -Path $LiteralPath | Out-Null
    return $quarantinePath
}

if (-not (Test-Path -LiteralPath $dockerDesktopExe)) {
    throw "Docker Desktop is not installed at $dockerDesktopExe"
}
if (-not (Test-Path -LiteralPath $dockerCliExe)) {
    throw "Docker CLI is not installed at $dockerCliExe"
}

$existingVersion = Get-DockerServerVersion
if ($existingVersion) {
    Write-Output "Docker Desktop is already ready. Server version: $existingVersion"
    exit 0
}

Stop-BrokenDockerProcesses

$quarantined = @()
$movedRunParams = @{
    LiteralPath    = $dockerRunRoot
    ExpectedParent = $dockerLocalRoot
    ExpectedName   = 'run'
}
$movedRun = Move-RuntimeDirectory @movedRunParams
if ($movedRun) {
    $quarantined += $movedRun
}

$movedSecretsParams = @{
    LiteralPath    = $dockerSecretsRoot
    ExpectedParent = $env:LOCALAPPDATA
    ExpectedName   = 'docker-secrets-engine'
}
$movedSecrets = Move-RuntimeDirectory @movedSecretsParams
if ($movedSecrets) {
    $quarantined += $movedSecrets
}

Start-Process -FilePath $dockerDesktopExe -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds($ReadyTimeoutSeconds)
do {
    Start-Sleep -Milliseconds 500
$version = Get-DockerServerVersion
} while (-not $version -and (Get-Date) -lt $deadline)

if (-not $version) {
    throw "Docker Desktop did not expose a responsive Linux engine within $ReadyTimeoutSeconds seconds."
}

Write-Output "Docker Desktop is ready. Server version: $version"
if ($quarantined.Count -gt 0) {
    Write-Output 'Quarantined stale runtime directories:'
    $quarantined | ForEach-Object { Write-Output "  $_" }
}
