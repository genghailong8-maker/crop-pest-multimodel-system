#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${TRAIN_PYTHON:-/root/miniconda3/bin/python}"
RUN_NAME="${RUN_NAME:-weak-crop-cls-v1-e30-b128}"
PID_FILE="$PROJECT_ROOT/artifacts/server/${RUN_NAME}.pid"

mkdir -p "$PROJECT_ROOT/artifacts/server"
if [[ -x "$SCRIPT_DIR/run_monitor.sh" ]]; then
  "$SCRIPT_DIR/run_monitor.sh" start >/dev/null 2>&1 || true
fi

echo "$$" > "$PID_FILE"
cleanup() {
  rm -f -- "$PID_FILE"
}
trap cleanup EXIT INT TERM

"$PYTHON" "$PROJECT_ROOT/training/train_crop_classifier.py" \
  --data "${DATA_ROOT:-$PROJECT_ROOT/data/experiments/weak-crop-cls-v1}" \
  --pretrained-detector "${PRETRAINED_DETECTOR:-$PROJECT_ROOT/runs/detect/official-plus-public-weak-v1-e120-b64/weights/best.pt}" \
  --epochs "${EPOCHS:-30}" \
  --image-size "${IMAGE_SIZE:-224}" \
  --batch "${BATCH:-128}" \
  --device "${DEVICE:-0}" \
  --workers "${WORKERS:-8}" \
  --patience "${PATIENCE:-8}" \
  --project "${RUNS_DIR:-$PROJECT_ROOT/runs/detect}" \
  --name "$RUN_NAME"
