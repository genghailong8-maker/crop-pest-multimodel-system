#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv-vision}"
DATA_YAML="${DATA_YAML:-$PROJECT_ROOT/data/official/dataset-training.yaml}"
MODE="${1:-smoke}"
export YOLO_CONFIG_DIR="${YOLO_CONFIG_DIR:-$PROJECT_ROOT/.ultralytics}"
mkdir -p "$YOLO_CONFIG_DIR"

# Start the private monitoring endpoint when available. A training run must not
# fail merely because monitoring could not be started.
if [[ -x "$SCRIPT_DIR/run_monitor.sh" ]]; then
  "$SCRIPT_DIR/run_monitor.sh" start >/dev/null 2>&1 || true
fi

if [[ -n "${TRAIN_PYTHON:-}" ]]; then
  TRAIN_PYTHON="$TRAIN_PYTHON"
elif [[ -x /root/miniconda3/bin/python ]]; then
  TRAIN_PYTHON=/root/miniconda3/bin/python
else
  TRAIN_PYTHON="$VENV_DIR/bin/python"
fi

case "$MODE" in
  smoke)
    EPOCHS="${EPOCHS:-5}"
    RUN_NAME="${RUN_NAME:-official-smoke}"
    ;;
  full)
    EPOCHS="${EPOCHS:-120}"
    RUN_NAME="${RUN_NAME:-official-baseline}"
    ;;
  *)
    echo "Usage: $0 [smoke|full]"
    exit 2
    ;;
esac

"$TRAIN_PYTHON" "$PROJECT_ROOT/training/verify_environment.py"
EXTRA_ARGS=()
if [[ -n "${PATIENCE:-}" ]]; then EXTRA_ARGS+=(--patience "$PATIENCE"); fi
if [[ -n "${OPTIMIZER:-}" ]]; then EXTRA_ARGS+=(--optimizer "$OPTIMIZER"); fi
if [[ -n "${LR0:-}" ]]; then EXTRA_ARGS+=(--lr0 "$LR0"); fi
if [[ -n "${LRF:-}" ]]; then EXTRA_ARGS+=(--lrf "$LRF"); fi
if [[ -n "${FREEZE:-}" ]]; then EXTRA_ARGS+=(--freeze "$FREEZE"); fi
"$TRAIN_PYTHON" "$PROJECT_ROOT/training/train_detector.py" \
  --data "$DATA_YAML" \
  --model "${MODEL:-yolo26n.pt}" \
  --epochs "$EPOCHS" \
  --image-size "${IMAGE_SIZE:-640}" \
  --batch "${BATCH:-8}" \
  --device "${DEVICE:-0}" \
  --workers "${WORKERS:-8}" \
  --project "${RUNS_DIR:-$PROJECT_ROOT/runs/detect}" \
  --name "$RUN_NAME" \
  ${CACHE:+--cache} \
  ${EXPORT_ONNX:+--export-onnx} \
  "${EXTRA_ARGS[@]}"
