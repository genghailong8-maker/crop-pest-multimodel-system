"""Prepare a GreenFlyDB class-9-only external evaluation package.

The source dataset contains ``greenfly`` and ``notgreenfly`` classes.  This
script keeps only clean images whose labels contain greenfly (source class 0),
remaps that class to the official Aphids class 9, and writes separate valid
and test manifests.  It never modifies the downloaded source or creates
training entries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_label(source: Path, target_class_id: int) -> tuple[str, int]:
    output: list[str] = []
    box_count = 0
    for line_number, raw in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        fields = raw.split()
        if len(fields) != 5 or fields[0] != "0":
            raise ValueError(f"{source}:{line_number}: expected a clean source class-0 YOLO row")
        output.append(" ".join([str(target_class_id), *fields[1:]]))
        box_count += 1
    if not output:
        raise ValueError(f"{source}: empty label")
    return "\n".join(output) + "\n", box_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("artifacts/public/greenflydb"))
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--target-class-id", type=int, default=9)
    args = parser.parse_args()

    root = args.root.resolve()
    audit_path = (args.audit or root / "audit.json").resolve()
    output_root = (args.output_root or root / "evaluation" / "official16-class9").resolve()
    audit = read_json(audit_path)
    invalid_by_split = {
        summary["split"]: {item["path"] for item in summary["invalid_labels"]}
        for summary in audit["splits"]
    }

    split_summaries = []
    all_hashes: dict[str, str] = {}
    for split in ("valid", "test"):
        source_root = root / "extracted" / split
        destination = output_root / split
        if destination.exists():
            shutil.rmtree(destination)
        images_dir = destination / "images"
        labels_dir = destination / "labels"
        images_dir.mkdir(parents=True)
        labels_dir.mkdir()
        selected = []
        excluded = Counter()
        records = next(summary["images"] for summary in audit["splits"] if summary["split"] == split)
        invalid_labels = invalid_by_split.get(split, set())
        for record in records:
            classes = record["class_ids"]
            if classes != [0]:
                excluded["not_greenfly_or_mixed"] += 1
                continue
            label_relative = record["label"]
            if label_relative in invalid_labels:
                excluded["invalid_label"] += 1
                continue
            source_image = source_root / record["image"]
            source_label = source_root / label_relative
            image_hash = sha256(source_image)
            duplicate_of = all_hashes.get(image_hash)
            if duplicate_of:
                excluded["cross_split_duplicate"] += 1
                continue
            try:
                label_text, box_count = clean_label(source_label, args.target_class_id)
            except ValueError:
                excluded["invalid_label"] += 1
                continue
            image_name = f"greenfly_{len(selected):05d}{source_image.suffix.lower()}"
            label_name = Path(image_name).with_suffix(".txt").name
            target_image = images_dir / image_name
            target_label = labels_dir / label_name
            shutil.copy2(source_image, target_image)
            target_label.write_text(label_text, encoding="utf-8")
            all_hashes[image_hash] = f"{split}/{image_name}"
            selected.append(
                {
                    "source_image": record["image"],
                    "source_label": label_relative,
                    "image": str(target_image.relative_to(output_root).as_posix()),
                    "label": str(target_label.relative_to(output_root).as_posix()),
                    "source_sha256": image_hash,
                    "box_count": box_count,
                }
            )
        image_list = destination / "images.txt"
        image_list.write_text("\n".join(str((output_root / item["image"]).resolve()) for item in selected) + "\n", encoding="utf-8")
        yaml_path = output_root / f"dataset-{split}.yaml"
        yaml_path.write_text(
            "\n".join(
                [
                    f"path: {json.dumps(str(output_root), ensure_ascii=False)}",
                    # Ultralytics requires both keys even for validation-only runs.
                    f"train: {json.dumps(str(image_list.resolve()), ensure_ascii=False)}",
                    f"val: {json.dumps(str(image_list.resolve()), ensure_ascii=False)}",
                    "names:",
                    *[f"  {index}: {json.dumps(name)}" for index, name in enumerate(NAMES)],
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (destination / "manifest.json").write_text(
            json.dumps(
                {
                    "source": "GreenFlyDB",
                    "source_split": split,
                    "source_audit": str(audit_path),
                    "target_class_id": args.target_class_id,
                    "selected_image_count": len(selected),
                    "selected_box_count": sum(item["box_count"] for item in selected),
                    "excluded_counts": dict(excluded),
                    "images": selected,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        split_summaries.append(
            {
                "split": split,
                "selected_image_count": len(selected),
                "selected_box_count": sum(item["box_count"] for item in selected),
                "excluded_counts": dict(excluded),
                "dataset_yaml": str(yaml_path),
            }
        )

    report = {
        "source_audit": str(audit_path),
        "output_root": str(output_root),
        "target_class_id": args.target_class_id,
        "training_merge": False,
        "splits": split_summaries,
    }
    (output_root / "prepare-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
