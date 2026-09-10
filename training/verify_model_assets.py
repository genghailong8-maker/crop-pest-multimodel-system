"""Verify detector checkpoints by size, SHA-256 and Ultralytics loading."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from ultralytics import YOLO

    records = []
    for model_path in args.models:
        path = model_path.resolve(strict=True)
        YOLO(str(path), task="detect")
        records.append({"name": path.name, "path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path), "loadable": True})
    payload = {"verified_count": len(records), "models": records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
