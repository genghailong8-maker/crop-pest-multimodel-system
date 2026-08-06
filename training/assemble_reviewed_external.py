"""Build a reproducible, train-only external augmentation package from reviews."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_label(path: Path) -> tuple[int, int]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for line_number, line in enumerate(lines, start=1):
        values = line.split()
        if len(values) != 5 or values[0] != "9":
            raise ValueError(f"{path}:{line_number}: expected class 9 and four YOLO values")
        coords = [float(value) for value in values[1:]]
        if any(value < 0 or value > 1 for value in coords) or coords[2] <= 0 or coords[3] <= 0:
            raise ValueError(f"{path}:{line_number}: invalid normalized coordinates")
        if coords[0] - coords[2] / 2 < -1e-6 or coords[0] + coords[2] / 2 > 1 + 1e-6:
            raise ValueError(f"{path}:{line_number}: horizontal box exceeds image")
        if coords[1] - coords[3] / 2 < -1e-6 or coords[1] + coords[3] / 2 > 1 + 1e-6:
            raise ValueError(f"{path}:{line_number}: vertical box exceeds image")
    return len(lines), sum(1 for line in lines if line)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prelabel-dir",
        type=Path,
        default=Path("artifacts/dataset-audit/pest65-aphids/prelabels"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/experiments/pest65-aphids-reviewed-v1"),
    )
    parser.add_argument(
        "--source-split",
        action="append",
        default=["train_images"],
        help="Only accepted images from these source splits enter training (repeatable).",
    )
    args = parser.parse_args()

    prelabel_dir = args.prelabel_dir.resolve()
    output_dir = args.output_dir.resolve()
    review_manifest = read_json(prelabel_dir / "review-manifest.json")
    source_manifest = read_json(prelabel_dir.parent / "manifest.json")
    source_root = Path(source_manifest["summary"]["source_root"]).resolve()
    source_splits = set(args.source_split)

    if output_dir.exists():
        for child in output_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    images_dir = output_dir / "images"
    labels_dir = output_dir / "labels"
    images_dir.mkdir(parents=True)
    labels_dir.mkdir()

    accepted = 0
    copied = 0
    box_count = 0
    excluded = 0
    records: list[dict[str, Any]] = []
    excluded_rows: list[dict[str, str]] = []

    for item in review_manifest.get("images", []):
        image_id = str(item["image_id"])
        review_path = prelabel_dir / "reviews" / f"{image_id}.json"
        if not review_path.is_file():
            continue
        review = read_json(review_path)
        if review.get("decision") != "accepted":
            continue
        accepted += 1
        relative_path = str(item["source_relative_path"])
        source_split = Path(relative_path).parts[0] if Path(relative_path).parts else ""
        if source_split not in source_splits:
            excluded += 1
            excluded_rows.append(
                {"image_id": image_id, "source_relative_path": relative_path, "reason": f"source_split:{source_split}"}
            )
            continue

        source_image = (source_root / relative_path).resolve()
        try:
            source_image.relative_to(source_root)
        except ValueError as exc:
            raise ValueError(f"source path escapes source root: {relative_path}") from exc
        if source_image.suffix.lower() not in IMAGE_SUFFIXES or not source_image.is_file():
            raise FileNotFoundError(source_image)
        source_label = prelabel_dir / "reviewed-labels" / f"{image_id}.txt"
        if not source_label.is_file():
            raise FileNotFoundError(source_label)
        labels, _ = validate_label(source_label)
        destination_image = images_dir / f"{image_id}{source_image.suffix.lower()}"
        destination_label = labels_dir / f"{image_id}.txt"
        shutil.copy2(source_image, destination_image)
        shutil.copy2(source_label, destination_label)
        copied += 1
        box_count += labels
        records.append(
            {
                "image_id": image_id,
                "source_relative_path": relative_path,
                "source_split": source_split,
                "image": str(destination_image.relative_to(output_dir).as_posix()),
                "label": str(destination_label.relative_to(output_dir).as_posix()),
                "review": str(review_path.relative_to(prelabel_dir).as_posix()),
                "source_sha256": sha256(source_image),
                "reviewed_box_count": labels,
            }
        )

    train_list = output_dir / "train.txt"
    train_list.write_text(
        "\n".join(record["image"] for record in records)
        + ("\n" if records else ""),
        encoding="utf-8",
    )
    (output_dir / "dataset.yaml").write_text(
        "\n".join(
            [
                f'path: {json.dumps(str(output_dir), ensure_ascii=False)}',
                "train: train.txt",
                "names:",
                '  0: "class_0"',
                '  1: "class_1"',
                '  2: "class_2"',
                '  3: "class_3"',
                '  4: "class_4"',
                '  5: "class_5"',
                '  6: "class_6"',
                '  7: "class_7"',
                '  8: "class_8"',
                '  9: "aphids"',
                '  10: "class_10"',
                '  11: "class_11"',
                '  12: "class_12"',
                '  13: "class_13"',
                '  14: "class_14"',
                '  15: "class_15"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "source": "pest65",
                "source_manifest": str((prelabel_dir.parent / "manifest.json").resolve()),
                "source_splits_used": sorted(source_splits),
                "accepted_review_count": accepted,
                "copied_train_image_count": copied,
                "excluded_non_train_count": excluded,
                "reviewed_box_count": box_count,
                "images": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with (output_dir / "excluded.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=["image_id", "source_relative_path", "reason"])
        writer.writeheader()
        writer.writerows(excluded_rows)

    print(
        json.dumps(
            {
                "accepted_review_count": accepted,
                "copied_train_image_count": copied,
                "excluded_non_train_count": excluded,
                "reviewed_box_count": box_count,
                "output_dir": str(output_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
