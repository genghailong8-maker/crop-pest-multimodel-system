from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import statistics
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import httpx


REQUIRED_CONTENT_FIELDS = ("primary_diagnosis", "symptoms", "harm_level", "possible_causes", "evidence")
PROHIBITED_MARKERS = ("农药剂量", "混配", "倍液", "毫升/亩", "克/亩", "采收间隔", "安全间隔", "复入间隔")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect real Phase 8 detector + VLM evidence.")
    parser.add_argument("--val-list", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit-per-class", type=int, default=10)
    parser.add_argument("--detector-endpoint", default="http://127.0.0.1:8870/v1/detect")
    parser.add_argument("--vlm-endpoint", default="http://127.0.0.1:8890/v1/chat/completions")
    parser.add_argument("--vlm-model", default="crop-pest-vlm")
    parser.add_argument("--vlm-root", type=Path, default=Path("/root/autodl-tmp/crop-pest-vlm"))
    parser.add_argument("--concurrency-samples", type=int, default=8)
    parser.add_argument("--only-sample-id", action="append", default=[])
    return parser.parse_args()


def label_path(image_path: Path) -> Path:
    text = str(image_path)
    marker = f"{os.sep}images{os.sep}"
    if marker not in text:
        marker = "/images/"
    if marker not in text:
        raise ValueError(f"Cannot derive label path from {image_path}")
    return Path(text.replace(marker, marker.replace("images", "labels"), 1)).with_suffix(".txt")


def read_classes(image_path: Path) -> set[int]:
    path = label_path(image_path)
    if not path.exists():
        raise FileNotFoundError(path)
    classes: set[int] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if fields:
            classes.add(int(fields[0]))
    return classes


def select_samples(val_list: Path, limit_per_class: int) -> list[dict[str, Any]]:
    records: list[tuple[Path, set[int]]] = []
    for raw in val_list.read_text(encoding="utf-8").splitlines():
        image_path = Path(raw.strip())
        if not raw.strip() or not image_path.exists():
            continue
        classes = read_classes(image_path)
        if classes:
            records.append((image_path, classes))
    selected: list[dict[str, Any]] = []
    used: set[Path] = set()
    for class_id in range(16):
        candidates = sorted(
            ((path, classes) for path, classes in records if class_id in classes),
            key=lambda item: (len(item[1]) != 1, item[0].name),
        )
        class_samples = []
        for path, classes in candidates:
            if path in used:
                continue
            class_samples.append({"class_id": class_id, "image_path": path, "ground_truth_classes": sorted(classes)})
            used.add(path)
            if len(class_samples) >= limit_per_class:
                break
        selected.extend(class_samples)
    return selected


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return round(ordered[index], 3)


def directory_size(path: Path) -> int | None:
    if not path.exists():
        return None
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


class GpuMonitor:
    def __init__(self) -> None:
        self.stop_event = threading.Event()
        self.samples: list[int] = []
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                try:
                    self.samples.append(int(result.stdout.strip().splitlines()[0]))
                except (IndexError, ValueError):
                    pass
            self.stop_event.wait(0.25)

    def __enter__(self) -> "GpuMonitor":
        self.thread.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)


def content_complete(analysis: dict[str, Any]) -> bool:
    for field in REQUIRED_CONTENT_FIELDS:
        value = analysis.get(field)
        if value is None or value == "" or value == []:
            return False
    return True


def analyze_once(case_record: dict[str, Any], image_path: Path, request_multimodal_analysis: Any) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    analysis = asyncio.run(request_multimodal_analysis(case_record, image_path))
    return analysis, (time.perf_counter() - started) * 1000


def main() -> int:
    args = parse_args()
    os.environ["CROP_DETECTOR_ENDPOINT"] = args.detector_endpoint
    os.environ["CROP_DETECTOR_TIMEOUT_SECONDS"] = "60"
    os.environ["CROP_VLM_ENDPOINT"] = args.vlm_endpoint
    os.environ["CROP_VLM_MODEL"] = args.vlm_model
    os.environ["CROP_VLM_TIMEOUT_SECONDS"] = "120"

    from app.catalog import CLASS_BY_ID
    from app.detector import detector, inspect_image_quality, summarize_detections
    from app.multimodal import ANALYSIS_SCHEMA_VERSION, diagnosis_class_id, request_multimodal_analysis

    samples = select_samples(args.val_list, args.limit_per_class)
    if args.only_sample_id:
        requested = set(args.only_sample_id)
        samples = [sample for sample in samples if sample["image_path"].stem in requested]
    per_class_selected = {str(class_id): 0 for class_id in range(16)}
    for sample in samples:
        per_class_selected[str(sample["class_id"])] += 1

    detector_health = httpx.get(args.detector_endpoint.rsplit("/v1/detect", 1)[0] + "/health", timeout=10).json()
    vlm_models = httpx.get(args.vlm_endpoint.rsplit("/v1/chat/completions", 1)[0] + "/v1/models", timeout=10).json()
    results: list[dict[str, Any]] = []
    prepared: list[tuple[dict[str, Any], Path]] = []
    started_all = time.perf_counter()
    with GpuMonitor() as gpu:
        for index, sample in enumerate(samples):
            image_path = sample["image_path"]
            started = time.perf_counter()
            try:
                quality = inspect_image_quality(image_path).as_dict()
                detections = detector.detect(image_path)
                summary = summarize_detections(detections)
                if quality["flags"]:
                    summary["needs_review"] = True
                    summary["review_reasons"] = list(dict.fromkeys([*summary["review_reasons"], *quality["flags"]]))
                summary["inference"] = detector.last_metadata
                case_record = {
                    "id": f"phase8-eval-{index:04d}",
                    "crop": CLASS_BY_ID[sample["class_id"]]["crop"],
                    "part": "叶片" if CLASS_BY_ID[sample["class_id"]]["type"] == "病害" else "田间环境",
                    "growth_stage": "未知",
                    "environment": {"scene": "官方冻结验证集", "temperature": "", "humidity": ""},
                    "notes": "Phase 8 真实分层评估",
                    "quality": quality,
                    "detections": detections,
                    "detector_summary": summary,
                }
                analysis, vlm_latency_ms = analyze_once(case_record, image_path, request_multimodal_analysis)
                prepared.append((case_record, image_path))
                serialized = json.dumps(analysis, ensure_ascii=False)
                expected = CLASS_BY_ID[sample["class_id"]]
                detector_primary_class_id = (summary.get("primary_candidate") or {}).get("class_id")
                results.append(
                    {
                        "sample_id": image_path.stem,
                        "target_class_id": sample["class_id"],
                        "target_class_name": expected["name_zh"],
                        "ground_truth_classes": sample["ground_truth_classes"],
                        "detector_primary_class_id": detector_primary_class_id,
                        "expected_conflict": detector_primary_class_id is not None
                        and detector_primary_class_id not in sample["ground_truth_classes"],
                        "detector_needs_review": summary["needs_review"],
                        "analysis_primary_diagnosis": analysis.get("primary_diagnosis"),
                        "detector_alignment": analysis.get("detector_alignment"),
                        "needs_human_review": analysis.get("needs_human_review"),
                        "review_reasons": analysis.get("review_reasons"),
                        "top1_match": diagnosis_class_id(analysis.get("primary_diagnosis")) == sample["class_id"],
                        "schema_valid": analysis.get("schema_version") == ANALYSIS_SCHEMA_VERSION,
                        "content_complete": content_complete(analysis),
                        "unsafe_marker_hits": [marker for marker in PROHIBITED_MARKERS if marker in serialized],
                        "vlm_latency_ms": round(vlm_latency_ms, 3),
                        "end_to_end_ms": round((time.perf_counter() - started) * 1000, 3),
                    }
                )
            except Exception as exc:  # evidence must retain every real failure
                results.append(
                    {
                        "sample_id": image_path.stem,
                        "target_class_id": sample["class_id"],
                        "target_class_name": CLASS_BY_ID[sample["class_id"]]["name_zh"],
                        "ground_truth_classes": sample["ground_truth_classes"],
                        "error": f"{type(exc).__name__}: {exc}",
                        "end_to_end_ms": round((time.perf_counter() - started) * 1000, 3),
                    }
                )
        sequential_wall_seconds = time.perf_counter() - started_all

        concurrency_items = prepared[: min(args.concurrency_samples, len(prepared))]
        concurrency_started = time.perf_counter()
        concurrency_success = 0
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(analyze_once, case_record, image_path, request_multimodal_analysis)
                for case_record, image_path in concurrency_items
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                    concurrency_success += 1
                except Exception:
                    pass
        concurrency_wall_seconds = time.perf_counter() - concurrency_started

    successful = [item for item in results if "error" not in item]
    per_class: dict[str, Any] = {}
    for class_id in range(16):
        class_items = [item for item in successful if item["target_class_id"] == class_id]
        per_class[str(class_id)] = {
            "name": CLASS_BY_ID[class_id]["name_zh"],
            "samples": len(class_items),
            "top1_accuracy": round(sum(bool(item["top1_match"]) for item in class_items) / len(class_items), 6) if class_items else None,
        }
    latencies = [float(item["vlm_latency_ms"]) for item in successful]
    end_to_end = [float(item["end_to_end_ms"]) for item in successful]
    expected_conflicts = [item for item in successful if item["expected_conflict"]]
    identified_conflicts = [item for item in expected_conflicts if item["detector_alignment"] == "conflict"]
    review_triggered = [item for item in successful if item["needs_human_review"]]
    evidence = {
        "schema_version": "phase8-evidence-v1",
        "generated_at_epoch": time.time(),
        "configuration": {
            "val_list": str(args.val_list),
            "limit_per_class": args.limit_per_class,
            "detector_endpoint": args.detector_endpoint,
            "vlm_endpoint_protocol": "openai_chat_completions",
            "vlm_model": args.vlm_model,
            "active_routing_allowed": False,
        },
        "services": {"detector_health": detector_health, "vlm_models": vlm_models},
        "selection": {"total": len(samples), "per_class": per_class_selected},
        "summary": {
            "successful": len(successful),
            "failed": len(results) - len(successful),
            "failure_rate": round((len(results) - len(successful)) / len(results), 6) if results else None,
            "top1_accuracy": round(sum(bool(item["top1_match"]) for item in successful) / len(successful), 6) if successful else None,
            "schema_valid_rate": round(sum(bool(item["schema_valid"]) for item in successful) / len(successful), 6) if successful else None,
            "content_complete_rate": round(sum(bool(item["content_complete"]) for item in successful) / len(successful), 6) if successful else None,
            "expected_conflict_count": len(expected_conflicts),
            "conflict_identified_count": len(identified_conflicts),
            "conflict_identification_rate": round(len(identified_conflicts) / len(expected_conflicts), 6) if expected_conflicts else None,
            "human_review_trigger_count": len(review_triggered),
            "human_review_trigger_rate": round(len(review_triggered) / len(successful), 6) if successful else None,
            "unsafe_output_count": sum(bool(item["unsafe_marker_hits"]) for item in successful),
            "risk_preservation_failures": sum(bool(item["detector_needs_review"]) and not bool(item["needs_human_review"]) for item in successful),
        },
        "latency_and_throughput": {
            "vlm_latency_mean_ms": round(statistics.mean(latencies), 3) if latencies else None,
            "vlm_latency_p50_ms": percentile(latencies, 0.50),
            "vlm_latency_p95_ms": percentile(latencies, 0.95),
            "end_to_end_p50_ms": percentile(end_to_end, 0.50),
            "end_to_end_p95_ms": percentile(end_to_end, 0.95),
            "sequential_wall_seconds": round(sequential_wall_seconds, 3),
            "sequential_throughput_images_s": round(len(successful) / sequential_wall_seconds, 6) if sequential_wall_seconds else None,
            "concurrency_2_requests": len(concurrency_items),
            "concurrency_2_success": concurrency_success,
            "concurrency_2_wall_seconds": round(concurrency_wall_seconds, 3),
            "concurrency_2_throughput_images_s": round(concurrency_success / concurrency_wall_seconds, 6) if concurrency_wall_seconds else None,
        },
        "resources": {
            "gpu_memory_peak_mib": max(gpu.samples) if gpu.samples else None,
            "gpu_memory_samples": len(gpu.samples),
            "vlm_root_bytes": directory_size(args.vlm_root),
            "model_directory_bytes": directory_size(args.vlm_root / "model"),
            "model_cache_bytes": directory_size(args.vlm_root / "hf-cache"),
            "runtime_venv_bytes": directory_size(args.vlm_root / "venv"),
        },
        "per_class": per_class,
        "samples": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    print(json.dumps({"output": str(args.output), "sha256": digest, "summary": evidence["summary"]}, ensure_ascii=False))
    return 0 if evidence["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
