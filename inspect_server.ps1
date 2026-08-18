$ErrorActionPreference = 'Continue'

$inspectionOutput = Join-Path $PSScriptRoot 'server_inspection_output.txt'

$remoteCommand = @'
echo "=== identity ==="
whoami
hostname
hostname -I 2>/dev/null

echo "=== system ==="
cat /etc/os-release 2>/dev/null
uname -a
ldd --version 2>/dev/null | head -1

echo "=== cpu ==="
if command -v lscpu >/dev/null 2>&1; then lscpu; else nproc; fi

echo "=== memory ==="
free -h

echo "=== disk ==="
df -hT

echo "=== gpu ==="
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi
else
    echo "nvidia-smi unavailable"
fi

echo "=== software ==="
for c in python3 python conda docker git node npm; do
    printf "%-10s" "$c"
    command -v "$c" || echo "unavailable"
done
python3 --version 2>/dev/null
python --version 2>/dev/null
docker --version 2>/dev/null
git --version 2>/dev/null

echo "=== listening ports ==="
ss -lntp 2>/dev/null | head -50

echo "=== failed services ==="
systemctl --failed --no-pager 2>/dev/null || true
'@

Write-Host '正在连接 192.168.15.133，请在提示后输入 SSH 密码。' -ForegroundColor Cyan
Write-Host '输入密码时屏幕不会显示字符，这是正常现象。' -ForegroundColor Yellow

ssh ghl $remoteCommand 2>&1 | Tee-Object -FilePath $inspectionOutput

Write-Host "`n检查输出已保存到：$inspectionOutput" -ForegroundColor Green
Read-Host '完成后按 Enter 关闭窗口'
