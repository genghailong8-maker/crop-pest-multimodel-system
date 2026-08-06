#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${MONITOR_PYTHON:-/root/miniconda3/bin/python}"
HOST="${MONITOR_HOST:-127.0.0.1}"
PORT="${MONITOR_PORT:-8765}"
PID_FILE="$PROJECT_ROOT/artifacts/server/training-monitor.pid"
LOG_FILE="$PROJECT_ROOT/artifacts/server/training-monitor.log"

mkdir -p "$PROJECT_ROOT/artifacts/server"

is_running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

case "${1:-start}" in
  start)
    if is_running; then
      echo "Training monitor is already running (PID $(cat "$PID_FILE"))."
      exit 0
    fi
    nohup "$PYTHON" "$PROJECT_ROOT/training/monitor_server.py" \
      --project-root "$PROJECT_ROOT" --host "$HOST" --port "$PORT" \
      > "$LOG_FILE" 2>&1 < /dev/null &
    echo $! > "$PID_FILE"
    echo "Training monitor started (PID $(cat "$PID_FILE"), ${HOST}:${PORT})."
    ;;
  stop)
    if is_running; then
      kill "$(cat "$PID_FILE")"
      echo "Training monitor stopped."
    else
      echo "Training monitor is not running."
    fi
    ;;
  status)
    if is_running; then
      echo "Training monitor is running (PID $(cat "$PID_FILE"))."
    else
      echo "Training monitor is not running."
      exit 1
    fi
    ;;
  *)
    echo "Usage: $0 [start|stop|status]"
    exit 2
    ;;
esac
