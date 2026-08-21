[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "status", "stop", "smoke")]
    [string]$Action = "status",
    [int]$BackendPort = 8000,
    [int]$WebPort = 3000,
    [switch]$CheckTavilyNetwork,
    [switch]$DryRun,
    [switch]$Library
)

$ErrorActionPreference = "Stop"
$script:WorkspaceRoot = Split-Path -Parent $PSScriptRoot
$script:BackendRoot = Join-Path $script:WorkspaceRoot "backend"
$script:WebRoot = Join-Path $script:WorkspaceRoot "web"
$script:StateDir = Join-Path $script:WorkspaceRoot "tmp\competition"
$script:LogDir = Join-Path $script:StateDir "logs"
$script:BackendPidFile = Join-Path $script:StateDir "competition-backend.pid"
$script:WebPidFile = Join-Path $script:StateDir "competition-web.pid"
$script:WebPortFile = Join-Path $script:StateDir "competition-web.port"
$script:TunnelPidFile = Join-Path $script:StateDir "competition-tunnel.pid"

function Get-EnvFilePaths {
    @(
        (Join-Path $script:WorkspaceRoot ".env"),
        (Join-Path $script:BackendRoot ".env")
    ) | Where-Object { Test-Path -LiteralPath $_ }
}

function Get-ConfiguredValue([string]$Name) {
    $environmentValue = [Environment]::GetEnvironmentVariable($Name)
    if (-not [string]::IsNullOrWhiteSpace($environmentValue)) {
        return $environmentValue.Trim()
    }
    foreach ($path in Get-EnvFilePaths) {
        foreach ($line in Get-Content -LiteralPath $path -ErrorAction SilentlyContinue) {
            if ($line -match '^\s*(?<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?<value>.*)\s*$' -and $Matches.name -ceq $Name) {
                $value = $Matches.value.Trim()
                if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
                    $value = $value.Substring(1, $value.Length - 2)
                }
                if (-not [string]::IsNullOrWhiteSpace($value)) {
                    return $value.Trim()
                }
            }
        }
    }
    return $null
}

function Resolve-BackendPath([string]$ConfiguredPath, [string]$DefaultPath) {
    $value = if ([string]::IsNullOrWhiteSpace($ConfiguredPath)) { $DefaultPath } else { $ConfiguredPath }
    $value = [Environment]::ExpandEnvironmentVariables($value.Trim())
    if ([IO.Path]::IsPathRooted($value)) {
        return [IO.Path]::GetFullPath($value)
    }
    return [IO.Path]::GetFullPath((Join-Path $script:BackendRoot $value))
}

function Import-CompetitionEnv {
    foreach ($path in Get-EnvFilePaths) {
        foreach ($line in Get-Content -LiteralPath $path -ErrorAction SilentlyContinue) {
            if ($line -match '^\s*(?<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?<value>.*)\s*$') {
                $name = $Matches.name
                if (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) {
                    continue
                }
                $value = $Matches.value.Trim()
                if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
                    $value = $value.Substring(1, $value.Length - 2)
                }
                Set-Item -Path "Env:$name" -Value $value
            }
        }
    }
}

function Set-CompetitionDefault([string]$Name, [string]$Value) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name))) {
        Set-Item -Path "Env:$Name" -Value $Value
    }
}

function Set-CompetitionRuntimeEnv {
    Import-CompetitionEnv
    Set-CompetitionDefault "CROP_API_HOST" "127.0.0.1"
    Set-CompetitionDefault "CROP_API_PORT" "$BackendPort"
    Set-CompetitionDefault "CROP_DETECTOR_ENDPOINT" "http://127.0.0.1:8870/v1/detect"
    Set-CompetitionDefault "CROP_VLM_ENDPOINT" "http://127.0.0.1:8890/v1/chat/completions"
    Set-CompetitionDefault "CROP_VLM_MODEL" "crop-pest-vlm"
    Set-CompetitionDefault "CROP_SEARCH_PROVIDER" "tavily"
    Set-CompetitionDefault "CROP_SEARCH_TIMEOUT_SECONDS" "10"
    Set-CompetitionDefault "CROP_SEARCH_MAX_SOURCES" "5"
    Set-CompetitionDefault "NEXT_PUBLIC_API_BASE_URL" "http://127.0.0.1:$BackendPort"
}

function Get-PythonPath {
    $candidate = Join-Path $script:BackendRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $candidate) { return $candidate }
    $command = Get-Command python.exe, python -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) { return $command.Source }
    return $null
}

function Get-NpmPath {
    $command = Get-Command npm.cmd, npm -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) { return $command.Source }
    return $null
}

function Get-SshPath {
    $command = Get-Command ssh.exe, ssh -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) { return $command.Source }
    return $null
}

function Get-GpuIdentityPath {
    $configured = Get-ConfiguredValue "CROP_GPU_SSH_IDENTITY_FILE"
    if ($configured) { return [Environment]::ExpandEnvironmentVariables($configured) }
    return Join-Path $env:USERPROFILE ".ssh\id_ed25519"
}

function Test-VersionAtLeast([string]$Text, [version]$Minimum) {
    try {
        $version = [version](($Text -replace '^[^0-9]*', '').Split('-')[0])
        return $version -ge $Minimum
    } catch {
        return $false
    }
}

function New-Check([string]$Name, [string]$State, [string]$Detail, [string]$Fix = "", [bool]$Blocking = $false) {
    [pscustomobject]@{ Name = $Name; State = $State; Detail = $Detail; Fix = $Fix; Blocking = $Blocking }
}

function Get-PreflightChecks {
    $checks = [System.Collections.Generic.List[object]]::new()
    $required = @(
        (Join-Path $script:WorkspaceRoot "inference\open_tunnel.ps1"),
        (Join-Path $script:BackendRoot "app\main.py"),
        (Join-Path $script:WebRoot "package.json"),
        (Join-Path $script:WorkspaceRoot "knowledge\baidu-baike-20260818\manifest.json")
    )
    foreach ($path in $required) {
        $checks.Add((New-Check "Project file $(Split-Path -Leaf $path)" $(if (Test-Path -LiteralPath $path) { "READY" } else { "FAILED" }) $path "Restore the repository files before starting." (-not (Test-Path -LiteralPath $path))))
    }

    $python = Get-PythonPath
    if ($python) {
        $versionText = (& $python --version 2>&1 | Out-String).Trim()
        $ok = Test-VersionAtLeast $versionText ([version]"3.11")
        $checks.Add((New-Check "Python" $(if ($ok) { "READY" } else { "FAILED" }) "$versionText ($python)" "Use backend\.venv\Scripts\python.exe or Python >= 3.11." (-not $ok)))
    } else {
        $checks.Add((New-Check "Python" "FAILED" "No Python interpreter found." "Create backend\.venv and install backend dependencies." $true))
    }

    $venv = Test-Path -LiteralPath (Join-Path $script:BackendRoot ".venv")
    $checks.Add((New-Check "backend/.venv" $(if ($venv) { "READY" } else { "FAILED" }) $(if ($venv) { "Existing virtual environment" } else { "Missing virtual environment" }) "cd backend; py -m venv .venv; .\.venv\Scripts\pip.exe install -e ." (-not $venv)))

    $node = Get-Command node.exe, node -ErrorAction SilentlyContinue | Select-Object -First 1
    $npm = Get-NpmPath
    if ($node) {
        $nodeVersion = (& $node.Source --version 2>&1 | Out-String).Trim()
        $nodeOk = Test-VersionAtLeast $nodeVersion ([version]"22.13.0")
        $checks.Add((New-Check "Node" $(if ($nodeOk) { "READY" } else { "FAILED" }) "$nodeVersion ($($node.Source))" "Install Node.js >= 22.13.0." (-not $nodeOk)))
    } else {
        $checks.Add((New-Check "Node" "FAILED" "node.exe was not found." "Install Node.js >= 22.13.0." $true))
    }
    $checks.Add((New-Check "npm" $(if ($npm) { "READY" } else { "FAILED" }) $(if ($npm) { (& $npm --version 2>&1 | Out-String).Trim() } else { "npm was not found." }) "Install npm with Node.js." (-not [bool]$npm)))

    $nodeModules = Test-Path -LiteralPath (Join-Path $script:WebRoot "node_modules")
    $checks.Add((New-Check "web/node_modules" $(if ($nodeModules) { "READY" } else { "FAILED" }) $(if ($nodeModules) { "Dependencies installed" } else { "Dependencies are missing" }) "cd web; npm ci" (-not $nodeModules)))

    $ssh = Get-SshPath
    $checks.Add((New-Check "ssh.exe" $(if ($ssh) { "READY" } else { "FAILED" }) $(if ($ssh) { $ssh } else { "OpenSSH client was not found." }) "Install the Windows OpenSSH client." (-not [bool]$ssh)))
    $detector = Get-DetectorStatus
    $vlm = Get-QwenStatus
    if ($detector.State -ne "READY" -or $vlm.State -ne "READY") {
        $identity = Get-GpuIdentityPath
        $identityReady = Test-Path -LiteralPath $identity
        $checks.Add((New-Check "GPU SSH identity" $(if ($identityReady) { "READY" } else { "FAILED" }) $(if ($identityReady) { $identity } else { "IdentityFile not found: $identity" }) "Set CROP_GPU_SSH_IDENTITY_FILE to the GPU-only private key path; do not use the GitHub key by assumption." (-not $identityReady)))
    } else {
        $checks.Add((New-Check "GPU SSH identity" "READY" "Detector and Qwen are already ready; no tunnel is needed."))
    }
    return $checks
}

function Invoke-JsonGet([string]$Uri, [int]$TimeoutSeconds = 5) {
    try {
        return Invoke-RestMethod -Uri $Uri -Method Get -TimeoutSec $TimeoutSeconds -ErrorAction Stop
    } catch {
        return $null
    }
}

function Get-BackendStatus {
    $uri = "http://127.0.0.1:$BackendPort/health"
    $payload = Invoke-JsonGet $uri
    if ($null -eq $payload) { return New-Check "Backend" "NOT RUNNING" $uri "Start the backend with the competition entrypoint." }
    if ($payload.status -ne "ok") { return New-Check "Backend" "FAILED" "$uri returned a non-ready status." "Inspect tmp\competition\logs\backend.err.log." $true }
    return New-Check "Backend" "READY" $uri
}

function Get-DetectorStatus {
    $uri = "http://127.0.0.1:8870/health"
    $payload = Invoke-JsonGet $uri
    $mainLoaded = $false
    if ($payload -and $payload.routing -and $payload.routing.models -and $payload.routing.models.main) {
        $mainLoaded = [bool]$payload.routing.models.main.loaded
    }
    if ($null -eq $payload) { return New-Check "Detector" "NOT RUNNING" $uri "Confirm the remote detector and reopen inference/open_tunnel.ps1." $true }
    if ($payload.status -ne "ok" -or [int]$payload.class_count -ne 16 -or -not $mainLoaded) {
        return New-Check "Detector" "FAILED" "$uri is reachable but the 16-class model is not ready." "Expected status=ok, class_count=16 and routing.models.main.loaded=true." $true
    }
    return New-Check "Detector" "READY" "$uri (16 classes, shadow routing)"
}

function Get-QwenStatus {
    $uri = "http://127.0.0.1:8890/v1/models"
    $payload = Invoke-JsonGet $uri
    $modelName = Get-ConfiguredValue "CROP_VLM_MODEL"
    if (-not $modelName) { $modelName = "crop-pest-vlm" }
    $found = $false
    if ($payload -and $payload.data) {
        $found = @($payload.data | Where-Object { $_.id -eq $modelName }).Count -gt 0
    }
    if ($null -eq $payload) { return New-Check "Qwen3-VL" "NOT RUNNING" $uri "Confirm Qwen3-VL is running and reopen inference/open_tunnel.ps1." $true }
    if (-not $found) { return New-Check "Qwen3-VL" "FAILED" "$uri does not list $modelName." "Start the configured Qwen3-VL service; do not silently change the model." $true }
    return New-Check "Qwen3-VL" "READY" "$uri ($modelName)"
}

function Get-FrontendStatus {
    $uri = "http://localhost:$WebPort/"
    try {
        $response = Invoke-WebRequest -Uri $uri -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ([int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 400) { return New-Check "Frontend" "READY" $uri }
        return New-Check "Frontend" "FAILED" "$uri returned HTTP $($response.StatusCode)." "Inspect tmp\competition\logs\web.err.log."
    } catch {
        return New-Check "Frontend" "NOT RUNNING" $uri "Start the web production server with the competition entrypoint."
    }
}

function Test-TavilyNetwork {
    $key = Get-ConfiguredValue "TAVILY_API_KEY"
    $endpoint = Get-ConfiguredValue "CROP_TAVILY_ENDPOINT"
    if (-not $endpoint) { $endpoint = "https://api.tavily.com/search" }
    if (-not $key) { return $false }
    try {
        $body = @{ api_key = $key; query = "蛴螬 农业 危害"; search_depth = "basic"; max_results = 1 } | ConvertTo-Json -Compress
        $response = Invoke-RestMethod -Uri $endpoint -Method Post -ContentType "application/json" -Body $body -TimeoutSec 10 -ErrorAction Stop
        return $null -ne $response.results
    } catch {
        return $false
    }
}

function Get-TavilyStatus([switch]$Network) {
    $provider = Get-ConfiguredValue "CROP_SEARCH_PROVIDER"
    $key = Get-ConfiguredValue "TAVILY_API_KEY"
    if ($provider -ne "tavily") {
        return New-Check "Tavily" "DEGRADED" "provider=$provider; expected provider=tavily." "Set CROP_SEARCH_PROVIDER=tavily. Core diagnosis remains available."
    }
    if (-not $key) {
        return New-Check "Tavily" "DEGRADED" "TAVILY_API_KEY: missing" "Configure TAVILY_API_KEY. Core diagnosis remains available."
    }
    if ($Network -and -not (Test-TavilyNetwork)) {
        return New-Check "Tavily" "DEGRADED" "TAVILY_API_KEY: configured; network request failed." "Check Tavily endpoint/network. Core diagnosis remains available."
    }
    return New-Check "Tavily" "READY" "provider=tavily; TAVILY_API_KEY: configured"
}

function Test-WritableDirectory([string]$Path) {
    try {
        if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Force -Path $Path | Out-Null }
        $probe = Join-Path $Path "competition-write-test-$PID.tmp"
        [IO.File]::WriteAllText($probe, "ok")
        Remove-Item -LiteralPath $probe -Force -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Get-StorageStatus {
    # Match backend/app/config.py: every relative path is relative to backend/.
    $storage = Resolve-BackendPath (Get-ConfiguredValue "CROP_STORAGE_DIR") "runtime"
    $knowledge = Resolve-BackendPath (Get-ConfiguredValue "CROP_KNOWLEDGE_DIR") "..\knowledge\baidu-baike-20260818"
    $writable = Test-WritableDirectory $storage
    $knowledgeReady = Test-Path -LiteralPath (Join-Path $knowledge "manifest.json")
    [pscustomobject]@{
        storage = New-Check "Storage" $(if ($writable) { "READY" } else { "FAILED" }) $storage "Ensure CROP_STORAGE_DIR exists and is writable." (-not $writable)
        knowledge = New-Check "Knowledge" $(if ($knowledgeReady) { "READY" } else { "FAILED" }) $knowledge "Restore knowledge/baidu-baike-20260818 and its manifest." (-not $knowledgeReady)
    }
}

function Get-CompetitionSnapshot([switch]$NetworkTavily) {
    $storage = Get-StorageStatus
    @(
        (Get-BackendStatus),
        (Get-DetectorStatus),
        (Get-QwenStatus),
        (Get-TavilyStatus -Network:$NetworkTavily),
        (Get-FrontendStatus),
        $storage.knowledge,
        $storage.storage
    )
}

function Resolve-OverallState([object[]]$Checks) {
    $core = @("Backend", "Detector", "Qwen3-VL", "Frontend")
    if (@($Checks | Where-Object { $_.Name -in $core -and $_.State -ne "READY" }).Count -gt 0) { return "FAILED" }
    if (@($Checks | Where-Object { $_.Name -in @("Tavily", "Knowledge", "Storage") -and $_.State -ne "READY" }).Count -gt 0) { return "DEGRADED" }
    return "READY"
}

function Write-Checks([object[]]$Checks) {
    Write-Output "Crop Pest Competition System"
    Write-Output ""
    foreach ($check in $Checks) {
        $detail = if ($check.Detail) { "  $($check.Detail)" } else { "" }
        Write-Output ("{0,-12} {1,-11} {2}" -f $check.Name, $check.State, $detail)
    }
    $overall = Resolve-OverallState $Checks
    if ($overall -eq "DEGRADED") { $overallText = "DEGRADED (core diagnosis available; web evidence is degraded)" } else { $overallText = $overall }
    Write-Output ""
    Write-Output "Overall      $overallText"
    $script:LastOverallState = $overall
}

function Read-OwnedProcess([string]$PidFile, [string[]]$Markers, [string[]]$Names) {
    if (-not (Test-Path -LiteralPath $PidFile)) { return $null }
    $saved = 0
    if (-not [int]::TryParse((Get-Content -LiteralPath $PidFile -Raw).Trim(), [ref]$saved)) { return $null }
    $details = Get-CimInstance Win32_Process -Filter "ProcessId = $saved" -ErrorAction SilentlyContinue
    if (-not $details -or $details.Name -notin $Names) { return $null }
    foreach ($marker in $Markers) {
        if ($details.CommandLine -notlike "*$marker*") { return $null }
    }
    return Get-Process -Id $saved -ErrorAction SilentlyContinue
}

function Get-DescendantProcessIds([int]$RootPid) {
    $all = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)
    $pending = [System.Collections.Generic.Queue[int]]::new()
    $pending.Enqueue($RootPid)
    $found = [System.Collections.Generic.List[int]]::new()
    while ($pending.Count -gt 0) {
        $parent = $pending.Dequeue()
        foreach ($child in @($all | Where-Object { [int]$_.ParentProcessId -eq $parent })) {
            $childPid = [int]$child.ProcessId
            if (-not $found.Contains($childPid)) {
                $found.Add($childPid)
                $pending.Enqueue($childPid)
            }
        }
    }
    return @($found)
}

function Stop-OwnedProcess([string]$Label, [string]$PidFile, [string[]]$Markers, [string[]]$Names, [string[]]$OrphanMarkers = @()) {
    $process = Read-OwnedProcess $PidFile $Markers $Names
    if ($process) {
        foreach ($childPid in @(Get-DescendantProcessIds $process.Id | Sort-Object -Descending)) {
            $childDetails = Get-CimInstance Win32_Process -Filter "ProcessId = $childPid" -ErrorAction SilentlyContinue
            if ($childDetails -and $childDetails.Name -in $Names) {
                Stop-Process -Id $childPid -ErrorAction SilentlyContinue
            }
        }
        if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
            Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
        }
        try {
            $current = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
            if ($current) {
                $current.WaitForExit(5000) | Out-Null
                if (-not $current.HasExited) { Stop-Process -Id $current.Id -Force -ErrorAction SilentlyContinue }
            }
        } catch {}
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
        Write-Output "$Label stopped (PID $($process.Id))."
    } else {
        if (Test-Path -LiteralPath $PidFile) { Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue }
        Write-Output "${Label}: no process owned by competition entrypoint."
    }
    if ($OrphanMarkers.Count -gt 0) {
        $orphanCandidates = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
            $details = $_
            $missing = @($OrphanMarkers | Where-Object {
                $marker = [string]$_
                [string]::IsNullOrWhiteSpace($marker) -or $details.CommandLine -notlike "*$marker*"
            })
            $details.Name -in $Names -and $missing.Count -eq 0
        })
        foreach ($orphan in $orphanCandidates) {
            if (-not $process -or [int]$orphan.ProcessId -ne $process.Id) {
                Stop-Process -Id ([int]$orphan.ProcessId) -ErrorAction SilentlyContinue
            }
        }
    }
}

function Wait-Until([scriptblock]$Probe, [int]$Seconds = 60) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        if (& $Probe) { return $true }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Start-Tunnel {
    if ((Get-DetectorStatus).State -eq "READY" -and (Get-QwenStatus).State -eq "READY") {
        Write-Output "Detector and Qwen3-VL are already ready; reusing existing tunnel/services."
        return
    }
    $ssh = Get-SshPath
    if (-not $ssh) { throw "ssh.exe is missing. Install the Windows OpenSSH client." }
    $tunnelScript = Join-Path $script:WorkspaceRoot "inference\open_tunnel.ps1"
    $identity = Get-GpuIdentityPath
    if (-not (Test-Path -LiteralPath $identity)) {
        throw "GPU SSH identity not found at $identity. Set CROP_GPU_SSH_IDENTITY_FILE to the GPU-only key path; do not assume the GitHub key is valid."
    }
    New-Item -ItemType Directory -Force -Path $script:StateDir | Out-Null
    $ps = (Get-Command pwsh.exe, powershell.exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    $arguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $tunnelScript, "-PidFile", $script:TunnelPidFile)
    $hostValue = Get-ConfiguredValue "CROP_GPU_SSH_HOST"
    $portValue = Get-ConfiguredValue "CROP_GPU_SSH_PORT"
    $userValue = Get-ConfiguredValue "CROP_GPU_SSH_USER"
    if ($hostValue) { $arguments += @("-SshHost", $hostValue) }
    if ($portValue) { $arguments += @("-SshPort", $portValue) }
    if ($userValue) { $arguments += @("-SshUser", $userValue) }
    if ((Get-ConfiguredValue "CROP_GPU_SSH_IDENTITY_FILE")) { $arguments += @("-IdentityFile", $identity) }
    Write-Output "Opening the existing detector/VLM SSH tunnel..."
    & $ps @arguments
    if ((Get-DetectorStatus).State -ne "READY" -or (Get-QwenStatus).State -ne "READY") {
        throw "SSH tunnel command completed but detector/Qwen readiness did not pass."
    }
}

function Start-Backend {
    if ((Get-BackendStatus).State -eq "READY") { Write-Output "Backend is already ready; reusing it."; return }
    $python = Get-PythonPath
    if (-not $python) { throw "No Python interpreter found. Run preflight and repair backend/.venv." }
    $listener = Get-NetTCPConnection -State Listen -LocalPort $BackendPort -ErrorAction SilentlyContinue
    if ($listener) { throw "Port $BackendPort is occupied but is not a healthy project backend; refusing to take it over." }
    New-Item -ItemType Directory -Force -Path $script:LogDir | Out-Null
    $stdout = Join-Path $script:LogDir "backend.out.log"
    $stderr = Join-Path $script:LogDir "backend.err.log"
    $args = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort")
    $process = Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $script:BackendRoot -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
    Set-Content -LiteralPath $script:BackendPidFile -Value $process.Id -Encoding ASCII
    if (-not (Wait-Until { (Get-BackendStatus).State -eq "READY" } 60)) {
        Stop-OwnedProcess "Backend" $script:BackendPidFile @("uvicorn", "app.main:app", "--port $BackendPort") @("python.exe", "python")
        throw "Backend did not become ready within 60 seconds. See $stderr"
    }
    Write-Output "Backend ready at http://127.0.0.1:$BackendPort"
}

function Start-Frontend {
    if ((Get-FrontendStatus).State -eq "READY") { Write-Output "Frontend is already ready; reusing it."; return }
    $npm = Get-NpmPath
    if (-not $npm) { throw "npm is missing. Install Node.js >= 22.13.0." }
    if (-not (Test-Path -LiteralPath (Join-Path $script:WebRoot "node_modules"))) { throw "web/node_modules is missing. Run: cd web; npm ci" }
    $listener = Get-NetTCPConnection -State Listen -LocalPort $WebPort -ErrorAction SilentlyContinue
    if ($listener) { throw "Port $WebPort is occupied but the project frontend is not responding; refusing to take it over." }
    New-Item -ItemType Directory -Force -Path $script:LogDir | Out-Null
    Push-Location $script:WebRoot
    try {
        Write-Output "Building the production frontend..."
        & $npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
    } finally { Pop-Location }
    $stdout = Join-Path $script:LogDir "web.out.log"
    $stderr = Join-Path $script:LogDir "web.err.log"
    $args = @("run", "start", "--", "--host", "127.0.0.1", "--port", "$WebPort")
    $process = Start-Process -FilePath $npm -ArgumentList $args -WorkingDirectory $script:WebRoot -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
    Set-Content -LiteralPath $script:WebPidFile -Value $process.Id -Encoding ASCII
    Set-Content -LiteralPath $script:WebPortFile -Value $WebPort -Encoding ASCII
    if (-not (Wait-Until { (Get-FrontendStatus).State -eq "READY" } 60)) {
        Stop-OwnedProcess "Frontend" $script:WebPidFile @("run", "start") @("node.exe", "npm.cmd", "cmd.exe") @("vinext", "--port", "$WebPort")
        throw "Frontend did not become ready within 60 seconds. See $stderr"
    }
    Write-Output "Frontend ready at http://localhost:$WebPort/"
}

function Invoke-Start {
    Set-CompetitionRuntimeEnv
    $preflight = @(Get-PreflightChecks)
    foreach ($check in $preflight) {
        $suffix = if ($check.Fix) { " — $($check.Fix)" } else { "" }
        Write-Output ("{0,-22} {1,-8} {2}{3}" -f $check.Name, $check.State, $check.Detail, $suffix)
    }
    if (@($preflight | Where-Object Blocking).Count -gt 0) { throw "Preflight failed; repair the listed items before starting." }
    if ($Library -or $DryRun) { return }
    Start-Tunnel
    Start-Backend
    Start-Frontend
    Write-Checks @(Get-CompetitionSnapshot)
    Write-Output "Open: http://localhost:$WebPort/"
}

function Invoke-Status([switch]$Network) {
    Write-Checks @(Get-CompetitionSnapshot -NetworkTavily:$Network)
    Write-Output "Open: http://localhost:$WebPort/"
}

function Invoke-Smoke {
    $preflight = @(Get-PreflightChecks)
    Write-Output "Competition smoke check"
    foreach ($check in $preflight) {
        Write-Output ("{0,-22} {1,-8} {2}" -f $check.Name, $check.State, $check.Detail)
    }
    $checks = @(Get-CompetitionSnapshot -NetworkTavily)
    Write-Checks $checks
    $overall = $script:LastOverallState
    if ($overall -eq "FAILED") { throw "Smoke check failed: core diagnosis is not ready." }
    if ($overall -eq "DEGRADED") { Write-Output "Smoke result: READY WITH DEGRADED WEB EVIDENCE" }
    else { Write-Output "Smoke result: READY" }
}

function Invoke-Stop {
    $ownedWebPort = $WebPort
    if (Test-Path -LiteralPath $script:WebPortFile) {
        $parsedPort = 0
        if ([int]::TryParse((Get-Content -LiteralPath $script:WebPortFile -Raw).Trim(), [ref]$parsedPort) -and $parsedPort -gt 0) { $ownedWebPort = $parsedPort }
    }
    Stop-OwnedProcess "Frontend" $script:WebPidFile @("run", "start") @("node.exe", "npm.cmd", "cmd.exe") @("vinext", "--port", "$ownedWebPort")
    Remove-Item -LiteralPath $script:WebPortFile -Force -ErrorAction SilentlyContinue
    Stop-OwnedProcess "Backend" $script:BackendPidFile @("uvicorn", "app.main:app") @("python.exe", "python")
    Stop-OwnedProcess "SSH tunnel" $script:TunnelPidFile @("ssh.exe") @("ssh.exe")
    Write-Output "Remote detector and Qwen3-VL services were not stopped."
}

if (-not $Library) {
    switch ($Action) {
        "start" { Invoke-Start }
        "status" { Invoke-Status -Network:$CheckTavilyNetwork }
        "smoke" { Invoke-Smoke }
        "stop" { Invoke-Stop }
    }
}
