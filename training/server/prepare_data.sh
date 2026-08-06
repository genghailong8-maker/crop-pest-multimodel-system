#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv-vision}"
DATA_ROOT="${DATA_ROOT:-$PROJECT_ROOT/data/official}"

if [[ -n "${TRAIN_PYTHON:-}" ]]; then
  TRAIN_PYTHON="$TRAIN_PYTHON"
elif [[ -x /root/miniconda3/bin/python ]]; then
  TRAIN_PYTHON=/root/miniconda3/bin/python
else
  TRAIN_PYTHON="$VENV_DIR/bin/python"
fi

if [[ -z "${OFFICIAL_DATASET_ROOT:-}" ]]; then
  echo "Set OFFICIAL_DATASET_ROOT to the official package directory on the server."
  exit 2
fi

"$TRAIN_PYTHON" "$PROJECT_ROOT/tools/create_server_data_view.py" \
  "$OFFICIAL_DATASET_ROOT" "$DATA_ROOT"
"$TRAIN_PYTHON" "$PROJECT_ROOT/tools/prepare_official_split.py" \
  "$DATA_ROOT" \
  --class-map "$OFFICIAL_DATASET_ROOT/文档/类别中英文对照.csv" \
  --val-fraction 0.2 \
  --seed 20260729
