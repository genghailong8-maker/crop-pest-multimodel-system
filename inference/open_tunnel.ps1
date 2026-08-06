param(
    [string]$SshHost = "connect.bjb2.seetacloud.com",
    [int]$SshPort = 10373,
    [string]$SshUser = "root",
    [string]$IdentityFile = "C:\Users\genghailong\.ssh\codex_autodl_nongxin_2026",
    [int]$LocalPort = 8870,
    [int]$RemotePort = 8870
)

$ErrorActionPreference = "Stop"

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$LocalPort/health" -TimeoutSec 2
    if ($health.status -eq "ok") {
        Write-Host "Inference tunnel is already ready at http://127.0.0.1:$LocalPort"
        exit 0
    }
} catch {}

$arguments = @(
    "-N",
    "-o", "BatchMode=yes",
    "-o", "ExitOnForwardFailure=yes",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=3",
    "-i", $IdentityFile,
    "-p", "$SshPort",
    "-L", "${LocalPort}:127.0.0.1:${RemotePort}",
    "${SshUser}@${SshHost}"
)

$process = Start-Process -FilePath "ssh.exe" -ArgumentList $arguments -WindowStyle Hidden -PassThru
foreach ($attempt in 1..30) {
    if ($process.HasExited) {
        throw "SSH inference tunnel exited with code $($process.ExitCode)."
    }
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$LocalPort/health" -TimeoutSec 2
        if ($health.status -eq "ok") {
            Write-Host "Inference tunnel is ready at http://127.0.0.1:$LocalPort"
            exit 0
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $process.HasExited) {
    Stop-Process -Id $process.Id
}
throw "Inference tunnel started, but the server health endpoint did not become ready."
