"""Train and rank the six Phase 9 detector candidates on one development split."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


MODEL_SPECS = (
    ("yolo26n", "yolo26n.pt", 32),
    ("yolo26s", "yolo26s.pt", 32),
    ("yolo11s", "yolo11s.pt", 32),
    ("yolo12s", "yolo12s.pt", 32),
    ("yolov8s", "yolov8s.pt", 32),
    ("yolov5su", "yolov5su.pt", 32),
)
WEAK_CLASS_IDS = (8, 10, 13, 15)


def summarize_metrics(name: str, metrics: dict[str, object]) -> dict[str, object]:
    class_maps = [float(value) for value in metrics["class_map50_95"]]
    if len(class_maps) != 16:
        raise ValueError(f"{name} 的逐类指标数量不是 16")
    weak_mean = sum(class_maps[index] for index in WEAK_CLASS_IDS) / len(WEAK_CLASS_IDS)
    overall = float(metrics["map50_95"])
    return {
        "name": name,
        "map50_95": overall,
        "map50": float(metrics["map50"]),
        "precision": float(metrics["precision_mean"]),
        "recall": float(metrics["recall_mean"]),
        "weak_map50_95": weak_mean,
        "selection_score": 0.7 * overall + 0.3 * weak_mean,
        "class_map50_95": class_maps,
        "best_weights": metrics["best_weights"],
        "training_arguments": metrics["training_arguments"],
    }


def write_report(path: Path, completed: list[dict[str, object]], failures: list[dict[str, object]]) -> None:
    ranked = sorted(completed, key=lambda item: (item["selection_score"], item["recall"]), reverse=True)
    report = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection_formula": "0.7 * map50_95 + 0.3 * mean(class 8,10,13,15 map50_95)",
        "official_frozen_used_for_selection": False,
        "completed": ranked,
        "failures": failures,
        "provisional_winner": ranked[0]["name"] if ranked else None,
        "tie_requires_runtime_benchmark": bool(
            len(ranked) > 1 and float(ranked[0]["selection_score"]) - float(ranked[1]["selection_score"]) <= 0.005
        ),
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20260729)
    args = parser.parse_args()

    project = args.project_root.resolve()
    data = args.data.resolve()
    runs = args.runs_root.resolve()
    runs.mkdir(parents=True, exist_ok=True)
    report_path = runs / "search-results.json"
    train_script = project / "training" / "train_detector.py"
    completed: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    for name, checkpoint, batch in MODEL_SPECS:
        run_name = f"phase9-{name}-e{args.epochs}-b{batch}"
        run_dir = runs / run_name
        metrics_path = run_dir / "competition-metrics.json"
        if metrics_path.is_file():
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            completed.append(summarize_metrics(name, metrics))
            write_report(report_path, completed, failures)
            continue

        log_path = runs / f"{run_name}.log"
        command = [
            sys.executable,
            str(train_script),
            "--data", str(data),
            "--model", checkpoint,
            "--epochs", str(args.epochs),
            "--image-size", "640",
            "--batch", str(batch),
            "--device", "0",
            "--workers", "4",
            "--seed", str(args.seed),
            "--patience", str(args.epochs),
            "--project", str(runs),
            "--name", run_name,
        ]
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run(command, cwd=project, stdout=log, stderr=subprocess.STDOUT, check=False)

        if result.returncode != 0 and name == "yolo12s" and batch == 32:
            fallback_name = f"phase9-{name}-e{args.epochs}-b16"
            fallback_dir = runs / fallback_name
            fallback_metrics = fallback_dir / "competition-metrics.json"
            fallback_log = runs / f"{fallback_name}.log"
            fallback_command = command.copy()
            fallback_command[fallback_command.index("--batch") + 1] = "16"
            fallback_command[fallback_command.index("--name") + 1] = fallback_name
            with fallback_log.open("w", encoding="utf-8") as log:
                result = subprocess.run(fallback_command, cwd=project, stdout=log, stderr=subprocess.STDOUT, check=False)
            metrics_path = fallback_metrics
            log_path = fallback_log

        if result.returncode != 0 or not metrics_path.is_file():
            failures.append({"name": name, "returncode": result.returncode, "log": str(log_path)})
        else:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            completed.append(summarize_metrics(name, metrics))
        write_report(report_path, completed, failures)

    if len(completed) != len(MODEL_SPECS):
        raise SystemExit(f"只有 {len(completed)}/{len(MODEL_SPECS)} 个候选完成，详见 {report_path}")
    print(report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
