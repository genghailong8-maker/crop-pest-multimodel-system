"""Build Phase 9 unified detector manifests without mutating source data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

try:
    import cv2
except ImportError:  # Local planning/test environments may not ship OpenCV.
    cv2 = None

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_weak_public_smoke import NAMES, digest, normalize_official, read_list, write_list


def validate_image_file(path: Path) -> None:
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        tail = path.read_bytes().rstrip(b"\x00\t\r\n ")[-2:]
        if tail != b"\xff\xd9":
            raise ValueError(f"JPEG 缺少完整结束标记：{path}")
    saved_stderr = os.dup(2)
    try:
        with tempfile.TemporaryFile() as diagnostics:
            os.dup2(diagnostics.fileno(), 2)
            try:
                with Image.open(path) as image:
                    image.load()
            finally:
                os.dup2(saved_stderr, 2)
            diagnostics.seek(0)
            warning = diagnostics.read().decode("utf-8", errors="replace").strip()
            if warning:
                raise ValueError(f"图片解码警告：{path}: {warning}")
        if cv2 is not None:
            with tempfile.TemporaryFile() as diagnostics:
                os.dup2(diagnostics.fileno(), 2)
                try:
                    decoded = cv2.imread(str(path), cv2.IMREAD_COLOR)
                finally:
                    os.dup2(saved_stderr, 2)
                diagnostics.seek(0)
                warning = diagnostics.read().decode("utf-8", errors="replace").strip()
                if decoded is None or warning:
                    raise ValueError(f"OpenCV 解码异常：{path}: {warning or '未返回图像'}")
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"图片解码校验失败：{path}: {exc}") from exc
    finally:
        os.close(saved_stderr)


def label_path(image: Path, official_root: Path) -> Path:
    if image.parent == official_root / "images" / "all":
        return official_root / "labels" / "all" / f"{image.stem}.txt"
    parts = list(image.parts)
    try:
        index = len(parts) - 1 - parts[::-1].index("images")
    except ValueError as exc:
        raise ValueError(f"无法推导标签路径：{image}") from exc
    parts[index] = "labels"
    return Path(*parts).with_suffix(".txt")


def validate_labels(image: Path, official_root: Path) -> list[int]:
    path = label_path(image, official_root)
    if not path.is_file():
        raise ValueError(f"图片缺少标签：{image}")
    classes: list[int] = []
    seen_rows: set[tuple[str, ...]] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"标签字段数错误：{path}:{line_number}")
        row = tuple(fields)
        if row in seen_rows:
            raise ValueError(f"标签包含重复框：{path}:{line_number}")
        seen_rows.add(row)
        class_id = int(fields[0])
        geometry = [float(value) for value in fields[1:]]
        if class_id not in range(16) or any(value < 0 or value > 1 for value in geometry):
            raise ValueError(f"标签越界：{path}:{line_number}")
        classes.append(class_id)
    if not classes:
        raise ValueError(f"标签为空：{path}")
    return classes


def stratified_split(entries: list[Path], official_root: Path, fraction: float, seed: int) -> tuple[list[Path], list[Path], Counter[int]]:
    groups: dict[int, list[Path]] = defaultdict(list)
    all_classes: Counter[int] = Counter()
    for image in entries:
        classes = validate_labels(image, official_root)
        all_classes.update(classes)
        groups[min(classes)].append(image)
    rng = random.Random(seed)
    train: list[Path] = []
    val: list[Path] = []
    for class_id in sorted(groups):
        group = sorted(groups[class_id], key=str)
        rng.shuffle(group)
        val_count = max(1, round(len(group) * fraction)) if len(group) > 1 else 0
        val.extend(group[:val_count])
        train.extend(group[val_count:])
    return sorted(train, key=str), sorted(val, key=str), all_classes


def yaml_text(train: Path, val: Path, test: Path | None = None) -> str:
    lines = ["path: /", f"train: {train}", f"val: {val}"]
    if test:
        lines.append(f"test: {test}")
    lines.append("names:")
    lines.extend(f"  {index}: {json.dumps(name)}" for index, name in enumerate(NAMES))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--dev-val-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=20260729)
    args = parser.parse_args()
    if not 0.05 <= args.dev_val_fraction <= 0.30:
        raise ValueError("dev-val-fraction 必须在 0.05 到 0.30 之间")

    project = args.project_root.resolve()
    output = args.output_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    official = project / "data" / "official"
    plantdoc = project / "artifacts" / "public" / "plantdoc-weak-v2"
    scidb = project / "artifacts" / "public" / "scidb-pests102" / "weak-subset-v1"
    pest65 = project / "artifacts" / "experiments" / "pest65-aphids-reviewed-v1"
    grasshopper_train = project / "artifacts" / "public" / "grasshopper-class13-train-v1"

    official_train = normalize_official(read_list(official / "splits" / "train.txt"), official)
    official_frozen = normalize_official(read_list(official / "splits" / "val.txt"), official)
    sources: dict[str, list[Path]] = {
        "official": official_train,
        "plantdoc": read_list(plantdoc / "train.txt", plantdoc),
        "scidb": read_list(scidb / "train.txt", scidb),
    }
    pest_manifest = json.loads((pest65 / "manifest.json").read_text(encoding="utf-8"))
    sources["pest65-reviewed"] = [(pest65 / item["image"]).resolve() for item in pest_manifest["images"]]

    exclusions: list[dict[str, str]] = []
    if grasshopper_train.is_dir() and (grasshopper_train / "train.txt").is_file():
        sources["class13-grasshopper-train"] = read_list(grasshopper_train / "train.txt", grasshopper_train)
    else:
        exclusions.append({"source": "class13-grasshopper-train", "reason": "excluded_missing_source", "expected_count": "445"})

    frozen_hashes = {digest(path): str(path) for path in official_frozen}
    seen: dict[str, str] = dict(frozen_hashes)
    accepted: list[Path] = []
    kept_counts: Counter[str] = Counter()
    for source, entries in sources.items():
        for image in entries:
            if not image.is_file():
                exclusions.append({"source": source, "path": str(image), "reason": "missing_image"})
                continue
            try:
                validate_image_file(image)
            except ValueError as exc:
                exclusions.append({"source": source, "path": str(image), "reason": "invalid_image", "detail": str(exc)})
                continue
            image_hash = digest(image)
            if image_hash in seen:
                exclusions.append({"source": source, "path": str(image), "reason": "exact_duplicate", "duplicate_of": seen[image_hash]})
                continue
            try:
                validate_labels(image, official)
            except ValueError as exc:
                exclusions.append({"source": source, "path": str(image), "reason": "invalid_label", "detail": str(exc)})
                continue
            seen[image_hash] = str(image)
            accepted.append(image)
            kept_counts[source] += 1

    dev_train, dev_val, class_boxes = stratified_split(accepted, official, args.dev_val_fraction, args.seed)
    write_list(output / "dev-train.txt", dev_train)
    write_list(output / "dev-val.txt", dev_val)
    write_list(output / "final-train.txt", sorted(accepted, key=str))
    write_list(output / "official-frozen-val.txt", official_frozen)
    (output / "dataset-dev.yaml").write_text(yaml_text(output / "dev-train.txt", output / "dev-val.txt"), encoding="utf-8")
    (output / "dataset-refit.yaml").write_text(yaml_text(output / "final-train.txt", output / "dev-val.txt"), encoding="utf-8")
    (output / "dataset-frozen-eval.yaml").write_text(yaml_text(output / "dev-train.txt", output / "official-frozen-val.txt"), encoding="utf-8")
    report = {
        "seed": args.seed,
        "dev_val_fraction": args.dev_val_fraction,
        "source_input_counts": {name: len(items) for name, items in sources.items()},
        "source_kept_counts": dict(kept_counts),
        "accepted_total": len(accepted),
        "dev_train_count": len(dev_train),
        "dev_val_count": len(dev_val),
        "official_frozen_count": len(official_frozen),
        "official_frozen_split_sha256": hashlib.sha256((official / "splits" / "val.txt").read_bytes()).hexdigest(),
        "class_box_counts": {str(key): value for key, value in sorted(class_boxes.items())},
        "exclusions": exclusions,
        "official_frozen_used_for_model_selection": False,
        "refit_yaml_contains_official_frozen": False,
    }
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
