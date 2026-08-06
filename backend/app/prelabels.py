from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
COMPLETE_REVIEW_STATUSES = {"accepted", "skipped"}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="预标注清单尚未准备好") from exc


def _context(prelabel_dir: Path) -> tuple[dict[str, Any], Path, Path]:
    review_manifest = _load_json(prelabel_dir / "review-manifest.json")
    manifest = _load_json(prelabel_dir.parent / "manifest.json")
    source_root = Path(manifest["summary"]["source_root"]).resolve()
    reviews_dir = prelabel_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    return review_manifest, source_root, reviews_dir


def _safe_source_path(source_root: Path, relative_path: str) -> Path:
    candidate = (source_root / relative_path).resolve()
    try:
        candidate.relative_to(source_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="图片路径不在数据集目录内") from exc
    if candidate.suffix.lower() not in IMAGE_SUFFIXES or not candidate.is_file():
        raise HTTPException(status_code=404, detail="预标注图片不存在")
    return candidate


def _review_path(reviews_dir: Path, image_id: str) -> Path:
    if not image_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in image_id):
        raise HTTPException(status_code=400, detail="图片编号格式错误")
    return reviews_dir / f"{image_id}.json"


def _read_review(reviews_dir: Path, image_id: str) -> dict[str, Any] | None:
    path = _review_path(reviews_dir, image_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail="复核记录损坏，请检查复核目录") from exc


def _priority_order(value: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2}.get(value, 9)


def _is_complete(status: str) -> bool:
    return status in COMPLETE_REVIEW_STATUSES


def _items(review_manifest: dict[str, Any], reviews_dir: Path) -> list[dict[str, Any]]:
    items = []
    for item in review_manifest.get("images", []):
        review = _read_review(reviews_dir, str(item["image_id"]))
        items.append(
            {
                **item,
                "review_status": review.get("decision") if review else "pending",
                "reviewed_at": review.get("reviewed_at") if review else None,
            }
        )
    return sorted(
        items,
        key=lambda item: (
            1 if _is_complete(str(item["review_status"])) else 0,
            _priority_order(str(item["review_priority"])),
            str(item["source_relative_path"]),
        ),
    )


def queue(prelabel_dir: Path, priority: str | None = None) -> dict[str, Any]:
    review_manifest, _, reviews_dir = _context(prelabel_dir)
    items = _items(review_manifest, reviews_dir)
    if priority and priority != "all":
        items = [item for item in items if item["review_priority"] == priority]
    all_items = _items(review_manifest, reviews_dir)
    counts = {key: sum(item["review_priority"] == key for item in all_items) for key in ("P0", "P1", "P2")}
    reviewed = sum(_is_complete(str(item["review_status"])) for item in all_items)
    return {
        "summary": review_manifest.get("summary", {}),
        "total": len(all_items),
        "reviewed": reviewed,
        "remaining": len(all_items) - reviewed,
        "priority_counts": counts,
        "items": items,
    }


def detail(prelabel_dir: Path, image_id: str) -> dict[str, Any]:
    review_manifest, source_root, reviews_dir = _context(prelabel_dir)
    item = next(
        (candidate for candidate in review_manifest.get("images", []) if candidate["image_id"] == image_id),
        None,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="预标注图片不存在")
    raw_path = prelabel_dir / "raw" / f"{image_id}.json"
    raw = _load_json(raw_path)
    review = _read_review(reviews_dir, image_id)
    return {
        **item,
        "image_url": f"/api/prelabels/{image_id}/image",
        "source_size": raw.get("source_size"),
        "working_size": raw.get("working_size"),
        "model_sha256": raw.get("model_sha256"),
        "detections": raw.get("detections", []),
        "target_detections": raw.get("target_detections", []),
        "review": review,
        "source_exists": _safe_source_path(source_root, str(item["source_relative_path"])).is_file(),
    }


def image_path(prelabel_dir: Path, image_id: str) -> Path:
    review_manifest, source_root, _ = _context(prelabel_dir)
    item = next(
        (candidate for candidate in review_manifest.get("images", []) if candidate["image_id"] == image_id),
        None,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="预标注图片不存在")
    return _safe_source_path(source_root, str(item["source_relative_path"]))


def _validate_box(box: Any) -> list[float]:
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        raise HTTPException(status_code=422, detail="每个框必须包含四个归一化坐标")
    values = [float(value) for value in box]
    if any(value < 0 or value > 1 for value in values) or values[2] <= 0 or values[3] <= 0:
        raise HTTPException(status_code=422, detail="框坐标必须位于0到1之间且宽高大于0")
    if values[0] + values[2] > 1.00001 or values[1] + values[3] > 1.00001:
        raise HTTPException(status_code=422, detail="框不能超出图片边界")
    return values


def save_review(
    prelabel_dir: Path,
    image_id: str,
    decision: str,
    boxes: list[dict[str, Any]],
    notes: str,
) -> dict[str, Any]:
    review_manifest, _, reviews_dir = _context(prelabel_dir)
    item = next(
        (candidate for candidate in review_manifest.get("images", []) if candidate["image_id"] == image_id),
        None,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="预标注图片不存在")
    if decision not in {"accepted", "needs_rework", "skipped"}:
        raise HTTPException(status_code=422, detail="复核决定不受支持")
    if len(boxes) > 1000:
        raise HTTPException(status_code=422, detail="单张图片最多保存1000个框")
    normalized_boxes = []
    for box in boxes:
        normalized_boxes.append(
            {
                "class_id": 9,
                "bbox": _validate_box(box.get("bbox")),
                "confidence": max(0.0, min(1.0, float(box.get("confidence", 0.0)))),
                "prelabel_method": str(box.get("prelabel_method", "manual")),
                "original_class_id": box.get("original_class_id"),
            }
        )
    record = {
        "image_id": image_id,
        "source_relative_path": item["source_relative_path"],
        "decision": decision,
        "boxes": normalized_boxes,
        "notes": notes.strip()[:2000],
        "reviewed_at": datetime.now(UTC).isoformat(),
    }
    path = _review_path(reviews_dir, image_id)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    if decision == "accepted":
        labels_dir = prelabel_dir / "reviewed-labels"
        labels_dir.mkdir(parents=True, exist_ok=True)
        label_path = labels_dir / f"{image_id}.txt"
        lines = []
        for box in normalized_boxes:
            x, y, width, height = box["bbox"]
            lines.append(f"9 {x + width / 2:.7f} {y + height / 2:.7f} {width:.7f} {height:.7f}")
        label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return detail(prelabel_dir, image_id)
