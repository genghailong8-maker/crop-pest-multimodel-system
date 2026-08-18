param(
    [ValidateSet("Start", "Stop", "Status")]
    [string]$Action = "Status"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $workspaceRoot "tmp\gpu-relay"
$gpuPidFile = Join-Path $stateDir "gpu-tunnel.pid"
$labPidFile = Join-Path $stateDir "lab-reverse-tunnel.pid"
$sshExe = Join-Path $env:WINDIR "System32\OpenSSH\ssh.exe"
$gpuKey = Join-Path $env:USERPROFILE ".ssh\codex_autodl_nongxin_2026"

function Get-RelayProcess([string]$PidFile, [string]$CommandMarker) {
    if (-not (Test-Path -LiteralPath $PidFile)) { return $null }
    $savedPid = 0
    if (-not [int]::TryParse((Get-Content -LiteralPath $PidFile -Raw).Trim(), [ref]$savedPid)) {
        return $null
    }
    $details = Get-CimInstance Win32_Process -Filter "ProcessId = $savedPid" -ErrorAction SilentlyContinue
    if (-not $details -or $details.Name -ne "ssh.exe" -or $details.CommandLine -notlike "*$CommandMarker*") {
        return $null
    }
    return Get-Process -Id $savedPid -ErrorAction SilentlyContinue
}

function Stop-RelayProcess([string]$PidFile, [string]$CommandMarker) {
    $process = Get-RelayProcess $PidFile $CommandMarker
    if ($process) {
        Stop-Process -Id $process.Id -Force
        $process.WaitForExit()
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

function Wait-ForPort([int]$Port, [int]$Seconds = 15) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
        if ($listener) { return $true }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    return $false
}

if ($Action -eq "Stop") {
    Stop-RelayProcess $labPidFile "18000:127.0.0.1:18001"
    Stop-RelayProcess $gpuPidFile "18001:127.0.0.1:8000"
    Write-Output "Windows GPU relay stopped."
    exit 0
}

if ($Action -eq "Status") {
    $gpuProcess = Get-RelayProcess $gpuPidFile "18001:127.0.0.1:8000"
    $labProcess = Get-RelayProcess $labPidFile "18000:127.0.0.1:18001"
    [pscustomobject]@{
        gpu_tunnel_pid = if ($gpuProcess) { $gpuProcess.Id } else { $null }
        lab_reverse_tunnel_pid = if ($labProcess) { $labProcess.Id } else { $null }
        local_port_18001 = [bool](Get-NetTCPConnection -State Listen -LocalPort 18001 -ErrorAction SilentlyContinue)
    } | ConvertTo-Json
    exit 0
}

New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
if ((Get-RelayProcess $gpuPidFile "18001:127.0.0.1:8000") -or (Get-RelayProcess $labPidFile "18000:127.0.0.1:18001")) {
    throw "Relay is already partially or fully running. Run Stop, then Start."
}
if (Get-NetTCPConnection -State Listen -LocalPort 18001 -ErrorAction SilentlyContinue) {
    throw "Local port 18001 is already in use."
}

$common = @(
    "-N", "-T", "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes",
    "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
    "-o", "ConnectTimeout=10", "-o", "LogLevel=ERROR"
)
$gpuArgs = $common + @(
    "-i", $gpuKey, "-p", "10373",
    "-L", "127.0.0.1:18001:127.0.0.1:8000",
    "root@connect.bjb2.seetacloud.com"
)
$gpuProcess = Start-Process -FilePath $sshExe -ArgumentList $gpuArgs -WindowStyle Hidden -PassThru
Set-Content -LiteralPath $gpuPidFile -Value $gpuProcess.Id -Encoding ASCII
if (-not (Wait-ForPort 18001)) {
    Stop-RelayProcess $gpuPidFile "18001:127.0.0.1:8000"
    throw "GPU tunnel did not open local port 18001."
}

$labArgs = $common + @(
    "-R", "127.0.0.1:18000:127.0.0.1:18001", "ghl"
)
$labProcess = Start-Process -FilePath $sshExe -ArgumentList $labArgs -WindowStyle Hidden -PassThru
Set-Content -LiteralPath $labPidFile -Value $labProcess.Id -Encoding ASCII
Start-Sleep -Seconds 2
if (-not (Get-RelayProcess $labPidFile "18000:127.0.0.1:18001")) {
    Stop-RelayProcess $gpuPidFile "18001:127.0.0.1:8000"
    Remove-Item -LiteralPath $labPidFile -Force -ErrorAction SilentlyContinue
    throw "Lab reverse tunnel exited before becoming ready."
}

Write-Output "Windows GPU relay started. Keep this computer awake and connected."
& $PSCommandPath -Action Status
