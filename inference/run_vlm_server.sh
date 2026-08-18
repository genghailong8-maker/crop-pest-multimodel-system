#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${CROP_VLM_ROOT:-/root/autodl-tmp/crop-pest-vlm}"
BASE_PYTHON="${CROP_VLM_BASE_PYTHON:-/root/miniconda3/bin/python}"
VENV_DIR="${CROP_VLM_VENV:-${ROOT_DIR}/venv}"
HF_HOME="${CROP_VLM_HF_HOME:-${ROOT_DIR}/hf-cache}"
HF_ENDPOINT="${CROP_VLM_HF_ENDPOINT:-https://hf-mirror.com}"
MODEL="${CROP_VLM_MODEL_SOURCE:-Qwen/Qwen3-VL-8B-Instruct}"
MODEL_REVISION="${CROP_VLM_MODEL_REVISION:-0c351dd01ed87e9c1b53cbc748cba10e6187ff3b}"
MODEL_DIR="${CROP_VLM_MODEL_DIR:-${ROOT_DIR}/model}"
SERVED_NAME="${CROP_VLM_SERVED_NAME:-crop-pest-vlm}"
HOST="${CROP_VLM_HOST:-127.0.0.1}"
PORT="${CROP_VLM_PORT:-8890}"
MAX_MODEL_LEN="${CROP_VLM_MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTILIZATION="${CROP_VLM_GPU_MEMORY_UTILIZATION:-0.65}"
PID_FILE="${ROOT_DIR}/server.pid"
LOG_FILE="${ROOT_DIR}/server.log"

mkdir -p "${ROOT_DIR}" "${HF_HOME}"

install_runtime() {
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    "${BASE_PYTHON}" -m venv "${VENV_DIR}"
  fi
  "${VENV_DIR}/bin/python" -m pip install --no-cache-dir --upgrade pip
  "${VENV_DIR}/bin/python" -m pip install --no-cache-dir "vllm==0.26.0"
  "${VENV_DIR}/bin/python" -m pip freeze > "${ROOT_DIR}/requirements.lock"
}

download_model() {
  mkdir -p "${MODEL_DIR}"
  env \
    HF_HOME="${HF_HOME}" \
    HF_ENDPOINT="${HF_ENDPOINT}" \
    HF_HUB_DISABLE_XET=1 \
    CROP_VLM_MODEL_SOURCE="${MODEL}" \
    CROP_VLM_MODEL_REVISION="${MODEL_REVISION}" \
    CROP_VLM_MODEL_DIR="${MODEL_DIR}" \
    "${VENV_DIR}/bin/python" -c 'import os; from huggingface_hub import snapshot_download; print(snapshot_download(repo_id=os.environ["CROP_VLM_MODEL_SOURCE"], revision=os.environ["CROP_VLM_MODEL_REVISION"], local_dir=os.environ["CROP_VLM_MODEL_DIR"], max_workers=4))'
}

is_running() {
  [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null
}

start_server() {
  if is_running; then
    echo "VLM server already running with PID $(cat "${PID_FILE}")"
    return 0
  fi
  if [[ ! -x "${VENV_DIR}/bin/vllm" ]]; then
    echo "vLLM runtime is not installed. Run: $0 install" >&2
    return 1
  fi
  if [[ ! -f "${MODEL_DIR}/config.json" ]]; then
    echo "Pinned model snapshot is not downloaded. Run: $0 download" >&2
    return 1
  fi
  rm -f "${PID_FILE}"
  nohup env HF_HOME="${HF_HOME}" HF_ENDPOINT="${HF_ENDPOINT}" HF_HUB_DISABLE_XET=1 VLLM_USE_FLASHINFER_SAMPLER=0 \
    "${VENV_DIR}/bin/vllm" serve "${MODEL_DIR}" \
    --served-model-name "${SERVED_NAME}" \
    --host "${HOST}" \
    --port "${PORT}" \
    --max-model-len "${MAX_MODEL_LEN}" \
    --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
    --limit-mm-per-prompt '{"image":1}' \
    --max-num-seqs 2 \
    >"${LOG_FILE}" 2>&1 &
  echo $! > "${PID_FILE}"
  echo "Started VLM server with PID $(cat "${PID_FILE}"); log: ${LOG_FILE}"
}

stop_server() {
  if ! is_running; then
    rm -f "${PID_FILE}"
    echo "VLM server is not running"
    return 0
  fi
  pid="$(cat "${PID_FILE}")"
  kill "${pid}"
  for _ in {1..30}; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      rm -f "${PID_FILE}"
      echo "Stopped VLM server"
      return 0
    fi
    sleep 1
  done
  echo "VLM server did not stop within 30 seconds" >&2
  return 1
}

status_server() {
  if is_running; then
    echo "running pid=$(cat "${PID_FILE}") model=${MODEL} revision=${MODEL_REVISION} local_dir=${MODEL_DIR} served_name=${SERVED_NAME} endpoint=http://${HOST}:${PORT}"
    curl --fail --silent --show-error "http://${HOST}:${PORT}/v1/models" || true
    echo
    return 0
  fi
  echo "stopped"
  return 1
}

case "${1:-status}" in
  install) install_runtime ;;
  download) download_model ;;
  start) start_server ;;
  stop) stop_server ;;
  restart) stop_server; start_server ;;
  status) status_server ;;
  log) tail -n "${2:-80}" "${LOG_FILE}" ;;
  *) echo "Usage: $0 {install|download|start|stop|restart|status|log [lines]}" >&2; exit 2 ;;
esac
