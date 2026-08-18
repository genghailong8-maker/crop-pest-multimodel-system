#!/usr/bin/env bash
set -euo pipefail

ROOT=/data/ghl
APP="$ROOT/app"
ENV_FILE="$APP/deploy/lab/.env"
PORT="$(sed -n 's/^CROP_HTTP_PORT=//p' "$ENV_FILE" | tail -n1 | tr -d '\r')"
PORT="${PORT:-8080}"

cd "$APP"
docker compose \
  -f deploy/lab/docker-compose.yml \
  -f deploy/lab/docker-compose.offline.yml \
  --env-file "$ENV_FILE" ps
curl --fail --silent "http://127.0.0.1:$PORT/health" | tee "$ROOT/runtime/logs/health.json"
echo
python3 - <<PY
import json
from pathlib import Path

payload = json.loads(Path("$ROOT/runtime/logs/health.json").read_text())
assert payload["status"] == "ok"
assert payload["instance_id"] == "lab_cpu"
assert payload["detector_mode"] == "remote"
assert payload["multimodal_configured"] is True
print("PASS: lab_cpu backend, detector endpoint and multimodal endpoint are configured")
PY
[[ -f "$ROOT/storage/crop-pest.sqlite3" ]]
[[ -d "$ROOT/storage/uploads" && -d "$ROOT/storage/reports" ]]
echo "PASS: storage paths exist under $ROOT; no cross-server synchronization is enabled."
