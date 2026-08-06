from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image


CLASS_NAMES = {
    8: "08_blister_beetle",
    10: "10_mirid_bugs",
    13: "13_grasshoppers",
    15: "15_legume_blister_beetle",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_images(path: Path, project_root: Path) -> list[Path]:
    images: list[Path] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        candidate = Path(raw_line.strip())
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
    rows: list[tuple[int, float, float, float, float]] = []
    if not path.exists():
        return rows
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.split()
        if len(parts) != 5:
            continue
        class_id, cx, cy, width, height = map(float, parts)
        rows.append((int(class_id), cx, cy, width, height))
    return rows


def internal_split(image_path: Path, seed: int, val_percent: int) -> str:
    token = hashlib.sha1(f"{seed}:{image_path.name}".encode()).digest()[0]
    return "val" if token < round(256 * val_percent / 100) else "train"


def crop_bounds(
    width: int,
    height: int,
    cx: float,
    cy: float,
    box_width: float,
    box_height: float,
    expand: float,
) -> tuple[int, int, int, int]:
    center_x, center_y = cx * width, cy * height
    crop_width = max(2.0, box_width * width * (1.0 + 2.0 * expand))
    crop_height = max(2.0, box_height * height * (1.0 + 2.0 * expand))
    left = max(0, int(round(center_x - crop_width / 2)))
    top = max(0, int(round(center_y - crop_height / 2)))
    right = min(width, int(round(center_x + crop_width / 2)))
    bottom = min(height, int(round(center_y + crop_height / 2)))
    return left, top, max(left + 1, right), max(top + 1, bottom)


def write_crops(
    image_paths: list[Path],
    output: Path,
    split_policy: str,
    seed: int,
    val_percent: int,
    expand: float,
) -> tuple[Counter, Counter]:
    image_counts: Counter = Counter()
    crop_counts: Counter = Counter()
    for image_path in image_paths:
        labels = [row for row in parse_labels(label_path(image_path)) if row[0] in CLASS_NAMES]
        if not labels:
            continue
        split = (
            internal_split(image_path, seed, val_percent)
            if split_policy == "internal"
            else "official_eval"
        )
        image_counts[split] += 1
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            for box_index, (class_id, cx, cy, box_width, box_height) in enumerate(labels):
                bounds = crop_bounds(
                    image.width,
                    image.height,
                    cx,
                    cy,
                    box_width,
                    box_height,
                    expand,
                )
                crop = image.crop(bounds)
                destination = output / split / CLASS_NAMES[class_id]
                destination.mkdir(parents=True, exist_ok=True)
                stable = hashlib.sha1(str(image_path).encode()).hexdigest()[:10]
                filename = f"{image_path.stem}_{stable}_{box_index:03d}.jpg"
                crop.save(destination / filename, format="JPEG", quality=95, optimize=True)
                crop_counts[(split, class_id)] += 1
    return image_counts, crop_counts


def cross_split_duplicates(output: Path) -> dict:
    hashes: dict[str, list[str]] = {}
    for split in ("train", "val", "official_eval"):
        for path in sorted((output / split).glob("*/*")):
            digest = sha256(path)
            hashes.setdefault(digest, []).append(str(path.relative_to(output)))
    conflicts = [paths for paths in hashes.values() if len({Path(path).parts[0] for path in paths}) > 1]
    return {
        "group_count": len(conflicts),
        "file_count": sum(len(paths) for paths in conflicts),
        "examples": conflicts[:10],
    }


def write_source_lists(
    output: Path,
    train_images: list[Path],
    official_val_images: list[Path],
    seed: int,
    val_percent: int,
) -> dict[str, Path]:
    selected_train = [
        path
        for path in train_images
        if any(row[0] in CLASS_NAMES for row in parse_labels(label_path(path)))
    ]
    paths_by_split = {
        "train": [path for path in selected_train if internal_split(path, seed, val_percent) == "train"],
        "val": [path for path in selected_train if internal_split(path, seed, val_percent) == "val"],
        "official_eval": list(official_val_images),
    }
    outputs: dict[str, Path] = {}
    for split, paths in paths_by_split.items():
        destination = output / f"source-{split}.txt"
        destination.write_text("".join(f"{path}\n" for path in paths), encoding="utf-8")
        outputs[split] = destination
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a leakage-safe 4-class crop classification pilot.")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--official-train", type=Path, required=True)
    parser.add_argument("--official-val", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--internal-val-percent", type=int, default=15)
    parser.add_argument("--crop-expand", type=float, default=0.5)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--source-lists-only", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.expanduser().resolve()
    official_train_list = args.official_train.expanduser().resolve(strict=True)
    official_val_list = args.official_val.expanduser().resolve(strict=True)
    output = args.output.expanduser().resolve()
    if args.source_lists_only:
        output.resolve(strict=True)
        source_lists = write_source_lists(
            output,
            read_images(official_train_list, project_root),
            read_images(official_val_list, project_root),
            args.seed,
            args.internal_val_percent,
        )
        print(
            json.dumps(
                {
                    split: {"path": str(path), "sha256": sha256(path)}
                    for split, path in source_lists.items()
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if output.exists():
        if not args.force:
            raise FileExistsError(f"output exists; pass --force to rebuild: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    train_images = read_images(official_train_list, project_root)
    official_val_images = read_images(official_val_list, project_root)
    internal_images, internal_crops = write_crops(
        train_images,
        output,
        "internal",
        args.seed,
        args.internal_val_percent,
        args.crop_expand,
    )
    eval_images, eval_crops = write_crops(
        official_val_images,
        output,
        "official_eval",
        args.seed,
        args.internal_val_percent,
        args.crop_expand,
    )
    source_lists = write_source_lists(
        output,
        train_images,
        official_val_images,
        args.seed,
        args.internal_val_percent,
    )

    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "policy": "official train only for fitting; official validation is frozen under official_eval",
        "seed": args.seed,
        "crop_expand": args.crop_expand,
        "internal_val_percent": args.internal_val_percent,
        "class_names": {str(class_id): name for class_id, name in CLASS_NAMES.items()},
        "sources": {
            "official_train": str(official_train_list),
            "official_train_sha256": sha256(official_train_list),
            "official_val": str(official_val_list),
            "official_val_sha256": sha256(official_val_list),
        },
        "source_image_counts": {
            "train": internal_images["train"],
            "val": internal_images["val"],
            "official_eval": eval_images["official_eval"],
        },
        "crop_counts": {
            split: {
                str(class_id): internal_crops[(split, class_id)] if split != "official_eval" else eval_crops[(split, class_id)]
                for class_id in CLASS_NAMES
            }
            for split in ("train", "val", "official_eval")
        },
        "cross_split_exact_duplicates": cross_split_duplicates(output),
        "source_lists": {
            split: {"path": str(path), "sha256": sha256(path)} for split, path in source_lists.items()
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
