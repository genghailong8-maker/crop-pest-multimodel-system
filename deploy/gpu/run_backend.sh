#!/usr/bin/env bash
set -euo pipefail

ROOT="${CROP_GPU_ROOT:-/root/autodl-tmp/ghl}"
APP="$ROOT/app"
ENV_FILE="$APP/deploy/gpu/.env"
PID_FILE="$ROOT/runtime/backend.pid"
LOG_FILE="$ROOT/runtime/logs/backend.log"

[[ -f "$ENV_FILE" ]] || { echo "ERROR: 缺少 $ENV_FILE" >&2; exit 1; }
set -a
source "$ENV_FILE"
set +a

is_running() { [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; }
case "${1:-start}" in
  start)
    is_running && { echo "Backend already running"; exit 0; }
    cd "$APP/backend"
    nohup "$ROOT/venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
    ;;
  stop)
    is_running && kill "$(cat "$PID_FILE")"
    rm -f "$PID_FILE"
    ;;
  status)
    is_running || { echo "Backend is not running"; exit 1; }
    curl --fail --silent http://127.0.0.1:8000/health
    echo
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  *) echo "Usage: $0 {start|stop|restart|status}" >&2; exit 2 ;;
esac
