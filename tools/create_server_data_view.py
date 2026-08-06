from __future__ import annotations

import argparse
import os
from pathlib import Path


def ensure_directory_link(link_path: Path, target_path: Path, dry_run: bool) -> None:
    target = target_path.resolve(strict=True)

    if os.path.lexists(link_path):
        try:
            current_target = link_path.resolve(strict=True)
        except OSError as exc:
            raise RuntimeError(f"Existing path cannot be resolved: {link_path}") from exc
        if current_target == target:
            print(f"already linked: {link_path} -> {target}")
            return
        raise FileExistsError(
            f"Refusing to replace existing path: {link_path} (currently resolves to {current_target})"
        )

    print(f"link: {link_path} -> {target}")
    if not dry_run:
        link_path.symlink_to(target, target_is_directory=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a read-only dataset view for server-side auditing and YOLO training."
    )
    parser.add_argument("official_root", type=Path, help="Root of the official competition data package")
    parser.add_argument("data_root", type=Path, help="Project data view, for example data/official")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    official_root = args.official_root.expanduser().resolve(strict=True)
    data_root = args.data_root.expanduser().resolve()
    image_source = official_root / "训练数据" / "图片"
    label_source = official_root / "训练数据" / "标签"
    class_map = official_root / "文档" / "类别中英文对照.csv"

    missing = [path for path in (image_source, label_source, class_map) if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Official data package is incomplete: {missing}")

    if not args.dry_run:
        (data_root / "images").mkdir(parents=True, exist_ok=True)
        (data_root / "labels").mkdir(parents=True, exist_ok=True)
        (data_root / "splits").mkdir(parents=True, exist_ok=True)

    ensure_directory_link(data_root / "images" / "all", image_source, args.dry_run)
    ensure_directory_link(data_root / "labels" / "all", label_source, args.dry_run)
    print(f"class map: {class_map}")


if __name__ == "__main__":
    main()
