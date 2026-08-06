from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


BACKGROUND = -1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_iou(left: list[float], right: list[float]) -> float:
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def label_path(image_path: Path) -> Path:
    text = str(image_path)
    if "/images/" in text:
        text = text.replace("/images/", "/labels/", 1)
    elif "\\images\\" in text:
        text = text.replace("\\images\\", "\\labels\\", 1)
    return Path(text).with_suffix(".txt")


def parse_label(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        class_id, cx, cy, width, height = map(float, parts)
        rows.append(
            {
                "class_id": int(class_id),
                "bbox_norm": [cx, cy, width, height],
            }
        )
    return rows


def norm_to_xyxy(box: list[float], width: int, height: int) -> list[float]:
    cx, cy, box_width, box_height = box
    return [
        (cx - box_width / 2) * width,
        (cy - box_height / 2) * height,
        (cx + box_width / 2) * width,
        (cy + box_height / 2) * height,
    ]


def read_images(path: Path) -> list[Path]:
    return [Path(line.strip()) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in value)


def prediction_rows(result: Any) -> list[dict[str, Any]]:
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return []
    xyxy = boxes.xyxy.detach().cpu().tolist()
    confidence = boxes.conf.detach().cpu().tolist()
    classes = boxes.cls.detach().cpu().tolist()
    return [
        {
            "class_id": int(class_id),
            "confidence": float(score),
            "bbox": [float(value) for value in coordinates],
        }
        for coordinates, score, class_id in zip(xyxy, confidence, classes)
    ]


def class_agnostic_confusion(
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    iou_threshold: float,
    class_count: int,
) -> tuple[list[list[int]], list[dict[str, Any]]]:
    matrix = [[0 for _ in range(class_count + 1)] for _ in range(class_count + 1)]
    pairs: list[dict[str, Any]] = []
    candidates = [
        (
            image_iou(gt["bbox"], prediction["bbox"]),
            gt_index,
            prediction_index,
        )
        for gt_index, gt in enumerate(ground_truth)
        for prediction_index, prediction in enumerate(predictions)
    ]
    candidates.sort(reverse=True)
    matched_gt: set[int] = set()
    matched_predictions: set[int] = set()
    for overlap, gt_index, prediction_index in candidates:
        if overlap < iou_threshold or gt_index in matched_gt or prediction_index in matched_predictions:
            continue
        matched_gt.add(gt_index)
        matched_predictions.add(prediction_index)
        gt = ground_truth[gt_index]
        prediction = predictions[prediction_index]
        matrix[prediction["class_id"]][gt["class_id"]] += 1
        pairs.append(
            {
                "gt_index": gt_index,
                "prediction_index": prediction_index,
                "actual_class": gt["class_id"],
                "predicted_class": prediction["class_id"],
                "iou": overlap,
                "confidence": prediction["confidence"],
            }
        )
    for gt_index, gt in enumerate(ground_truth):
        if gt_index not in matched_gt:
            matrix[class_count][gt["class_id"]] += 1
            pairs.append(
                {
                    "gt_index": gt_index,
                    "prediction_index": None,
                    "actual_class": gt["class_id"],
                    "predicted_class": BACKGROUND,
                    "iou": 0.0,
                    "confidence": 0.0,
                }
            )
    for prediction_index, prediction in enumerate(predictions):
        if prediction_index not in matched_predictions:
            matrix[prediction["class_id"]][class_count] += 1
            pairs.append(
                {
                    "gt_index": None,
                    "prediction_index": prediction_index,
                    "actual_class": BACKGROUND,
                    "predicted_class": prediction["class_id"],
                    "iou": 0.0,
                    "confidence": prediction["confidence"],
                }
            )
    return matrix, pairs


def target_metrics(
    samples: list[dict[str, Any]],
    class_id: int,
    threshold: float,
    iou_threshold: float,
) -> dict[str, float | int]:
    true_positive = false_positive = false_negative = 0
    for sample in samples:
        gt = [item for item in sample["ground_truth"] if item["class_id"] == class_id]
        predictions = [
            item for item in sample["predictions"] if item["confidence"] >= threshold
        ]
        matched_gt: set[int] = set()
        matched_predictions: set[int] = set()
        candidates = [
            (
                image_iou(target["bbox"], prediction["bbox"]),
                gt_index,
                prediction_index,
            )
            for gt_index, target in enumerate(gt)
            for prediction_index, prediction in enumerate(predictions)
            if prediction["class_id"] == class_id
        ]
        candidates.sort(reverse=True)
        for overlap, gt_index, prediction_index in candidates:
            if overlap < iou_threshold or gt_index in matched_gt or prediction_index in matched_predictions:
                continue
            matched_gt.add(gt_index)
            matched_predictions.add(prediction_index)
        true_positive += len(matched_gt)
        false_negative += len(gt) - len(matched_gt)
        false_positive += sum(
            1
            for index, prediction in enumerate(predictions)
            if prediction["class_id"] == class_id and index not in matched_predictions
        )
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "class_id": class_id,
        "threshold": threshold,
        "tp": true_positive,
        "fp": false_positive,
        "fn": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def hard_sample_rows(
    samples: list[dict[str, Any]],
    class_ids: set[int],
    threshold: float,
    iou_threshold: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sample in samples:
        gt = sample["ground_truth"]
        predictions = [item for item in sample["predictions"] if item["confidence"] >= threshold]
        _, pairs = class_agnostic_confusion(gt, predictions, iou_threshold, sample["class_count"])
        target_gt = [item for item in gt if item["class_id"] in class_ids]
        target_predictions = [item for item in predictions if item["class_id"] in class_ids]
        for target in target_gt:
            overlaps = [
                (
                    image_iou(target["bbox"], prediction["bbox"]),
                    prediction,
                )
                for prediction in predictions
            ]
            overlaps.sort(reverse=True, key=lambda item: item[0])
            best_iou = overlaps[0][0] if overlaps else 0.0
            best_prediction = overlaps[0][1] if overlaps else None
            reason = None
            if best_prediction is None or best_iou < iou_threshold:
                reason = "missed_or_low_iou"
            elif best_prediction["class_id"] != target["class_id"]:
                reason = "wrong_class_confusion"
            elif best_prediction["confidence"] < threshold:
                reason = "low_confidence"
            if reason:
                rows.append(
                    {
                        "split": sample["split"],
                        "image": sample["image"],
                        "target_class": target["class_id"],
                        "reason": reason,
                        "best_iou": best_iou,
                        "best_prediction_class": best_prediction["class_id"] if best_prediction else None,
                        "best_prediction_confidence": best_prediction["confidence"] if best_prediction else 0.0,
                        "ground_truth_count": len(gt),
                        "target_prediction_count": len(target_predictions),
                        "predictions": predictions,
                        "pairs": pairs,
                    }
                )
        for prediction in target_predictions:
            overlaps = [image_iou(prediction["bbox"], target["bbox"]) for target in target_gt]
            if not overlaps or max(overlaps) < iou_threshold:
                rows.append(
                    {
                        "split": sample["split"],
                        "image": sample["image"],
                        "target_class": prediction["class_id"],
                        "reason": "false_positive",
                        "best_iou": max(overlaps) if overlaps else 0.0,
                        "best_prediction_class": prediction["class_id"],
                        "best_prediction_confidence": prediction["confidence"],
                        "ground_truth_count": len(gt),
                        "target_prediction_count": len(target_predictions),
                        "predictions": predictions,
                        "pairs": pairs,
                    }
                )
    return rows


def aggregate_matrix(matrices: Iterable[list[list[int]]], size: int) -> list[list[int]]:
    output = [[0 for _ in range(size)] for _ in range(size)]
    for matrix in matrices:
        for row in range(size):
            for column in range(size):
                output[row][column] += int(matrix[row][column])
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit weak classes with confusion, thresholds, and hard samples.")
    parser.add_argument("model", type=Path)
    parser.add_argument("--dataset", action="append", required=True, help="split_name=path_to_image_list")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--classes", default="8,10")
    parser.add_argument("--device", default="0")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--prediction-confidence", type=float, default=0.001)
    parser.add_argument("--operating-threshold", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--max-det", type=int, default=300)
    parser.add_argument("--contact-sheet-dir", type=Path)
    args = parser.parse_args()

    from ultralytics import YOLO

    model_path = args.model.expanduser().resolve(strict=True)
    model = YOLO(str(model_path), task="detect")
    names = model.names
    class_count = len(names)
    class_ids = {int(value) for value in args.classes.split(",") if value.strip()}
    split_paths: list[tuple[str, Path]] = []
    for entry in args.dataset:
        if "=" not in entry:
            raise ValueError(f"dataset must be name=path: {entry}")
        name, path = entry.split("=", 1)
        split_paths.append((name, Path(path).expanduser().resolve(strict=True)))

    all_samples: list[dict[str, Any]] = []
    split_results: dict[str, Any] = {}
    prediction_kwargs = {
        "imgsz": args.image_size,
        "batch": args.batch,
        "device": args.device,
        "conf": args.prediction_confidence,
        "iou": 0.7,
        "max_det": args.max_det,
        "stream": True,
        "verbose": False,
        "save": False,
    }
    for split, list_path in split_paths:
        image_paths = read_images(list_path)
        samples: list[dict[str, Any]] = []
        for image_path, result in zip(image_paths, model.predict(source=[str(path) for path in image_paths], **prediction_kwargs)):
            image_width, image_height = result.orig_shape[1], result.orig_shape[0]
            ground_truth = parse_label(label_path(image_path))
            for item in ground_truth:
                item["bbox"] = norm_to_xyxy(item.pop("bbox_norm"), image_width, image_height)
            predictions = prediction_rows(result)
            samples.append(
                {
                    "split": split,
                    "image": str(image_path),
                    "ground_truth": ground_truth,
                    "predictions": predictions,
                    "class_count": class_count,
                }
            )
        all_samples.extend(samples)
        thresholds = [round(0.05 * index, 2) for index in range(1, 20)]
        threshold_rows = {
            str(class_id): [target_metrics(samples, class_id, threshold, args.iou) for threshold in thresholds]
            for class_id in sorted(class_ids)
        }
        best_rows = {}
        for class_id, rows in threshold_rows.items():
            best_rows[class_id] = max(rows, key=lambda row: (row["f1"], row["recall"], -row["threshold"]))
        matrices = []
        for sample in samples:
            matrix, _ = class_agnostic_confusion(
                sample["ground_truth"],
                [item for item in sample["predictions"] if item["confidence"] >= args.operating_threshold],
                args.iou,
                class_count,
            )
            matrices.append(matrix)
        hard = hard_sample_rows(samples, class_ids, args.operating_threshold, args.iou)
        split_results[split] = {
            "image_count": len(samples),
            "ground_truth_counts": dict(Counter(item["class_id"] for sample in samples for item in sample["ground_truth"])),
            "prediction_counts_at_operating_threshold": dict(
                Counter(
                    item["class_id"]
                    for sample in samples
                    for item in sample["predictions"]
                    if item["confidence"] >= args.operating_threshold
                )
            ),
            "thresholds": thresholds,
            "threshold_scan": threshold_rows,
            "best_threshold": best_rows,
            "confusion_matrix": {
                "axis": "rows=predicted, columns=actual; final index=background",
                "labels": [*(names[index] for index in range(class_count)), "background"],
                "matrix": aggregate_matrix(matrices, class_count + 1),
            },
            "hard_sample_count": len(hard),
            "hard_samples": hard,
        }

    overall_thresholds = [round(0.05 * index, 2) for index in range(1, 20)]
    overall_scan = {
        str(class_id): [target_metrics(all_samples, class_id, threshold, args.iou) for threshold in overall_thresholds]
        for class_id in sorted(class_ids)
    }
    overall_best = {
        class_id: max(rows, key=lambda row: (row["f1"], row["recall"], -row["threshold"]))
        for class_id, rows in overall_scan.items()
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "model": {
            "path": str(model_path),
            "sha256": sha256(model_path),
            "size_bytes": model_path.stat().st_size,
        },
        "configuration": {
            "classes": sorted(class_ids),
            "image_size": args.image_size,
            "batch": args.batch,
            "device": args.device,
            "prediction_confidence": args.prediction_confidence,
            "operating_threshold": args.operating_threshold,
            "iou": args.iou,
        },
        "class_names": {str(index): names[index] for index in range(class_count)},
        "overall_threshold_scan": overall_scan,
        "overall_best_threshold": overall_best,
        "splits": split_results,
        "environment": {
            "python": platform.python_version(),
            "ultralytics": getattr(__import__("ultralytics"), "__version__", None),
        },
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    hard_rows = []
    for split, result in split_results.items():
        for row in result["hard_samples"]:
            hard_rows.append(
                {
                    "split": split,
                    "image": row["image"],
                    "target_class": row["target_class"],
                    "reason": row["reason"],
                    "best_iou": row["best_iou"],
                    "best_prediction_class": row["best_prediction_class"],
                    "best_prediction_confidence": row["best_prediction_confidence"],
                    "ground_truth_count": row["ground_truth_count"],
                    "target_prediction_count": row["target_prediction_count"],
                }
            )
    csv_path = output.with_suffix(".hard-samples.csv")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(hard_rows[0]) if hard_rows else ["split", "image", "target_class", "reason"])
        writer.writeheader()
        writer.writerows(hard_rows)
    print(json.dumps({"output": str(output), "hard_samples_csv": str(csv_path), "overall_best_threshold": overall_best}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
