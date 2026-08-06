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
    parser = argparse.ArgumentParser(description="Train the official 16-class object detector.")
    parser.add_argument("--data", type=Path, required=True, help="Path to dataset.yaml")
    parser.add_argument("--model", default="yolo26n.pt", help="Ultralytics checkpoint or model definition")
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--optimizer", default="auto", help="Ultralytics optimizer name or auto")
    parser.add_argument("--lr0", type=float, default=None, help="Initial learning rate override")
    parser.add_argument("--lrf", type=float, default=None, help="Final learning-rate fraction override")
    parser.add_argument("--freeze", type=int, default=None, help="Freeze the first N model layers")
    parser.add_argument("--project", type=Path, default=Path("runs/detect"))
    parser.add_argument("--name", default="official-baseline")
    parser.add_argument("--cache", action="store_true")
    parser.add_argument("--plots", action="store_true", help="Render Ultralytics plots (may require a valid server font).")
    parser.add_argument("--export-onnx", action="store_true")
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
        import torch
    except ImportError as exc:
        raise SystemExit(
            "Ultralytics is not installed. Install the vision environment after GPU compatibility is confirmed."
        ) from exc

    data_path = args.data.resolve()
    if not data_path.exists():
        raise FileNotFoundError(data_path)

    model = YOLO(args.model)
    train_kwargs = {
        "data": str(data_path),
        "epochs": args.epochs,
        "imgsz": args.image_size,
        "batch": args.batch,
        "device": args.device,
        "workers": args.workers,
        "seed": args.seed,
        "deterministic": True,
        "patience": args.patience,
        "project": str(args.project.resolve()),
        "name": args.name,
        "cache": args.cache,
        "amp": True,
        "cos_lr": True,
        "close_mosaic": 10,
        "degrees": 5.0,
        "translate": 0.1,
        "scale": 0.35,
        "fliplr": 0.5,
        "flipud": 0.0,
        "hsv_h": 0.015,
        "hsv_s": 0.5,
        "hsv_v": 0.35,
        "plots": args.plots,
        "optimizer": args.optimizer,
    }
    if args.lr0 is not None:
        train_kwargs["lr0"] = args.lr0
    if args.lrf is not None:
        train_kwargs["lrf"] = args.lrf
    if args.freeze is not None:
        train_kwargs["freeze"] = args.freeze

    results = model.train(
        **train_kwargs,
    )

    best_path = Path(results.save_dir) / "weights" / "best.pt"
    best_model = YOLO(str(best_path))
    validation = best_model.val(
        data=str(data_path),
        imgsz=args.image_size,
        batch=args.batch,
        device=args.device,
        split="val",
        plots=args.plots,
    )
    metrics = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "best_weights": str(best_path),
        "dataset_yaml": str(data_path),
        "dataset_yaml_sha256": sha256(data_path),
        "training_arguments": {
            "model": args.model,
            "epochs": args.epochs,
            "image_size": args.image_size,
            "batch": args.batch,
            "device": args.device,
            "workers": args.workers,
            "seed": args.seed,
            "patience": args.patience,
            "cache": args.cache,
            "optimizer": args.optimizer,
            "lr0": args.lr0,
            "lrf": args.lrf,
            "freeze": args.freeze,
            "plots": args.plots,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "torch": torch.__version__,
            "torch_cuda_build": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count(),
            "cuda_devices": [
                {
                    "index": index,
                    "name": torch.cuda.get_device_name(index),
                    "total_memory_gb": round(
                        torch.cuda.get_device_properties(index).total_memory / 1024**3,
                        2,
                    ),
                }
                for index in range(torch.cuda.device_count())
            ],
            "ultralytics": package_version("ultralytics"),
        },
        "map50": float(validation.box.map50),
        "map50_95": float(validation.box.map),
        "precision_mean": float(validation.box.mp),
        "recall_mean": float(validation.box.mr),
        "class_map50_95": [float(value) for value in validation.box.maps],
    }
    metrics_path = Path(results.save_dir) / "competition-metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

    if args.export_onnx:
        best_model.export(format="onnx", imgsz=args.image_size, dynamic=True, simplify=True)


if __name__ == "__main__":
    main()
