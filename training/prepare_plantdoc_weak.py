"""Download and prepare the PlantDoc weak-class detection subset.

PlantDoc is published as Pascal-VOC XML plus a CSV index.  This utility keeps
only images whose complete XML annotation consists of the three official weak
classes that have an unambiguous mapping:

* ``Potato leaf early blight`` -> official class 3
* ``Tomato leaf bacterial spot`` -> official class 5
* ``Potato leaf late blight`` -> official class 7

Images containing an additional class are excluded rather than silently
creating unlabeled objects.  The source repository is never modified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


COMMIT = "4730a233a555b30ee98e0879c63ad25d82407455"
RAW_ROOT = f"https://raw.githubusercontent.com/pratikkayal/PlantDoc-Object-Detection-Dataset/{COMMIT}"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
REPO_URL = "https://github.com/pratikkayal/PlantDoc-Object-Detection-Dataset"

TARGETS = {
    "Potato leaf early blight": 3,
    "Tomato leaf bacterial spot": 5,
    "Potato leaf late blight": 7,
}

NAMES = [
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, destination: Path, retries: int = 4) -> None:
    """Fetch a source file atomically, preserving a valid existing copy."""

    if destination.is_file() and destination.stat().st_size > 0:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "crop-pest-system/plantdoc-audit"},
            )
            with urllib.request.urlopen(request, timeout=90) as response, temporary.open("wb") as stream:
                shutil.copyfileobj(response, stream, length=1024 * 1024)
            if temporary.stat().st_size == 0:
                raise OSError(f"empty response from {url}")
            temporary.replace(destination)
            return
        except Exception as error:  # urllib raises several transport-specific types.
            last_error = error
            if temporary.exists():
                temporary.unlink()
            if attempt + 1 < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"failed to download {url}: {last_error}")


def source_url(split: str, name: str) -> str:
    # The repository contains literal percent signs and question marks in a
    # few filenames; quote every path component so the raw URL is unambiguous.
    return f"{RAW_ROOT}/{split}/{urllib.parse.quote(name, safe='')}"


def read_index(url: str) -> list[dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": "crop-pest-system/plantdoc-audit"})
    with urllib.request.urlopen(request, timeout=90) as response:
        text = response.read().decode("utf-8-sig")
    return [dict(row) for row in csv.DictReader(text.splitlines())]


def parse_xml(path: Path) -> tuple[int, int, list[tuple[str, float, float, float, float]]]:
    root = ET.parse(path).getroot()
    size = root.find("size")
    if size is None:
        raise ValueError("missing XML size")
    width = int(size.findtext("width", "0"))
    height = int(size.findtext("height", "0"))
    if width <= 0 or height <= 0:
        raise ValueError("invalid XML size")
    objects: list[tuple[str, float, float, float, float]] = []
    for object_node in root.findall("object"):
        name = " ".join((object_node.findtext("name") or "").split())
        box = object_node.find("bndbox")
        if not name or box is None:
            raise ValueError("missing object name or bndbox")
        xmin = float(box.findtext("xmin", "nan"))
        ymin = float(box.findtext("ymin", "nan"))
        xmax = float(box.findtext("xmax", "nan"))
        ymax = float(box.findtext("ymax", "nan"))
        if not (0 <= xmin < xmax <= width and 0 <= ymin < ymax <= height):
            raise ValueError(f"invalid box {name}: {xmin},{ymin},{xmax},{ymax}")
        objects.append((name, xmin, ymin, xmax, ymax))
    if not objects:
        raise ValueError("empty XML annotation")
    return width, height, objects


def yolo_line(class_id: int, width: int, height: int, box: tuple[float, float, float, float]) -> str:
    xmin, ymin, xmax, ymax = box
    x_center = ((xmin + xmax) / 2) / width
    y_center = ((ymin + ymax) / 2) / height
    box_width = (xmax - xmin) / width
    box_height = (ymax - ymin) / height
    return f"{class_id} {x_center:.8f} {y_center:.8f} {box_width:.8f} {box_height:.8f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/public/plantdoc-weak-v1"))
    parser.add_argument("--source-root", type=Path, default=Path("artifacts/public/plantdoc-source-selective"))
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    source_root = args.source_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    source_root.mkdir(parents=True, exist_ok=True)

    index_records: dict[str, list[dict[str, str]]] = {}
    for split, filename in (("TRAIN", "train_labels.csv"), ("TEST", "test_labels.csv")):
        index_path = source_root / filename
        fetch(f"{RAW_ROOT}/{filename}", index_path)
        with index_path.open("r", encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        index_records[split] = rows

    selected_names: dict[str, list[str]] = {}
    for split, rows in index_records.items():
        by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            by_name[row["filename"]].append(row)
        selected_names[split] = sorted(
            name for name, records in by_name.items() if any(record["class"] in TARGETS for record in records)
        )

    duplicate_hashes: dict[str, str] = {}
    split_summaries: list[dict[str, Any]] = []
    exclusions = Counter()
    class_image_counts = Counter()
    class_box_counts = Counter()
    records_out: list[dict[str, Any]] = []

    # Process TRAIN first so an exact duplicate that appears in TEST is held out
    # instead of leaking between the candidate training and external test sets.
    for source_split, output_split in (("TRAIN", "train"), ("TEST", "test")):
        image_dir = output_root / output_split / "images"
        label_dir = output_root / output_split / "labels"
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        selected = 0
        boxes = 0
        for source_name in selected_names[source_split]:
            source_image = source_root / source_split / source_name
            source_xml = source_root / source_split / f"{source_name}.xml"
            try:
                fetch(source_url(source_split, source_name), source_image)
                fetch(source_url(source_split, f"{source_name}.xml"), source_xml)
                width, height, objects = parse_xml(source_xml)
                if any(name not in TARGETS for name, *_ in objects):
                    exclusions["contains_non_target_object"] += 1
                    continue
                digest = sha256(source_image)
                if digest in duplicate_hashes:
                    exclusions["exact_duplicate_cross_split_or_within_split"] += 1
                    continue
                yolo_lines = [
                    yolo_line(TARGETS[name], width, height, (xmin, ymin, xmax, ymax))
                    for name, xmin, ymin, xmax, ymax in objects
                ]
                safe_suffix = source_image.suffix.lower() or ".jpg"
                output_name = f"plantdoc_{output_split}_{selected:05d}{safe_suffix}"
                target_image = image_dir / output_name
                target_label = label_dir / f"{Path(output_name).stem}.txt"
                shutil.copy2(source_image, target_image)
                target_label.write_text("\n".join(yolo_lines) + "\n", encoding="utf-8")
                duplicate_hashes[digest] = f"{output_split}/{output_name}"
                selected += 1
                boxes += len(objects)
                for name, *_ in objects:
                    class_image_counts[TARGETS[name]] += 1
                    class_box_counts[TARGETS[name]] += 1
                records_out.append(
                    {
                        "source_split": source_split,
                        "source_filename": source_name,
                        "output_split": output_split,
                        "image": str(target_image.relative_to(output_root).as_posix()),
                        "label": str(target_label.relative_to(output_root).as_posix()),
                        "source_sha256": digest,
                        "source_xml": str(source_xml.relative_to(source_root).as_posix()),
                        "objects": [{"source_class": name, "official_class_id": TARGETS[name]} for name, *_ in objects],
                    }
                )
            except Exception as error:
                exclusions[f"invalid_or_download_error:{type(error).__name__}"] += 1

        image_list = output_root / f"{output_split}.txt"
        entries = [record["image"] for record in records_out if record["output_split"] == output_split]
        image_list.write_text("\n".join(entries) + ("\n" if entries else ""), encoding="utf-8")
        split_summaries.append({"split": output_split, "image_count": selected, "box_count": boxes, "image_list": str(image_list)})

    yaml_lines = [
        f"path: {json.dumps(str(output_root), ensure_ascii=False)}",
        "train: train.txt",
        "val: test.txt",
        "names:",
        *[f"  {index}: {json.dumps(name)}" for index, name in enumerate(NAMES)],
    ]
    (output_root / "dataset.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    manifest = {
        "source": "PlantDoc-Object-Detection-Dataset",
        "source_repository": REPO_URL,
        "source_commit": COMMIT,
        "source_license": "CC BY 4.0",
        "source_license_url": LICENSE_URL,
        "target_mapping": TARGETS,
        "training_merge": False,
        "selected_source_image_counts": {split: len(names) for split, names in selected_names.items()},
        "split_summaries": split_summaries,
        "excluded_counts": dict(exclusions),
        "official_class_image_counts": dict(sorted(class_image_counts.items())),
        "official_class_box_counts": dict(sorted(class_box_counts.items())),
        "exact_duplicate_group_count": len(duplicate_hashes) - len(records_out),
        "images": records_out,
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_root / "provenance.json").write_text(
        json.dumps(
            {
                "dataset": "PlantDoc Object Detection",
                "repository": REPO_URL,
                "commit": COMMIT,
                "license": "CC BY 4.0",
                "license_url": LICENSE_URL,
                "selection": "Only complete XML images whose objects are Potato leaf early blight, Tomato leaf bacterial spot, or Potato leaf late blight.",
                "official_mapping": TARGETS,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"output_root": str(output_root), **{key: manifest[key] for key in ("split_summaries", "excluded_counts", "official_class_image_counts", "official_class_box_counts")}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
