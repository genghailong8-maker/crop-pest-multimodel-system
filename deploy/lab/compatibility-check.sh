#!/usr/bin/env bash
set -euo pipefail

ROOT=/data/ghl
COMPOSE_FILE="$ROOT/app/deploy/lab/docker-compose.yml"

echo "== Host =="
uname -a
cat /etc/os-release
findmnt /data
df -h / /data
grep -m1 -o 'avx2' /proc/cpuinfo >/dev/null || { echo "ERROR: CPU 缺少 AVX2" >&2; exit 1; }

[[ "$(findmnt -n -o TARGET --target /data)" == "/data" ]] || {
  echo "ERROR: /data 不是独立挂载点" >&2
  exit 1
}
[[ -f "$COMPOSE_FILE" ]] || { echo "ERROR: 部署代码尚未上传到 $ROOT/app" >&2; exit 1; }
command -v docker >/dev/null || { echo "ERROR: Docker 未安装" >&2; exit 1; }
docker version

DOCKER_ROOT="$(docker info --format '{{.DockerRootDir}}')"
echo "Docker root: $DOCKER_ROOT"
case "$(readlink -f "$DOCKER_ROOT")" in
  "$ROOT"/docker|"$ROOT"/docker/*) ;;
  *)
    echo "ERROR: Docker 数据仍位于 $DOCKER_ROOT。先运行 prepare-docker-data-root.sh；未拉取任何镜像。" >&2
    exit 2
    ;;
esac

docker run --rm --pull never public.ecr.aws/docker/library/python:3.12-slim python --version
docker run --rm --pull never public.ecr.aws/docker/library/node:22-bookworm-slim node --version
docker compose \
  -f "$COMPOSE_FILE" \
  -f "$ROOT/app/deploy/lab/docker-compose.offline.yml" \
  --env-file "$ROOT/app/deploy/lab/.env" config >/dev/null
echo "PASS: Python 3.12、Node 22、Compose 与 /data/ghl 数据根兼容门通过。"
