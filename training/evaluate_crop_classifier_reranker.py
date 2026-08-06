from __future__ import annotations

import argparse
import json
import math
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from evaluate_weak_reranker import (
    best_f1,
    clone_samples,
    crop_box,
    label_path,
    metrics,
    parse_ground_truth,
    prediction_rows,
    read_images,
    sha256,
)


CLASSIFIER_TO_OFFICIAL = {0: 8, 1: 10, 2: 13, 3: 15}
CANDIDATE_CLASSES = set(CLASSIFIER_TO_OFFICIAL.values())
TARGET_CLASSES = (8, 10)
SOURCE_CLASSES = (13, 15)


def collect_samples(
    main_model: Any,
    classifier: Any,
    image_list: Path,
    device: str,
    image_size: int,
    classifier_image_size: int,
    batch: int,
    main_confidence: float,
    candidate_confidence: float,
    crop_expand: float,
) -> tuple[list[dict[str, Any]], dict[tuple[int, int], dict[int, float]], int]:
    image_paths = read_images(image_list)
    samples: list[dict[str, Any]] = []
    candidate_records: list[tuple[int, int, Image.Image]] = []
    results = main_model.predict(
        source=[str(path) for path in image_paths],
        imgsz=image_size,
        batch=batch,
        device=device,
        conf=main_confidence,
        iou=0.7,
        max_det=300,
        stream=True,
        verbose=False,
        save=False,
    )
    for image_index, (image_path, result) in enumerate(zip(image_paths, results)):
        predictions = prediction_rows(result)
        width, height = result.orig_shape[1], result.orig_shape[0]
        samples.append(
            {
                "image": str(image_path),
                "ground_truth": parse_ground_truth(label_path(image_path), width, height),
                "predictions": predictions,
            }
        )
        indexes = [
            index
            for index, prediction in enumerate(predictions)
            if prediction["class_id"] in CANDIDATE_CLASSES
            and prediction["confidence"] >= candidate_confidence
        ]
        if indexes:
            with Image.open(image_path) as image:
                image = image.convert("RGB")
                for prediction_index in indexes:
                    candidate_records.append(
                        (
                            image_index,
                            prediction_index,
                            crop_box(image, predictions[prediction_index]["bbox"], crop_expand),
                        )
                    )

    support: dict[tuple[int, int], dict[int, float]] = {}
    crops = [np.asarray(record[2]) for record in candidate_records]
    for start in range(0, len(crops), batch):
        records = candidate_records[start : start + batch]
        results = classifier.predict(
            source=crops[start : start + batch],
            imgsz=classifier_image_size,
            batch=batch,
            device=device,
            verbose=False,
            save=False,
        )
        for record, result in zip(records, results):
            probabilities = result.probs.data.detach().cpu().tolist()
            support[(record[0], record[1])] = {
                CLASSIFIER_TO_OFFICIAL[index]: float(probability)
                for index, probability in enumerate(probabilities)
            }
    return samples, support, len(candidate_records)


def fuse(
    samples: list[dict[str, Any]],
    support: dict[tuple[int, int], dict[int, float]],
    apply_classes: set[int],
    reclassify: bool,
    threshold: float,
    margin: float,
    score_mode: str,
) -> list[dict[str, Any]]:
    output = clone_samples(samples)
    for image_index, sample in enumerate(output):
        for prediction_index, prediction in enumerate(sample["predictions"]):
            original_class = prediction["class_id"]
            if original_class not in apply_classes:
                continue
            probabilities = support.get((image_index, prediction_index))
            if not probabilities:
                continue
            final_class = original_class
            if reclassify:
                top_class, top_score = max(probabilities.items(), key=lambda item: item[1])
                original_score = probabilities.get(original_class, 0.0)
                if (
                    top_class != original_class
                    and top_score >= threshold
                    and top_score >= original_score + margin
                ):
                    final_class = top_class
                    prediction["class_id"] = top_class
            classifier_score = probabilities.get(final_class, 0.0)
            if score_mode == "product":
                prediction["confidence"] *= classifier_score
            elif score_mode == "geometric":
                prediction["confidence"] = math.sqrt(prediction["confidence"] * classifier_score)
    return output


def acceptable(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
    baseline_f1: dict[str, dict[str, Any]],
    source_tolerance: float,
    min_weak_gain: float,
) -> bool:
    per_class = candidate["metrics"]["per_class"]
    baseline_per_class = baseline["per_class"]
    return (
        per_class[8]["map50_95"] >= baseline_per_class[8]["map50_95"]
        and per_class[10]["map50_95"] >= baseline_per_class[10]["map50_95"]
        and per_class[13]["map50_95"] >= baseline_per_class[13]["map50_95"] - source_tolerance
        and per_class[15]["map50_95"] >= baseline_per_class[15]["map50_95"] - source_tolerance
        and candidate["metrics"]["map50_95"] >= baseline["map50_95"]
        and candidate["metrics"]["weak_map50_95"] >= baseline["weak_map50_95"] + min_weak_gain
        and candidate["best_f1"]["8"]["f1"] >= baseline_f1["8"]["f1"]
        and candidate["best_f1"]["10"]["f1"] >= baseline_f1["10"]["f1"]
    )


def evaluate_configuration(
    samples: list[dict[str, Any]],
    support: dict[tuple[int, int], dict[int, float]],
    configuration: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    fused = fuse(
        samples,
        support,
        set(configuration["apply_classes"]),
        configuration["reclassify"],
        configuration["threshold"],
        configuration["margin"],
        configuration["score_mode"],
    )
    fused_metrics = metrics(fused, baseline=baseline, changed_classes=CANDIDATE_CLASSES)
    return {
        **configuration,
        "metrics": fused_metrics,
        "best_f1": {str(class_id): best_f1(fused, class_id) for class_id in TARGET_CLASSES},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune and evaluate a 4-class crop-classifier reranker.")
    parser.add_argument("--main-model", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--tune-images", type=Path, required=True)
    parser.add_argument("--eval-images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="0")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--classifier-image-size", type=int, default=224)
    parser.add_argument("--batch", type=int, default=128)
    parser.add_argument("--main-confidence", type=float, default=0.001)
    parser.add_argument("--candidate-confidence", type=float, default=0.05)
    parser.add_argument("--crop-expand", type=float, default=0.5)
    parser.add_argument("--source-tolerance", type=float, default=0.002)
    parser.add_argument("--min-weak-gain", type=float, default=0.00001)
    args = parser.parse_args()

    from ultralytics import YOLO

    main_path = args.main_model.expanduser().resolve(strict=True)
    classifier_path = args.classifier.expanduser().resolve(strict=True)
    tune_list = args.tune_images.expanduser().resolve(strict=True)
    eval_list = args.eval_images.expanduser().resolve(strict=True)
    main_model = YOLO(str(main_path), task="detect")
    classifier = YOLO(str(classifier_path), task="classify")

    tune_samples, tune_support, tune_crop_count = collect_samples(
        main_model,
        classifier,
        tune_list,
        args.device,
        args.image_size,
        args.classifier_image_size,
        args.batch,
        args.main_confidence,
        args.candidate_confidence,
        args.crop_expand,
    )
    tune_baseline = metrics(tune_samples)
    tune_baseline_f1 = {str(class_id): best_f1(tune_samples, class_id) for class_id in TARGET_CLASSES}
    candidates: list[dict[str, Any]] = []
    apply_presets = ({8}, {10}, {8, 10}, {8, 10, 13, 15})
    for apply_classes in apply_presets:
        for reclassify in (False, True):
            for score_mode in ("keep", "product", "geometric"):
                thresholds = (0.35, 0.50, 0.60, 0.70, 0.80, 0.90) if reclassify else (0.0,)
                margins = (0.0, 0.10, 0.20, 0.30) if reclassify else (0.0,)
                for threshold in thresholds:
                    for margin in margins:
                        configuration = {
                            "apply_classes": sorted(apply_classes),
                            "reclassify": reclassify,
                            "score_mode": score_mode,
                            "threshold": threshold,
                            "margin": margin,
                        }
                        row = evaluate_configuration(
                            tune_samples,
                            tune_support,
                            configuration,
                            tune_baseline,
                        )
                        if acceptable(
                            row,
                            tune_baseline,
                            tune_baseline_f1,
                            args.source_tolerance,
                            args.min_weak_gain,
                        ):
                            candidates.append(row)

    ranking_key = lambda row: (
        row["metrics"]["weak_map50_95"],
        row["metrics"]["map50_95"],
        row["best_f1"]["8"]["f1"] + row["best_f1"]["10"]["f1"],
    )
    selected = max(candidates, key=ranking_key) if candidates else None

    eval_samples, eval_support, eval_crop_count = collect_samples(
        main_model,
        classifier,
        eval_list,
        args.device,
        args.image_size,
        args.classifier_image_size,
        args.batch,
        args.main_confidence,
        args.candidate_confidence,
        args.crop_expand,
    )
    eval_baseline = metrics(eval_samples)
    eval_baseline_f1 = {str(class_id): best_f1(eval_samples, class_id) for class_id in TARGET_CLASSES}
    eval_result = (
        evaluate_configuration(eval_samples, eval_support, selected, eval_baseline)
        if selected is not None
        else None
    )
    frozen_acceptable = (
        acceptable(
            eval_result,
            eval_baseline,
            eval_baseline_f1,
            args.source_tolerance,
            args.min_weak_gain,
        )
        if eval_result is not None
        else False
    )
    payload = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "main_model": {"path": str(main_path), "sha256": sha256(main_path)},
        "classifier": {"path": str(classifier_path), "sha256": sha256(classifier_path)},
        "configuration": {
            "device": args.device,
            "image_size": args.image_size,
            "classifier_image_size": args.classifier_image_size,
            "batch": args.batch,
            "main_confidence": args.main_confidence,
            "candidate_confidence": args.candidate_confidence,
            "crop_expand": args.crop_expand,
            "source_tolerance": args.source_tolerance,
            "min_weak_gain": args.min_weak_gain,
        },
        "tuning": {
            "image_list": str(tune_list),
            "image_list_sha256": sha256(tune_list),
            "image_count": len(tune_samples),
            "candidate_crop_count": tune_crop_count,
            "acceptable_count": len(candidates),
            "baseline": tune_baseline,
            "baseline_best_f1": tune_baseline_f1,
            "selected": selected,
        },
        "frozen_official_evaluation": {
            "image_list": str(eval_list),
            "image_list_sha256": sha256(eval_list),
            "image_count": len(eval_samples),
            "candidate_crop_count": eval_crop_count,
            "baseline": eval_baseline,
            "baseline_best_f1": eval_baseline_f1,
            "result": eval_result,
            "acceptable": frozen_acceptable,
        },
        "decision": "eligible_for_shadow_test" if frozen_acceptable else "keep_current_main_model",
        "environment": {"python": platform.python_version()},
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "tune_acceptable_count": len(candidates),
                "selected": selected and {key: selected[key] for key in ("apply_classes", "reclassify", "score_mode", "threshold", "margin")},
                "frozen_acceptable": frozen_acceptable,
                "decision": payload["decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
