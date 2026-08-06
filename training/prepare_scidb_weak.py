"""Audit and extract the ScienceDB pests-dataset102 weak-class subset.

The archive is a 102-class YOLO export.  This utility deliberately keeps only
images whose *complete* annotation consists of the two exact source classes
that map to the official weak classes:

* ``Miridae`` -> official class 10 (Mirid bugs (Miridae))
* ``blister beetle`` -> official class 8 (Blister beetle)

Images with any other source class are excluded instead of silently creating
unlabelled objects.  Exact duplicate images are retained only in the first
split in which they occur (train, then valid, then test), so a duplicate can
never leak into an evaluation split.  A compact perceptual hash is recorded
for audit; it is not used as a hard exclusion because visually similar but
distinct insects are common in this dataset.

The source archive is never modified.  The output is a self-contained YOLO
dataset with 16-class official label IDs and provenance/manifest JSON files.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import math
import shutil
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError as error:  # pragma: no cover - server runtime supplies Pillow
    raise SystemExit("Pillow is required for image validation: %s" % (error,))


OFFICIAL_NAMES = [
    "Corn leaf blight",
    "Tomato Septoria leaf spot",
    "Squash powdery mildew",
    "Potato early blight",
    "Corn rust",
    "Tomato bacterial spot",
    "Tomato late blight",
    "Potato late blight",
    "Blister beetle",
    "Aphids",
    "Mirid bugs (Miridae)",
    "Mole cricket",
    "Leafhoppers (Cicadellidae)",
    "Grasshoppers (Locustoidea)",
    "White grub",
    "Legume blister beetle",
]

TARGET_SOURCE_TO_OFFICIAL = {
    "Miridae": 10,
    "blister beetle": 8,
}
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def perceptual_hash(data: bytes) -> str:
    """Return a small grayscale hash for duplicate-rate reporting."""

    with Image.open(io.BytesIO(data)) as image:
        image = image.convert("L").resize((16, 16))
        pixels = list(image.getdata())
    mean = sum(pixels) / len(pixels)
    bits = 0
    for pixel in pixels:
        bits = (bits << 1) | int(pixel >= mean)
    return f"{bits:064x}"


def parse_names(data_yaml: str) -> list[str]:
    for line in data_yaml.splitlines():
        if line.strip().startswith("names:"):
            value = line.split(":", 1)[1].strip()
            names = ast.literal_eval(value)
            if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
                raise ValueError("data.yaml names is not a string list")
            return names
    raise ValueError("data.yaml does not contain names")


def parse_label(text: str, class_count: int) -> list[tuple[int, float, float, float, float]]:
    records: list[tuple[int, float, float, float, float]] = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"line {line_number}: expected 5 YOLO fields")
        class_id = int(fields[0])
        values = tuple(float(item) for item in fields[1:])
        if class_id < 0 or class_id >= class_count:
            raise ValueError(f"line {line_number}: class id {class_id} out of range")
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"line {line_number}: non-finite bbox")
        if not all(0.0 <= value <= 1.0 for value in values) or values[2] <= 0 or values[3] <= 0:
            raise ValueError(f"line {line_number}: bbox outside normalized range")
        records.append((class_id, *values))
    return records


def find_image_members(members: set[str], split: str) -> dict[str, str]:
    result: dict[str, str] = {}
    prefix = f"{split}/images/"
    for member in members:
        if not member.startswith(prefix):
            continue
        path = Path(member)
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        result[path.stem] = member
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    archive = args.archive.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    archive_sha = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            archive_sha.update(chunk)

    with zipfile.ZipFile(archive) as source:
        members = {info.filename for info in source.infolist() if not info.is_dir()}
        data_yaml = source.read("data.yaml").decode("utf-8")
        source_names = parse_names(data_yaml)
        source_to_id = {name: index for index, name in enumerate(source_names)}
        missing = [name for name in TARGET_SOURCE_TO_OFFICIAL if name not in source_to_id]
        if missing:
            raise ValueError(f"target source classes missing from data.yaml: {missing}")
        target_source_ids = {source_to_id[name]: official for name, official in TARGET_SOURCE_TO_OFFICIAL.items()}

        split_specs = (("train", "train"), ("valid", "valid"), ("test", "test"))
        image_maps = {source_split: find_image_members(members, source_split) for source_split, _ in split_specs}
        duplicate_sha_to_output: dict[str, str] = {}
        duplicate_phash_to_outputs: defaultdict[str, list[str]] = defaultdict(list)
        records: list[dict[str, Any]] = []
        exclusions = Counter()
        class_image_counts = Counter()
        class_box_counts = Counter()
        source_label_counts = Counter()
        split_summaries: list[dict[str, Any]] = []

        # Process train first: exact duplicates in validation/test are removed.
        for source_split, output_split in split_specs:
            image_dir = output_root / output_split / "images"
            label_dir = output_root / output_split / "labels"
            image_dir.mkdir(parents=True, exist_ok=True)
            label_dir.mkdir(parents=True, exist_ok=True)
            selected = 0
            boxes = 0
            label_members = sorted(
                member for member in members if member.startswith(f"{source_split}/labels/") and member.endswith(".txt")
            )
            for label_member in label_members:
                stem = Path(label_member).stem
                image_member = image_maps[source_split].get(stem)
                if image_member is None:
                    exclusions["missing_image"] += 1
                    continue
                try:
                    label_text = source.read(label_member).decode("utf-8-sig")
                    source_boxes = parse_label(label_text, len(source_names))
                    if not source_boxes:
                        exclusions["empty_annotation"] += 1
                        continue
                    source_label_counts.update(class_id for class_id, *_ in source_boxes)
                    if any(class_id not in target_source_ids for class_id, *_ in source_boxes):
                        exclusions["contains_non_target_object"] += 1
                        continue
                    image_bytes = source.read(image_member)
                    with Image.open(io.BytesIO(image_bytes)) as image:
                        image.verify()
                    image_sha = sha256_bytes(image_bytes)
                    if image_sha in duplicate_sha_to_output:
                        exclusions["exact_duplicate"] += 1
                        continue
                    image_phash = perceptual_hash(image_bytes)
                    remapped = [
                        (target_source_ids[class_id], cx, cy, width, height)
                        for class_id, cx, cy, width, height in source_boxes
                    ]
                    output_name = f"scidb_{output_split}_{selected:06d}{Path(image_member).suffix.lower()}"
                    target_image = image_dir / output_name
                    target_label = label_dir / f"{target_image.stem}.txt"
                    target_image.write_bytes(image_bytes)
                    target_label.write_text(
                        "".join(f"{class_id} {cx:.8f} {cy:.8f} {width:.8f} {height:.8f}\n" for class_id, cx, cy, width, height in remapped),
                        encoding="utf-8",
                    )
                    relative_image = target_image.relative_to(output_root).as_posix()
                    duplicate_sha_to_output[image_sha] = relative_image
                    duplicate_phash_to_outputs[image_phash].append(relative_image)
                    selected += 1
                    boxes += len(remapped)
                    for class_id, *_ in remapped:
                        class_image_counts[class_id] += 1
                        class_box_counts[class_id] += 1
                    records.append(
                        {
                            "source_split": source_split,
                            "source_image_member": image_member,
                            "source_label_member": label_member,
                            "output_split": output_split,
                            "image": relative_image,
                            "label": target_label.relative_to(output_root).as_posix(),
                            "source_sha256": image_sha,
                            "perceptual_hash_16x16": image_phash,
                            "objects": [
                                {"source_class": source_names[class_id], "source_class_id": class_id, "official_class_id": official}
                                for class_id, official in ((item[0], target_source_ids[item[0]]) for item in source_boxes)
                            ],
                        }
                    )
                except Exception as error:
                    exclusions[f"invalid:{type(error).__name__}"] += 1
            entries = [record["image"] for record in records if record["output_split"] == output_split]
            (output_root / f"{output_split}.txt").write_text("\n".join(entries) + ("\n" if entries else ""), encoding="utf-8")
            split_summaries.append(
                {
                    "source_split": source_split,
                    "output_split": output_split,
                    "candidate_label_files": len(label_members),
                    "image_count": selected,
                    "box_count": boxes,
                }
            )

    yaml_lines = [
        f"path: {json.dumps(str(output_root), ensure_ascii=False)}",
        "train: train.txt",
        "val: valid.txt",
        "test: test.txt",
        "names:",
        *[f"  {index}: {json.dumps(name)}" for index, name in enumerate(OFFICIAL_NAMES)],
    ]
    (output_root / "dataset.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    phash_groups = {key: value for key, value in duplicate_phash_to_outputs.items() if len(value) > 1}
    manifest = {
        "source": "ScienceDB pests dataset102 v2 (Roboflow YOLOv11 export)",
        "source_archive": str(archive),
        "source_archive_sha256": archive_sha.hexdigest(),
        "source_names_count": len(source_names),
        "source_license_evidence": {
            "sciencedb_metadata": "MIT",
            "archive_data_yaml": "Public Domain",
            "archive_readme": "Public Domain",
            "status": "both permissive; preserve discrepancy for competition provenance review",
        },
        "target_mapping": TARGET_SOURCE_TO_OFFICIAL,
        "selection_rule": "keep only complete annotations containing exclusively Miridae or blister beetle; remap to official classes 10 and 8",
        "split_summaries": split_summaries,
        "excluded_counts": dict(exclusions),
        "source_label_counts": {source_names[index]: count for index, count in sorted(source_label_counts.items())},
        "official_class_image_counts": dict(sorted(class_image_counts.items())),
        "official_class_box_counts": dict(sorted(class_box_counts.items())),
        "exact_duplicate_count_removed": exclusions["exact_duplicate"],
        "perceptual_hash_exact_groups": phash_groups,
        "records": records,
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_root / "provenance.json").write_text(
        json.dumps(
            {
                "dataset": manifest["source"],
                "archive_sha256": archive_sha.hexdigest(),
                "source_license_evidence": manifest["source_license_evidence"],
                "source_classes": TARGET_SOURCE_TO_OFFICIAL,
                "official_class_names": {"8": OFFICIAL_NAMES[8], "10": OFFICIAL_NAMES[10]},
                "filter": manifest["selection_rule"],
                "duplicate_policy": "exact SHA-256 duplicates removed in train-first order; perceptual hash retained for audit",
                "training_policy": "candidate subset is isolated; do not deploy or merge until smoke-train comparison passes",
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    summary = {key: manifest[key] for key in ("split_summaries", "excluded_counts", "official_class_image_counts", "official_class_box_counts", "exact_duplicate_count_removed")}
    print(json.dumps({"output_root": str(output_root), **summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
