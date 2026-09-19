from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def yaml_path_value(data_path: Path, key: str) -> Path | None:
    prefix = f"{key}:"
    for raw_line in data_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip().strip('"').strip("'")
        if not value or value.startswith("["):
            return None
        return Path(value).expanduser().resolve()
    return None


def list_record(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {"path": str(path), "sha256": sha256(path), "non_empty_lines": len(lines)}


def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def values(array: Any) -> list[float]:
    if array is None:
        return []
    if hasattr(array, "tolist"):
        array = array.tolist()
    return [float(item) for item in array]


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a PT or ONNX detector and preserve per-class metrics.")
    parser.add_argument("model", type=Path)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--device", default="0")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--project", type=Path, default=Path("runs/evaluation"))
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--plots", action="store_true")
    args = parser.parse_args()

    model_path = args.model.expanduser().resolve(strict=True)
    data_path = args.data.expanduser().resolve(strict=True)
    project_path = args.project.expanduser().resolve()
    dataset_lists = {
        key: list_record(yaml_path_value(data_path, key))
        for key in ("train", "val")
    }
    from ultralytics import YOLO

    model = YOLO(str(model_path), task="detect")
    metrics = model.val(
        data=str(data_path),
        split="val",
        imgsz=args.image_size,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=str(project_path),
        name=args.name,
        exist_ok=True,
        plots=args.plots,
        verbose=False,
    )
    box = metrics.box
    class_ids = [int(item) for item in values(box.ap_class_index)]
    precision = values(box.p)
    recall = values(box.r)
    f1 = values(box.f1)
    ap50 = values(box.ap50)
    ap = values(box.ap)
    names = metrics.names
    confusion = metrics.confusion_matrix.matrix
    if hasattr(confusion, "tolist"):
        confusion = confusion.tolist()
    per_class = []
    for index, class_id in enumerate(class_ids):
        per_class.append(
            {
                "class_id": class_id,
                "class_name": names[class_id] if isinstance(names, dict) else names[class_id],
                "precision": precision[index],
                "recall": recall[index],
                "f1": f1[index],
                "map50": ap50[index],
                "map50_95": ap[index],
            }
        )
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "model": {
            "path": str(model_path),
            "format": model_path.suffix.lower().lstrip("."),
            "sha256": sha256(model_path),
            "size_bytes": model_path.stat().st_size,
        },
        "data": str(data_path),
        "data_yaml_sha256": sha256(data_path),
        "dataset_lists": dataset_lists,
        "configuration": {
            "device": args.device,
            "image_size": args.image_size,
            "batch": args.batch,
            "workers": args.workers,
        },
        "overall": {
            "precision": float(box.mp),
            "recall": float(box.mr),
            "map50": float(box.map50),
            "map50_95": float(box.map),
        },
        "per_class": per_class,
        "confusion_matrix": {
            "axis": "rows=predicted, columns=actual; final index=background",
            "labels": [
                *(names[index] if isinstance(names, dict) else names[index] for index in range(len(names))),
                "background",
            ],
            "matrix": confusion,
        },
        "speed_ms_per_image": {key: float(value) for key, value in metrics.speed.items()},
        "environment": {
            "python": platform.python_version(),
            "ultralytics": package_version("ultralytics"),
            "torch": package_version("torch"),
            "onnxruntime_gpu": package_version("onnxruntime-gpu"),
        },
    }
    output = args.output or (project_path / args.name / "metrics.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
