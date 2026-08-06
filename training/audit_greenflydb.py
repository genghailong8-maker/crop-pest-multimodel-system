"""Extract and audit the downloaded GreenFlyDB YOLO archives without relabeling them."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLITS = ("train", "valid", "test")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as handle:
        bad_member = handle.testzip()
        if bad_member:
            raise RuntimeError(f"{archive}: corrupt member {bad_member}")
        for member in handle.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"Unsafe archive member: {member.filename}")
        handle.extractall(destination)


def candidate_label_paths(image: Path) -> list[Path]:
    candidates = [image.with_suffix(".txt")]
    parts = list(image.parts)
    for index, part in enumerate(parts):
        if part.lower() in {"images", "image", "imgs"}:
            replaced = parts[:]
            replaced[index] = "labels"
            candidates.append(Path(*replaced).with_suffix(".txt"))
    return list(dict.fromkeys(candidates))


def parse_label(path: Path) -> tuple[Counter[int], int, list[str]]:
    classes: Counter[int] = Counter()
    invalid: list[str] = []
    rows = 0
    for line_number, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) != 5:
            invalid.append(f"line {line_number}: expected 5 fields")
            continue
        try:
            class_id = int(fields[0])
            coords = [float(value) for value in fields[1:]]
        except ValueError:
            invalid.append(f"line {line_number}: non-numeric value")
            continue
        if class_id < 0 or any(value < 0 or value > 1 for value in coords):
            invalid.append(f"line {line_number}: class/coordinate out of range")
            continue
        classes[class_id] += 1
        rows += 1
    return classes, rows, invalid


def audit_split(root: Path, split: str) -> dict[str, object]:
    images = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
    image_records = []
    class_counts: Counter[int] = Counter()
    label_count = 0
    box_count = 0
    missing_labels = []
    invalid_labels = []
    invalid_images = []
    image_hashes: Counter[str] = Counter()
    for image in images:
        try:
            with Image.open(image) as handle:
                handle.verify()
            image_hashes[sha256(image)] += 1
        except (OSError, UnidentifiedImageError) as exc:
            invalid_images.append({"path": str(image.relative_to(root)), "error": repr(exc)})
        label = next((candidate for candidate in candidate_label_paths(image) if candidate.is_file()), None)
        if label is None:
            missing_labels.append(str(image.relative_to(root)))
            classes, rows, errors = Counter(), 0, []
        else:
            label_count += 1
            classes, rows, errors = parse_label(label)
            class_counts.update(classes)
            box_count += rows
            if errors:
                invalid_labels.append({"path": str(label.relative_to(root)), "errors": errors})
        image_records.append(
            {
                "image": str(image.relative_to(root)),
                "label": str(label.relative_to(root)) if label else None,
                "box_count": rows,
                "class_ids": sorted(classes),
            }
        )
    duplicate_hashes = {digest: count for digest, count in image_hashes.items() if count > 1}
    return {
        "split": split,
        "root": str(root),
        "image_count": len(images),
        "label_file_count": label_count,
        "box_count": box_count,
        "class_counts": {str(key): value for key, value in sorted(class_counts.items())},
        "missing_label_count": len(missing_labels),
        "missing_labels_sample": missing_labels[:20],
        "invalid_image_count": len(invalid_images),
        "invalid_images": invalid_images[:20],
        "invalid_label_count": len(invalid_labels),
        "invalid_labels": invalid_labels[:20],
        "duplicate_image_hash_count": len(duplicate_hashes),
        "duplicate_image_hashes": duplicate_hashes,
        "images": image_records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("artifacts/public/greenflydb"))
    parser.add_argument("--extract-dir", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    extract_dir = (args.extract_dir or root / "extracted").resolve()
    extract_dir.mkdir(parents=True, exist_ok=True)

    archives = {
        "train": root / "GreenflyDB_YOLO_train.zip",
        "valid": root / "GreenflyDB_YOLO_valid.zip",
        "test": root / "GreenflyDB_YOLO_test_and_config.zip",
    }
    missing = [str(path) for path in archives.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing archives: " + ", ".join(missing))

    summaries = []
    for split, archive in archives.items():
        destination = extract_dir / split
        safe_extract(archive, destination)
        summaries.append(audit_split(destination, split))

    config_files = []
    for path in sorted(extract_dir.rglob("*.yaml")) + sorted(extract_dir.rglob("*.yml")):
        config_files.append({"path": str(path.relative_to(extract_dir)), "text": path.read_text(encoding="utf-8", errors="replace")[:20000]})
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": "GreenFlyDB",
        "archives": {split: {"path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size} for split, path in archives.items()},
        "extracted_root": str(extract_dir),
        "config_files": config_files,
        "splits": summaries,
        "usage_decision": {
            "green_fly": "candidate for mapping to official class 9 only after visual/label audit",
            "not_green_fly": "hard-negative candidate; do not convert to a 16-class positive label",
            "training": "not merged automatically by this audit",
        },
    }
    (root / "audit.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (root / "audit-class-counts.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["split", "class_id", "box_count"])
        for summary in summaries:
            for class_id, count in summary["class_counts"].items():
                writer.writerow([summary["split"], class_id, count])
    print(json.dumps({"audit": str(root / "audit.json"), "splits": [{key: value for key, value in summary.items() if key not in {"images", "invalid_images", "invalid_labels"}} for summary in summaries]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
