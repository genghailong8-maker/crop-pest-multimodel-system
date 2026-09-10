from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image


MODULE_PATH = Path(__file__).parents[1] / "build_phase9_unified_dataset.py"
SPEC = importlib.util.spec_from_file_location("phase9_builder", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_validate_labels_and_stratified_split(tmp_path: Path) -> None:
    official = tmp_path / "official"
    image_dir = official / "images" / "all"
    label_dir = official / "labels" / "all"
    image_dir.mkdir(parents=True)
    label_dir.mkdir(parents=True)
    images = []
    for index, class_id in enumerate((0, 0, 1, 1)):
        image = image_dir / f"sample-{index}.jpg"
        image.write_bytes(f"image-{index}".encode())
        (label_dir / f"sample-{index}.txt").write_text(f"{class_id} 0.5 0.5 0.2 0.2\n", encoding="utf-8")
        images.append(image)
    train, val, counts = module.stratified_split(images, official, 0.25, 7)
    assert len(train) == 2
    assert len(val) == 2
    assert counts == {0: 2, 1: 2}
    assert not set(train) & set(val)


def test_label_path_for_external_images(tmp_path: Path) -> None:
    image = tmp_path / "train" / "images" / "leaf.jpg"
    assert module.label_path(image, tmp_path / "official") == tmp_path / "train" / "labels" / "leaf.txt"


def test_incomplete_jpeg_is_rejected(tmp_path: Path) -> None:
    image = tmp_path / "truncated.jpg"
    image.write_bytes(b"\xff\xd8incomplete")
    try:
        module.validate_image_file(image)
    except ValueError as exc:
        assert "结束标记" in str(exc)
    else:
        raise AssertionError("截断 JPEG 不应通过质量检查")


def test_complete_jpeg_is_accepted(tmp_path: Path) -> None:
    image = tmp_path / "complete.jpg"
    Image.new("RGB", (8, 8), "green").save(image)
    module.validate_image_file(image)


def test_duplicate_label_row_is_rejected(tmp_path: Path) -> None:
    official = tmp_path / "official"
    image_dir = official / "images" / "all"
    label_dir = official / "labels" / "all"
    image_dir.mkdir(parents=True)
    label_dir.mkdir(parents=True)
    image = image_dir / "duplicate.jpg"
    image.write_bytes(b"placeholder")
    row = "9 0.5 0.5 0.2 0.2\n"
    (label_dir / "duplicate.txt").write_text(row + row, encoding="utf-8")
    try:
        module.validate_labels(image, official)
    except ValueError as exc:
        assert "重复框" in str(exc)
    else:
        raise AssertionError("重复标注框不应通过质量检查")
