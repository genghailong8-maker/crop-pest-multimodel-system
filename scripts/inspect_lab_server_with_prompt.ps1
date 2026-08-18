$credential = Get-Credential -UserName "root" -Message "SSH password for lab server 192.168.15.133 (memory only)"
if ($null -eq $credential) {
    throw "SSH login was cancelled"
}
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($credential.Password)
try {
    $env:GHL_SSH_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    & "$PSScriptRoot\..\backend\.venv\Scripts\python.exe" "$PSScriptRoot\inspect_lab_server.py"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Remove-Item Env:GHL_SSH_PASSWORD -ErrorAction SilentlyContinue
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
