"""Build an isolated official-plus-public weak-class smoke-train manifest.

The script does not copy or mutate source data.  It composes absolute image
lists, removes any exact SHA-256 duplicate between official and candidate
images (and among candidate sources), and keeps the official validation split
frozen for an apples-to-apples comparison with the deployed baseline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable


NAMES = [
    "Corn leaf blight", "Tomato Septoria leaf spot", "Squash powdery mildew",
    "Potato early blight", "Corn rust", "Tomato bacterial spot",
    "Tomato late blight", "Potato late blight", "Blister beetle", "Aphids",
    "Mirid bugs (Miridae)", "Mole cricket", "Leafhoppers (Cicadellidae)",
    "Grasshoppers (Locustoidea)", "White grub", "Legume blister beetle",
]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def read_list(path: Path, root: Path | None = None) -> list[Path]:
    entries: list[Path] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        candidate = Path(line.strip()).expanduser()
        if not candidate.is_absolute() and root is not None:
            candidate = root / candidate
        entries.append(candidate.resolve())
    return entries


def write_list(path: Path, entries: Iterable[Path]) -> None:
    path.write_text("\n".join(str(entry) for entry in entries) + "\n", encoding="utf-8")


def normalize_official(entries: list[Path], official_root: Path) -> list[Path]:
    """Use the project-local image/label view when the split list is stale.

    Historical server split lists point at ``official-dataset/训练数据/图片``;
    those images have labels in a sibling directory that Ultralytics cannot
    infer from the image path.  The project view keeps matching
    ``images/all`` and ``labels/all`` paths together.
    """

    normalized: list[Path] = []
    for path in entries:
        local = official_root / "images" / "all" / path.name
        # Preserve the project symlink spelling.  ``Path.resolve()`` would
        # rewrite ``images/all`` to the source directory with Chinese names,
        # breaking Ultralytics' image-to-label path inference.
        normalized.append(local if local.is_file() else path)
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--plantdoc-root", type=Path, required=True)
    parser.add_argument("--scidb-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    official_root = args.official_root.resolve()
    plantdoc_root = args.plantdoc_root.resolve()
    scidb_root = args.scidb_root.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    official_train = normalize_official(read_list(official_root / "splits/train.txt"), official_root)
    official_val = normalize_official(read_list(official_root / "splits/val.txt"), official_root)
    plantdoc_train = read_list(plantdoc_root / "train.txt", plantdoc_root)
    plantdoc_test = read_list(plantdoc_root / "test.txt", plantdoc_root)
    scidb_train = read_list(scidb_root / "train.txt", scidb_root)
    scidb_valid = read_list(scidb_root / "valid.txt", scidb_root)
    scidb_test = read_list(scidb_root / "test.txt", scidb_root)

    official_all = official_train + official_val
    official_hashes = {digest(path): str(path) for path in official_all}
    seen_hashes = dict(official_hashes)
    excluded: list[dict[str, str]] = []

    def accept_candidates(entries: Iterable[Path], source: str) -> list[Path]:
        accepted: list[Path] = []
        for path in entries:
            if not path.is_file():
                excluded.append({"source": source, "path": str(path), "reason": "missing_image"})
                continue
            image_hash = digest(path)
            duplicate_of = seen_hashes.get(image_hash)
            if duplicate_of is not None:
                excluded.append({"source": source, "path": str(path), "reason": "exact_duplicate", "duplicate_of": duplicate_of})
                continue
            seen_hashes[image_hash] = str(path)
            accepted.append(path)
        return accepted

    plantdoc_train_kept = accept_candidates(plantdoc_train, "plantdoc-train")
    scidb_train_kept = accept_candidates(scidb_train, "scidb-train")
    # Evaluation lists are checked against every training/official image, but
    # duplicates inside an evaluation list are also removed.
    candidate_valid_kept = accept_candidates(plantdoc_test + scidb_valid, "candidate-valid")
    candidate_test_kept = accept_candidates(scidb_test, "candidate-test")

    train_entries = official_train + plantdoc_train_kept + scidb_train_kept
    write_list(output_root / "train.txt", train_entries)
    write_list(output_root / "val.txt", official_val)
    write_list(output_root / "candidate-valid.txt", candidate_valid_kept)
    write_list(output_root / "candidate-test.txt", candidate_test_kept)

    names_lines = "\n".join(f"  {index}: {json.dumps(name)}" for index, name in enumerate(NAMES))
    for yaml_name, train_file, val_file, test_file in (
        ("dataset.yaml", "train.txt", "val.txt", "candidate-test.txt"),
        ("candidate-eval.yaml", "candidate-valid.txt", "candidate-valid.txt", "candidate-test.txt"),
        ("candidate-test-eval.yaml", "candidate-test.txt", "candidate-test.txt", "candidate-test.txt"),
    ):
        (output_root / yaml_name).write_text(
            f"path: /\ntrain: {output_root / train_file}\nval: {output_root / val_file}\ntest: {output_root / test_file}\nnames:\n{names_lines}\n",
            encoding="utf-8",
        )

    manifest = {
        "official_train_count": len(official_train),
        "official_val_count": len(official_val),
        "plantdoc_train_input_count": len(plantdoc_train),
        "plantdoc_train_kept_count": len(plantdoc_train_kept),
        "scidb_train_input_count": len(scidb_train),
        "scidb_train_kept_count": len(scidb_train_kept),
        "candidate_valid_kept_count": len(candidate_valid_kept),
        "candidate_test_kept_count": len(candidate_test_kept),
        "combined_train_count": len(train_entries),
        "exact_duplicate_exclusions": excluded,
        "official_validation_frozen": True,
        "seed": 20260729,
        "policy": "smoke only; no deployment or full retraining until official validation and weak-class metrics are compared",
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
