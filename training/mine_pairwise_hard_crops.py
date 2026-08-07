from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from evaluate_weak_reranker import crop_box, iou, label_path, parse_ground_truth, read_images, sha256


CLASS_NAMES = {10: "10_mirid_bugs", 13: "13_grasshoppers", 99: "99_background"}
TARGET_CLASSES = {10, 13}


def split_for_image(path: Path, seed: int, val_percent: int) -> str:
    digest = hashlib.sha1(f"{seed}:{path.name}".encode()).digest()[0]
    return "val" if digest < round(256 * val_percent / 100) else "train"


def stable_name(path: Path) -> str:
    return hashlib.sha1(str(path).encode()).hexdigest()[:10]


def matched_label(candidate: list[float], ground_truth: list[dict[str, Any]]) -> tuple[int, float, int | None]:
    best_target_iou = 0.0
    best_target_class: int | None = None
    best_any_iou = 0.0
    for target in ground_truth:
        overlap = iou(candidate, target["bbox"])
        if overlap > best_any_iou:
            best_any_iou = overlap
        if target["class_id"] in TARGET_CLASSES and overlap > best_target_iou:
            best_target_iou = overlap
            best_target_class = target["class_id"]
    if best_target_class is not None and best_target_iou >= 0.30:
        return best_target_class, best_target_iou, best_target_class
    return 99, best_any_iou, None


def write_source_list(path: Path, records: list[dict[str, Any]]) -> None:
    images = sorted({str(record["image"]) for record in records})
    path.write_text("".join(f"{image}\n" for image in images), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mine official-train hard crops for classes 10 versus 13.")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--official-train", type=Path, required=True)
    parser.add_argument("--main-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="0")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument(
        "--prediction-confidence",
        type=float,
        default=0.001,
        help="Detector confidence passed to NMS; can be lower than the candidate filter to mine hard negatives.",
    )
    parser.add_argument("--candidate-confidence", type=float, default=0.05)
    parser.add_argument("--crop-expand", type=float, default=0.5)
    parser.add_argument("--internal-val-percent", type=int, default=15)
    parser.add_argument("--background-ratio", type=float, default=2.0)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    from ultralytics import YOLO

    project_root = args.project_root.expanduser().resolve()
    official_train = args.official_train.expanduser().resolve(strict=True)
    main_path = args.main_model.expanduser().resolve(strict=True)
    output = args.output.expanduser().resolve()
    if output.exists():
        if not args.force:
            raise FileExistsError(f"output exists; pass --force to rebuild: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    image_paths = read_images(official_train)
    model = YOLO(str(main_path), task="detect")
    raw_records: list[dict[str, Any]] = []
    stats = Counter()
    # Process bounded chunks rather than one giant source list. Some official
    # images have extreme aspect ratios; handing all paths to the predictor can
    # make its warm-up batch unexpectedly large on the 32 GB GPU.
    for start in range(0, len(image_paths), args.batch):
        batch_paths = image_paths[start : start + args.batch]
        results = model.predict(
            source=[str(path) for path in batch_paths],
            imgsz=args.image_size,
            batch=len(batch_paths),
            device=args.device,
            conf=min(args.prediction_confidence, args.candidate_confidence),
            iou=0.7,
            max_det=300,
            verbose=False,
            save=False,
        )
        for image_path, result in zip(batch_paths, results):
            width, height = result.orig_shape[1], result.orig_shape[0]
            ground_truth = parse_ground_truth(label_path(image_path), width, height)
            split = split_for_image(image_path, args.seed, args.internal_val_percent)
            stats[("source_images", split)] += 1
            for box_index, target in enumerate(ground_truth):
                if target["class_id"] in TARGET_CLASSES:
                    raw_records.append(
                        {
                            "image": image_path,
                            "bbox": target["bbox"],
                            "label": target["class_id"],
                            "split": split,
                            "kind": "ground_truth",
                            "predicted_class": None,
                            "prediction_confidence": None,
                            "iou": 1.0,
                            "source_index": box_index,
                        }
                    )
                    stats[("ground_truth", split, target["class_id"])] += 1
            boxes = result.boxes
            for prediction_index in range(len(boxes) if boxes is not None else 0):
                prediction = boxes[prediction_index]
                predicted_class = int(prediction.cls.item())
                confidence = float(prediction.conf.item())
                if predicted_class not in TARGET_CLASSES or confidence < args.candidate_confidence:
                    continue
                bbox = [float(value) for value in prediction.xyxy[0].detach().cpu().tolist()]
                label, overlap, matched_target = matched_label(bbox, ground_truth)
                raw_records.append(
                    {
                        "image": image_path,
                        "bbox": bbox,
                        "label": label,
                        "split": split,
                        "kind": "candidate",
                        "predicted_class": predicted_class,
                        "prediction_confidence": confidence,
                        "iou": overlap,
                        "matched_target": matched_target,
                        "source_index": prediction_index,
                    }
                )
                stats[("candidate", split, predicted_class, label)] += 1

    for split in ("train", "val"):
        positives = [record for record in raw_records if record["split"] == split and record["label"] in TARGET_CLASSES]
        backgrounds = [record for record in raw_records if record["split"] == split and record["label"] == 99]
        max_background = int(max(1, len(positives) * args.background_ratio))
        backgrounds = sorted(
            backgrounds,
            key=lambda record: hashlib.sha1(
                f"{args.seed}:{record['image']}:{record['source_index']}".encode()
            ).hexdigest(),
        )[:max_background]
        selected = positives + backgrounds
        random.Random(args.seed + (1 if split == "val" else 0)).shuffle(selected)
        saved_records: list[dict[str, Any]] = []
        for index, record in enumerate(selected):
            with Image.open(record["image"]) as image:
                crop = crop_box(image.convert("RGB"), record["bbox"], args.crop_expand)
                if min(crop.size) < 10:
                    stats[("dropped_tiny", split, record["label"])] += 1
                    continue
                class_dir = output / split / CLASS_NAMES[record["label"]]
                class_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{Path(record['image']).stem}_{stable_name(record['image'])}_{index:05d}.jpg"
                crop.save(class_dir / filename, format="JPEG", quality=95, optimize=True)
                saved_records.append(record)
            stats[("selected_crops", split, record["label"])] += 1
        write_source_list(output / f"source-{split}.txt", saved_records)

    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "policy": "official train only; class 10/13 ground-truth crops plus main-model candidate hard negatives; official validation is untouched",
        "seed": args.seed,
        "class_names": {str(key): value for key, value in CLASS_NAMES.items()},
        "parameters": {
            "device": args.device,
            "image_size": args.image_size,
            "batch": args.batch,
            "prediction_confidence": args.prediction_confidence,
            "candidate_confidence": args.candidate_confidence,
            "crop_expand": args.crop_expand,
            "internal_val_percent": args.internal_val_percent,
            "background_ratio": args.background_ratio,
        },
        "sources": {
            "official_train": str(official_train),
            "official_train_sha256": sha256(official_train),
            "main_model": str(main_path),
            "main_model_sha256": sha256(main_path),
        },
        "counts": {"/".join(map(str, key)): value for key, value in stats.items()},
        "raw_record_count": len(raw_records),
        "selected_record_count": sum(
            value for key, value in stats.items() if key[0] == "selected_crops"
        ),
        "source_lists": {
            split: {
                "path": str(output / f"source-{split}.txt"),
                "sha256": sha256(output / f"source-{split}.txt"),
            }
            for split in ("train", "val")
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
