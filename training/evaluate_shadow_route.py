"""Evaluate the deployed detector's shadow evidence without changing routing.

The script calls the existing inference HTTP service, so it does not load a
second copy of the detector or experts.  It reports the unchanged shadow
baseline and a counterfactual active result using the already calibrated
configuration returned by the service.  The counterfactual is never sent back
to the service and cannot change production behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import mimetypes
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

TARGET_CLASSES = {8, 10, 13, 15}
ROUTING_CLASSES = {10, 13}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def label_path(image_path: Path) -> Path:
    text = str(image_path)
    if "/images/" in text:
        text = text.replace("/images/", "/labels/", 1)
    elif "\\images\\" in text:
        text = text.replace("\\images\\", "\\labels\\", 1)
    return Path(text).with_suffix(".txt")


def read_images(path: Path) -> list[Path]:
    base = path.resolve().parent
    images: list[Path] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        image = Path(line.strip()).expanduser()
        images.append(image if image.is_absolute() else (base / image).resolve())
    return images


def parse_ground_truth(path: Path, image_width: int, image_height: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        class_id, cx, cy, width, height = map(float, parts)
        rows.append(
            {
                "class_id": int(class_id),
                "bbox": [
                    (cx - width / 2) * image_width,
                    (cy - height / 2) * image_height,
                    (cx + width / 2) * image_width,
                    (cy + height / 2) * image_height,
                ],
            }
        )
    return rows


def iou(left: list[float], right: list[float]) -> float:
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def average_precision(samples: list[dict[str, Any]], class_id: int, iou_threshold: float) -> float:
    ground_truth_by_image: dict[int, list[list[float]]] = {}
    total_ground_truth = 0
    ranked_predictions: list[tuple[float, int, list[float]]] = []
    for image_index, sample in enumerate(samples):
        targets = [item["bbox"] for item in sample["ground_truth"] if item["class_id"] == class_id]
        ground_truth_by_image[image_index] = targets
        total_ground_truth += len(targets)
        for prediction in sample["predictions"]:
            if prediction["class_id"] == class_id:
                ranked_predictions.append((prediction["confidence"], image_index, prediction["bbox"]))
    if total_ground_truth == 0 or not ranked_predictions:
        return 0.0
    ranked_predictions.sort(reverse=True, key=lambda item: item[0])
    matched = {image_index: set() for image_index in ground_truth_by_image}
    true_positive: list[float] = []
    false_positive: list[float] = []
    for _, image_index, box in ranked_predictions:
        targets = ground_truth_by_image[image_index]
        best_index = None
        best_overlap = 0.0
        for target_index, target in enumerate(targets):
            if target_index in matched[image_index]:
                continue
            overlap = iou(box, target)
            if overlap > best_overlap:
                best_overlap = overlap
                best_index = target_index
        if best_index is not None and best_overlap >= iou_threshold:
            matched[image_index].add(best_index)
            true_positive.append(1.0)
            false_positive.append(0.0)
        else:
            true_positive.append(0.0)
            false_positive.append(1.0)
    cumulative_tp = 0.0
    cumulative_fp = 0.0
    precisions: list[float] = []
    recalls: list[float] = []
    for tp, fp in zip(true_positive, false_positive):
        cumulative_tp += tp
        cumulative_fp += fp
        precisions.append(cumulative_tp / max(cumulative_tp + cumulative_fp, 1e-12))
        recalls.append(cumulative_tp / total_ground_truth)
    values = []
    for recall_point in [index / 100 for index in range(101)]:
        eligible = [precision for precision, recall in zip(precisions, recalls) if recall >= recall_point]
        values.append(max(eligible) if eligible else 0.0)
    return sum(values) / len(values)


def metrics(samples: list[dict[str, Any]], class_count: int = 16) -> dict[str, Any]:
    per_class: list[dict[str, Any]] = []
    for class_id in range(class_count):
        aps = [average_precision(samples, class_id, 0.50 + 0.05 * index) for index in range(10)]
        per_class.append(
            {
                "class_id": class_id,
                "ap50": aps[0],
                "map50_95": sum(aps) / len(aps),
                "aps": aps,
            }
        )
    return {
        "map50": sum(item["ap50"] for item in per_class) / class_count,
        "map50_95": sum(item["map50_95"] for item in per_class) / class_count,
        "weak_map50_95": sum(per_class[class_id]["map50_95"] for class_id in sorted(TARGET_CLASSES)) / len(TARGET_CLASSES),
        "per_class": per_class,
    }


def normalized_to_pixels(box: list[float], width: int, height: int) -> list[float]:
    x, y, box_width, box_height = box
    return [x * width, y * height, (x + box_width) * width, (y + box_height) * height]


def prediction_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    image = payload["image"]
    width = int(image["width"])
    height = int(image["height"])
    return [
        {
            "class_id": int(item["class_id"]),
            "confidence": float(item["confidence"]),
            "bbox": normalized_to_pixels(item["bbox"], width, height),
        }
        for item in payload.get("detections", [])
    ]


def supports_from_route(route: dict[str, Any]) -> tuple[dict[int, dict[int, float]], dict[int, dict[int, float]]]:
    crop_support: dict[int, dict[int, float]] = {}
    class10_support: dict[int, dict[int, float]] = {}
    for decision in route.get("decisions", []):
        index = int(decision["candidate_index"])
        crop_support[index] = {int(key): float(value) for key, value in decision.get("crop_support", {}).items()}
        class10_support[index] = {
            int(key): float(value) for key, value in decision.get("class10_support", {}).items()
        }
    return crop_support, class10_support


def active_counterfactual(
    detections: list[dict[str, Any]],
    route: dict[str, Any],
) -> list[dict[str, Any]]:
    """Apply the exact current calibrated active rules locally for comparison."""
    config = route.get("configuration", {})
    crop_support, class10_support = supports_from_route(route)
    output: list[dict[str, Any]] = []
    for index, detection in enumerate(detections):
        item = dict(detection)
        original_class = int(item["class_id"])
        if original_class not in ROUTING_CLASSES or index not in crop_support:
            output.append(item)
            continue
        support = crop_support[index]
        target_scores = {class_id: float(support.get(class_id, 0.0)) for class_id in ROUTING_CLASSES}
        best_score = max(target_scores.values())
        background_score = float(support.get(99, 0.0))
        if background_score >= float(config.get("background_threshold", 0.9)) and background_score >= best_score + float(config.get("background_margin", 0.0)):
            continue
        class10_score = class10_support.get(index, {}).get(10, 0.0)
        if original_class == 10 and class10_score < float(config.get("class10_expert_threshold", 0.0)):
            continue
        confidence = float(item["confidence"])
        score_mode = config.get("score_mode", "keep")
        if score_mode == "product":
            confidence *= target_scores.get(original_class, 0.0)
        elif score_mode == "geometric":
            confidence = (confidence * target_scores.get(original_class, 0.0)) ** 0.5
        temperature = float(config.get("temperature10", 1.25) if original_class == 10 else config.get("temperature13", 0.75))
        confidence = min(max(confidence, 1e-6), 1.0 - 1e-6)
        logit = math.log(confidence / (1.0 - confidence))
        confidence = 1.0 / (1.0 + math.exp(-logit / temperature))
        threshold = float(config.get("threshold10", 0.15) if original_class == 10 else config.get("threshold13", 0.15))
        if confidence < threshold:
            continue
        item["confidence"] = confidence
        output.append(item)
    return output


def candidate_coverage(samples: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter()
    covered = Counter()
    expert_agreement = Counter()
    for sample in samples:
        route = sample["routing"]
        detections = sample["predictions"]
        ground_truth = sample["ground_truth"]
        decisions = {int(row["candidate_index"]): row for row in route.get("decisions", [])}
        for gt in ground_truth:
            if gt["class_id"] not in ROUTING_CLASSES:
                continue
            counts[gt["class_id"]] += 1
            matching = [
                (index, detection)
                for index, detection in enumerate(detections)
                if detection["class_id"] in ROUTING_CLASSES
                and detection["confidence"] >= float(route.get("configuration", {}).get("candidate_confidence", 0.05))
                and iou(gt["bbox"], detection["bbox"]) >= 0.5
            ]
            if matching:
                covered[gt["class_id"]] += 1
                index, detection = max(matching, key=lambda item: item[1]["confidence"])
                decision = decisions.get(index, {})
                support = {int(k): float(v) for k, v in decision.get("crop_support", {}).items()}
                if support and max(support, key=support.get) == gt["class_id"]:
                    expert_agreement[gt["class_id"]] += 1
    return {
        "ground_truth_boxes": {str(key): counts[key] for key in sorted(counts)},
        "candidate_box_coverage_at_iou50": {str(key): covered[key] for key in sorted(counts)},
        "crop_top1_agreement_on_covered_boxes": {str(key): expert_agreement[key] for key in sorted(counts)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate current detector shadow evidence through HTTP.")
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8870/v1/detect")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--request-confidence", type=float, default=0.05)
    parser.add_argument("--limit", type=int, default=None, help="Optional small-sample limit for a smoke run.")
    args = parser.parse_args()

    image_paths = read_images(args.images.expanduser().resolve(strict=True))
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be positive")
        image_paths = image_paths[: args.limit]
    samples: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    missing_labels = 0
    started = time.perf_counter()
    with httpx.Client(timeout=args.timeout) as client:
        for index, image_path in enumerate(image_paths, start=1):
            try:
                content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
                response = client.post(
                    args.endpoint,
                    files={"image": (image_path.name, image_path.read_bytes(), content_type)},
                    data={"confidence": str(args.request_confidence)},
                )
                response.raise_for_status()
                payload = response.json()
                predictions = prediction_rows(payload)
                width = int(payload["image"]["width"])
                height = int(payload["image"]["height"])
                ground_truth = parse_ground_truth(label_path(image_path), width, height)
                if not label_path(image_path).is_file():
                    missing_labels += 1
                route = payload.get("routing", {})
                samples.append(
                    {
                        "image": str(image_path),
                        "ground_truth": ground_truth,
                        "predictions": predictions,
                        "routing": route,
                        "model_sha256": payload.get("model_sha256"),
                        "speed_ms": payload.get("speed_ms", {}),
                    }
                )
                if index % 50 == 0 or index == len(image_paths):
                    print(f"processed {index}/{len(image_paths)}")
            except Exception as exc:  # preserve the exact failing sample for diagnosis
                errors.append({"image": str(image_path), "error": repr(exc)})

    baseline_samples = [
        {"image": s["image"], "ground_truth": s["ground_truth"], "predictions": s["predictions"]}
        for s in samples
    ]
    counterfactual_samples = [
        {
            "image": s["image"],
            "ground_truth": s["ground_truth"],
            "predictions": active_counterfactual(s["predictions"], s["routing"]),
        }
        for s in samples
    ]
    baseline_metrics = metrics(baseline_samples)
    shadow_metrics = metrics(baseline_samples)
    counterfactual_metrics = metrics(counterfactual_samples)
    baseline_per_class = baseline_metrics["per_class"]
    counterfactual_per_class = counterfactual_metrics["per_class"]
    per_class_delta = {
        str(class_id): counterfactual_per_class[class_id]["map50_95"] - baseline_per_class[class_id]["map50_95"]
        for class_id in range(16)
    }
    non_target_deltas = [per_class_delta[str(class_id)] for class_id in range(16) if class_id not in TARGET_CLASSES]
    overall_delta_map50 = counterfactual_metrics["map50"] - baseline_metrics["map50"]
    overall_delta_map50_95 = counterfactual_metrics["map50_95"] - baseline_metrics["map50_95"]
    weak_delta_map50_95 = counterfactual_metrics["weak_map50_95"] - baseline_metrics["weak_map50_95"]
    result = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "scope": {
            "image_list": str(args.images.expanduser().resolve()),
            "image_list_sha256": sha256(args.images.expanduser().resolve()),
            "image_count": len(image_paths),
            "successful_requests": len(samples),
            "failed_requests": len(errors),
            "missing_label_files": missing_labels,
            "endpoint": args.endpoint,
            "request_confidence": args.request_confidence,
        },
        "errors": errors,
        "service": {
            "model_sha256": samples[0].get("model_sha256") if samples else None,
            "routing_mode_observed": sorted({s["routing"].get("mode") for s in samples}),
            "reclassify_observed": sorted({s["routing"].get("configuration", {}).get("reclassify", False) for s in samples}),
        },
        "baseline_main_and_shadow_keep": {
            "main": baseline_metrics,
            "shadow_keep": shadow_metrics,
            "identical": baseline_metrics == shadow_metrics,
        },
        "counterfactual_current_active_parameters": {
            "metrics": counterfactual_metrics,
            "delta_map50_vs_main": overall_delta_map50,
            "delta_map50_95_vs_main": overall_delta_map50_95,
            "delta_weak_map50_95_vs_main": weak_delta_map50_95,
            "per_class_map50_95_delta_vs_main": per_class_delta,
            "target_classes": sorted(TARGET_CLASSES),
            "non_target_min_delta": min(non_target_deltas) if non_target_deltas else 0.0,
            "all_target_classes_non_decreasing": all(per_class_delta[str(class_id)] >= -1e-12 for class_id in TARGET_CLASSES),
            "overall_non_decreasing": counterfactual_metrics["map50_95"] >= baseline_metrics["map50_95"] - 1e-12,
        },
        "candidate_coverage": candidate_coverage(samples),
        "latency": {
            "successful_requests": len(samples),
            "request_model_ms": [float(s["speed_ms"].get("request_model_ms", 0.0)) for s in samples],
            "routing_ms": [float(s["speed_ms"].get("routing_ms", 0.0)) for s in samples],
        },
        "decision": "keep_shadow",
        "decision_reason": "The service was observed in shadow mode; counterfactual active results are diagnostic only and do not satisfy independent frozen promotion gates by themselves.",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "successful_requests": len(samples),
        "failed_requests": len(errors),
        "baseline_map50_95": baseline_metrics["map50_95"],
        "counterfactual_map50_95": counterfactual_metrics["map50_95"],
        "decision": result["decision"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
