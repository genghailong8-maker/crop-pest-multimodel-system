#!/usr/bin/env bash
set -euo pipefail

# Run the reproducible evaluation/export/benchmark chain after a background
# training run finishes.  This script intentionally does not replace the live
# inference model; deployment is decided after the frozen validation metrics
# are compared with the baseline.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${TRAIN_PYTHON:-/root/miniconda3/bin/python}"
RUN_NAME="${RUN_NAME:-official-plus-pest65-aphids-v1-e120-b64}"
RUN_PID_FILE="${RUN_PID_FILE:-$PROJECT_ROOT/artifacts/server/${RUN_NAME}.pid}"
DATA_YAML="${DATA_YAML:-$PROJECT_ROOT/data/experiments/official-plus-pest65-aphids-v1/dataset-training.yaml}"
WEIGHTS="$PROJECT_ROOT/runs/detect/$RUN_NAME/weights/best.pt"
ONNX="$PROJECT_ROOT/runs/detect/$RUN_NAME/weights/best.onnx"
EVALUATION_DIR="$PROJECT_ROOT/artifacts/server/evaluations/$RUN_NAME"
BENCHMARK_DIR="$PROJECT_ROOT/artifacts/server/benchmarks/$RUN_NAME"
POSTPROCESS_LOG="${POSTPROCESS_LOG:-$PROJECT_ROOT/artifacts/server/${RUN_NAME}.postprocess.log}"

mkdir -p "$EVALUATION_DIR" "$BENCHMARK_DIR"
exec > >(tee -a "$POSTPROCESS_LOG") 2>&1

echo "[postprocess] waiting for training PID file: $RUN_PID_FILE"
while [[ -f "$RUN_PID_FILE" ]] && kill -0 "$(cat "$RUN_PID_FILE")" 2>/dev/null; do
  sleep "${POLL_SECONDS:-30}"
done

if [[ ! -f "$WEIGHTS" ]]; then
  echo "[postprocess] training ended without best weights: $WEIGHTS" >&2
  exit 1
fi

echo "[postprocess] evaluating PT weights on the frozen official validation split"
"$PYTHON" "$PROJECT_ROOT/training/evaluate_detector.py" "$WEIGHTS" \
  --data "$DATA_YAML" --device "${DEVICE:-0}" --image-size "${IMAGE_SIZE:-640}" \
  --batch "${BATCH:-64}" --workers "${WORKERS:-8}" \
  --project "$EVALUATION_DIR" --name pt --output "$EVALUATION_DIR/pt-metrics.json"

if [[ ! -f "$ONNX" ]]; then
  echo "[postprocess] exporting ONNX"
  "$PYTHON" "$PROJECT_ROOT/training/export_onnx.py" "$WEIGHTS" \
    --device "${DEVICE:-0}" --image-size "${IMAGE_SIZE:-640}" --opset 19 \
    --metadata "$EVALUATION_DIR/onnx-export.json"
else
  echo "[postprocess] ONNX already exists: $ONNX"
fi

echo "[postprocess] evaluating ONNX weights on the frozen official validation split"
"$PYTHON" "$PROJECT_ROOT/training/evaluate_detector.py" "$ONNX" \
  --data "$DATA_YAML" --device "${DEVICE:-0}" --image-size "${IMAGE_SIZE:-640}" \
  --batch "${BATCH:-64}" --workers "${WORKERS:-8}" \
  --project "$EVALUATION_DIR" --name onnx --output "$EVALUATION_DIR/onnx-metrics.json"

IMAGES_FILE="$PROJECT_ROOT/data/official/splits/val.txt"
echo "[postprocess] benchmarking PT runtime"
"$PYTHON" "$PROJECT_ROOT/inference/benchmark_runtime.py" "$WEIGHTS" \
  --images-file "$IMAGES_FILE" --device "${DEVICE:-0}" --image-size "${IMAGE_SIZE:-640}" \
  --batch-sizes "${BENCHMARK_BATCH_SIZES:-1,8,32,64}" --warmup "${BENCHMARK_WARMUP:-10}" \
  --iterations "${BENCHMARK_ITERATIONS:-30}" --output "$BENCHMARK_DIR/pt.json"

echo "[postprocess] benchmarking ONNX runtime"
"$PYTHON" "$PROJECT_ROOT/inference/benchmark_runtime.py" "$ONNX" \
  --images-file "$IMAGES_FILE" --device "${DEVICE:-0}" --image-size "${IMAGE_SIZE:-640}" \
  --batch-sizes "${BENCHMARK_BATCH_SIZES:-1,8,32,64}" --warmup "${BENCHMARK_WARMUP:-10}" \
  --iterations "${BENCHMARK_ITERATIONS:-30}" --output "$BENCHMARK_DIR/onnx.json"

echo "[postprocess] completed; live inference deployment remains pending metric comparison"
