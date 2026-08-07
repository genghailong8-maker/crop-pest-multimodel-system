"""Prepare the licensed Roboflow grasshopper valid/test splits for review.

The selected dataset is intentionally evaluation-only.  Its ``valid`` split
becomes the threshold-tuning set and its ``test`` split becomes the untouched
frozen evaluation set.  The script validates every YOLO box, remaps the single
source class to official class 13, removes exact duplicates, reports perceptual
near matches, and creates a CSV that must be completed by a human reviewer.

No output from this script is eligible for calibration until ``review.csv`` is
fully accepted and the resulting manifest is finalized in a separate step.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from PIL import Image


OFFICIAL_CLASS_ID = 13
SOURCE_PROJECT = "grasshopper-qpkes-i1pbc/1"
SOURCE_URL = "https://universe.roboflow.com/amiruls-workspace-wyolc/grasshopper-qpkes-i1pbc/dataset/1"
LICENSE = "CC BY 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLITS = (("valid", "tune", 70), ("test", "frozen", 72))
BOX_EDGE_TOLERANCE = 0.002
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def average_hash(data: bytes) -> str:
    with Image.open(io.BytesIO(data)) as image:
        pixels = list(image.convert("L").resize((16, 16)).getdata())
    mean = sum(pixels) / len(pixels)
    bits = 0
    for pixel in pixels:
        bits = (bits << 1) | int(pixel >= mean)
    return f"{bits:064x}"


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def parse_names(data_yaml: str) -> list[str]:
    lines = data_yaml.splitlines()
    for index, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped.startswith("names:"):
            continue
        inline = stripped.split(":", 1)[1].strip()
        if inline:
            value = ast.literal_eval(inline)
            if isinstance(value, dict):
                return [str(value[key]) for key in sorted(value, key=lambda item: int(item))]
            if isinstance(value, list):
                return [str(item) for item in value]
            raise ValueError("data.yaml names must be a list or integer-keyed mapping")

        names: list[str] = []
        for candidate in lines[index + 1 :]:
            if not candidate.strip():
                continue
            if not candidate.startswith((" ", "\t")):
                break
            item = candidate.strip()
            if item.startswith("-"):
                names.append(item[1:].strip().strip("'\""))
            elif ":" in item:
                _, name = item.split(":", 1)
                names.append(name.strip().strip("'\""))
        if names:
            return names
        raise ValueError("data.yaml names block is empty")
    raise ValueError("data.yaml does not define names")


def parse_label(
    text: str, source_class_count: int
) -> tuple[list[tuple[float, float, float, float]], list[dict[str, Any]]]:
    boxes: list[tuple[float, float, float, float]] = []
    repairs: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"line {line_number}: expected 5 YOLO fields")
        class_id = int(fields[0])
        if class_id != 0 or source_class_count != 1:
            raise ValueError(f"line {line_number}: expected the dataset's sole class id 0")
        cx, cy, width, height = (float(value) for value in fields[1:])
        values = (cx, cy, width, height)
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"line {line_number}: non-finite coordinate")
        if not all(0.0 <= value <= 1.0 for value in values) or width <= 0 or height <= 0:
            raise ValueError(f"line {line_number}: invalid normalized box")
        left, right = cx - width / 2, cx + width / 2
        top, bottom = cy - height / 2, cy + height / 2
        overflow = max(0.0, -left, right - 1.0, -top, bottom - 1.0)
        if overflow > BOX_EDGE_TOLERANCE:
            raise ValueError(
                f"line {line_number}: box exceeds the image by {overflow:.8f}, "
                f"greater than tolerance {BOX_EDGE_TOLERANCE:.8f}"
            )
        clipped_left, clipped_right = max(0.0, left), min(1.0, right)
        clipped_top, clipped_bottom = max(0.0, top), min(1.0, bottom)
        clipped = (
            (clipped_left + clipped_right) / 2,
            (clipped_top + clipped_bottom) / 2,
            clipped_right - clipped_left,
            clipped_bottom - clipped_top,
        )
        if overflow > 0:
            repairs.append(
                {
                    "line_number": line_number,
                    "reason": "clip_small_edge_overflow",
                    "maximum_overflow": overflow,
                    "original": values,
                    "repaired": clipped,
                }
            )
        boxes.append(clipped)
    return boxes, repairs


def find_archive_root(members: set[str]) -> tuple[str, str]:
    candidates = sorted(
        (member for member in members if PurePosixPath(member).name == "data.yaml"),
        key=lambda item: (item.count("/"), len(item)),
    )
    if not candidates:
        raise ValueError("archive does not contain data.yaml")
    data_yaml = candidates[0]
    return data_yaml[: -len("data.yaml")], data_yaml


def image_members(members: set[str], prefix: str, split: str) -> dict[str, str]:
    start = f"{prefix}{split}/images/"
    result: dict[str, str] = {}
    for member in members:
        path = PurePosixPath(member)
        if member.startswith(start) and path.suffix.lower() in IMAGE_SUFFIXES:
            if path.stem in result:
                raise ValueError(f"duplicate image stem in {split}: {path.stem}")
            result[path.stem] = member
    return result


def iter_images(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        resolved = root.expanduser().resolve(strict=True)
        if resolved.is_file() and resolved.suffix.lower() in IMAGE_SUFFIXES:
            yield resolved
            continue
        if resolved.is_dir():
            yield from (
                path
                for path in resolved.rglob("*")
                if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
            )


def comparison_index(
    roots: list[Path],
) -> tuple[dict[str, list[str]], list[tuple[str, str]], int, list[dict[str, str]]]:
    exact: defaultdict[str, list[str]] = defaultdict(list)
    perceptual: list[tuple[str, str]] = []
    skipped: list[dict[str, str]] = []
    count = 0
    for path in iter_images(roots):
        try:
            data = path.read_bytes()
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            image_hash = average_hash(data)
        except Exception as error:
            skipped.append(
                {
                    "path": str(path),
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            continue
        text = str(path)
        exact[sha256_bytes(data)].append(text)
        perceptual.append((image_hash, text))
        count += 1
    return dict(exact), perceptual, count, skipped


def ensure_empty_output(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise FileExistsError(f"output path is not a directory: {path}")
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"output directory is not empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="Roboflow YOLO export ZIP")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--comparison-root",
        type=Path,
        action="append",
        default=[],
        help="Official/public image root used for cross-dataset duplicate checks; repeatable",
    )
    parser.add_argument("--near-duplicate-distance", type=int, default=6)
    args = parser.parse_args()

    archive = args.archive.expanduser().resolve(strict=True)
    output_root = args.output_root.expanduser().resolve()
    if not zipfile.is_zipfile(archive):
        raise ValueError(f"not a ZIP archive: {archive}")
    if args.near_duplicate_distance < 0:
        raise ValueError("near-duplicate distance must be non-negative")
    ensure_empty_output(output_root)

    comparison_exact, comparison_perceptual, comparison_count, comparison_skipped = comparison_index(
        args.comparison_root
    )
    seen_exact: dict[str, str] = {}
    seen_perceptual: list[tuple[str, str]] = []
    records: list[dict[str, Any]] = []
    invalid_records: list[dict[str, str]] = []
    exclusions = Counter()
    split_summaries: list[dict[str, Any]] = []

    with zipfile.ZipFile(archive) as source:
        members = {info.filename for info in source.infolist() if not info.is_dir()}
        prefix, data_yaml_member = find_archive_root(members)
        names = parse_names(source.read(data_yaml_member).decode("utf-8-sig"))
        if len(names) != 1 or names[0].strip().casefold() != "grasshopper":
            raise ValueError(f"expected exactly one source class named grasshopper, got {names!r}")

        for source_split, output_split, expected_images in SPLITS:
            images = image_members(members, prefix, source_split)
            output_images = output_root / output_split / "images"
            output_labels = output_root / output_split / "labels"
            output_images.mkdir(parents=True)
            output_labels.mkdir(parents=True)
            selected = 0
            box_count = 0

            for stem, image_member in sorted(images.items()):
                label_member = f"{prefix}{source_split}/labels/{stem}.txt"
                if label_member not in members:
                    exclusions[f"{source_split}:missing_label"] += 1
                    continue
                try:
                    boxes, box_repairs = parse_label(
                        source.read(label_member).decode("utf-8-sig"), len(names)
                    )
                    image_bytes = source.read(image_member)
                    with Image.open(io.BytesIO(image_bytes)) as image:
                        image.verify()
                    digest = sha256_bytes(image_bytes)
                    if digest in seen_exact:
                        exclusions[f"{source_split}:exact_duplicate_in_archive"] += 1
                        continue
                    if digest in comparison_exact:
                        exclusions[f"{source_split}:exact_duplicate_external"] += 1
                        continue
                    image_hash = average_hash(image_bytes)
                    near_matches = [
                        {"path": path, "distance": hamming(image_hash, known_hash)}
                        for known_hash, path in (*comparison_perceptual, *seen_perceptual)
                        if hamming(image_hash, known_hash) <= args.near_duplicate_distance
                    ]
                    near_matches.sort(key=lambda item: (item["distance"], item["path"]))
                    output_name = f"grasshopper_{output_split}_{selected:06d}{PurePosixPath(image_member).suffix.lower()}"
                    target_image = output_images / output_name
                    target_label = output_labels / f"{target_image.stem}.txt"
                    target_image.write_bytes(image_bytes)
                    target_label.write_text(
                        "".join(
                            f"{OFFICIAL_CLASS_ID} {cx:.8f} {cy:.8f} {width:.8f} {height:.8f}\n"
                            for cx, cy, width, height in boxes
                        ),
                        encoding="utf-8",
                    )
                    record = {
                        "record_id": f"{output_split}-{selected:06d}",
                        "source_split": source_split,
                        "source_image_member": image_member,
                        "source_label_member": label_member,
                        "output_split": output_split,
                        "image": target_image.relative_to(output_root).as_posix(),
                        "label": target_label.relative_to(output_root).as_posix(),
                        "box_count": len(boxes),
                        "box_repairs": box_repairs,
                        "source_sha256": digest,
                        "perceptual_hash_16x16": image_hash,
                        "near_duplicate_matches": near_matches[:10],
                    }
                    records.append(record)
                    seen_exact[digest] = str(target_image.resolve())
                    seen_perceptual.append((image_hash, str(target_image.resolve())))
                    selected += 1
                    box_count += len(boxes)
                except Exception as error:
                    exclusions[f"{source_split}:invalid:{type(error).__name__}"] += 1
                    invalid_records.append(
                        {
                            "source_split": source_split,
                            "source_image_member": image_member,
                            "source_label_member": label_member,
                            "error_type": type(error).__name__,
                            "error": str(error),
                        }
                    )

            selected_records = [record for record in records if record["output_split"] == output_split]
            list_path = output_root / f"{output_split}.txt"
            list_path.write_text(
                "\n".join(record["image"] for record in selected_records)
                + ("\n" if selected_records else ""),
                encoding="utf-8",
            )
            split_summaries.append(
                {
                    "source_split": source_split,
                    "output_split": output_split,
                    "source_image_count": len(images),
                    "expected_image_count": expected_images,
                    "selected_image_count": selected,
                    "box_count": box_count,
                    "count_matches_expected": selected == expected_images,
                }
            )

    with (output_root / "review.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        fieldnames = [
            "record_id",
            "output_split",
            "image",
            "box_count",
            "near_duplicate_count",
            "box_repair_count",
            "review_decision",
            "review_notes",
        ]
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "record_id": record["record_id"],
                    "output_split": record["output_split"],
                    "image": record["image"],
                    "box_count": record["box_count"],
                    "near_duplicate_count": len(record["near_duplicate_matches"]),
                    "box_repair_count": len(record["box_repairs"]),
                    "review_decision": "",
                    "review_notes": "",
                }
            )

    yaml_lines = [
        f"path: {json.dumps(str(output_root), ensure_ascii=False)}",
        "train: tune.txt",
        "val: tune.txt",
        "test: frozen.txt",
        "names:",
        *[f"  {index}: {json.dumps(name)}" for index, name in enumerate(OFFICIAL_NAMES)],
    ]
    (output_root / "dataset.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    automated_gate = all(item["count_matches_expected"] for item in split_summaries) and not exclusions
    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_project": SOURCE_PROJECT,
        "source_url": SOURCE_URL,
        "source_license": LICENSE,
        "source_license_url": LICENSE_URL,
        "source_archive": str(archive),
        "source_archive_sha256": sha256_file(archive),
        "mapping": {"grasshopper": OFFICIAL_CLASS_ID},
        "policy": {
            "valid_role": "threshold tuning only",
            "test_role": "untouched frozen evaluation only",
            "training_allowed": False,
        },
        "comparison_roots": [str(path.expanduser().resolve()) for path in args.comparison_root],
        "comparison_image_count": comparison_count,
        "comparison_skipped": comparison_skipped,
        "near_duplicate_distance": args.near_duplicate_distance,
        "box_edge_tolerance": BOX_EDGE_TOLERANCE,
        "box_repair_count": sum(len(record["box_repairs"]) for record in records),
        "split_summaries": split_summaries,
        "excluded_counts": dict(exclusions),
        "invalid_records": invalid_records,
        "automated_gate_passed": automated_gate,
        "human_review_status": "pending",
        "calibration_eligible": False,
        "records": records,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output_root": str(output_root),
                "split_summaries": split_summaries,
                "excluded_counts": dict(exclusions),
                "invalid_record_count": len(invalid_records),
                "comparison_image_count": comparison_count,
                "comparison_skipped_count": len(comparison_skipped),
                "automated_gate_passed": automated_gate,
                "human_review_status": "pending",
                "calibration_eligible": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
