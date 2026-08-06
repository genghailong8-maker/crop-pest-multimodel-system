"""Create a reproducible official-train plus reviewed-external YOLO manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


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


def lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path("/root/autodl-tmp/crop-pest-system"))
    parser.add_argument(
        "--external-root",
        type=Path,
        default=Path("artifacts/experiments/pest65-aphids-reviewed-v1"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/experiments/official-plus-pest65-aphids-v1"),
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    official_root = project_root / "data" / "official"
    external_root = (project_root / args.external_root).resolve() if not args.external_root.is_absolute() else args.external_root.resolve()
    output_root = (project_root / args.output_root).resolve() if not args.output_root.is_absolute() else args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    official_train = lines(official_root / "splits" / "train.txt")
    official_val = lines(official_root / "splits" / "val.txt")
    external_manifest = json.loads((external_root / "manifest.json").read_text(encoding="utf-8"))
    external_train = [
        str((external_root / record["image"]).resolve())
        for record in external_manifest.get("images", [])
    ]
    if not official_train or not official_val or not external_train:
        raise ValueError("official train/val and external train manifests must be non-empty")
    if set(official_train) & set(official_val):
        raise ValueError("official train and validation overlap")
    if set(external_train) & set(official_val):
        raise ValueError("external augmentation overlaps frozen official validation")

    combined_train = output_root / "train-plus-aphid.txt"
    combined_val = output_root / "val-official-frozen.txt"
    combined_train.write_text("\n".join(official_train + external_train) + "\n", encoding="utf-8")
    combined_val.write_text("\n".join(official_val) + "\n", encoding="utf-8")
    dataset_yaml = output_root / "dataset-training.yaml"
    yaml_lines = [
        f'path: {json.dumps(str(project_root), ensure_ascii=False)}',
        f'train: {json.dumps(str(combined_train), ensure_ascii=False)}',
        f'val: {json.dumps(str(combined_val), ensure_ascii=False)}',
        "names:",
    ]
    yaml_lines.extend(f"  {index}: {json.dumps(name)}" for index, name in enumerate(NAMES))
    dataset_yaml.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    report = {
        "official_train_count": len(official_train),
        "official_val_count": len(official_val),
        "external_train_count": len(external_train),
        "combined_train_count": len(official_train) + len(external_train),
        "official_val_sha256": sha256(official_root / "splits" / "val.txt"),
        "external_manifest": str((external_root / "manifest.json").resolve()),
        "dataset_yaml": str(dataset_yaml),
        "official_validation_frozen": True,
    }
    (output_root / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
