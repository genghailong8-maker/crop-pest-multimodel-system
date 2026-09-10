param(
    [string]$SshHost = "connect.bjb2.seetacloud.com",
    [int]$SshPort = 10373,
    [string]$SshUser = "root",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519",
    [int]$LocalPort = 8870,
    [int]$RemotePort = 8870,
    [string]$PidFile = ""
)

$ErrorActionPreference = "Stop"

function Test-Detector {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$LocalPort/health" -TimeoutSec 2
        return $health.status -eq "ok"
    } catch { return $false }
}

$detectorReady = Test-Detector
if ($detectorReady) {
    Write-Host "Detector tunnel is already ready."
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
$arguments += "${SshUser}@${SshHost}"

$process = Start-Process -FilePath "ssh.exe" -ArgumentList $arguments -WindowStyle Hidden -PassThru
if ($PidFile) {
    $pidDirectory = Split-Path -Parent $PidFile
    New-Item -ItemType Directory -Force -Path $pidDirectory | Out-Null
    Set-Content -LiteralPath $PidFile -Value $process.Id -Encoding ASCII
}
foreach ($attempt in 1..300) {
    if ($process.HasExited) {
        if ($PidFile) { Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue }
        throw "SSH inference tunnel exited with code $($process.ExitCode)."
    }
    try {
        if ($detectorReady -or (Test-Detector)) {
            Write-Host "Detector tunnel: http://127.0.0.1:$LocalPort"
            exit 0
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $process.HasExited) {
    Stop-Process -Id $process.Id
}
if ($PidFile) { Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue }
throw "SSH tunnel started, but detector readiness did not complete within 5 minutes."
