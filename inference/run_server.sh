#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ -x /root/miniconda3/bin/python ]]; then
  DEFAULT_PYTHON=/root/miniconda3/bin/python
else
  DEFAULT_PYTHON=python
fi
PYTHON="${PYTHON:-$DEFAULT_PYTHON}"
HOST="${CROP_INFERENCE_HOST:-127.0.0.1}"
PORT="${CROP_INFERENCE_PORT:-8870}"
RUNTIME_DIR="$PROJECT_ROOT/artifacts/server/inference"
PID_FILE="$RUNTIME_DIR/server.pid"
LOG_FILE="$RUNTIME_DIR/server.log"

mkdir -p "$RUNTIME_DIR"

is_running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

case "${1:-start}" in
  start)
    if is_running; then
      echo "Inference server is already running (PID $(cat "$PID_FILE"))."
      exit 0
    fi
    cd "$PROJECT_ROOT"
    nohup "$PYTHON" -m uvicorn inference.service:app --host "$HOST" --port "$PORT" \
      >"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
    for _ in $(seq 1 60); do
      if curl --fail --silent "http://127.0.0.1:${PORT}/health" >/dev/null; then
        echo "Inference server is ready on ${HOST}:${PORT} (PID $(cat "$PID_FILE"))."
        exit 0
      fi
      if ! is_running; then
        tail -n 80 "$LOG_FILE"
        exit 1
      fi
      sleep 1
    done
    echo "Inference server did not become ready within 60 seconds."
    tail -n 80 "$LOG_FILE"
    exit 1
    ;;
  stop)
    if is_running; then
      kill "$(cat "$PID_FILE")"
      rm -f "$PID_FILE"
      echo "Inference server stopped."
    else
      echo "Inference server is not running."
    fi
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    if is_running; then
      echo "Inference server is running (PID $(cat "$PID_FILE"))."
      curl --fail --silent "http://127.0.0.1:${PORT}/health"
      echo
    else
      echo "Inference server is not running."
      exit 1
    fi
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}" >&2
    exit 2
    ;;
esac
