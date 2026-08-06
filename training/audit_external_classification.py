from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageOps


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit folder-labelled classification images without modifying the source dataset."
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--include-class-prefix", action="append", default=[])
    parser.add_argument("--target-class-id", type=int)
    parser.add_argument("--target-class-name")
    parser.add_argument("--reference-root", type=Path)
    parser.add_argument("--reference-files", type=Path)
    parser.add_argument("--near-threshold", type=int, default=3)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_image(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        width, height = image.size
        image_format = image.format
        mode = image.mode
        gray = ImageOps.exif_transpose(image).convert("L").resize(
            (9, 8), Image.Resampling.LANCZOS
        )
        pixels = gray.tobytes()

    difference_hash = 0
    for y in range(8):
        row = pixels[y * 9 : (y + 1) * 9]
        for x in range(8):
            difference_hash = (difference_hash << 1) | (row[x] > row[x + 1])

    return {
        "width": width,
        "height": height,
        "format": image_format,
        "mode": mode,
        "sha256": file_sha256(path),
        "dhash": f"{difference_hash:016x}",
    }


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def class_name_for(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    if len(relative.parts) < 3:
        return relative.parent.name
    return relative.parts[-2]


def selected_files(root: Path, prefixes: list[str]) -> list[Path]:
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]
    if not prefixes:
        return sorted(files)
    return sorted(
        path
        for path in files
        if any(class_name_for(path, root).startswith(prefix) for prefix in prefixes)
    )


def reference_records(root: Path, file_list: Path) -> list[dict[str, object]]:
    names = [
        line.strip()
        for line in file_list.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    records = []
    for name in names:
        path = root / name
        image = inspect_image(path)
        records.append({"name": name, **image})
    return records


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    fieldnames = [
        "relative_path",
        "source_split",
        "source_class",
        "target_class_id",
        "target_class_name",
        "status",
        "reason",
        "canonical_relative_path",
        "bytes",
        "width",
        "height",
        "format",
        "mode",
        "sha256",
        "dhash",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: record.get(key) for key in fieldnames} for record in records)


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = selected_files(root, args.include_class_prefix)
    records: list[dict[str, object]] = []
    valid_indices: list[int] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        parts = path.relative_to(root).parts
        record: dict[str, object] = {
            "relative_path": relative,
            "source_split": parts[0] if len(parts) >= 3 else "",
            "source_class": class_name_for(path, root),
            "target_class_id": args.target_class_id,
            "target_class_name": args.target_class_name,
            "bytes": path.stat().st_size,
        }
        try:
            record.update(inspect_image(path))
            record["status"] = "pending"
            record["reason"] = ""
            valid_indices.append(len(records))
        except Exception as error:  # Pillow exposes several decoder-specific errors.
            record["status"] = "reject"
            record["reason"] = f"unreadable:{type(error).__name__}:{error}"
        records.append(record)

    reference = []
    if args.reference_root and args.reference_files:
        reference = reference_records(args.reference_root.resolve(), args.reference_files.resolve())
    reference_by_sha: dict[str, list[str]] = defaultdict(list)
    for item in reference:
        reference_by_sha[str(item["sha256"])].append(str(item["name"]))

    disjoint = DisjointSet(len(records))
    for left_offset, left_index in enumerate(valid_indices):
        left = records[left_index]
        left_hash = int(str(left["dhash"]), 16)
        for right_index in valid_indices[left_offset + 1 :]:
            right = records[right_index]
            same_bytes = left["sha256"] == right["sha256"]
            distance = (left_hash ^ int(str(right["dhash"]), 16)).bit_count()
            if same_bytes or distance <= args.near_threshold:
                disjoint.union(left_index, right_index)

    components: dict[int, list[int]] = defaultdict(list)
    for index in valid_indices:
        components[disjoint.find(index)].append(index)

    reference_near_count = 0
    for index in valid_indices:
        record = records[index]
        exact_matches = reference_by_sha.get(str(record["sha256"]), [])
        near_matches = []
        if not exact_matches:
            image_hash = int(str(record["dhash"]), 16)
            near_matches = [
                str(item["name"])
                for item in reference
                if (image_hash ^ int(str(item["dhash"]), 16)).bit_count()
                <= args.near_threshold
            ]
        if exact_matches or near_matches:
            record["status"] = "reject"
            kind = "reference_exact" if exact_matches else "reference_near"
            matches = exact_matches or near_matches
            record["reason"] = f"{kind}:{'|'.join(matches)}"
            reference_near_count += bool(near_matches)

    duplicate_extra_count = 0
    for component in components.values():
        eligible = [index for index in component if records[index]["status"] == "pending"]
        if not eligible:
            continue
        canonical = max(
            eligible,
            key=lambda index: (
                int(records[index]["width"]) * int(records[index]["height"]),
                int(records[index]["bytes"]),
                str(records[index]["relative_path"]),
            ),
        )
        canonical_path = str(records[canonical]["relative_path"])
        records[canonical]["status"] = "candidate"
        records[canonical]["canonical_relative_path"] = canonical_path
        for index in eligible:
            records[index]["canonical_relative_path"] = canonical_path
            if index == canonical:
                continue
            records[index]["status"] = "reject"
            records[index]["reason"] = f"duplicate_or_near_duplicate:{canonical_path}"
            duplicate_extra_count += 1

    status_counts = Counter(str(record["status"]) for record in records)
    reason_counts = Counter(
        str(record["reason"]).split(":", 1)[0]
        for record in records
        if record.get("reason")
    )
    summary = {
        "source_root": str(root),
        "source_is_read_only": True,
        "class_prefixes": args.include_class_prefix,
        "target_mapping": {
            "class_id": args.target_class_id,
            "class_name": args.target_class_name,
        },
        "raw_file_count": len(records),
        "status_counts": dict(status_counts),
        "reason_counts": dict(reason_counts),
        "duplicate_or_near_duplicate_extra_count": duplicate_extra_count,
        "near_duplicate_hamming_threshold": args.near_threshold,
        "reference": {
            "root": str(args.reference_root.resolve()) if args.reference_root else None,
            "file_list": str(args.reference_files.resolve()) if args.reference_files else None,
            "image_count": len(reference),
            "near_overlap_count": reference_near_count,
        },
        "provenance_and_license": "missing; must be supplied before competition submission or redistribution",
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(output_dir / "manifest.csv", records)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
