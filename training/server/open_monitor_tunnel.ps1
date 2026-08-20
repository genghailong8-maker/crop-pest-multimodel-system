param(
    [string]$SshHost = "connect.bjb2.seetacloud.com",
    [int]$SshPort = 10373,
    [string]$SshUser = "root",
    [string]$IdentityFile = $env:CROP_SSH_IDENTITY_FILE,
    [int]$LocalPort = 8765
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($IdentityFile)) {
    throw "Pass -IdentityFile or set CROP_SSH_IDENTITY_FILE; the SSH private key is never stored in the repository."
}
$existing = Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Training monitor tunnel is already available: http://localhost:3000/training"
    exit 0
}

$sshPath = (Get-Command ssh.exe).Source
$arguments = @(
    "-N",
    "-o", "ExitOnForwardFailure=yes",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=3",
    "-i", $IdentityFile,
    "-p", $SshPort,
    "-L", "${LocalPort}:127.0.0.1:8765",
    "${SshUser}@${SshHost}"
)

Start-Process -FilePath $sshPath -ArgumentList $arguments -WindowStyle Hidden
Start-Sleep -Seconds 2

$listener = Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction SilentlyContinue
if (-not $listener) {
    throw "The training monitor tunnel failed to start. Check the server instance and SSH address."
}

$health = Invoke-RestMethod -Uri "http://127.0.0.1:${LocalPort}/health" -TimeoutSec 5
if ($health.status -ne "ok") {
    throw "The server-side training monitor is not ready."
}

Write-Host "Training monitor is ready: http://localhost:3000/training"
