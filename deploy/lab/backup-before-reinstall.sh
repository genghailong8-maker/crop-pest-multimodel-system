#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-check}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="/data/ghl/migration-backup/$STAMP"

[[ "$(findmnt -n -o TARGET --target /data)" == "/data" ]] || {
  echo "ERROR: /data 不是独立挂载点" >&2
  exit 1
}
echo "Backup destination: $DEST"
echo "Sources: /root /home /etc, MySQL dump, Docker metadata/data"
if [[ "$MODE" != "--apply" ]]; then
  echo "CHECK ONLY: 未复制数据。使用 --apply 执行在线第一轮备份。"
  exit 0
fi

install -d -m 0700 "$DEST/files" "$DEST/mysql" "$DEST/docker" "$DEST/inventory"
for source in /root /home /etc; do
  [[ -e "$source" ]] && rsync -aHAX --numeric-ids "$source" "$DEST/files/"
done
if [[ -d /var/lib/mysql ]]; then
  install -d "$DEST/files/var/lib"
  rsync -aHAX --numeric-ids /var/lib/mysql "$DEST/files/var/lib/"
fi
if [[ -d /var/spool/cron ]]; then
  install -d "$DEST/files/var/spool"
  rsync -aHAX --numeric-ids /var/spool/cron "$DEST/files/var/spool/"
fi

if command -v mysqldump >/dev/null; then
  mysqldump --all-databases --single-transaction --routines --events \
    >"$DEST/mysql/all-databases.sql"
fi
docker info >"$DEST/inventory/docker-info.txt" 2>&1 || true
docker ps -a --no-trunc >"$DEST/inventory/docker-containers.txt" 2>&1 || true
DOCKER_ROOT="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
if [[ -n "$DOCKER_ROOT" && "$(readlink -f "$DOCKER_ROOT")" != /data/* ]]; then
  rsync -aHAX --numeric-ids "$DOCKER_ROOT/" "$DEST/docker/"
fi
findmnt -o TARGET,SOURCE,FSTYPE,UUID,OPTIONS >"$DEST/inventory/mounts.txt"
lsblk -o NAME,SIZE,FSTYPE,UUID,MOUNTPOINTS >"$DEST/inventory/block-devices.txt"
du -sh "$DEST" >"$DEST/inventory/backup-size.txt"
find "$DEST" -type f ! -path "$DEST/inventory/sha256.txt" -print0 | sort -z | xargs -0 sha256sum >"$DEST/inventory/sha256.txt"
echo "Backup complete: $DEST"
echo "在停服务后的最终增量备份中再次使用相同目标执行 rsync，并重新生成校验清单；重装前必须人工抽样恢复。"
