from __future__ import annotations

import argparse
import json
import math
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evaluate_pairwise_crop_reranker import collect, fuse
from evaluate_weak_reranker import best_f1, clone_samples, metrics, sha256


CALIBRATED_CLASSES = (10, 13)
SCORE_MODES = ("keep", "product", "geometric")
TEMPERATURES = (0.75, 1.0, 1.25)
OPERATING_THRESHOLDS = (0.15, 0.25, 0.35, 0.45, 0.55, 0.65)


def config_grid() -> list[dict[str, Any]]:
    """A bounded, reproducible reranker grid for calibration."""
    configs: list[dict[str, Any]] = []
    for reclassify in (False, True):
        target_thresholds = (0.0,) if not reclassify else (0.50, 0.70, 0.90)
        target_margins = (0.0,) if not reclassify else (0.0, 0.10)
        for score_mode in SCORE_MODES:
            for target_threshold in target_thresholds:
                for target_margin in target_margins:
                    for background_threshold in (0.50, 0.70, 0.90):
                        for background_margin in (0.0, 0.10):
                            configs.append(
                                {
                                    "reclassify": reclassify,
                                    "target_threshold": target_threshold,
                                    "target_margin": target_margin,
                                    "background_threshold": background_threshold,
                                    "background_margin": background_margin,
                                    "score_mode": score_mode,
                                }
                            )
    return configs


def logit(value: float) -> float:
    value = min(max(value, 1e-6), 1.0 - 1e-6)
    return math.log(value / (1.0 - value))


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def calibrate(
    samples: list[dict[str, Any]],
    temperature10: float,
    temperature13: float,
    threshold10: float,
    threshold13: float,
) -> list[dict[str, Any]]:
    output = clone_samples(samples)
    temperatures = {10: temperature10, 13: temperature13}
    thresholds = {10: threshold10, 13: threshold13}
    for sample in output:
        retained: list[dict[str, Any]] = []
        for prediction in sample["predictions"]:
            class_id = prediction["class_id"]
            if class_id in CALIBRATED_CLASSES:
                prediction["confidence"] = sigmoid(logit(prediction["confidence"]) / temperatures[class_id])
                if prediction["confidence"] < thresholds[class_id]:
                    continue
            retained.append(prediction)
        sample["predictions"] = retained
    return output


def row_for(
    samples: list[dict[str, Any]],
    support: dict[tuple[int, int], dict[int, float]],
    config: dict[str, Any],
    temperature10: float,
    temperature13: float,
    threshold10: float,
    threshold13: float,
    baseline: dict[str, Any],
) -> dict[str, Any]:
    fused = fuse(samples, support, **config)
    calibrated = calibrate(fused, temperature10, temperature13, threshold10, threshold13)
    return {
        **config,
        "temperature10": temperature10,
        "temperature13": temperature13,
        "threshold10": threshold10,
        "threshold13": threshold13,
        "metrics": metrics(calibrated, baseline=baseline, changed_classes=set(CALIBRATED_CLASSES)),
        "best_f1": {str(class_id): best_f1(calibrated, class_id) for class_id in CALIBRATED_CLASSES},
    }


def ranking(row: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        row["metrics"]["weak_map50_95"],
        row["metrics"]["map50_95"],
        row["best_f1"]["10"]["f1"],
        row["best_f1"]["13"]["f1"],
    )


def acceptable(row: dict[str, Any], baseline: dict[str, Any], baseline_f1: dict[str, dict[str, Any]], min_gain: float) -> bool:
    per_class = row["metrics"]["per_class"]
    base = baseline["per_class"]
    return (
        per_class[10]["map50_95"] >= base[10]["map50_95"]
        and per_class[13]["map50_95"] >= base[13]["map50_95"]
        and row["metrics"]["map50_95"] >= baseline["map50_95"]
        and row["metrics"]["weak_map50_95"] >= baseline["weak_map50_95"] + min_gain
        and row["best_f1"]["10"]["f1"] >= baseline_f1["10"]["f1"]
        and row["best_f1"]["13"]["f1"] >= baseline_f1["13"]["f1"]
    )


def compact(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: value for key, value in row.items() if key not in {"metrics", "best_f1"}} | {
        "metrics": {
            "map50_95": row["metrics"]["map50_95"],
            "weak_map50_95": row["metrics"]["weak_map50_95"],
            "class10_map50_95": row["metrics"]["per_class"][10]["map50_95"],
            "class13_map50_95": row["metrics"]["per_class"][13]["map50_95"],
        },
        "best_f1": row["best_f1"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune independent class-10/13 temperatures and operating thresholds.")
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
    parser.add_argument("--top-configs", type=int, default=12)
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
        main_model,
        classifier,
        tune_list,
        args.device,
        args.image_size,
        args.classifier_image_size,
        args.batch,
        args.candidate_confidence,
        args.crop_expand,
    )
    tune_baseline = metrics(tune_samples)
    tune_baseline_f1 = {str(class_id): best_f1(tune_samples, class_id) for class_id in CALIBRATED_CLASSES}

    # First rank reranker configurations without class thresholds. Only the
    # strongest rows proceed to the more expensive temperature/threshold grid.
    uncalibrated = []
    for config in config_grid():
        uncalibrated.append(
            row_for(tune_samples, tune_support, config, 1.0, 1.0, 0.0, 0.0, tune_baseline)
        )
    top_configs = sorted(uncalibrated, key=ranking, reverse=True)[: max(1, args.top_configs)]

    candidates: list[dict[str, Any]] = []
    for row in top_configs:
        config = {key: row[key] for key in config_grid()[0]}
        for temperature10 in TEMPERATURES:
            for temperature13 in TEMPERATURES:
                for threshold10 in OPERATING_THRESHOLDS:
                    for threshold13 in OPERATING_THRESHOLDS:
                        candidates.append(
                            row_for(
                                tune_samples,
                                tune_support,
                                config,
                                temperature10,
                                temperature13,
                                threshold10,
                                threshold13,
                                tune_baseline,
                            )
                        )
    acceptable_rows = [
        row for row in candidates if acceptable(row, tune_baseline, tune_baseline_f1, args.min_weak_gain)
    ]
    selected = max(acceptable_rows, key=ranking) if acceptable_rows else None
    best_unconstrained = max(candidates, key=ranking) if candidates else None

    eval_samples, eval_support, eval_crops = collect(
        main_model,
        classifier,
        eval_list,
        args.device,
        args.image_size,
        args.classifier_image_size,
        args.batch,
        args.candidate_confidence,
        args.crop_expand,
    )
    eval_baseline = metrics(eval_samples)
    eval_baseline_f1 = {str(class_id): best_f1(eval_samples, class_id) for class_id in CALIBRATED_CLASSES}

    def frozen_result(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        config = {key: row[key] for key in config_grid()[0]}
        result = row_for(
            eval_samples,
            eval_support,
            config,
            row["temperature10"],
            row["temperature13"],
            row["threshold10"],
            row["threshold13"],
            eval_baseline,
        )
        return result

    selected_eval = frozen_result(selected)
    best_unconstrained_eval = frozen_result(best_unconstrained)
    frozen_acceptable = bool(
        selected_eval and acceptable(selected_eval, eval_baseline, eval_baseline_f1, args.min_weak_gain)
    )
    payload = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "main_model": {"path": str(main_path), "sha256": sha256(main_path)},
        "classifier": {"path": str(classifier_path), "sha256": sha256(classifier_path)},
        "configuration": {
            key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()
        },
        "tuning": {
            "image_count": len(tune_samples),
            "candidate_crops": tune_crops,
            "baseline": tune_baseline,
            "baseline_best_f1": tune_baseline_f1,
            "grid_config_count": len(config_grid()),
            "top_config_count": len(top_configs),
            "temperature_grid": TEMPERATURES,
            "operating_threshold_grid": OPERATING_THRESHOLDS,
            "calibration_candidate_count": len(candidates),
            "acceptable_count": len(acceptable_rows),
            "selected": compact(selected),
            "best_unconstrained": compact(best_unconstrained),
            "top_uncalibrated": [compact(row) for row in top_configs[:5]],
        },
        "frozen_official_evaluation": {
            "image_count": len(eval_samples),
            "candidate_crops": eval_crops,
            "baseline": eval_baseline,
            "baseline_best_f1": eval_baseline_f1,
            "selected": compact(selected_eval),
            "acceptable": frozen_acceptable,
            "best_unconstrained": compact(best_unconstrained_eval),
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
                "tune_acceptable_count": len(acceptable_rows),
                "selected": compact(selected),
                "frozen_acceptable": frozen_acceptable,
                "decision": payload["decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
