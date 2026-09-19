"""Create metrics and contact sheets for cross-split perceptual-hash pairs."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


def load_rgb(path: Path) -> Image.Image:
    with Image.open(path) as image:
        result = image.convert("RGB")
        result.load()
        return result


def metrics(left: Image.Image, right: Image.Image) -> dict[str, float | list[int]]:
    left_rgb = np.asarray(left.resize((128, 128), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
    right_rgb = np.asarray(right.resize((128, 128), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
    left_gray = left_rgb.mean(axis=2).reshape(-1)
    right_gray = right_rgb.mean(axis=2).reshape(-1)
    left_center = left_gray - left_gray.mean()
    right_center = right_gray - right_gray.mean()
    denominator = float(np.linalg.norm(left_center) * np.linalg.norm(right_center))
    correlation = float(np.dot(left_center, right_center) / denominator) if denominator else 0.0
    mae = float(np.abs(left_rgb - right_rgb).mean())
    mse = float(((left_rgb - right_rgb) ** 2).mean())
    left_hist = np.histogram(left_rgb, bins=32, range=(0.0, 1.0), density=True)[0]
    right_hist = np.histogram(right_rgb, bins=32, range=(0.0, 1.0), density=True)[0]
    hist_l1 = float(np.abs(left_hist - right_hist).mean())
    return {
        "left_size": list(left.size),
        "right_size": list(right.size),
        "gray_correlation": correlation,
        "resized_rgb_mae": mae,
        "resized_rgb_mse": mse,
        "channel_histogram_l1": hist_l1,
    }


def short_path(path: str) -> str:
    return path.replace("/root/autodl-tmp/crop-pest-system/", "")


def render_page(pairs: list[dict[str, object]], output: Path, page_number: int) -> None:
    row_height = 230
    canvas = Image.new("RGB", (1200, max(1, len(pairs)) * row_height), "white")
    draw = ImageDraw.Draw(canvas)
    for row, pair in enumerate(pairs):
        top = row * row_height
        left = load_rgb(Path(str(pair["train_path"])))
        right = load_rgb(Path(str(pair["frozen_path"])))
        left_thumb = ImageOps.contain(left, (260, 190))
        right_thumb = ImageOps.contain(right, (260, 190))
        canvas.paste(left_thumb, (10, top + 25))
        canvas.paste(right_thumb, (290, top + 25))
        draw.text((570, top + 8), f"#{pair['pair_index']}  pHash distance={pair['phash_distance']}", fill="black")
        draw.text((570, top + 38), f"train: {short_path(str(pair['train_path']))}", fill="black")
        draw.text((570, top + 66), f"frozen: {short_path(str(pair['frozen_path']))}", fill="black")
        values = pair["metrics"]
        draw.text(
            (570, top + 98),
            "corr={:.3f}  MAE={:.3f}  MSE={:.3f}  histL1={:.3f}".format(
                values["gray_correlation"], values["resized_rgb_mae"], values["resized_rgb_mse"], values["channel_histogram_l1"]
            ),
            fill="black",
        )
        draw.line((0, top + row_height - 2, 1200, top + row_height - 2), fill="#cccccc", width=1)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=4)
    args = parser.parse_args()
    source = json.loads(args.report.read_text(encoding="utf-8"))
    pairs: list[dict[str, object]] = []
    pair_index = 0
    exact_items = source["cross_split"]["phash_exact_pairs"]
    for item in exact_items:
        for train_path in item["train_paths"]:
            for frozen_path in item["frozen_paths"]:
                pair_index += 1
                left = load_rgb(Path(train_path))
                right = load_rgb(Path(frozen_path))
                pairs.append(
                    {
                        "pair_index": pair_index,
                        "pair_kind": "exact_phash",
                        "phash": item["phash"],
                        "phash_distance": 0,
                        "train_path": train_path,
                        "frozen_path": frozen_path,
                        "metrics": metrics(left, right),
                    }
                )
    for item in source["cross_split"]["near_phash_pairs"]:
        pair_index += 1
        train_path = item["train_path"]
        frozen_path = item["frozen_path"]
        left = load_rgb(Path(train_path))
        right = load_rgb(Path(frozen_path))
        pairs.append(
            {
                "pair_index": pair_index,
                "pair_kind": "near_phash",
                "phash": None,
                "phash_distance": item["distance"],
                "train_path": train_path,
                "frozen_path": frozen_path,
                "metrics": metrics(left, right),
            }
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "phash-exact-pair-metrics.json").write_text(
        json.dumps({"pair_count": len(pairs), "pairs": pairs}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for page_start in range(0, len(pairs), args.page_size):
        page = pairs[page_start : page_start + args.page_size]
        render_page(page, args.output_dir / f"phash-exact-page-{page_start // args.page_size + 1:02d}.png", page_start // args.page_size + 1)
    print(json.dumps({"pair_count": len(pairs), "pages": math.ceil(len(pairs) / args.page_size)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
