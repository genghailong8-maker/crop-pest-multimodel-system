from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


TARGET_CLASSES = (8, 10)
RESCUE_SOURCE = {15: 8, 13: 10}
EXPERT_TO_OFFICIAL = {0: 8, 1: 10}


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
    return [Path(line.strip()) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def prediction_rows(result: Any) -> list[dict[str, Any]]:
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return []
    return [
        {
            "class_id": int(class_id),
            "confidence": float(confidence),
            "bbox": [float(value) for value in coordinates],
        }
        for coordinates, confidence, class_id in zip(
            boxes.xyxy.detach().cpu().tolist(),
            boxes.conf.detach().cpu().tolist(),
            boxes.cls.detach().cpu().tolist(),
        )
    ]


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


def crop_box(image: Image.Image, box: list[float], expand: float) -> Image.Image:
    x1, y1, x2, y2 = box
    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)
    x1 = max(0, math.floor(x1 - width * expand))
    y1 = max(0, math.floor(y1 - height * expand))
    x2 = min(image.width, math.ceil(x2 + width * expand))
    y2 = min(image.height, math.ceil(y2 + height * expand))
    return image.crop((x1, y1, max(x1 + 1, x2), max(y1 + 1, y2))).convert("RGB")


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
    if total_ground_truth == 0:
        return 0.0
    ranked_predictions.sort(reverse=True, key=lambda item: item[0])
    matched = {image_index: set() for image_index in ground_truth_by_image}
    true_positive: list[float] = []
    false_positive: list[float] = []
    for _, image_index, box in ranked_predictions:
        targets = ground_truth_by_image[image_index]
        best_index = None
        best_iou = 0.0
        for target_index, target in enumerate(targets):
            if target_index in matched[image_index]:
                continue
            overlap = iou(box, target)
            if overlap > best_iou:
                best_iou = overlap
                best_index = target_index
        if best_index is not None and best_iou >= iou_threshold:
            matched[image_index].add(best_index)
            true_positive.append(1.0)
            false_positive.append(0.0)
        else:
            true_positive.append(0.0)
            false_positive.append(1.0)
    if not ranked_predictions:
        return 0.0
    tp = np.cumsum(np.asarray(true_positive))
    fp = np.cumsum(np.asarray(false_positive))
    recall = tp / total_ground_truth
    precision = tp / np.maximum(tp + fp, 1e-12)
    return float(
        np.mean(
            [
                np.max(precision[recall >= recall_point]) if np.any(recall >= recall_point) else 0.0
                for recall_point in np.linspace(0.0, 1.0, 101)
            ]
        )
    )


def metrics(
    samples: list[dict[str, Any]],
    class_count: int = 16,
    baseline: dict[str, Any] | None = None,
    changed_classes: set[int] | None = None,
) -> dict[str, Any]:
    per_class: list[dict[str, Any]] = []
    iou_thresholds = [round(0.50 + 0.05 * index, 2) for index in range(10)]
    for class_id in range(class_count):
        if baseline is not None and changed_classes is not None and class_id not in changed_classes:
            per_class.append(dict(baseline["per_class"][class_id]))
        else:
            aps = [average_precision(samples, class_id, threshold) for threshold in iou_thresholds]
            per_class.append(
                {
                    "class_id": class_id,
                    "ap50": aps[0],
                    "map50_95": float(np.mean(aps)),
                    "aps": aps,
                }
            )
    return {
        "map50": float(np.mean([item["ap50"] for item in per_class])),
        "map50_95": float(np.mean([item["map50_95"] for item in per_class])),
        "weak_map50_95": float(np.mean([per_class[class_id]["map50_95"] for class_id in TARGET_CLASSES])),
        "per_class": per_class,
    }


def best_f1(samples: list[dict[str, Any]], class_id: int) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for threshold in [round(index * 0.05, 2) for index in range(1, 20)]:
        true_positive = false_positive = false_negative = 0
        for sample in samples:
            targets = [item["bbox"] for item in sample["ground_truth"] if item["class_id"] == class_id]
            predictions = [
                item for item in sample["predictions"]
                if item["class_id"] == class_id and item["confidence"] >= threshold
            ]
            pairs = sorted(
                [
                    (iou(target, prediction["bbox"]), target_index, prediction_index)
                    for target_index, target in enumerate(targets)
                    for prediction_index, prediction in enumerate(predictions)
                ],
                reverse=True,
            )
            matched_targets: set[int] = set()
            matched_predictions: set[int] = set()
            for overlap, target_index, prediction_index in pairs:
                if overlap < 0.5 or target_index in matched_targets or prediction_index in matched_predictions:
                    continue
                matched_targets.add(target_index)
                matched_predictions.add(prediction_index)
            true_positive += len(matched_targets)
            false_negative += len(targets) - len(matched_targets)
            false_positive += len(predictions) - len(matched_predictions)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        row = {
            "threshold": threshold,
            "tp": true_positive,
            "fp": false_positive,
            "fn": false_negative,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
        if best is None or (row["f1"], row["recall"], -row["threshold"]) > (
            best["f1"], best["recall"], -best["threshold"]
        ):
            best = row
    return best or {}


def clone_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "image": sample["image"],
            "ground_truth": sample["ground_truth"],
            "predictions": [dict(prediction) for prediction in sample["predictions"]],
        }
        for sample in samples
    ]


def fuse(
    samples: list[dict[str, Any]],
    support_by_candidate: dict[tuple[int, int], dict[int, float]],
    support_threshold: float,
    rescue_threshold: float | None,
    score_mode: str,
    apply_classes: set[int],
) -> list[dict[str, Any]]:
    output = clone_samples(samples)
    for image_index, sample in enumerate(output):
        fused_predictions: list[dict[str, Any]] = []
        for prediction_index, prediction in enumerate(sample["predictions"]):
            class_id = prediction["class_id"]
            support = support_by_candidate.get((image_index, prediction_index), {})
            if class_id in apply_classes:
                expert_score = support.get(class_id, 0.0)
                if expert_score < support_threshold:
                    continue
                if score_mode == "product":
                    prediction["confidence"] *= expert_score
                elif score_mode == "geometric":
                    prediction["confidence"] = math.sqrt(prediction["confidence"] * expert_score)
            elif rescue_threshold is not None and class_id in RESCUE_SOURCE:
                target_class = RESCUE_SOURCE[class_id]
                if target_class not in apply_classes:
                    fused_predictions.append(prediction)
                    continue
                expert_score = support.get(target_class, 0.0)
                other_score = support.get(10 if target_class == 8 else 8, 0.0)
                if expert_score >= rescue_threshold and expert_score >= other_score + 0.15:
                    prediction["class_id"] = target_class
                    prediction["confidence"] = math.sqrt(prediction["confidence"] * expert_score)
            fused_predictions.append(prediction)
        sample["predictions"] = fused_predictions
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a crop-level weak-class expert reranker.")
    parser.add_argument("--main-model", type=Path, required=True)
    parser.add_argument("--expert", action="append", required=True, help="name=path_to_expert_model")
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="0")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--expert-image-size", type=int, default=320)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--main-confidence", type=float, default=0.001)
    parser.add_argument("--candidate-confidence", type=float, default=0.05)
    parser.add_argument("--crop-expand", type=float, default=0.2)
    args = parser.parse_args()

    from ultralytics import YOLO

    main_path = args.main_model.expanduser().resolve(strict=True)
    image_list = args.images.expanduser().resolve(strict=True)
    image_paths = read_images(image_list)
    main_model = YOLO(str(main_path), task="detect")
    samples: list[dict[str, Any]] = []
    candidate_records: list[tuple[int, int, Image.Image]] = []
    main_results = main_model.predict(
        source=[str(path) for path in image_paths],
        imgsz=args.image_size,
        batch=args.batch,
        device=args.device,
        conf=args.main_confidence,
        iou=0.7,
        max_det=300,
        stream=True,
        verbose=False,
        save=False,
    )
    for image_index, (image_path, result) in enumerate(zip(image_paths, main_results)):
        predictions = prediction_rows(result)
        width, height = result.orig_shape[1], result.orig_shape[0]
        sample = {
            "image": str(image_path),
            "ground_truth": parse_ground_truth(label_path(image_path), width, height),
            "predictions": predictions,
        }
        samples.append(sample)
        candidate_indexes = [
            index for index, prediction in enumerate(predictions)
            if prediction["class_id"] in {*TARGET_CLASSES, *RESCUE_SOURCE}
            and prediction["confidence"] >= args.candidate_confidence
        ]
        if candidate_indexes:
            with Image.open(image_path) as image:
                image = image.convert("RGB")
                for prediction_index in candidate_indexes:
                    candidate_records.append(
                        (
                            image_index,
                            prediction_index,
                            crop_box(image, predictions[prediction_index]["bbox"], args.crop_expand),
                        )
                    )

    baseline_metrics = metrics(samples)
    baseline_f1 = {str(class_id): best_f1(samples, class_id) for class_id in TARGET_CLASSES}
    expert_results: dict[str, Any] = {}
    for entry in args.expert:
        name, raw_path = entry.split("=", 1)
        expert_path = Path(raw_path).expanduser().resolve(strict=True)
        expert_model = YOLO(str(expert_path), task="detect")
        support_by_candidate: dict[tuple[int, int], dict[int, float]] = {}
        crops = [np.asarray(record[2]) for record in candidate_records]
        for start in range(0, len(crops), args.batch):
            batch_records = candidate_records[start : start + args.batch]
            batch_crops = crops[start : start + args.batch]
            predictions = expert_model.predict(
                source=batch_crops,
                imgsz=args.expert_image_size,
                batch=args.batch,
                device=args.device,
                conf=0.001,
                iou=0.7,
                max_det=20,
                verbose=False,
                save=False,
            )
            for record, result in zip(batch_records, predictions):
                support = {8: 0.0, 10: 0.0}
                for prediction in prediction_rows(result):
                    official_class = EXPERT_TO_OFFICIAL.get(prediction["class_id"])
                    if official_class is not None:
                        support[official_class] = max(support[official_class], prediction["confidence"])
                support_by_candidate[(record[0], record[1])] = support

        candidates: list[dict[str, Any]] = []
        for apply_classes in ({8, 10}, {8}, {10}):
            for score_mode in ("keep", "product", "geometric"):
                for support_threshold in (0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70):
                    for rescue_threshold in (None, 0.60, 0.70, 0.80, 0.90):
                        fused_samples = fuse(
                            samples,
                            support_by_candidate,
                            support_threshold,
                            rescue_threshold,
                            score_mode,
                            apply_classes,
                        )
                        fused_metrics = metrics(
                            fused_samples,
                            baseline=baseline_metrics,
                            changed_classes={8, 10, 13, 15},
                        )
                        candidates.append(
                            {
                                "apply_classes": sorted(apply_classes),
                                "score_mode": score_mode,
                                "support_threshold": support_threshold,
                                "rescue_threshold": rescue_threshold,
                                "metrics": fused_metrics,
                                "best_f1": {
                                    str(class_id): best_f1(fused_samples, class_id) for class_id in TARGET_CLASSES
                                },
                            }
                        )
        acceptable = [
            row for row in candidates
            if row["metrics"]["per_class"][8]["map50_95"] >= baseline_metrics["per_class"][8]["map50_95"]
            and row["metrics"]["per_class"][10]["map50_95"] >= baseline_metrics["per_class"][10]["map50_95"]
            and row["metrics"]["map50_95"] >= baseline_metrics["map50_95"]
        ]
        ranking_key = lambda row: (
            row["metrics"]["weak_map50_95"],
            row["metrics"]["map50_95"],
            row["best_f1"]["8"]["f1"] + row["best_f1"]["10"]["f1"],
        )
        expert_results[name] = {
            "model": {"path": str(expert_path), "sha256": sha256(expert_path)},
            "candidate_crop_count": len(candidate_records),
            "acceptable_count": len(acceptable),
            "best_acceptable": max(acceptable, key=ranking_key) if acceptable else None,
            "best_unconstrained": max(candidates, key=ranking_key),
            "top_candidates": sorted(candidates, key=ranking_key, reverse=True)[:10],
        }

    payload = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "main_model": {"path": str(main_path), "sha256": sha256(main_path)},
        "image_list": str(image_list),
        "image_count": len(samples),
        "candidate_crop_count": len(candidate_records),
        "configuration": {
            "device": args.device,
            "image_size": args.image_size,
            "expert_image_size": args.expert_image_size,
            "batch": args.batch,
            "main_confidence": args.main_confidence,
            "candidate_confidence": args.candidate_confidence,
            "crop_expand": args.crop_expand,
        },
        "baseline": {"metrics": baseline_metrics, "best_f1": baseline_f1},
        "experts": expert_results,
        "environment": {"python": platform.python_version()},
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "output": str(output),
        "baseline_weak_map50_95": baseline_metrics["weak_map50_95"],
        "experts": {
            name: {
                "acceptable_count": result["acceptable_count"],
                "best_acceptable_weak_map50_95": (
                    result["best_acceptable"]["metrics"]["weak_map50_95"] if result["best_acceptable"] else None
                ),
                "best_unconstrained_weak_map50_95": result["best_unconstrained"]["metrics"]["weak_map50_95"],
            }
            for name, result in expert_results.items()
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
