"""Retrain the selected Phase 9 architecture on all allowed data without touching frozen validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    from ultralytics import YOLO
    import torch

    data = args.data.resolve(strict=True)
    project = args.project.resolve()
    project.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.model)
    results = model.train(
        data=str(data),
        epochs=args.epochs,
        imgsz=args.image_size,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        seed=args.seed,
        deterministic=True,
        project=str(project),
        name=args.name,
        val=False,
        patience=0,
        cache=False,
        amp=True,
        cos_lr=True,
        close_mosaic=10,
        degrees=5.0,
        translate=0.1,
        scale=0.35,
        fliplr=0.5,
        flipud=0.0,
        hsv_h=0.015,
        hsv_s=0.5,
        hsv_v=0.35,
        plots=False,
        optimizer="auto",
    )
    last_weights = Path(results.save_dir) / "weights" / "last.pt"
    if not last_weights.is_file():
        raise FileNotFoundError(last_weights)
    record = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "weights": str(last_weights),
        "weights_sha256": sha256(last_weights),
        "dataset_yaml": str(data),
        "dataset_yaml_sha256": sha256(data),
        "frozen_validation_used_during_training": False,
        "training_arguments": vars(args),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "torch": torch.__version__,
            "torch_cuda_build": torch.version.cuda,
            "ultralytics": package_version("ultralytics"),
        },
    }
    record["training_arguments"] = {key: str(value) if isinstance(value, Path) else value for key, value in record["training_arguments"].items()}
    output = Path(results.save_dir) / "phase9-final-training.json"
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
