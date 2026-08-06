#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv-vision}"

if [[ -n "${TRAIN_PYTHON:-}" ]]; then
  TRAIN_PYTHON="$TRAIN_PYTHON"
elif [[ -x /root/miniconda3/bin/python ]]; then
  TRAIN_PYTHON=/root/miniconda3/bin/python
elif [[ -x "$VENV_DIR/bin/python" ]]; then
  TRAIN_PYTHON="$VENV_DIR/bin/python"
else
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  TRAIN_PYTHON="$VENV_DIR/bin/python"
fi

"$TRAIN_PYTHON" -m pip install --upgrade pip wheel

if ! "$TRAIN_PYTHON" -c 'import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)'; then
  if [[ -z "${PYTORCH_INDEX_URL:-}" ]]; then
    echo "CUDA-enabled PyTorch is unavailable. Set PYTORCH_INDEX_URL to the matching official wheel index."
    exit 2
  fi
  "$TRAIN_PYTHON" -m pip install torch torchvision --index-url "$PYTORCH_INDEX_URL"
fi

"$TRAIN_PYTHON" -m pip install -r "$PROJECT_ROOT/training/requirements-vision.txt"
"$TRAIN_PYTHON" "$PROJECT_ROOT/training/verify_environment.py" \
  --output "$PROJECT_ROOT/artifacts/server/environment.json"
