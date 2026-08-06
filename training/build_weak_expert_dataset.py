from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from collections import Counter
from pathlib import Path
from typing import Iterable


TARGET_TO_EXPERT = {8: 0, 10: 1}
EXPERT_NAMES = {0: "Blister beetle", 1: "Mirid bugs (Miridae)"}


def read_images(path: Path, project_root: Path) -> list[Path]:
    images: list[Path] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        candidate = Path(line.strip())
        # Historical official split files contain the original server path. Use
        # the project-local symlink view so labels remain inferable and read-only.
        local_candidate = project_root / "data" / "official" / "images" / "all" / candidate.name
        if local_candidate.exists():
            candidate = local_candidate
        images.append(candidate)
    return images


def label_path(image_path: Path) -> Path:
    text = str(image_path)
    if "/images/" in text:
        text = text.replace("/images/", "/labels/", 1)
    elif "\\images\\" in text:
        text = text.replace("\\images\\", "\\labels\\", 1)
    return Path(text).with_suffix(".txt")


def parse_labels(path: Path) -> list[tuple[int, float, float, float, float]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        class_id, cx, cy, width, height = map(float, parts)
        rows.append((int(class_id), cx, cy, width, height))
    return rows


def stable_key(path: Path) -> str:
    return hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:10]


def select_limited(items: list[Path], limit: int | None, seed: int) -> list[Path]:
    if limit is None or len(items) <= limit:
        return sorted(items, key=str)
    shuffled = sorted(items, key=lambda item: hashlib.sha1(f"{seed}:{item}".encode()).hexdigest())
    return sorted(shuffled[:limit], key=str)


def source_record(path: Path, split: str, source: str) -> dict:
    labels = parse_labels(label_path(path))
    target_labels = [row for row in labels if row[0] in TARGET_TO_EXPERT]
    return {
        "path": path,
        "split": split,
        "source": source,
        "labels": labels,
        "target_labels": target_labels,
    }


def write_sample(record: dict, root: Path, split: str, index: int, keep_targets: bool) -> tuple[Path, Path, int]:
    source = record["path"]
    prefix = f"{record['source']}_{record['split']}_{index:05d}_{stable_key(source)}"
    image_name = prefix + source.suffix.lower()
    image_out = root / "images" / split / image_name
    label_out = root / "labels" / split / (Path(image_name).stem + ".txt")
    image_out.parent.mkdir(parents=True, exist_ok=True)
    label_out.parent.mkdir(parents=True, exist_ok=True)
    image_out.symlink_to(source)
    rows = record["target_labels"] if keep_targets else []
    label_out.write_text(
        "".join(
            f"{TARGET_TO_EXPERT[class_id]} {cx:.8f} {cy:.8f} {width:.8f} {height:.8f}\n"
            for class_id, cx, cy, width, height in rows
        ),
        encoding="utf-8",
    )
    return image_out, label_out, len(rows)


def write_list(path: Path, images: Iterable[Path]) -> None:
    path.write_text("".join(f"{item}\n" for item in images), encoding="utf-8")


def write_yaml(path: Path, train: Path, val: Path, test: Path | None = None) -> None:
    lines = [
        "path: /",
        f"train: {train.resolve()}",
        f"val: {val.resolve()}",
    ]
    if test:
        lines.append(f"test: {test.resolve()}")
    lines += ["names:", '  0: "Blister beetle"', '  1: "Mirid bugs (Miridae)"', ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_eval_split(records: list[dict], root: Path, split: str) -> Path:
    images: list[Path] = []
    for index, record in enumerate(records):
        image, _, _ = write_sample(record, root, split, index, keep_targets=True)
        images.append(image)
    list_path = root / f"{split}.txt"
    write_list(list_path, images)
    return list_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a balanced 2-class expert dataset for classes 8 and 10.")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--official-train", type=Path, required=True)
    parser.add_argument("--official-val", type=Path, required=True)
    parser.add_argument("--scidb-root", type=Path, required=True)
    parser.add_argument("--public-class10-max", type=int, default=210)
    parser.add_argument("--hard-negative-max", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists():
        if not args.force:
            raise FileExistsError(f"output exists; pass --force to rebuild: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    official_train_paths = read_images(args.official_train.expanduser().resolve(strict=True), project_root)
    official_val_paths = read_images(args.official_val.expanduser().resolve(strict=True), project_root)
    official_train = [source_record(path, "official_train", "official") for path in official_train_paths]
    official_val = [source_record(path, "official_val", "official") for path in official_val_paths]
    official_target = [record for record in official_train if record["target_labels"]]
    hard_negative_candidates = [
        record
        for record in official_train
        if not record["target_labels"] and any(class_id in {13, 15} for class_id, *_ in record["labels"])
    ]
    hard_negative = select_limited(hard_negative_candidates, args.hard_negative_max, args.seed)

    scidb_root = args.scidb_root.expanduser().resolve(strict=True)
    scidb_train_paths = sorted((scidb_root / "train" / "images").glob("*"))
    scidb_records = [source_record(path, "scidb_train", "scidb") for path in scidb_train_paths]
    scidb_class8 = [record for record in scidb_records if any(row[0] == 8 for row in record["labels"])]
    scidb_class10 = [record for record in scidb_records if any(row[0] == 10 for row in record["labels"])]
    scidb_class10 = select_limited(scidb_class10, args.public_class10_max, args.seed)
    scidb_selected = scidb_class8 + scidb_class10

    official_target_sorted = sorted(official_target, key=lambda record: hashlib.sha1(f"{args.seed}:{record['path']}".encode()).hexdigest())
    internal_val_count = max(1, round(len(official_target_sorted) * 0.1))
    internal_val_records = official_target_sorted[:internal_val_count]
    internal_val_keys = {record["path"] for record in internal_val_records}
    hard_negative_val = select_limited(hard_negative, max(1, round(len(hard_negative) * 0.1)), args.seed + 1)
    hard_negative_val_keys = {record["path"] for record in hard_negative_val}
    hard_negative_train = [record for record in hard_negative if record["path"] not in hard_negative_val_keys]
    train_records = [record for record in official_target_sorted if record["path"] not in internal_val_keys]
    train_records += scidb_selected
    train_records += hard_negative_train
    random.Random(args.seed).shuffle(train_records)

    train_images: list[Path] = []
    train_box_count = Counter()
    for index, record in enumerate(train_records):
        image, _, count = write_sample(record, output, "train", index, keep_targets=bool(record["target_labels"]))
        train_images.append(image)
        for class_id, *_ in record["target_labels"]:
            train_box_count[TARGET_TO_EXPERT[class_id]] += 1
    val_images: list[Path] = []
    val_box_count = Counter()
    val_records = internal_val_records + hard_negative_val
    for index, record in enumerate(val_records):
        image, _, count = write_sample(record, output, "val", index, keep_targets=bool(record["target_labels"]))
        val_images.append(image)
        for class_id, *_ in record["target_labels"]:
            val_box_count[TARGET_TO_EXPERT[class_id]] += 1
    train_list = output / "train.txt"
    val_list = output / "val.txt"
    write_list(train_list, train_images)
    write_list(val_list, val_images)
    write_yaml(output / "dataset.yaml", train_list, val_list)

    eval_records = {
        "official_eval": official_val,
        "scidb_valid_eval": [source_record(path, "scidb_valid", "scidb") for path in sorted((scidb_root / "valid" / "images").glob("*"))],
        "scidb_test_eval": [source_record(path, "scidb_test", "scidb") for path in sorted((scidb_root / "test" / "images").glob("*"))],
    }
    eval_lists = {}
    for split, records in eval_records.items():
        eval_lists[split] = build_eval_split(records, output / "eval", split)
        write_yaml(output / f"{split}.yaml", eval_lists[split], eval_lists[split], eval_lists[split])

    manifest = {
        "created_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
        "seed": args.seed,
        "policy": "classes 8/10 expert only; official validation remains frozen and is copied only for evaluation",
        "source_license": {
            "official": "competition-provided; source remains read-only",
            "scidb": "archive README/data.yaml Public Domain; ScienceDB metadata MIT; discrepancy retained for provenance review",
        },
        "selection": {
            "official_train_target_images": len(official_target),
            "official_internal_val_target_images": len(internal_val_records),
            "scidb_class8_images": len(scidb_class8),
            "scidb_class10_images_available": len([record for record in scidb_records if any(row[0] == 10 for row in record["labels"])]),
            "scidb_class10_images_selected": len(scidb_class10),
            "hard_negative_candidates_class13_or_15": len(hard_negative_candidates),
            "hard_negative_selected": len(hard_negative),
            "train_records": len(train_records),
            "val_records": len(val_records),
        },
        "train_box_counts": dict(train_box_count),
        "val_box_counts": dict(val_box_count),
        "evaluation_records": {name: len(records) for name, records in eval_records.items()},
        "paths": {"dataset_yaml": str(output / "dataset.yaml"), **{name: str(path) for name, path in eval_lists.items()}},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
