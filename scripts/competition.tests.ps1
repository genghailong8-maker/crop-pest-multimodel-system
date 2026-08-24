$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "competition.ps1") -Library

if ((Resolve-OverallState @(
        (New-Check "Backend" "READY" ""),
        (New-Check "Detector" "READY" ""),
        (New-Check "Frontend" "READY" ""),
        (New-Check "Tavily" "DEGRADED" "")
    )) -ne "DEGRADED") { throw "Tavily degradation classification failed." }

if ((Resolve-OverallState @(
        (New-Check "Backend" "READY" ""),
        (New-Check "Detector" "FAILED" ""),
        (New-Check "Frontend" "READY" ""),
        (New-Check "Tavily" "READY" "")
    )) -ne "FAILED") { throw "Detector failure classification failed." }

if ((Resolve-OverallState @(
        (New-Check "Backend" "NOT RUNNING" ""),
        (New-Check "Detector" "READY" ""),
        (New-Check "Frontend" "READY" ""),
        (New-Check "Tavily" "READY" "")
    )) -ne "FAILED") { throw "Backend failure classification failed." }

function Restore-TestEnvironmentValue([string]$Name, [string]$Value) {
    if ($null -eq $Value) {
        Remove-Item -Path "Env:$Name" -ErrorAction SilentlyContinue
    } else {
        Set-Item -Path "Env:$Name" -Value $Value
    }
}

$oldStorage = [Environment]::GetEnvironmentVariable("CROP_STORAGE_DIR")
$oldKnowledge = [Environment]::GetEnvironmentVariable("CROP_KNOWLEDGE_DIR")
$testRoot = Join-Path ([IO.Path]::GetTempPath()) "编程大赛 P1 路径测试 $PID"
$absoluteStorage = Join-Path $testRoot "storage folder"
$absoluteKnowledge = Join-Path $testRoot "knowledge folder"
$missingKnowledge = Join-Path $testRoot "does-not-exist"
try {
    # Test 1: repository-root semantics match backend/app/config.py.
    $env:CROP_STORAGE_DIR = "runtime"
    $env:CROP_KNOWLEDGE_DIR = "..\knowledge\baidu-baike-20260818"
    $rootChecks = @(Get-StorageStatus)
    $expectedStorage = [IO.Path]::GetFullPath((Join-Path $script:BackendRoot "runtime"))
    $expectedKnowledge = [IO.Path]::GetFullPath((Join-Path $script:BackendRoot "..\knowledge\baidu-baike-20260818"))
    if ($rootChecks.storage.Detail -ne $expectedStorage -or $rootChecks.storage.State -ne "READY") { throw "Repository-root storage path resolution failed." }
    if ($rootChecks.knowledge.Detail -ne $expectedKnowledge -or $rootChecks.knowledge.State -ne "READY") { throw "Repository-root knowledge path resolution failed." }

    # Test 2: an absolute script call from outside the repository keeps the same paths.
    $outsideRoot = Join-Path ([IO.Path]::GetTempPath()) "competition-p1-outside-$PID"
    New-Item -ItemType Directory -Force -Path $outsideRoot | Out-Null
    Push-Location $outsideRoot
    try {
        $statusOutput = (& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $script:WorkspaceRoot "scripts\competition.ps1") status | Out-String)
    } finally {
        Pop-Location
        Remove-Item -LiteralPath $outsideRoot -Force -Recurse -ErrorAction SilentlyContinue
    }
    if ($statusOutput -notmatch "Storage\s+READY" -or $statusOutput -notmatch "Knowledge\s+READY") { throw "External-cwd status path resolution failed.`n$statusOutput" }

    # Tests 3/4/6: absolute paths, including Chinese characters and spaces.
    New-Item -ItemType Directory -Force -Path $absoluteStorage, $absoluteKnowledge | Out-Null
    Set-Content -LiteralPath (Join-Path $absoluteKnowledge "manifest.json") -Value '{}' -Encoding UTF8
    $env:CROP_STORAGE_DIR = $absoluteStorage
    $env:CROP_KNOWLEDGE_DIR = $absoluteKnowledge
    $absoluteChecks = @(Get-StorageStatus)
    if ($absoluteChecks.storage.Detail -ne [IO.Path]::GetFullPath($absoluteStorage) -or $absoluteChecks.storage.State -ne "READY") { throw "Absolute storage path resolution failed." }
    if ($absoluteChecks.knowledge.Detail -ne [IO.Path]::GetFullPath($absoluteKnowledge) -or $absoluteChecks.knowledge.State -ne "READY") { throw "Absolute knowledge path resolution failed." }

    # Test 5: a real missing knowledge directory remains degraded.
    $env:CROP_STORAGE_DIR = $absoluteStorage
    $env:CROP_KNOWLEDGE_DIR = $missingKnowledge
    $missingChecks = @(Get-StorageStatus)
    if ($missingChecks.knowledge.State -ne "FAILED") { throw "Missing knowledge directory was not reported as degraded." }
} finally {
    Restore-TestEnvironmentValue "CROP_STORAGE_DIR" $oldStorage
    Restore-TestEnvironmentValue "CROP_KNOWLEDGE_DIR" $oldKnowledge
    Remove-Item -LiteralPath $testRoot -Force -Recurse -ErrorAction SilentlyContinue
}

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
