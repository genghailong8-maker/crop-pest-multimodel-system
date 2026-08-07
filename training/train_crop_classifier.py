from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def package_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classification_metrics(model, root: Path, image_size: int, batch: int, device: str) -> dict:
    class_dirs = sorted(path for path in root.iterdir() if path.is_dir())
    paths: list[Path] = []
    targets: list[int] = []
    for class_index, class_dir in enumerate(class_dirs):
        for path in sorted(class_dir.glob("*")):
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                paths.append(path)
                targets.append(class_index)
    confusion = [[0 for _ in class_dirs] for _ in class_dirs]
    predictions: list[int] = []
    for start in range(0, len(paths), batch):
        results = model.predict(
            source=[str(path) for path in paths[start : start + batch]],
            imgsz=image_size,
            batch=batch,
            device=device,
            verbose=False,
            save=False,
        )
        predictions.extend(int(result.probs.top1) for result in results)
    for target, prediction in zip(targets, predictions):
        confusion[target][prediction] += 1
    per_class = []
    for index, class_dir in enumerate(class_dirs):
        tp = confusion[index][index]
        fp = sum(confusion[row][index] for row in range(len(class_dirs)) if row != index)
        fn = sum(confusion[index][column] for column in range(len(class_dirs)) if column != index)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class.append(
            {
                "index": index,
                "name": class_dir.name,
                "support": sum(confusion[index]),
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    correct = sum(confusion[index][index] for index in range(len(class_dirs)))
    return {
        "image_count": len(paths),
        "accuracy": correct / len(paths) if paths else 0.0,
        "macro_f1": sum(row["f1"] for row in per_class) / len(per_class) if per_class else 0.0,
        "class_names": [path.name for path in class_dirs],
        "confusion_matrix_actual_rows_predicted_columns": confusion,
        "per_class": per_class,
    }


def normalize_results_csv(path: Path) -> None:
    """Add monitor-compatible aliases while retaining native classification metrics."""
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys()) if rows else []
    aliases = (
        ("train/loss", "train/cls_loss"),
        ("val/loss", "val/cls_loss"),
        ("metrics/accuracy_top1", "metrics/precision(B)"),
        ("metrics/accuracy_top1", "metrics/recall(B)"),
    )
    for _, destination in aliases:
        if destination not in fieldnames:
            fieldnames.append(destination)
    for row in rows:
        for source, destination in aliases:
            row[destination] = row.get(source, "")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a 4-class crop classifier from the detector backbone.")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--pretrained-detector", type=Path, required=True)
    parser.add_argument("--model", default="yolo26n-cls.yaml")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--batch", type=int, default=128)
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--project", type=Path, default=Path("runs/detect"))
    parser.add_argument("--name", default="weak-crop-cls-v1")
    parser.add_argument(
        "--frozen-eval",
        type=Path,
        default=None,
        help="Optional external frozen evaluation folder with class subdirectories.",
    )
    args = parser.parse_args()

    import torch
    from ultralytics import YOLO

    data_root = args.data.expanduser().resolve(strict=True)
    manifest_path = data_root / "manifest.json"
    detector_path = args.pretrained_detector.expanduser().resolve(strict=True)
    model = YOLO(args.model, task="classify")
    model.load(str(detector_path))
    results = model.train(
        data=str(data_root),
        epochs=args.epochs,
        imgsz=args.image_size,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        seed=args.seed,
        deterministic=True,
        patience=args.patience,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        weight_decay=0.01,
        warmup_epochs=2.0,
        amp=True,
        cos_lr=True,
        project=str(args.project.expanduser().resolve()),
        name=args.name,
        plots=False,
        cache=False,
    )
    run_dir = Path(results.save_dir)
    best_path = run_dir / "weights" / "best.pt"
    best_model = YOLO(str(best_path), task="classify")
    internal_val = classification_metrics(best_model, data_root / "val", args.image_size, args.batch, args.device)
    frozen_eval_root = args.frozen_eval.expanduser().resolve() if args.frozen_eval else data_root / "official_eval"
    official_eval = (
        classification_metrics(best_model, frozen_eval_root, args.image_size, args.batch, args.device)
        if frozen_eval_root.is_dir()
        else None
    )
    normalize_results_csv(run_dir / "results.csv")
    payload = {
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "task": "crop_classification",
        "best_weights": str(best_path),
        "best_weights_sha256": sha256(best_path),
        "dataset_root": str(data_root),
        "dataset_manifest_sha256": sha256(manifest_path) if manifest_path.exists() else None,
        "pretrained_detector": str(detector_path),
        "pretrained_detector_sha256": sha256(detector_path),
        "arguments": vars(args),
        "internal_validation": internal_val,
        "frozen_official_validation": official_eval,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "ultralytics": package_version("ultralytics"),
        },
    }
    payload["arguments"] = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    output = run_dir / "competition-metrics.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
