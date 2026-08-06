from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    parser = argparse.ArgumentParser(description="Render contact sheets for weak-class hard samples.")
    parser.add_argument("report", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--per-group", type=int, default=12)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--tile-width", type=int, default=420)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    groups: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for split, payload in report["splits"].items():
        for row in payload["hard_samples"]:
            key = (split, int(row["target_class"]), row["reason"])
            if len(groups[key]) < args.per_group:
                groups[key].append(row)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    for (split, class_id, reason), rows in sorted(groups.items()):
        tiles = []
        for row in rows:
            path = Path(row["image"])
            try:
                image = Image.open(path).convert("RGB")
            except (OSError, ValueError):
                continue
            scale = args.tile_width / image.width
            tile_height = max(180, int(image.height * scale))
            image = image.resize((args.tile_width, tile_height))
            draw = ImageDraw.Draw(image)
            text = (
                f"class {class_id} {reason}\n"
                f"IoU {float(row['best_iou']):.2f} "
                f"pred {row.get('best_prediction_class')} "
                f"conf {float(row['best_prediction_confidence']):.2f}\n"
                f"{path.name}"
            )
            draw.rectangle((0, 0, args.tile_width, 42), fill=(0, 0, 0))
            draw.multiline_text((5, 4), text, fill=(255, 255, 255), font=font, spacing=1)
            tiles.append(image)
        if not tiles:
            continue
        rows_count = (len(tiles) + args.columns - 1) // args.columns
        tile_height = max(tile.height for tile in tiles)
        sheet = Image.new("RGB", (args.columns * args.tile_width, rows_count * tile_height), (30, 30, 30))
        for index, tile in enumerate(tiles):
            x = (index % args.columns) * args.tile_width
            y = (index // args.columns) * tile_height
            sheet.paste(tile, (x, y))
        output = args.output_dir / f"{split}-class{class_id}-{reason}.jpg"
        sheet.save(output, quality=90)


if __name__ == "__main__":
    main()
