from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a trained detector to ONNX with reproducibility metadata.")
    parser.add_argument("weights", type=Path)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--device", default="0")
    parser.add_argument("--opset", type=int, default=19)
    parser.add_argument("--half", action="store_true")
    parser.add_argument("--static", action="store_true", help="Export a fixed batch shape instead of dynamic axes.")
    parser.add_argument("--no-simplify", action="store_true")
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()

    weights = args.weights.expanduser().resolve(strict=True)
    from ultralytics import YOLO

    model = YOLO(str(weights))
    exported = Path(
        model.export(
            format="onnx",
            imgsz=args.image_size,
            device=args.device,
            opset=args.opset,
            dynamic=not args.static,
            simplify=not args.no_simplify,
            half=args.half,
        )
    ).resolve(strict=True)
    metadata_path = args.metadata or exported.with_suffix(".export.json")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "source": {
            "path": str(weights),
            "sha256": sha256(weights),
            "size_bytes": weights.stat().st_size,
        },
        "onnx": {
            "path": str(exported),
            "sha256": sha256(exported),
            "size_bytes": exported.stat().st_size,
        },
        "configuration": {
            "image_size": args.image_size,
            "device": args.device,
            "opset": args.opset,
            "dynamic": not args.static,
            "simplify": not args.no_simplify,
            "half": args.half,
        },
        "environment": {
            "python": platform.python_version(),
            "ultralytics": version("ultralytics"),
            "torch": version("torch"),
            "onnx": version("onnx"),
        },
    }
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
