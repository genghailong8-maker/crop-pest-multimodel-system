from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "server" / "phase5-full-evidence-20260810.json"
MIB = 1024 * 1024


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.is_file():
        return {"path": relative, "exists": False}
    stat = path.stat()
    return {
        "path": relative,
        "exists": True,
        "size_bytes": stat.st_size,
        "size_mib": round(stat.st_size / MIB, 6),
        "sha256": sha256(path),
        "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }


def read_json(relative: str) -> dict[str, Any] | list[Any] | None:
    path = ROOT / relative
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def http_json(url: str, timeout: float = 12.0) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def http_probe(url: str, timeout: float = 12.0) -> dict[str, Any]:
    try:
        payload = http_json(url, timeout)
        return {"url": url, "reachable": True, "payload": payload}
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {"url": url, "reachable": False, "error": repr(exc)}


def http_text_probe(url: str, timeout: float = 12.0) -> dict[str, Any]:
    """Probe a text/HTML endpoint without requiring a JSON response."""
    try:
        request = urllib.request.Request(url, headers={"Accept": "text/html,application/xhtml+xml"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type")
            return {
                "url": url,
                "reachable": True,
                "status": response.status,
                "content_type": content_type,
                "bytes": len(body),
            }
    except (OSError, urllib.error.URLError) as exc:
        return {"url": url, "reachable": False, "error": repr(exc)}


def git_snapshot() -> dict[str, Any]:
    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        )
        return completed.stdout.strip()

    return {
        "branch": run("branch", "--show-current"),
        "commit": run("rev-parse", "HEAD"),
        "status_short": run("status", "--short", "--branch").splitlines(),
    }


def calibration_summary() -> dict[str, Any]:
    relative = "artifacts/experiments/independent-field-calibration-10-13-v2/second-round-calibration-v2.json"
    report = read_json(relative)
    if not isinstance(report, dict):
        return {"report": file_record(relative), "available": False}
    tuning = report.get("tuning") or {}
    frozen = report.get("frozen_official_evaluation") or {}
    selected = tuning.get("selected") or {}
    return {
        "report": file_record(relative),
        "available": True,
        "decision": report.get("decision"),
        "configuration": report.get("configuration"),
        "tuning": {
            "image_count": tuning.get("image_count"),
            "grid_config_count": tuning.get("grid_config_count"),
            "acceptable_count": tuning.get("acceptable_count"),
            "selected": selected,
        },
        "frozen_official_evaluation": {
            "image_count": frozen.get("image_count"),
            "baseline": frozen.get("baseline"),
            "selected": frozen.get("selected"),
            "acceptable": frozen.get("acceptable"),
        },
    }


def metrics_summary() -> dict[str, Any]:
    main_relative = "artifacts/experiments/official-plus-public-weak-v1-e120-b64/full-pt-official-metrics.json"
    baseline_relative = "artifacts/server/evaluations/official-baseline-yolo26n-e120-b64/pt-metrics.json"
    main = read_json(main_relative)
    baseline = read_json(baseline_relative)
    return {
        "main_official_frozen": {
            "evidence": file_record(main_relative),
            "overall": main.get("overall") if isinstance(main, dict) else None,
            "data": main.get("data") if isinstance(main, dict) else None,
        },
        "official_baseline": {
            "evidence": file_record(baseline_relative),
            "overall": baseline.get("overall") if isinstance(baseline, dict) else None,
            "data": baseline.get("data") if isinstance(baseline, dict) else None,
        },
        "route_benchmark": {
            "evidence": file_record("artifacts/server/phase5-benchmark-20260810-route.json"),
            "summary": _benchmark_summary("artifacts/server/phase5-benchmark-20260810-route.json"),
        },
        "main_pt_benchmark": {
            "evidence": file_record("artifacts/server/phase5-benchmark-20260810-main-pt.json"),
            "summary": _benchmark_summary("artifacts/server/phase5-benchmark-20260810-main-pt.json"),
        },
    }


def _benchmark_summary(relative: str) -> dict[str, Any] | None:
    payload = read_json(relative)
    if not isinstance(payload, dict):
        return None
    result: dict[str, Any] = {}
    for name in ("sequential", "concurrent"):
        section = payload.get(name)
        if isinstance(section, dict):
            result[name] = {
                "elapsed_s": section.get("elapsed_s"),
                "throughput_requests_per_second": section.get("throughput_requests_per_second"),
                "summary": section.get("summary"),
            }
    if isinstance(payload.get("batches"), list):
        result["batches"] = [
            {
                "batch_size": item.get("batch_size"),
                "latency_batch_ms": item.get("latency_batch_ms"),
                "latency_per_image_ms": item.get("latency_per_image_ms"),
                "throughput_images_per_second": item.get("throughput_images_per_second"),
                "gpu_memory_peak_mib": item.get("gpu_memory_peak_mib"),
            }
            for item in payload["batches"]
            if isinstance(item, dict)
        ]
    return result


def artifact_inventory() -> list[dict[str, Any]]:
    allowed_suffixes = {".json", ".yaml", ".yml", ".txt", ".md"}
    tokens = (
        "metric",
        "benchmark",
        "checkpoint",
        "args",
        "competition",
        "calibration",
        "report",
        "manifest",
        "provenance",
        "export",
        "dataset",
        "split",
        "results",
        "audit",
    )
    records: list[dict[str, Any]] = []
    for root_name in ("artifacts/server", "artifacts/experiments"):
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
                continue
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
            relative = path.relative_to(ROOT).as_posix()
            if any(token in path.name.lower() for token in tokens) or path.suffix.lower() in {".yaml", ".yml"}:
                records.append(file_record(relative))
    return sorted(records, key=lambda item: str(item["path"]))


def main() -> None:
    model_roles = {
        "official_baseline_16_class": file_record(
            "artifacts/server/official-baseline-yolo26n-e120-b64/weights/best.pt"
        ),
        "production_main_16_class": file_record(
            "artifacts/server/remote-runs/official-plus-public-weak-v1-e120-b64/weights/best.pt"
        ),
        "class10_detector_expert": file_record(
            "artifacts/server/experiments/weak-expert-v2-full-public10-ft-freeze10-lr1e4-e18-b64/best.pt"
        ),
        "class10_13_crop_classifier_expert": file_record(
            "artifacts/server/experiments/pairwise-crop-cls-10-13-v5-e30-b128/best.pt"
        ),
        "production_main_onnx": file_record(
            "artifacts/server/remote-runs/official-plus-public-weak-v1-e120-b64/weights/best.onnx"
        ),
    }
    inference = http_probe("http://127.0.0.1:8870/health")
    backend = http_probe("http://127.0.0.1:8000/health")
    monitor = http_probe("http://127.0.0.1:8765/health")
    training = http_probe("http://127.0.0.1:8765/api/training/status")
    web = http_text_probe("http://localhost:3000/training")
    cases = http_probe("http://127.0.0.1:8000/api/cases?limit=1")
    case_payload = cases.get("payload") if cases.get("reachable") else None
    latest_case = case_payload[0] if isinstance(case_payload, list) and case_payload else None
    case_summary = None
    if isinstance(latest_case, dict):
        case_summary = {
            "id": latest_case.get("id"),
            "created_at": latest_case.get("created_at"),
            "status": latest_case.get("status"),
            "image_filename": latest_case.get("image_filename"),
            "quality": latest_case.get("quality"),
            "detector_summary": latest_case.get("detector_summary"),
        }

    evidence_paths = [
        "artifacts/server/phase5-live-checkpoint-20260807.json",
        "artifacts/server/phase5-shutdown-task-nodes-20260807.json",
        "artifacts/server/phase5-benchmark-checkpoint-20260810.json",
        "artifacts/experiments/class-pair-audit-8-15-v1/report.json",
        "artifacts/experiments/class-pair-audit-6-12-v1/report.json",
        "artifacts/server/pairwise-calibration-v1-checkpoint-20260807.json",
        "artifacts/server/pairwise-hard-crops-10-13-v5-checkpoint-20260807.json",
        "artifacts/experiments/independent-field-calibration-10-13-v2/second-round-calibration-v2.json",
    ]

    output = {
        "created_at": utc_now(),
        "purpose": "Phase 5 full monitoring, configuration, metrics, and weight evidence",
        "scope": {
            "training_experiments_known": 12,
            "retained_model_roles": 4,
            "official_classes": 16,
            "official_training_images": 3321,
            "official_frozen_validation_images": 833,
            "independent_tune_images": 101,
            "independent_frozen_images": 85,
            "active_routing_allowed": False,
        },
        "runtime": {
            "inference_health": inference,
            "backend_health": backend,
            "training_monitor_health": monitor,
            "training_monitor_status": training,
            "web_training_probe": {key: value for key, value in web.items() if key != "payload"},
            "latest_case": case_summary,
        },
        "configuration": {
            "inference_health_routing": (
                inference.get("payload", {}).get("routing") if inference.get("reachable") else None
            ),
            "inference_models": (
                inference.get("payload", {}).get("routing", {}).get("models")
                if inference.get("reachable")
                else None
            ),
            "web_backend_endpoint": "http://127.0.0.1:8000",
            "inference_tunnel_endpoint": "http://127.0.0.1:8870",
            "training_monitor_endpoint": "http://127.0.0.1:8765",
            "routing_gate": "shadow_only_until_new_independent_frozen_gate_passes",
        },
        "models": model_roles,
        "metrics": metrics_summary(),
        "calibration": calibration_summary(),
        "evidence_files": [file_record(path) for path in evidence_paths],
        "artifact_inventory": artifact_inventory(),
        "git": git_snapshot(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "bytes": OUTPUT.stat().st_size, "runs": len((training.get("payload") or {}).get("runs", [])) if training.get("reachable") else 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
