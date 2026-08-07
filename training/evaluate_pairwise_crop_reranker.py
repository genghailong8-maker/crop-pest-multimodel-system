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
    iou,
    label_path,
    metrics,
    parse_ground_truth,
    prediction_rows,
    read_images,
    sha256,
)


CLASSIFIER_TO_OFFICIAL = {0: 10, 1: 13, 2: 99}
TARGET_CLASSES = {10, 13}
CHANGED_CLASSES = {10, 13}
CONFIG_KEYS = (
    "reclassify", "target_threshold", "target_margin",
    "background_threshold", "background_margin", "score_mode",
)


def collect(
    main_model: Any,
    classifier: Any,
    image_list: Path,
    device: str,
    image_size: int,
    classifier_image_size: int,
    batch: int,
    candidate_confidence: float,
    crop_expand: float,
) -> tuple[list[dict[str, Any]], dict[tuple[int, int], dict[int, float]], int]:
    image_paths = read_images(image_list)
    samples: list[dict[str, Any]] = []
    candidate_records: list[tuple[int, int, Image.Image]] = []
    for start in range(0, len(image_paths), batch):
        batch_paths = image_paths[start : start + batch]
        results = main_model.predict(
            source=[str(path) for path in batch_paths],
            imgsz=image_size,
            batch=len(batch_paths),
            device=device,
            conf=0.001,
            iou=0.7,
            max_det=300,
            verbose=False,
            save=False,
        )
        for image_index, (image_path, result) in enumerate(zip(batch_paths, results), start=start):
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
                if prediction["class_id"] in TARGET_CLASSES
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
            batch=len(records),
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
    reclassify: bool,
    target_threshold: float,
    target_margin: float,
    background_threshold: float,
    background_margin: float,
    score_mode: str,
) -> list[dict[str, Any]]:
    output = clone_samples(samples)
    for image_index, sample in enumerate(output):
        retained: list[dict[str, Any]] = []
        for prediction_index, prediction in enumerate(sample["predictions"]):
            original_class = prediction["class_id"]
            probabilities = support.get((image_index, prediction_index))
            if original_class not in TARGET_CLASSES or not probabilities:
                retained.append(prediction)
                continue
            background_score = probabilities.get(99, 0.0)
            target_scores = {class_id: probabilities.get(class_id, 0.0) for class_id in TARGET_CLASSES}
            best_target, best_target_score = max(target_scores.items(), key=lambda item: item[1])
            if (
                background_score >= background_threshold
                and background_score >= best_target_score + background_margin
            ):
                continue
            final_class = original_class
            if (
                reclassify
                and best_target != original_class
                and best_target_score >= target_threshold
                and best_target_score >= target_scores[original_class] + target_margin
            ):
                final_class = best_target
                prediction["class_id"] = best_target
            score = target_scores.get(final_class, 0.0)
            if score_mode == "product":
                prediction["confidence"] *= score
            elif score_mode == "geometric":
                prediction["confidence"] = math.sqrt(prediction["confidence"] * score)
            retained.append(prediction)
        sample["predictions"] = retained
    return output


def acceptable(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
    baseline_f1: dict[str, dict[str, Any]],
    min_weak_gain: float,
) -> bool:
    per_class = candidate["metrics"]["per_class"]
    base = baseline["per_class"]
    return (
        per_class[8]["map50_95"] >= base[8]["map50_95"]
        and per_class[10]["map50_95"] >= base[10]["map50_95"]
        and per_class[13]["map50_95"] >= base[13]["map50_95"]
        and per_class[15]["map50_95"] >= base[15]["map50_95"]
        and candidate["metrics"]["map50_95"] >= baseline["map50_95"]
        and candidate["metrics"]["weak_map50_95"] >= baseline["weak_map50_95"] + min_weak_gain
        and candidate["best_f1"]["8"]["f1"] >= baseline_f1["8"]["f1"]
        and candidate["best_f1"]["10"]["f1"] >= baseline_f1["10"]["f1"]
    )


def evaluate(samples: list[dict[str, Any]], support: dict[tuple[int, int], dict[int, float]], config: dict, baseline: dict) -> dict:
    fused = fuse(samples, support, **config)
    result = {
        **config,
        "metrics": metrics(fused, baseline=baseline, changed_classes=CHANGED_CLASSES),
        "best_f1": {str(class_id): best_f1(fused, class_id) for class_id in (8, 10)},
    }
    return result


def config_from_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Extract only fuse() arguments from an evaluated candidate row."""
    return {key: row[key] for key in CONFIG_KEYS} if row else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a 10/13/background crop classifier reranker.")
    parser.add_argument("--main-model", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--tune-images", type=Path, required=True)
    parser.add_argument("--eval-images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="0")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--classifier-image-size", type=int, default=320)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--candidate-confidence", type=float, default=0.05)
    parser.add_argument("--crop-expand", type=float, default=0.5)
    parser.add_argument("--min-weak-gain", type=float, default=0.00001)
    args = parser.parse_args()

    from ultralytics import YOLO

    main_path = args.main_model.expanduser().resolve(strict=True)
    classifier_path = args.classifier.expanduser().resolve(strict=True)
    tune_list = args.tune_images.expanduser().resolve(strict=True)
    eval_list = args.eval_images.expanduser().resolve(strict=True)
    main_model = YOLO(str(main_path), task="detect")
    classifier = YOLO(str(classifier_path), task="classify")

    tune_samples, tune_support, tune_crops = collect(
        main_model, classifier, tune_list, args.device, args.image_size,
        args.classifier_image_size, args.batch, args.candidate_confidence, args.crop_expand,
    )
    tune_baseline = metrics(tune_samples)
    tune_baseline_f1 = {str(class_id): best_f1(tune_samples, class_id) for class_id in (8, 10)}
    candidates: list[dict[str, Any]] = []
    # Keep the strongest configuration even when no row passes the strict
    # non-regression gate.  This makes a failed tune actionable: we can see
    # whether the expert is promising but needs calibration, or is simply
    # hurting the frozen baseline.
    ranking = lambda row: (
        row["metrics"]["weak_map50_95"],
        row["metrics"]["map50_95"],
        row["best_f1"]["8"]["f1"] + row["best_f1"]["10"]["f1"],
    )
    best_unconstrained: dict[str, Any] | None = None
    best_reclassify: dict[str, Any] | None = None
    for reclassify in (False, True):
        target_thresholds = (0.35, 0.50, 0.60, 0.70, 0.80, 0.90) if reclassify else (0.0,)
        target_margins = (0.0, 0.10, 0.20, 0.30) if reclassify else (0.0,)
        for score_mode in ("keep", "product", "geometric"):
            for target_threshold in target_thresholds:
                for target_margin in target_margins:
                    for background_threshold in (0.35, 0.50, 0.60, 0.70, 0.80, 0.90):
                        for background_margin in (0.0, 0.10, 0.20):
                            config = {
                                "reclassify": reclassify,
                                "target_threshold": target_threshold,
                                "target_margin": target_margin,
                                "background_threshold": background_threshold,
                                "background_margin": background_margin,
                                "score_mode": score_mode,
                            }
                            row = evaluate(tune_samples, tune_support, config, tune_baseline)
                            if best_unconstrained is None or ranking(row) > ranking(best_unconstrained):
                                best_unconstrained = row
                            if reclassify and (
                                best_reclassify is None or ranking(row) > ranking(best_reclassify)
                            ):
                                best_reclassify = row
                            if acceptable(row, tune_baseline, tune_baseline_f1, args.min_weak_gain):
                                candidates.append(row)
    selected = max(candidates, key=ranking) if candidates else None

    eval_samples, eval_support, eval_crops = collect(
        main_model, classifier, eval_list, args.device, args.image_size,
        args.classifier_image_size, args.batch, args.candidate_confidence, args.crop_expand,
    )
    eval_baseline = metrics(eval_samples)
    eval_baseline_f1 = {str(class_id): best_f1(eval_samples, class_id) for class_id in (8, 10)}
    eval_result = (
        evaluate(eval_samples, eval_support, config_from_row(selected), eval_baseline)
        if selected else None
    )
    # Also score the best tuning row on the frozen set for diagnosis.  This
    # is never eligible for deployment by itself; it only tells us whether a
    # failed tune is caused by overfitting or by a generally harmful expert.
    unconstrained_eval_result = (
        evaluate(eval_samples, eval_support, config_from_row(best_unconstrained), eval_baseline)
        if best_unconstrained else None
    )
    unconstrained_frozen_acceptable = bool(
        unconstrained_eval_result
        and acceptable(
            unconstrained_eval_result, eval_baseline, eval_baseline_f1, args.min_weak_gain
        )
    )
    reclassify_eval_result = (
        evaluate(eval_samples, eval_support, config_from_row(best_reclassify), eval_baseline)
        if best_reclassify else None
    )
    reclassify_frozen_acceptable = bool(
        reclassify_eval_result
        and acceptable(reclassify_eval_result, eval_baseline, eval_baseline_f1, args.min_weak_gain)
    )
    frozen_acceptable = bool(
        eval_result and acceptable(eval_result, eval_baseline, eval_baseline_f1, args.min_weak_gain)
    )
    payload = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "main_model": {"path": str(main_path), "sha256": sha256(main_path)},
        "classifier": {"path": str(classifier_path), "sha256": sha256(classifier_path)},
        "configuration": vars(args) | {
            "main_model": str(main_path), "classifier": str(classifier_path),
            "tune_images": str(tune_list), "eval_images": str(eval_list), "output": str(args.output),
        },
        "tuning": {
            "image_count": len(tune_samples), "candidate_crops": tune_crops,
            "image_list": str(tune_list), "image_list_sha256": sha256(tune_list),
            "baseline": tune_baseline, "baseline_best_f1": tune_baseline_f1,
            "acceptable_count": len(candidates), "selected": selected,
            "best_unconstrained": best_unconstrained,
            "best_reclassify": best_reclassify,
        },
        "frozen_official_evaluation": {
            "image_count": len(eval_samples), "candidate_crops": eval_crops,
            "image_list": str(eval_list), "image_list_sha256": sha256(eval_list),
            "baseline": eval_baseline, "baseline_best_f1": eval_baseline_f1,
            "result": eval_result, "acceptable": frozen_acceptable,
            "best_unconstrained_result": unconstrained_eval_result,
            "best_unconstrained_acceptable": unconstrained_frozen_acceptable,
            "best_reclassify_result": reclassify_eval_result,
            "best_reclassify_acceptable": reclassify_frozen_acceptable,
        },
        "decision": "eligible_for_shadow_test" if frozen_acceptable else "keep_current_main_model",
        "environment": {"python": platform.python_version()},
    }
    payload["configuration"] = {
        key: str(value) if isinstance(value, Path) else value for key, value in payload["configuration"].items()
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output), "tune_acceptable_count": len(candidates),
        "selected": selected and {key: selected[key] for key in selected if key not in {"metrics", "best_f1"}},
        "frozen_acceptable": frozen_acceptable, "decision": payload["decision"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
