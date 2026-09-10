#!/usr/bin/env bash
set -u

cd /root/autodl-tmp/crop-pest-system

PYTHON=/root/miniconda3/bin/python
TRAIN_DATA=data/experiments/phase9-independent-v1/dataset-independent-train-only.yaml
EVAL_DATA=data/experiments/phase9-independent-v1/dataset-independent-frozen-eval.yaml
STATUS_DIR=artifacts/server/phase9-fulltrain-status-20260813
mkdir -p "$STATUS_DIR"

timestamp() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

status() {
  printf '%s\t%s\t%s\n' "$(timestamp)" "$1" "$2" | tee -a "$STATUS_DIR/status.tsv"
}

wait_for_tag() {
  local tag="$1"
  status "$tag" "waiting-for-current-training"
  while pgrep -af "^/root/miniconda3/bin/python training/train_phase9_finalist.py.*--model ${tag}\.pt" >/dev/null 2>&1; do
    sleep 20
  done
  status "$tag" "current-training-process-ended"
}

find_training_record() {
  local tag="$1"
  find "runs/phase9-fulltrain-b64-${tag}" -name phase9-final-training.json -type f -print 2>/dev/null | sort | tail -n 1
}

weights_from_record() {
  "$PYTHON" - "$1" <<'PY'
import json
import sys
print(json.loads(open(sys.argv[1], encoding="utf-8").read())["weights"])
PY
}

evaluate_tag() {
  local tag="$1"
  local model_path="$2"
  local output="artifacts/server/phase9-fulltrain-eval-20260813-${tag}.json"
  status "$tag" "evaluation-started"
  if [[ ! -f "$model_path" ]]; then
    status "$tag" "evaluation-skipped-missing-weight"
    return 1
  fi
  set +e
  "$PYTHON" training/evaluate_detector.py "$model_path" \
    --data "$EVAL_DATA" --device 0 --image-size 640 --batch 64 --workers 4 \
    --project "runs/phase9-fulltrain-eval-b64-${tag}" --name frozen \
    --output "$output" > "/tmp/phase9-fulltrain-eval-${tag}.log" 2>&1
  local rc=$?
  set -e
  if [[ $rc -eq 0 && -f "$output" ]]; then
    status "$tag" "evaluation-completed"
    return 0
  fi
  status "$tag" "evaluation-failed-rc-${rc}"
  return 1
}

train_and_evaluate() {
  local tag="$1"
  local model="$2"
  local run_root="runs/phase9-fulltrain-b64-${tag}"
  status "$tag" "training-started"
  set +e
  "$PYTHON" training/train_phase9_finalist.py \
    --data "$TRAIN_DATA" --model "$model" --epochs 120 --image-size 640 \
    --batch 64 --device 0 --workers 4 --seed 20260729 \
    --project "$run_root" --name run > "/tmp/phase9-${tag}-train.log" 2>&1
  local rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    status "$tag" "training-failed-rc-${rc}"
    return 0
  fi
  local record
  record="$(find_training_record "$tag")"
  if [[ -z "$record" ]]; then
    status "$tag" "training-failed-missing-record"
    return 0
  fi
  local weights
  weights="$(weights_from_record "$record")"
  status "$tag" "training-completed-last-pt"
  evaluate_tag "$tag" "$weights" || true
}

# YOLO26n was started before this orchestrator; wait for it, then evaluate it.
wait_for_tag yolo26n
YOLO26N_RECORD="$(find_training_record yolo26n)"
if [[ -n "$YOLO26N_RECORD" ]]; then
  YOLO26N_WEIGHTS="$(weights_from_record "$YOLO26N_RECORD")"
  evaluate_tag yolo26n "$YOLO26N_WEIGHTS" || true
else
  status yolo26n training-record-missing
fi

# Establish the same frozen-set baseline without any runtime service or expert.
evaluate_tag current-main runs/detect/official-plus-public-weak-v1-e120-b64/weights/best.pt || true

train_and_evaluate yolo26s yolo26s.pt
train_and_evaluate yolo11s yolo11s.pt
train_and_evaluate yolo12s yolo12s.pt
train_and_evaluate yolov8s yolov8s.pt
train_and_evaluate yolov5su yolov5su.pt

status all done
touch "$STATUS_DIR/COMPLETE"
