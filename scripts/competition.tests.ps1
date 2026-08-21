$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "competition.ps1") -Library

if ((Resolve-OverallState @(
        (New-Check "Backend" "READY" ""),
        (New-Check "Detector" "READY" ""),
        (New-Check "Qwen3-VL" "READY" ""),
        (New-Check "Frontend" "READY" ""),
        (New-Check "Tavily" "DEGRADED" "")
    )) -ne "DEGRADED") { throw "Tavily degradation classification failed." }

if ((Resolve-OverallState @(
        (New-Check "Backend" "READY" ""),
        (New-Check "Detector" "FAILED" ""),
        (New-Check "Qwen3-VL" "READY" ""),
        (New-Check "Frontend" "READY" ""),
        (New-Check "Tavily" "READY" "")
    )) -ne "FAILED") { throw "Detector failure classification failed." }

if ((Resolve-OverallState @(
        (New-Check "Backend" "READY" ""),
        (New-Check "Detector" "READY" ""),
        (New-Check "Qwen3-VL" "NOT RUNNING" ""),
        (New-Check "Frontend" "READY" ""),
        (New-Check "Tavily" "READY" "")
    )) -ne "FAILED") { throw "Qwen failure classification failed." }

if ((Resolve-OverallState @(
        (New-Check "Backend" "NOT RUNNING" ""),
        (New-Check "Detector" "READY" ""),
        (New-Check "Qwen3-VL" "READY" ""),
        (New-Check "Frontend" "READY" ""),
        (New-Check "Tavily" "READY" "")
    )) -ne "FAILED") { throw "Backend failure classification failed." }

$pidProbe = Join-Path ([IO.Path]::GetTempPath()) "competition-pid-safety-$PID.pid"
Set-Content -LiteralPath $pidProbe -Value $PID -Encoding ASCII
try {
    $owned = Read-OwnedProcess $pidProbe @("this-marker-cannot-match") @("pwsh.exe", "powershell.exe")
    if ($null -ne $owned) { throw "PID ownership check accepted an unrelated process." }
    Stop-OwnedProcess "PID safety probe" $pidProbe @("this-marker-cannot-match") @("pwsh.exe", "powershell.exe") | Out-Null
    if (-not (Get-Process -Id $PID -ErrorAction SilentlyContinue)) { throw "PID safety probe stopped the test runner." }
} finally {
    Remove-Item -LiteralPath $pidProbe -Force -ErrorAction SilentlyContinue
}

Write-Output "PASS: competition health classification and core/degraded policy"
