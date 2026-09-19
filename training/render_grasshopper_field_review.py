"""Render an offline, read-only gallery for class-13 field review."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


def load_boxes(path: Path) -> list[tuple[int, float, float, float, float]]:
    boxes: list[tuple[int, float, float, float, float]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"{path}: line {line_number} does not have five fields")
        boxes.append((int(fields[0]), *(float(value) for value in fields[1:])))
    return boxes


def render_image(image_path: Path, label_path: Path, target: Path, title: str) -> None:
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    stroke = max(2, round(min(width, height) * 0.004))
    for index, (class_id, cx, cy, box_width, box_height) in enumerate(load_boxes(label_path), 1):
        left = max(0, round((cx - box_width / 2) * width))
        right = min(width - 1, round((cx + box_width / 2) * width))
        top = max(0, round((cy - box_height / 2) * height))
        bottom = min(height - 1, round((cy + box_height / 2) * height))
        draw.rectangle((left, top, right, bottom), outline=(255, 40, 40), width=stroke)
        caption = f"{class_id}:{index}"
        text_box = draw.textbbox((left, top), caption)
        draw.rectangle(text_box, fill=(255, 40, 40))
        draw.text((left, top), caption, fill=(255, 255, 255))

    header_height = 34
    canvas = Image.new("RGB", (width, height + header_height), (24, 28, 36))
    canvas.paste(image, (0, header_height))
    ImageDraw.Draw(canvas).text((8, 9), title, fill=(255, 255, 255))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, format="JPEG", quality=90, optimize=True)


def ensure_empty(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise FileExistsError(f"output is not a directory: {path}")
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"output directory is not empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()

    root = args.dataset_root.expanduser().resolve(strict=True)
    output = (args.output_root or root / "review_gallery").expanduser().resolve()
    ensure_empty(output)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = manifest["records"]
    path_to_id = {
        str((root / record["image"]).resolve()): str(record["record_id"]) for record in records
    }

    cards: list[str] = []
    summary = {"records": len(records), "negative": 0, "near_duplicate": 0, "repaired": 0}
    for record in records:
        record_id = str(record["record_id"])
        image_path = (root / record["image"]).resolve(strict=True)
        label_path = (root / record["label"]).resolve(strict=True)
        image_path.relative_to(root)
        label_path.relative_to(root)
        near_matches = record.get("near_duplicate_matches", [])
        repairs = record.get("box_repairs", [])
        negative = int(record["box_count"]) == 0
        summary["negative"] += int(negative)
        summary["near_duplicate"] += int(bool(near_matches))
        summary["repaired"] += int(bool(repairs))
        flags = [str(record["output_split"])]
        if negative:
            flags.append("negative")
        if near_matches:
            flags.extend(("near", "flagged"))
        if repairs:
            flags.extend(("repaired", "flagged"))
        title = (
            f"{record_id} | boxes={record['box_count']} | near={len(near_matches)} | "
            f"repairs={len(repairs)}"
        )
        asset = output / "assets" / f"{record_id}.jpg"
        render_image(image_path, label_path, asset, title)
        details: list[str] = []
        for match in near_matches:
            matched_id = path_to_id.get(str(Path(match["path"]).resolve()), match["path"])
            details.append(f"near d={match['distance']}: {matched_id}")
        for repair in repairs:
            details.append(
                f"repaired line {repair['line_number']}, overflow={repair['maximum_overflow']:.8f}"
            )
        if negative:
            details.append("negative image: empty YOLO label")
        detail_html = "<br>".join(html.escape(item) for item in details) or "no audit flags"
        cards.append(
            f'<article class="card" data-flags="{html.escape(" ".join(flags))}">'
            f'<a href="assets/{record_id}.jpg"><img loading="lazy" src="assets/{record_id}.jpg" '
            f'alt="{html.escape(record_id)}"></a>'
            f'<h2>{html.escape(record_id)}</h2><p>{html.escape(title)}</p><p>{detail_html}</p></article>'
        )

    controls = " ".join(
        f'<button onclick="filterCards(\'{value}\')">{label}</button>'
        for value, label in (
            ("all", "All 142"),
            ("flagged", "Flagged"),
            ("negative", "Negative"),
            ("near", "Near duplicate"),
            ("repaired", "Repaired box"),
            ("tune", "Tune"),
            ("frozen", "Frozen"),
        )
    )
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Class 13 Field Review</title><style>
body{{font-family:system-ui,sans-serif;margin:0;background:#111827;color:#e5e7eb}}
header{{position:sticky;top:0;z-index:2;padding:16px;background:#111827ee;border-bottom:1px solid #374151}}
button{{margin:3px;padding:8px 12px;border:0;border-radius:8px;cursor:pointer}}
main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;padding:14px}}
.card{{background:#1f2937;border:1px solid #374151;border-radius:10px;padding:10px}}
.card img{{width:100%;height:280px;object-fit:contain;background:#030712}}
h1{{font-size:20px;margin:0 0 8px}}h2{{font-size:16px;margin:8px 0 3px}}p{{font-size:13px;margin:3px 0;color:#cbd5e1}}
</style></head><body><header><h1>Class 13 人工复核 — 只读画廊</h1>
<p>逐图确认：类别纯度、检测框覆盖、负样本合理性；近重复与修复框必须写 review_notes。</p>{controls}</header>
<main>{''.join(cards)}</main><script>
function filterCards(flag){{document.querySelectorAll('.card').forEach(card=>{{
card.style.display=(flag==='all'||card.dataset.flags.split(' ').includes(flag))?'block':'none';}});}}
</script></body></html>"""
    (output / "index.html").write_text(page, encoding="utf-8")
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"output": str(output), **summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
