#!/usr/bin/env bash
set -euo pipefail

ROOT="${CROP_GPU_ROOT:-/root/autodl-tmp/ghl}"
APP="$ROOT/app"
PYTHON="${CROP_GPU_PYTHON:-python3}"

install -d -m 0750 "$APP" "$ROOT/storage/uploads" "$ROOT/storage/reports" "$ROOT/runtime/logs"
[[ -f "$APP/backend/pyproject.toml" ]] || {
  echo "ERROR: 请先把项目代码上传到 $APP" >&2
  exit 1
}
chmod 0750 "$APP/deploy/gpu/run_backend.sh"
"$PYTHON" -m venv --system-site-packages "$ROOT/venv"
"$ROOT/venv/bin/python" -m pip install --no-build-isolation --no-deps "$APP/backend"
echo "GPU 后端环境已创建并复用系统依赖；未启动 detector 或后端。"
