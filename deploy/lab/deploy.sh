#!/usr/bin/env bash
set -euo pipefail

ROOT=/data/ghl
APP="$ROOT/app"
ENV_FILE="$APP/deploy/lab/.env"

for required in \
  "$ROOT/models/detector/main.pt" \
  "$ROOT/models/experts/class10.pt" \
  "$ROOT/models/experts/crop-classifier.pt" \
  "$ROOT/models/qwen3-vl/Qwen3VL-8B-Instruct-Q4_K_M.gguf" \
  "$ROOT/models/qwen3-vl/mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf" \
  "$ROOT/cache/wheels/backend" \
  "$ROOT/cache/wheels/inference" \
  "$ROOT/cache/npm" \
  "$ENV_FILE"; do
  [[ -e "$required" ]] || { echo "ERROR: 缺少 $required" >&2; exit 1; }
done

bash "$APP/deploy/lab/compatibility-check.sh"
cd "$APP"
COMPOSE=(docker compose -f deploy/lab/docker-compose.yml -f deploy/lab/docker-compose.offline.yml --env-file "$ENV_FILE")
"${COMPOSE[@]}" build
"${COMPOSE[@]}" up -d
"${COMPOSE[@]}" ps
echo "Deployment started. Run deploy/lab/verify.sh after model loading completes."
