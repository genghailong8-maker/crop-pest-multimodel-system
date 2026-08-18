#!/usr/bin/env bash
set -euo pipefail

ROOT=/data/ghl
if [[ "$(findmnt -n -o TARGET --target /data)" != "/data" ]]; then
  echo "ERROR: /data 不是独立挂载点，拒绝创建部署目录。" >&2
  exit 1
fi

install -d -m 0750 \
  "$ROOT/app" \
  "$ROOT/storage/uploads" \
  "$ROOT/storage/reports" \
  "$ROOT/storage/backups" \
  "$ROOT/models/detector" \
  "$ROOT/models/experts" \
  "$ROOT/models/qwen3-vl" \
  "$ROOT/runtime/control" \
  "$ROOT/runtime/logs" \
  "$ROOT/cache/huggingface" \
  "$ROOT/cache/pip" \
  "$ROOT/cache/npm" \
  "$ROOT/docker" \
  "$ROOT/migration-backup"

echo "Created/verified $ROOT layout. No existing files were removed."
