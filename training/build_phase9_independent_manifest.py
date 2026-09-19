"""Build a derived training manifest after removing confirmed cross-split visual duplicates."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from build_weak_public_smoke import NAMES


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_list(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def yaml_text(train: Path, frozen: Path) -> str:
    lines = ["path: /", f"train: {train}", f"val: {frozen}", "names:"]
    lines.extend(f"  {index}: {json.dumps(name, ensure_ascii=False)}" for index, name in enumerate(NAMES))
    return "\n".join(lines) + "\n"


def train_yaml_text(train: Path) -> str:
    # Ultralytics requires a val key even when train(..., val=False). Point it
    # at the training list as a framework-only placeholder; final evaluation
    # uses the separate frozen-eval YAML and is never read during training.
    lines = ["path: /", f"train: {train}", f"val: {train}", "names:"]
    lines.extend(f"  {index}: {json.dumps(name, ensure_ascii=False)}" for index, name in enumerate(NAMES))
    return "\n".join(lines) + "\n"


def source_name(path: str) -> str:
    if "/artifacts/public/plantdoc-" in path:
        return "plantdoc"
    if "/artifacts/public/scidb-" in path:
        return "scidb"
    if "/data/official/" in path:
        return "official-train"
    return "other"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_train", type=Path)
    parser.add_argument("independence_report", type=Path)
    parser.add_argument("frozen_list", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    original = read_list(args.original_train)
    original_set = set(original)
    report = json.loads(args.independence_report.read_text(encoding="utf-8"))
    excluded: set[str] = set()
    for item in report["cross_split"]["phash_exact_pairs"]:
        excluded.update(item["train_paths"])
    for item in report["cross_split"]["near_phash_pairs"]:
        excluded.add(item["train_path"])
    unexpected = sorted(excluded - original_set)
    if unexpected:
        raise SystemExit(f"排除路径不属于原始训练清单：{unexpected[:5]}")
    remaining = [path for path in original if path not in excluded]
    if len(remaining) != len(set(remaining)):
        raise SystemExit("派生训练清单包含重复路径")
    missing = [path for path in remaining if not Path(path).is_file()]
    if missing:
        raise SystemExit(f"派生训练清单存在缺失图片：{missing[:5]}")

    output = args.output_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    train_path = output / "train-independent-v1.txt"
    frozen_path = args.frozen_list.resolve()
    yaml_path = output / "dataset-independent-frozen-eval.yaml"
    train_yaml_path = output / "dataset-independent-train-only.yaml"
    exclusion_path = output / "excluded-cross-split-visual-duplicates.txt"
    train_path.write_text("\n".join(remaining) + "\n", encoding="utf-8")
    exclusion_path.write_text("\n".join(sorted(excluded)) + "\n", encoding="utf-8")
    yaml_path.write_text(yaml_text(train_path, frozen_path), encoding="utf-8")
    train_yaml_path.write_text(train_yaml_text(train_path), encoding="utf-8")
    summary = {
        "created_from": str(args.original_train.resolve()),
        "created_from_sha256": sha256(args.original_train.resolve()),
        "independence_report": str(args.independence_report.resolve()),
        "frozen_list": str(frozen_path),
        "frozen_list_sha256": sha256(frozen_path),
        "original_count": len(original),
        "excluded_count": len(excluded),
        "independent_train_count": len(remaining),
        "excluded_by_source": dict(Counter(source_name(path) for path in excluded)),
        "excluded_paths": sorted(excluded),
        "train_list": str(train_path),
        "train_list_sha256": sha256(train_path),
        "dataset_yaml": str(yaml_path),
        "dataset_yaml_sha256": sha256(yaml_path),
        "training_yaml": str(train_yaml_path),
        "training_yaml_sha256": sha256(train_yaml_path),
        "frozen_validation_used_during_training": False,
        "derivation": "remove all training paths appearing in exact or near pHash cross-split pairs (Hamming distance <= 8)",
    }
    (output / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
