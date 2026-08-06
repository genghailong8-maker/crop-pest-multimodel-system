from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image

from audit_official_dataset import difference_hash, file_sha256, load_class_map, parse_label


def image_class_counts(label_path: Path) -> Counter[int]:
    boxes, errors = parse_label(label_path)
    if errors:
        raise ValueError(f"Invalid label {label_path}: {errors}")
    return Counter({class_id: 1 for class_id in {box[0] for box in boxes}})


def add_group_counts(target: Counter[int], group_counts: Counter[int]) -> None:
    for class_id, count in group_counts.items():
        target[class_id] += count


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a duplicate-aware local train/validation split without modifying official data."
    )
    parser.add_argument("data_root", type=Path)
    parser.add_argument("--class-map", type=Path, required=True)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=20260729)
    args = parser.parse_args()

    if not 0 < args.val_fraction < 1:
        raise ValueError("--val-fraction must be between 0 and 1")

    data_root = args.data_root.resolve()
    image_dir = data_root / "images" / "all"
    label_dir = data_root / "labels" / "all"
    split_dir = data_root / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)

    class_map_rows = load_class_map(args.class_map.resolve())
    class_names_zh = {int(row["class_id"]): row["name_zh"] for row in class_map_rows}
    class_names_en = {int(row["class_id"]): row["name_en"] for row in class_map_rows}
    image_paths = sorted(image_dir.glob("*.jpg"))

    exact_hash_groups: dict[str, list[Path]] = defaultdict(list)
    perceptual_groups: dict[str, list[Path]] = defaultdict(list)
    class_counts_by_image: dict[str, Counter[int]] = {}
    all_class_counts: Counter[int] = Counter()

    for image_path in image_paths:
        label_path = label_dir / f"{image_path.stem}.txt"
        if not label_path.exists():
            raise FileNotFoundError(f"Missing label for {image_path.name}")
        class_counts = image_class_counts(label_path)
        class_counts_by_image[image_path.name] = class_counts
        add_group_counts(all_class_counts, class_counts)
        exact_hash_groups[file_sha256(image_path)].append(image_path)
        with Image.open(image_path) as image:
            image.load()
            perceptual_groups[difference_hash(image)].append(image_path)

    conflicting_exact_groups: list[dict[str, Any]] = []
    quarantined_names: set[str] = set()
    for digest, group in exact_hash_groups.items():
        if len(group) < 2:
            continue
        class_sets = {
            tuple(sorted(class_counts_by_image[path.name]))
            for path in group
        }
        if len(class_sets) > 1:
            quarantined_names.update(path.name for path in group)
            conflicting_exact_groups.append(
                {
                    "sha256": digest,
                    "files": [path.name for path in group],
                    "classes": {
                        path.name: sorted(class_counts_by_image[path.name])
                        for path in group
                    },
                }
            )

    groups: list[dict[str, Any]] = []
    grouped_names: set[str] = set()
    for digest, paths in perceptual_groups.items():
        clean_paths = [path for path in paths if path.name not in quarantined_names]
        if not clean_paths:
            continue
        group_counts: Counter[int] = Counter()
        for path in clean_paths:
            add_group_counts(group_counts, class_counts_by_image[path.name])
            grouped_names.add(path.name)
        groups.append(
            {
                "id": digest,
                "paths": clean_paths,
                "class_counts": group_counts,
            }
        )

    expected_clean_names = {path.name for path in image_paths} - quarantined_names
    if grouped_names != expected_clean_names:
        missing = sorted(expected_clean_names - grouped_names)
        raise RuntimeError(f"Images missing from duplicate groups: {missing[:10]}")

    clean_class_counts: Counter[int] = Counter()
    for group in groups:
        add_group_counts(clean_class_counts, group["class_counts"])
    target_val_counts = {
        class_id: max(1, round(count * args.val_fraction))
        for class_id, count in clean_class_counts.items()
    }

    rng = random.Random(args.seed)
    rng.shuffle(groups)
    val_group_ids: set[str] = set()
    val_class_counts: Counter[int] = Counter()

    for class_id in sorted(target_val_counts, key=lambda item: (clean_class_counts[item], item)):
        target = target_val_counts[class_id]
        while val_class_counts[class_id] < target:
            candidates = [
                group
                for group in groups
                if group["id"] not in val_group_ids and group["class_counts"][class_id] > 0
            ]
            if not candidates:
                break
            remaining = target - val_class_counts[class_id]

            def candidate_key(group: dict[str, Any]) -> tuple[int, int, float]:
                class_contribution = group["class_counts"][class_id]
                overshoot = max(0, class_contribution - remaining)
                total_size = len(group["paths"])
                return overshoot, abs(class_contribution - remaining), total_size

            best_key = min(candidate_key(group) for group in candidates)
            tied = [group for group in candidates if candidate_key(group) == best_key]
            chosen = rng.choice(tied)
            val_group_ids.add(chosen["id"])
            add_group_counts(val_class_counts, chosen["class_counts"])

    train_paths: list[Path] = []
    val_paths: list[Path] = []
    train_class_counts: Counter[int] = Counter()
    for group in groups:
        if group["id"] in val_group_ids:
            val_paths.extend(group["paths"])
        else:
            train_paths.extend(group["paths"])
            add_group_counts(train_class_counts, group["class_counts"])

    train_paths.sort(key=lambda path: path.name)
    val_paths.sort(key=lambda path: path.name)
    quarantined_paths = sorted(
        (image_dir / name for name in quarantined_names),
        key=lambda path: path.name,
    )

    (split_dir / "train.txt").write_text(
        "\n".join(str(path) for path in train_paths) + "\n",
        encoding="utf-8",
    )
    (split_dir / "val.txt").write_text(
        "\n".join(str(path) for path in val_paths) + "\n",
        encoding="utf-8",
    )
    (split_dir / "quarantine-conflicting-labels.txt").write_text(
        "\n".join(str(path) for path in quarantined_paths) + ("\n" if quarantined_paths else ""),
        encoding="utf-8",
    )
    # Filename-only manifests are portable between the local workstation and a
    # Linux training server. The absolute manifests above remain the files YOLO
    # consumes on the machine where this script is run.
    (split_dir / "train-files.txt").write_text(
        "\n".join(path.name for path in train_paths) + "\n",
        encoding="utf-8",
    )
    (split_dir / "val-files.txt").write_text(
        "\n".join(path.name for path in val_paths) + "\n",
        encoding="utf-8",
    )
    (split_dir / "quarantine-files.txt").write_text(
        "\n".join(path.name for path in quarantined_paths) + ("\n" if quarantined_paths else ""),
        encoding="utf-8",
    )

    yaml_lines = [
        f"path: {yaml_quote(str(data_root))}",
        "train: splits/train.txt",
        "val: splits/val.txt",
        "names:",
    ]
    yaml_lines.extend(
        f"  {class_id}: {yaml_quote(class_names_zh[class_id])}"
        for class_id in sorted(class_names_zh)
    )
    (data_root / "dataset.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    # Ultralytics downloads a large Unicode font whenever class names contain
    # Chinese characters. Keep the Chinese dataset config for the product and
    # reports, while using an ID-equivalent English config for server training.
    training_yaml_lines = [
        f"path: {yaml_quote(str(data_root))}",
        "train: splits/train.txt",
        "val: splits/val.txt",
        "names:",
    ]
    training_yaml_lines.extend(
        f"  {class_id}: {yaml_quote(class_names_en[class_id])}"
        for class_id in sorted(class_names_en)
    )
    (data_root / "dataset-training.yaml").write_text(
        "\n".join(training_yaml_lines) + "\n",
        encoding="utf-8",
    )

    split_report = {
        "seed": args.seed,
        "val_fraction_requested": args.val_fraction,
        "image_count_original": len(image_paths),
        "image_count_clean": len(train_paths) + len(val_paths),
        "train_image_count": len(train_paths),
        "val_image_count": len(val_paths),
        "val_fraction_actual": len(val_paths) / (len(train_paths) + len(val_paths)),
        "quarantined_image_count": len(quarantined_paths),
        "conflicting_exact_duplicate_groups": conflicting_exact_groups,
        "perceptual_group_count": len(groups),
        "multi_image_perceptual_group_count": sum(1 for group in groups if len(group["paths"]) > 1),
        "class_counts": [
            {
                "class_id": class_id,
                "name_zh": class_names_zh[class_id],
                "clean_total": clean_class_counts[class_id],
                "train": train_class_counts[class_id],
                "val": val_class_counts[class_id],
                "val_fraction": val_class_counts[class_id] / clean_class_counts[class_id],
                "target_val": target_val_counts[class_id],
            }
            for class_id in sorted(class_names_zh)
        ],
    }
    report_path = split_dir / "split-report.json"
    report_path.write_text(json.dumps(split_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(split_report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
