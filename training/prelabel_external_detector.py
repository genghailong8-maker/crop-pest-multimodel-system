from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageOps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create reviewable YOLO pre-labels through the remote detector API."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8870/v1/detect")
    parser.add_argument("--confidence", type=float, default=0.10)
    parser.add_argument("--target-class-id", type=int, required=True)
    parser.add_argument(
        "--remap-class-id",
        action="append",
        type=int,
        default=[],
        help="Remap a detector class to the folder-level target class while preserving provenance.",
    )
    parser.add_argument("--max-working-side", type=int, default=2560)
    parser.add_argument("--tile-size", type=int, default=1280)
    parser.add_argument("--tile-overlap", type=float, default=0.20)
    parser.add_argument("--nms-iou", type=float, default=0.50)
    parser.add_argument("--jpeg-quality", type=int, default=90)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def stable_image_id(relative_path: str) -> str:
    digest = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:12]
    stem = Path(relative_path).stem
    class_index = Path(relative_path).parts[1].split(".", 1)[0]
    split = Path(relative_path).parts[0].replace("_images", "")
    return f"p{class_index}_{split}_{stem}_{digest}"


def resize_for_inference(image: Image.Image, max_side: int) -> Image.Image:
    largest = max(image.size)
    if largest <= max_side:
        return image
    scale = max_side / largest
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )


def tile_origins(length: int, tile_size: int, overlap: float) -> list[int]:
    if length <= tile_size:
        return [0]
    stride = max(1, round(tile_size * (1.0 - overlap)))
    origins = list(range(0, max(1, length - tile_size + 1), stride))
    last = length - tile_size
    if origins[-1] != last:
        origins.append(last)
    return origins


def encode_jpeg(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def request_detection(
    client: httpx.Client,
    endpoint: str,
    image: Image.Image,
    confidence: float,
    quality: int,
    retries: int,
) -> dict[str, Any]:
    payload = encode_jpeg(image, quality)
    error: Exception | None = None
    for attempt in range(retries):
        try:
            response = client.post(
                endpoint,
                data={"confidence": str(confidence)},
                files={"image": ("prelabel.jpg", payload, "image/jpeg")},
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as caught:
            error = caught
            if attempt + 1 < retries:
                time.sleep(0.5 * (2**attempt))
    raise RuntimeError(f"Detector request failed after {retries} attempts: {error}")


def to_global_detection(
    detection: dict[str, Any],
    origin_x: int,
    origin_y: int,
    crop_width: int,
    crop_height: int,
    image_width: int,
    image_height: int,
    source: str,
) -> dict[str, Any]:
    x, y, width, height = map(float, detection["bbox"])
    return {
        "class_id": int(detection["class_id"]),
        "confidence": float(detection["confidence"]),
        "bbox": [
            (origin_x + x * crop_width) / image_width,
            (origin_y + y * crop_height) / image_height,
            width * crop_width / image_width,
            height * crop_height / image_height,
        ],
        "source": source,
    }


def box_iou(left: list[float], right: list[float]) -> float:
    left_x2, left_y2 = left[0] + left[2], left[1] + left[3]
    right_x2, right_y2 = right[0] + right[2], right[1] + right[3]
    intersection_width = max(0.0, min(left_x2, right_x2) - max(left[0], right[0]))
    intersection_height = max(0.0, min(left_y2, right_y2) - max(left[1], right[1]))
    intersection = intersection_width * intersection_height
    union = left[2] * left[3] + right[2] * right[3] - intersection
    return intersection / union if union > 0 else 0.0


def class_aware_nms(detections: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for detection in sorted(detections, key=lambda item: item["confidence"], reverse=True):
        if any(
            detection["class_id"] == existing["class_id"]
            and box_iou(detection["bbox"], existing["bbox"]) >= threshold
            for existing in kept
        ):
            continue
        kept.append(detection)
    return kept


def yolo_line(detection: dict[str, Any]) -> str:
    x, y, width, height = detection["bbox"]
    center_x = min(1.0, max(0.0, x + width / 2))
    center_y = min(1.0, max(0.0, y + height / 2))
    width = min(1.0, max(0.0, width))
    height = min(1.0, max(0.0, height))
    return f"{detection['class_id']} {center_x:.7f} {center_y:.7f} {width:.7f} {height:.7f}"


def process_image(
    client: httpx.Client,
    args: argparse.Namespace,
    source_path: Path,
) -> tuple[dict[str, Any], int]:
    with Image.open(source_path) as source:
        oriented = ImageOps.exif_transpose(source).convert("RGB")
    image = resize_for_inference(oriented, args.max_working_side)
    detections: list[dict[str, Any]] = []
    calls = 0

    full_response = request_detection(
        client,
        args.endpoint,
        image,
        args.confidence,
        args.jpeg_quality,
        args.retries,
    )
    calls += 1
    detections.extend(
        to_global_detection(
            item,
            0,
            0,
            image.width,
            image.height,
            image.width,
            image.height,
            "full",
        )
        for item in full_response["detections"]
    )

    if max(image.size) > args.tile_size:
        x_origins = tile_origins(image.width, args.tile_size, args.tile_overlap)
        y_origins = tile_origins(image.height, args.tile_size, args.tile_overlap)
        for y in y_origins:
            for x in x_origins:
                right = min(image.width, x + args.tile_size)
                bottom = min(image.height, y + args.tile_size)
                tile = image.crop((x, y, right, bottom))
                response = request_detection(
                    client,
                    args.endpoint,
                    tile,
                    args.confidence,
                    args.jpeg_quality,
                    args.retries,
                )
                calls += 1
                detections.extend(
                    to_global_detection(
                        item,
                        x,
                        y,
                        tile.width,
                        tile.height,
                        image.width,
                        image.height,
                        f"tile:{x},{y},{tile.width},{tile.height}",
                    )
                    for item in response["detections"]
                )

    detections = class_aware_nms(detections, args.nms_iou)
    target = []
    other = []
    for item in detections:
        if item["class_id"] == args.target_class_id:
            target.append({**item, "prelabel_method": "native"})
        elif item["class_id"] in args.remap_class_id:
            target.append(
                {
                    **item,
                    "original_class_id": item["class_id"],
                    "class_id": args.target_class_id,
                    "prelabel_method": "folder_label_remap",
                }
            )
        else:
            other.append(item)
    return (
        {
            "source_size": {"width": oriented.width, "height": oriented.height},
            "working_size": {"width": image.width, "height": image.height},
            "model_sha256": full_response["model_sha256"],
            "detections": detections,
            "target_detections": target,
            "other_class_detections": other,
        },
        calls,
    )


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    output_dir = args.output_dir.resolve()
    labels_dir = output_dir / "labels"
    raw_dir = output_dir / "raw"
    labels_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_root = Path(manifest["summary"]["source_root"])
    candidates = [record for record in manifest["records"] if record["status"] == "candidate"]
    if args.limit is not None:
        candidates = candidates[: args.limit]

    endpoint_root = args.endpoint.rsplit("/v1/detect", 1)[0]
    with httpx.Client(timeout=args.timeout) as client:
        health = client.get(f"{endpoint_root}/health")
        health.raise_for_status()
        health_payload = health.json()
        if health_payload.get("status") != "ok":
            raise RuntimeError(f"Detector is not ready: {health_payload}")

        results = []
        started = time.perf_counter()
        total_calls = 0
        for position, record in enumerate(candidates, 1):
            relative_path = str(record["relative_path"])
            image_id = stable_image_id(relative_path)
            raw_path = raw_dir / f"{image_id}.json"
            label_path = labels_dir / f"{image_id}.txt"
            if raw_path.is_file():
                result = json.loads(raw_path.read_text(encoding="utf-8"))
                calls = 0
            else:
                inference, calls = process_image(client, args, source_root / relative_path)
                result = {
                    "image_id": image_id,
                    "source_relative_path": relative_path,
                    **inference,
                }
                raw_path.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            total_calls += calls
            target = result["target_detections"]
            label_path.write_text(
                "\n".join(yolo_line(item) for item in target) + ("\n" if target else ""),
                encoding="utf-8",
            )
            flags = []
            if not target:
                flags.append("no_target_box")
            if result["other_class_detections"]:
                flags.append("other_class_prediction")
            if any(item["confidence"] < 0.25 for item in target):
                flags.append("low_confidence_box")
            if any(item.get("prelabel_method") == "folder_label_remap" for item in target):
                flags.append("remapped_class_box")
            if any(
                item["bbox"][2] * item["bbox"][3] > 0.20
                or item["bbox"][2] > 0.75
                or item["bbox"][3] > 0.75
                for item in target
            ):
                flags.append("oversized_box")
            if any(
                box_iou(left["bbox"], right["bbox"]) >= 0.20
                for offset, left in enumerate(target)
                for right in target[offset + 1 :]
            ):
                flags.append("overlapping_boxes")
            if len(target) > 20:
                flags.append("many_boxes")
            results.append(
                {
                    "image_id": image_id,
                    "source_relative_path": relative_path,
                    "label_relative_path": label_path.relative_to(output_dir).as_posix(),
                    "target_box_count": len(target),
                    "native_box_count": sum(
                        item.get("prelabel_method") == "native" for item in target
                    ),
                    "remapped_box_count": sum(
                        item.get("prelabel_method") == "folder_label_remap" for item in target
                    ),
                    "other_box_count": len(result["other_class_detections"]),
                    "minimum_target_confidence": min(
                        (item["confidence"] for item in target), default=None
                    ),
                    "maximum_target_confidence": max(
                        (item["confidence"] for item in target), default=None
                    ),
                    "flags": flags,
                }
            )
            if position % 10 == 0 or position == len(candidates):
                elapsed = time.perf_counter() - started
                print(
                    f"processed={position}/{len(candidates)} calls={total_calls} "
                    f"elapsed_s={elapsed:.1f}",
                    flush=True,
                )

    box_count = sum(item["target_box_count"] for item in results)
    flag_counts = Counter(flag for item in results for flag in item["flags"])
    for item in results:
        if "no_target_box" in item["flags"]:
            item["review_priority"] = "P0"
        elif item["flags"]:
            item["review_priority"] = "P1"
        else:
            item["review_priority"] = "P2"
    summary = {
        "source_manifest": str(manifest_path),
        "endpoint": args.endpoint,
        "model": health_payload,
        "configuration": {
            "confidence": args.confidence,
            "target_class_id": args.target_class_id,
            "remap_class_ids": args.remap_class_id,
            "max_working_side": args.max_working_side,
            "tile_size": args.tile_size,
            "tile_overlap": args.tile_overlap,
            "nms_iou": args.nms_iou,
            "jpeg_quality": args.jpeg_quality,
        },
        "image_count": len(results),
        "image_with_target_boxes": sum(item["target_box_count"] > 0 for item in results),
        "image_without_target_boxes": sum(item["target_box_count"] == 0 for item in results),
        "target_box_count": box_count,
        "native_box_count": sum(item["native_box_count"] for item in results),
        "remapped_box_count": sum(item["remapped_box_count"] for item in results),
        "mean_target_boxes_per_image": box_count / len(results) if results else math.nan,
        "flag_counts": dict(flag_counts),
        "detector_request_count_this_run": total_calls,
        "elapsed_seconds": time.perf_counter() - started,
        "requires_human_review": True,
    }
    (output_dir / "review-manifest.json").write_text(
        json.dumps({"summary": summary, "images": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    queue_fields = [
        "review_priority",
        "image_id",
        "source_relative_path",
        "label_relative_path",
        "target_box_count",
        "native_box_count",
        "remapped_box_count",
        "other_box_count",
        "minimum_target_confidence",
        "maximum_target_confidence",
        "flags",
    ]
    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    with (output_dir / "review-queue.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=queue_fields)
        writer.writeheader()
        for item in sorted(
            results,
            key=lambda row: (
                priority_order[str(row["review_priority"])],
                str(row["source_relative_path"]),
            ),
        ):
            writer.writerow(
                {
                    **{field: item.get(field) for field in queue_fields},
                    "flags": "|".join(item["flags"]),
                }
            )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
