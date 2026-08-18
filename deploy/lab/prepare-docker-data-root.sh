#!/usr/bin/env bash
set -euo pipefail

TARGET=/data/ghl/docker
MODE="${1:-check}"
CURRENT="$(docker info --format '{{.DockerRootDir}}')"

[[ "$(findmnt -n -o TARGET --target /data)" == "/data" ]] || {
  echo "ERROR: /data 不是独立挂载点" >&2
  exit 1
}
case "$(readlink -f "$TARGET")" in /data/ghl/docker) ;; *) exit 1 ;; esac

echo "Current Docker root: $CURRENT"
echo "Requested Docker root: $TARGET"
if [[ "$(readlink -f "$CURRENT")" == "$TARGET" ]]; then
  echo "Docker 已使用目标目录。"
  exit 0
fi

RUNNING="$(docker ps -q)"
if [[ -n "$RUNNING" ]]; then
  echo "ERROR: 当前存在运行中的容器，拒绝迁移 Docker 数据目录：" >&2
  docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}'
  exit 2
fi

if [[ "$MODE" != "--apply" ]]; then
  echo "CHECK ONLY: 未修改配置。确认无运行容器后使用 --apply。原 Docker 数据不会被删除。"
  exit 0
fi

install -d -m 0710 "$TARGET" /data/ghl/runtime
systemctl stop docker
rsync -aHAX --numeric-ids "$CURRENT/" "$TARGET/"
install -d -m 0755 /etc/docker
[[ ! -f /etc/docker/daemon.json ]] || cp -a /etc/docker/daemon.json "/data/ghl/migration-backup/daemon.json.$(date -u +%Y%m%dT%H%M%SZ)"
python3 - "$TARGET" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path("/etc/docker/daemon.json")
try:
    payload = json.loads(path.read_text()) if path.exists() else {}
except json.JSONDecodeError as exc:
    raise SystemExit(f"Invalid /etc/docker/daemon.json: {exc}")
payload["data-root"] = sys.argv[1]
temporary = path.with_suffix(".tmp")
temporary.write_text(json.dumps(payload, indent=2) + "\n")
temporary.replace(path)
PY
systemctl start docker
[[ "$(readlink -f "$(docker info --format '{{.DockerRootDir}}')")" == "$TARGET" ]] || {
  echo "ERROR: Docker 重启后未使用目标目录" >&2
  exit 3
}
echo "Docker data-root 已切换。旧目录 $CURRENT 保留，未删除。"
