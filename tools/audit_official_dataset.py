from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def describe(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "p05": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p95": None,
            "max": None,
            "mean": None,
        }
    return {
        "count": len(values),
        "min": min(values),
        "p05": percentile(values, 0.05),
        "p25": percentile(values, 0.25),
        "median": percentile(values, 0.5),
        "p75": percentile(values, 0.75),
        "p95": percentile(values, 0.95),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def difference_hash(image: Image.Image) -> str:
    grayscale = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    # Pillow 12 renamed the legacy sequence accessor. Both return the same
    # row-major pixel values, so keep the hash stable across server images.
    flattened_data = getattr(grayscale, "get_flattened_data", grayscale.getdata)
    pixels = list(flattened_data())
    bits = []
    for row in range(8):
        offset = row * 9
        for column in range(8):
            bits.append(pixels[offset + column] > pixels[offset + column + 1])
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def source_prefix(stem: str) -> str:
    if "_" not in stem:
        return "other"
    return stem.split("_", 1)[0].lower()


def load_class_map(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return sorted(rows, key=lambda item: int(item["class_id"]))


def parse_label(path: Path) -> tuple[list[tuple[int, float, float, float, float]], list[str]]:
    boxes: list[tuple[int, float, float, float, float]] = []
    errors: list[str] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            errors.append(f"line {line_number}: expected 5 values, found {len(parts)}")
            continue
        try:
            class_id = int(parts[0])
            x_center, y_center, width, height = map(float, parts[1:])
        except ValueError as exc:
            errors.append(f"line {line_number}: {exc}")
            continue
        boxes.append((class_id, x_center, y_center, width, height))
    return boxes, errors


def save_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def render_contact_sheets(
    output_dir: Path,
    samples_by_class: dict[int, list[Path]],
    labels_by_stem: dict[str, list[tuple[int, float, float, float, float]]],
    class_map: dict[int, dict[str, str]],
) -> list[str]:
    output_files: list[str] = []
    font = ImageFont.load_default()
    cell_width = 360
    cell_height = 300
    columns = 3
    classes_per_sheet = 4
    colors = [
        "#ef4444",
        "#f97316",
        "#eab308",
        "#22c55e",
        "#06b6d4",
        "#3b82f6",
        "#8b5cf6",
        "#ec4899",
    ]

    class_ids = sorted(class_map)
    for sheet_index in range(0, len(class_ids), classes_per_sheet):
        sheet_classes = class_ids[sheet_index : sheet_index + classes_per_sheet]
        canvas = Image.new(
            "RGB",
            (columns * cell_width, len(sheet_classes) * cell_height),
            "white",
        )
        canvas_draw = ImageDraw.Draw(canvas)
        for row_index, class_id in enumerate(sheet_classes):
            samples = samples_by_class.get(class_id, [])[:columns]
            for column_index in range(columns):
                x_offset = column_index * cell_width
                y_offset = row_index * cell_height
                canvas_draw.rectangle(
                    (x_offset, y_offset, x_offset + cell_width - 1, y_offset + cell_height - 1),
                    outline="#cbd5e1",
                )
                if column_index >= len(samples):
                    continue
                image_path = samples[column_index]
                with Image.open(image_path) as raw_image:
                    source_width, source_height = raw_image.size
                    image = raw_image.convert("RGB")
                image.thumbnail((cell_width - 16, cell_height - 54), Image.Resampling.LANCZOS)
                image_x = x_offset + (cell_width - image.width) // 2
                image_y = y_offset + 38 + (cell_height - 46 - image.height) // 2
                scale_x = image.width / source_width
                scale_y = image.height / source_height
                draw = ImageDraw.Draw(image)
                for box_class, x_center, y_center, width, height in labels_by_stem[image_path.stem]:
                    left = (x_center - width / 2) * source_width * scale_x
                    top = (y_center - height / 2) * source_height * scale_y
                    right = (x_center + width / 2) * source_width * scale_x
                    bottom = (y_center + height / 2) * source_height * scale_y
                    draw.rectangle(
                        (left, top, right, bottom),
                        outline=colors[box_class % len(colors)],
                        width=3,
                    )
                    draw.text(
                        (max(0, left + 2), max(0, top + 2)),
                        str(box_class),
                        fill=colors[box_class % len(colors)],
                        font=font,
                        stroke_width=1,
                        stroke_fill="white",
                    )
                canvas.paste(image, (image_x, image_y))
                title = (
                    f"class {class_id}: {class_map[class_id]['name_en']} | "
                    f"{image_path.name}"
                )
                canvas_draw.text((x_offset + 8, y_offset + 8), title[:54], fill="#0f172a", font=font)
        output_path = output_dir / f"contact-sheet-{sheet_index // classes_per_sheet + 1:02d}.jpg"
        canvas.save(output_path, quality=90)
        output_files.append(str(output_path))
    return output_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the official crop pest competition dataset.")
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260729)
    args = parser.parse_args()

    dataset_root = args.dataset_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    image_dir = dataset_root / "训练数据" / "图片"
    label_dir = dataset_root / "训练数据" / "标签"
    class_map_rows = load_class_map(dataset_root / "文档" / "类别中英文对照.csv")
    class_map = {int(row["class_id"]): row for row in class_map_rows}

    image_paths = sorted(path for path in image_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)
    label_paths = sorted(label_dir.glob("*.txt"))
    images_by_stem = {path.stem: path for path in image_paths}
    labels_by_path_stem = {path.stem: path for path in label_paths}

    missing_labels = sorted(set(images_by_stem) - set(labels_by_path_stem))
    missing_images = sorted(set(labels_by_path_stem) - set(images_by_stem))

    invalid_records: list[dict[str, Any]] = []
    boxes_by_class: dict[int, list[dict[str, Any]]] = defaultdict(list)
    images_by_class: dict[int, set[str]] = defaultdict(set)
    samples_by_class: dict[int, list[Path]] = defaultdict(list)
    labels_by_stem: dict[str, list[tuple[int, float, float, float, float]]] = {}
    boxes_per_image: list[int] = []
    empty_labels: list[str] = []
    multi_class_images = 0
    source_counts: Counter[str] = Counter()
    dimension_counts: Counter[str] = Counter()
    image_widths: list[float] = []
    image_heights: list[float] = []
    exact_hashes: dict[str, list[str]] = defaultdict(list)
    difference_hashes: dict[str, list[str]] = defaultdict(list)
    corrupt_images: list[str] = []
    rng = random.Random(args.seed)

    shuffled_images = image_paths[:]
    rng.shuffle(shuffled_images)
    for image_path in shuffled_images:
        source_counts[source_prefix(image_path.stem)] += 1
        try:
            with Image.open(image_path) as image:
                image.load()
                width, height = image.size
                image_widths.append(float(width))
                image_heights.append(float(height))
                dimension_counts[f"{width}x{height}"] += 1
                difference_hashes[difference_hash(image)].append(image_path.name)
        except Exception as exc:  # Pillow raises multiple exception types for corrupt input.
            corrupt_images.append(f"{image_path.name}: {exc}")
            continue

        exact_hashes[file_sha256(image_path)].append(image_path.name)
        label_path = labels_by_path_stem.get(image_path.stem)
        if label_path is None:
            continue
        boxes, parse_errors = parse_label(label_path)
        labels_by_stem[image_path.stem] = boxes
        for error in parse_errors:
            invalid_records.append({"file": label_path.name, "issue": error})
        boxes_per_image.append(len(boxes))
        if not boxes:
            empty_labels.append(label_path.name)
        classes_in_image = {box[0] for box in boxes}
        if len(classes_in_image) > 1:
            multi_class_images += 1

        for class_id, x_center, y_center, box_width, box_height in boxes:
            if class_id not in class_map:
                invalid_records.append({"file": label_path.name, "issue": f"unknown class id {class_id}"})
                continue
            values = (x_center, y_center, box_width, box_height)
            if any(not math.isfinite(value) for value in values):
                invalid_records.append({"file": label_path.name, "issue": "non-finite coordinate"})
                continue
            if not (0 <= x_center <= 1 and 0 <= y_center <= 1):
                invalid_records.append({"file": label_path.name, "issue": "center outside [0, 1]"})
            if not (0 < box_width <= 1 and 0 < box_height <= 1):
                invalid_records.append({"file": label_path.name, "issue": "box size outside (0, 1]"})
            if x_center - box_width / 2 < -1e-6 or x_center + box_width / 2 > 1 + 1e-6:
                invalid_records.append({"file": label_path.name, "issue": "box exceeds horizontal boundary"})
            if y_center - box_height / 2 < -1e-6 or y_center + box_height / 2 > 1 + 1e-6:
                invalid_records.append({"file": label_path.name, "issue": "box exceeds vertical boundary"})

            box_record = {
                "file": image_path.name,
                "area_ratio": box_width * box_height,
                "width_ratio": box_width,
                "height_ratio": box_height,
                "width_pixels": box_width * width,
                "height_pixels": box_height * height,
            }
            boxes_by_class[class_id].append(box_record)
            images_by_class[class_id].add(image_path.name)
            if len(samples_by_class[class_id]) < 12:
                samples_by_class[class_id].append(image_path)

    class_stats: list[dict[str, Any]] = []
    all_box_areas: list[float] = []
    all_box_width_pixels: list[float] = []
    all_box_height_pixels: list[float] = []
    for class_id in sorted(class_map):
        records = boxes_by_class[class_id]
        areas = [record["area_ratio"] for record in records]
        widths_pixels = [record["width_pixels"] for record in records]
        heights_pixels = [record["height_pixels"] for record in records]
        all_box_areas.extend(areas)
        all_box_width_pixels.extend(widths_pixels)
        all_box_height_pixels.extend(heights_pixels)
        class_stats.append(
            {
                "class_id": class_id,
                "name_zh": class_map[class_id]["name_zh"],
                "name_en": class_map[class_id]["name_en"],
                "crop": class_map[class_id]["crop"],
                "category_type": class_map[class_id]["category_type"],
                "source_dataset": class_map[class_id]["source_dataset"],
                "image_count": len(images_by_class[class_id]),
                "box_count": len(records),
                "median_area_ratio": percentile(areas, 0.5),
                "p05_area_ratio": percentile(areas, 0.05),
                "median_box_width_pixels": percentile(widths_pixels, 0.5),
                "median_box_height_pixels": percentile(heights_pixels, 0.5),
                "boxes_under_32px": sum(
                    1 for record in records if min(record["width_pixels"], record["height_pixels"]) < 32
                ),
            }
        )

    exact_duplicate_groups = [files for files in exact_hashes.values() if len(files) > 1]
    difference_hash_groups = [files for files in difference_hashes.values() if len(files) > 1]
    top_dimensions = [
        {"size": size, "count": count}
        for size, count in dimension_counts.most_common(20)
    ]

    report = {
        "dataset_root": str(dataset_root),
        "seed": args.seed,
        "image_count": len(image_paths),
        "label_count": len(label_paths),
        "class_count": len(class_map),
        "box_count": sum(len(records) for records in boxes_by_class.values()),
        "missing_labels": missing_labels,
        "missing_images": missing_images,
        "empty_label_count": len(empty_labels),
        "empty_labels": empty_labels,
        "multi_class_image_count": multi_class_images,
        "corrupt_images": corrupt_images,
        "invalid_record_count": len(invalid_records),
        "source_prefix_counts": dict(source_counts),
        "image_width_summary": describe(image_widths),
        "image_height_summary": describe(image_heights),
        "boxes_per_image_summary": describe([float(value) for value in boxes_per_image]),
        "box_area_ratio_summary": describe(all_box_areas),
        "box_width_pixels_summary": describe(all_box_width_pixels),
        "box_height_pixels_summary": describe(all_box_height_pixels),
        "boxes_with_min_side_under_16px": sum(
            1 for width, height in zip(all_box_width_pixels, all_box_height_pixels) if min(width, height) < 16
        ),
        "boxes_with_min_side_under_32px": sum(
            1 for width, height in zip(all_box_width_pixels, all_box_height_pixels) if min(width, height) < 32
        ),
        "top_image_dimensions": top_dimensions,
        "exact_duplicate_group_count": len(exact_duplicate_groups),
        "exact_duplicate_groups": exact_duplicate_groups,
        "difference_hash_group_count": len(difference_hash_groups),
        "difference_hash_groups_sample": difference_hash_groups[:50],
        "class_stats": class_stats,
    }

    report_path = output_dir / "dataset-audit.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    save_csv(
        output_dir / "class-stats.csv",
        class_stats,
        [
            "class_id",
            "name_zh",
            "name_en",
            "crop",
            "category_type",
            "source_dataset",
            "image_count",
            "box_count",
            "median_area_ratio",
            "p05_area_ratio",
            "median_box_width_pixels",
            "median_box_height_pixels",
            "boxes_under_32px",
        ],
    )
    save_csv(output_dir / "invalid-records.csv", invalid_records, ["file", "issue"])
    contact_sheets = render_contact_sheets(
        output_dir,
        samples_by_class,
        labels_by_stem,
        class_map,
    )
    print(
        json.dumps(
            {
                "report": str(report_path),
                "class_stats": str(output_dir / "class-stats.csv"),
                "invalid_records": str(output_dir / "invalid-records.csv"),
                "contact_sheets": contact_sheets,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
