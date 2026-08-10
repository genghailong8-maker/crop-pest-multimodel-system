param(
    [string]$SshHost = "connect.bjb2.seetacloud.com",
    [int]$SshPort = 10373,
    [string]$SshUser = "root",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519",
    [int]$LocalPort = 8870,
    [int]$RemotePort = 8870,
    [int]$VlmLocalPort = 8890,
    [int]$VlmRemotePort = 8890
)

$ErrorActionPreference = "Stop"

function Test-Detector {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$LocalPort/health" -TimeoutSec 2
        return $health.status -eq "ok"
    } catch { return $false }
}

function Test-Vlm {
    try {
        $models = Invoke-RestMethod -Uri "http://127.0.0.1:$VlmLocalPort/v1/models" -TimeoutSec 2
        return $null -ne $models.data
    } catch { return $false }
}

$detectorReady = Test-Detector
$vlmReady = Test-Vlm
if ($detectorReady -and $vlmReady) {
    Write-Host "Detector and VLM tunnels are already ready."
    exit 0
}

$arguments = @(
    "-N",
    "-o", "BatchMode=yes",
    "-o", "ExitOnForwardFailure=yes",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=3",
    "-i", $IdentityFile,
    "-p", "$SshPort"
)
if (-not $detectorReady) {
    $arguments += @("-L", "${LocalPort}:127.0.0.1:${RemotePort}")
}
if (-not $vlmReady) {
    $arguments += @("-L", "${VlmLocalPort}:127.0.0.1:${VlmRemotePort}")
}
$arguments += "${SshUser}@${SshHost}"

$process = Start-Process -FilePath "ssh.exe" -ArgumentList $arguments -WindowStyle Hidden -PassThru
foreach ($attempt in 1..300) {
    if ($process.HasExited) {
        throw "SSH inference tunnel exited with code $($process.ExitCode)."
    }
    try {
        if (($detectorReady -or (Test-Detector)) -and ($vlmReady -or (Test-Vlm))) {
            Write-Host "Detector tunnel: http://127.0.0.1:$LocalPort"
            Write-Host "VLM tunnel: http://127.0.0.1:$VlmLocalPort"
            exit 0
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $process.HasExited) {
    Stop-Process -Id $process.Id
}
throw "SSH tunnel started, but detector/VLM readiness did not complete within 5 minutes."
