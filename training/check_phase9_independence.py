"""Check file, decoded-pixel, and perceptual-hash independence between splits."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

try:
    import cv2
except ImportError:  # pragma: no cover - the server image includes OpenCV
    cv2 = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decoded_pixel_hash(path: Path) -> tuple[str, tuple[int, int]]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        rgb.load()
        pixels = np.asarray(rgb, dtype=np.uint8)
        digest = hashlib.sha256()
        digest.update(f"{rgb.width}x{rgb.height}:".encode("ascii"))
        digest.update(pixels.tobytes(order="C"))
        return digest.hexdigest(), (rgb.width, rgb.height)


def perceptual_hash(path: Path) -> str:
    with Image.open(path) as image:
        gray = np.asarray(
            ImageOps.grayscale(image).resize((32, 32), Image.Resampling.LANCZOS),
            dtype=np.float32,
        )
    if cv2 is None:
        raise RuntimeError("OpenCV is required for the 16x16 DCT perceptual hash")
    coefficients = cv2.dct(gray)[:16, :16]
    median = float(np.median(coefficients[1:, :]))
    bits = (coefficients > median).reshape(-1)
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:064x}"


def read_paths(path: Path) -> list[Path]:
    return [Path(line.strip()) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def group_duplicates(values: dict[str, list[str]]) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for value, paths in values.items():
        groups[value].extend(paths)
    return sorted((sorted(paths) for paths in groups.values() if len(paths) > 1), key=lambda item: (len(item), item))


def hamming_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def summarize_split(paths: list[Path]) -> tuple[dict[str, object], dict[str, dict[str, str]]]:
    errors: list[dict[str, str]] = []
    file_hashes: dict[str, list[str]] = defaultdict(list)
    pixel_hashes: dict[str, list[str]] = defaultdict(list)
    perceptual_hashes: dict[str, list[str]] = defaultdict(list)
    dimensions: dict[str, list[int]] = {}
    for path in paths:
        key = str(path)
        if not path.is_file():
            errors.append({"path": key, "error": "missing_file"})
            continue
        try:
            file_hashes[sha256_file(path)].append(key)
            pixel_hash, size = decoded_pixel_hash(path)
            pixel_hashes[pixel_hash].append(key)
            perceptual_hashes[perceptual_hash(path)].append(key)
            dimensions[key] = list(size)
        except Exception as exc:  # keep the report complete for all paths
            errors.append({"path": key, "error": f"{type(exc).__name__}: {exc}"})
    summary = {
        "listed_count": len(paths),
        "path_unique_count": len({str(path) for path in paths}),
        "processed_count": sum(len(paths) for paths in file_hashes.values()),
        "missing_or_decode_error_count": len(errors),
        "file_sha_unique_count": len(file_hashes),
        "decoded_pixel_sha_unique_count": len(pixel_hashes),
        "phash_unique_count": len(perceptual_hashes),
        "file_sha_duplicate_groups": group_duplicates(file_hashes),
        "decoded_pixel_duplicate_groups": group_duplicates(pixel_hashes),
        "phash_exact_duplicate_groups": group_duplicates(perceptual_hashes),
        "errors": errors,
    }
    records = {
        "file_sha": file_hashes,
        "pixel_sha": pixel_hashes,
        "phash": perceptual_hashes,
    }
    return summary, records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train_list", type=Path)
    parser.add_argument("frozen_list", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--near-threshold", type=int, default=8)
    args = parser.parse_args()

    train_paths = read_paths(args.train_list)
    frozen_paths = read_paths(args.frozen_list)
    train_summary, train_records = summarize_split(train_paths)
    frozen_summary, frozen_records = summarize_split(frozen_paths)

    near_pairs: list[dict[str, object]] = []
    frozen_phashes = list(frozen_records["phash"].items())
    for train_hash, train_paths_for_hash in train_records["phash"].items():
        for frozen_hash, frozen_paths_for_hash in frozen_phashes:
            distance = hamming_distance(train_hash, frozen_hash)
            if 0 < distance <= args.near_threshold:
                for train_path in train_paths_for_hash:
                    for frozen_path in frozen_paths_for_hash:
                        near_pairs.append({"distance": distance, "train_path": train_path, "frozen_path": frozen_path})
    near_pairs.sort(key=lambda item: (int(item["distance"]), str(item["train_path"]), str(item["frozen_path"])))

    cross_file = sorted(set(train_records["file_sha"]) & set(frozen_records["file_sha"]))
    cross_pixel = sorted(set(train_records["pixel_sha"]) & set(frozen_records["pixel_sha"]))
    cross_phash = sorted(set(train_records["phash"]) & set(frozen_records["phash"]))
    exact_phash_pairs = [
        {"phash": value, "train_paths": train_records["phash"][value], "frozen_paths": frozen_records["phash"][value]}
        for value in cross_phash
    ]
    errors = train_summary["errors"] + frozen_summary["errors"]
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "tool": "training/check_phase9_independence.py",
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pillow": Image.__version__,
            "opencv": getattr(cv2, "__version__", None),
        },
        "algorithm": {
            "decoded_pixel": "PIL RGB decode; width/height plus C-order RGB bytes SHA-256",
            "perceptual": "PIL grayscale 32x32, OpenCV DCT top-left 16x16, median threshold, 256-bit hash",
            "near_phash_hamming_threshold": args.near_threshold,
        },
        "train": train_summary,
        "frozen": frozen_summary,
        "cross_split": {
            "file_sha_intersection_count": len(cross_file),
            "file_sha_intersection": cross_file,
            "decoded_pixel_sha_intersection_count": len(cross_pixel),
            "decoded_pixel_sha_intersection": cross_pixel,
            "phash_exact_intersection_count": len(cross_phash),
            "phash_exact_intersection": cross_phash,
            "phash_exact_pairs": exact_phash_pairs,
            "near_phash_pair_count": len(near_pairs),
            "near_phash_pairs": near_pairs,
        },
        "gate": {
            "status": "pass" if not errors and not cross_pixel else "block",
            "blocking_reasons": [
                *(("missing_or_decode_error",) if errors else ()),
                *(("decoded_pixel_cross_split_duplicate",) if cross_pixel else ()),
            ],
            "near_phash_requires_manual_review": bool(near_pairs),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
