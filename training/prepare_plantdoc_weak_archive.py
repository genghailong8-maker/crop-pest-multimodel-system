"""Prepare a provenance-preserving PlantDoc weak-class detection subset.

This variant reads the official GitHub repository archive instead of issuing
one HTTP request per image.  It validates the complete Pascal-VOC XML for
each image and keeps only the three exact PlantDoc classes that map to weak
official classes 3, 5 and 7.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image


COMMIT = "4730a233a555b30ee98e0879c63ad25d82407455"
REPOSITORY = "https://github.com/pratikkayal/PlantDoc-Object-Detection-Dataset"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
TARGETS = {
    "Potato leaf early blight": 3,
    "Tomato leaf bacterial spot": 5,
    "Potato leaf late blight": 7,
}
NAMES = [
    "Corn leaf blight", "Tomato Septoria leaf spot", "Squash powdery mildew",
    "Potato early blight", "Corn rust", "Tomato bacterial spot",
    "Tomato late blight", "Potato late blight", "Blister beetle", "Aphids",
    "Mirid bugs (Miridae)", "Mole cricket", "Leafhoppers (Cicadellidae)",
    "Grasshoppers (Locustoidea)", "White grub", "Legume blister beetle",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def phash(data: bytes) -> str:
    with Image.open(io.BytesIO(data)) as image:
        pixels = list(image.convert("L").resize((16, 16)).getdata())
    mean = sum(pixels) / len(pixels)
    bits = 0
    for pixel in pixels:
        bits = (bits << 1) | int(pixel >= mean)
    return f"{bits:064x}"


def parse_voc(data: bytes) -> tuple[int, int, list[tuple[str, float, float, float, float]]]:
    root = ET.fromstring(data)
    size = root.find("size")
    if size is None:
        raise ValueError("missing size")
    width = int(size.findtext("width", "0"))
    height = int(size.findtext("height", "0"))
    if width <= 0 or height <= 0:
        raise ValueError("invalid image size")
    objects: list[tuple[str, float, float, float, float]] = []
    for node in root.findall("object"):
        name = " ".join((node.findtext("name") or "").split())
        box = node.find("bndbox")
        if not name or box is None:
            raise ValueError("missing object or box")
        xmin = float(box.findtext("xmin", "nan"))
        ymin = float(box.findtext("ymin", "nan"))
        xmax = float(box.findtext("xmax", "nan"))
        ymax = float(box.findtext("ymax", "nan"))
        if not all(math.isfinite(value) for value in (xmin, ymin, xmax, ymax)):
            raise ValueError("non-finite box")
        if not (0 <= xmin < xmax <= width and 0 <= ymin < ymax <= height):
            raise ValueError("box outside image")
        objects.append((name, xmin, ymin, xmax, ymax))
    if not objects:
        raise ValueError("empty annotation")
    return width, height, objects


def yolo(class_id: int, width: int, height: int, box: tuple[float, float, float, float]) -> str:
    xmin, ymin, xmax, ymax = box
    return f"{class_id} {((xmin + xmax) / 2) / width:.8f} {((ymin + ymax) / 2) / height:.8f} {(xmax - xmin) / width:.8f} {(ymax - ymin) / height:.8f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    archive = args.archive.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    archive_digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            archive_digest.update(chunk)

    with zipfile.ZipFile(archive) as source:
        members = {info.filename for info in source.infolist() if not info.is_dir()}
        root_prefix = next((name.split("/", 1)[0] + "/" for name in members if name.endswith("/train_labels.csv")), None)
        if root_prefix is None:
            root_prefix = next(name.split("/", 1)[0] + "/" for name in members if name.endswith("train_labels.csv"))
        # Build a flat lookup for the repository's TRAIN/TEST files.
        lookup = {name[len(root_prefix):]: name for name in members if name.startswith(root_prefix)}
        duplicate_sha: dict[str, str] = {}
        phash_groups: defaultdict[str, list[str]] = defaultdict(list)
        records: list[dict[str, Any]] = []
        exclusions = Counter()
        class_images = Counter()
        class_boxes = Counter()
        summaries: list[dict[str, Any]] = []
        for source_split, output_split in (("TRAIN", "train"), ("TEST", "test")):
            csv_member = lookup.get(f"{source_split.lower()}_labels.csv")
            if csv_member is None:
                raise ValueError(f"missing CSV for {source_split}")
            import csv
            rows = csv.DictReader(io.TextIOWrapper(source.open(csv_member), encoding="utf-8-sig"))
            by_filename: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
            for row in rows:
                by_filename[row["filename"]].append(dict(row))
            selected_names = sorted(name for name, rows_for_image in by_filename.items() if any(row["class"] in TARGETS for row in rows_for_image))
            image_dir = output_root / output_split / "images"
            label_dir = output_root / output_split / "labels"
            image_dir.mkdir(parents=True, exist_ok=True)
            label_dir.mkdir(parents=True, exist_ok=True)
            selected = 0
            boxes = 0
            for filename in selected_names:
                try:
                    image_key = f"{source_split}/{filename}"
                    xml_key = f"{source_split}/{Path(filename).stem}.xml"
                    image_member = lookup.get(image_key)
                    xml_member = lookup.get(xml_key)
                    if image_member is None:
                        exclusions["missing_image"] += 1
                        continue
                    if xml_member is None:
                        exclusions["missing_xml"] += 1
                        continue
                    image_bytes = source.read(image_member)
                    width, height, objects = parse_voc(source.read(xml_member))
                    if any(name not in TARGETS for name, *_ in objects):
                        exclusions["contains_non_target_object"] += 1
                        continue
                    digest = sha256(image_bytes)
                    if digest in duplicate_sha:
                        exclusions["exact_duplicate"] += 1
                        continue
                    with Image.open(io.BytesIO(image_bytes)) as image:
                        image.verify()
                    phash_value = phash(image_bytes)
                    output_name = f"plantdoc_{output_split}_{selected:06d}{Path(filename).suffix.lower() or '.jpg'}"
                    target_image = image_dir / output_name
                    target_label = label_dir / f"{target_image.stem}.txt"
                    target_image.write_bytes(image_bytes)
                    target_label.write_text("".join(yolo(TARGETS[name], width, height, (xmin, ymin, xmax, ymax)) + "\n" for name, xmin, ymin, xmax, ymax in objects), encoding="utf-8")
                    relative = target_image.relative_to(output_root).as_posix()
                    duplicate_sha[digest] = relative
                    phash_groups[phash_value].append(relative)
                    selected += 1
                    boxes += len(objects)
                    # An image may contain multiple boxes of one class.  Keep
                    # image and box counts separate for the audit report.
                    for class_id in {TARGETS[name] for name, *_ in objects}:
                        class_images[class_id] += 1
                    for name, *_ in objects:
                        class_boxes[TARGETS[name]] += 1
                    records.append({
                        "source_split": source_split,
                        "source_image_member": image_member,
                        "source_xml_member": xml_member,
                        "output_split": output_split,
                        "image": relative,
                        "label": target_label.relative_to(output_root).as_posix(),
                        "source_sha256": digest,
                        "perceptual_hash_16x16": phash_value,
                        "objects": [{"source_class": name, "official_class_id": TARGETS[name]} for name, *_ in objects],
                    })
                except Exception as error:
                    exclusions[f"invalid:{type(error).__name__}"] += 1
            entries = [record["image"] for record in records if record["output_split"] == output_split]
            (output_root / f"{output_split}.txt").write_text("\n".join(entries) + ("\n" if entries else ""), encoding="utf-8")
            summaries.append({"source_split": source_split, "output_split": output_split, "source_candidate_image_count": len(selected_names), "image_count": selected, "box_count": boxes})

    yaml_lines = [f"path: {json.dumps(str(output_root), ensure_ascii=False)}", "train: train.txt", "val: test.txt", "test: test.txt", "names:", *[f"  {index}: {json.dumps(name)}" for index, name in enumerate(NAMES)]]
    (output_root / "dataset.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    manifest = {
        "source": "PlantDoc Object Detection Dataset",
        "source_repository": REPOSITORY,
        "source_commit": COMMIT,
        "source_archive_sha256": archive_digest.hexdigest(),
        "source_license": "CC BY 4.0",
        "source_license_url": LICENSE_URL,
        "target_mapping": TARGETS,
        "selection_rule": "keep only complete XML images whose objects are Potato leaf early blight, Tomato leaf bacterial spot, or Potato leaf late blight",
        "split_summaries": summaries,
        "excluded_counts": dict(exclusions),
        "official_class_image_counts": dict(sorted(class_images.items())),
        "official_class_box_counts": dict(sorted(class_boxes.items())),
        "exact_duplicate_count_removed": exclusions["exact_duplicate"],
        "perceptual_hash_exact_groups": {key: value for key, value in phash_groups.items() if len(value) > 1},
        "records": records,
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_root / "provenance.json").write_text(json.dumps({"dataset": manifest["source"], "repository": REPOSITORY, "commit": COMMIT, "license": "CC BY 4.0", "license_url": LICENSE_URL, "mapping": TARGETS, "duplicate_policy": "exact SHA-256 duplicates removed in train-first order", "training_policy": "candidate remains isolated until smoke-train comparison passes"}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output_root": str(output_root), "split_summaries": summaries, "excluded_counts": dict(exclusions), "official_class_image_counts": dict(sorted(class_images.items())), "official_class_box_counts": dict(sorted(class_boxes.items())), "exact_duplicate_count_removed": exclusions["exact_duplicate"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
