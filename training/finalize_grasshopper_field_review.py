"""Finalize a fully accepted class-13 field review for calibration."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pixel_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Image.open(path) as source:
        image = source.convert("RGB")
    digest.update(f"{image.width}x{image.height}:RGB\n".encode("ascii"))
    digest.update(image.tobytes())
    return digest.hexdigest()


def read_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("records"), list):
        raise ValueError("manifest.json does not contain records")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    args = parser.parse_args()

    root = args.dataset_root.expanduser().resolve(strict=True)
    manifest_path = root / "manifest.json"
    review_path = root / "review.csv"
    manifest = read_manifest(manifest_path)
    if not manifest.get("automated_gate_passed"):
        raise ValueError("automated audit gate did not pass")

    with review_path.open(newline="", encoding="utf-8-sig") as stream:
        reviews = {row["record_id"]: row for row in csv.DictReader(stream)}
    expected_ids = {str(record["record_id"]) for record in manifest["records"]}
    if set(reviews) != expected_ids:
        missing = sorted(expected_ids - set(reviews))
        extra = sorted(set(reviews) - expected_ids)
        raise ValueError(f"review IDs do not match manifest; missing={missing}, extra={extra}")

    unresolved = []
    rejected = []
    final_records = []
    reviewed_records = []
    record_by_image_name = {
        Path(record["image"]).name: record for record in manifest["records"]
    }
    for record in manifest["records"]:
        review = reviews[str(record["record_id"])]
        decision = review.get("review_decision", "").strip().casefold()
        notes = review.get("review_notes", "").strip()
        if decision not in {"accepted", "rejected"}:
            unresolved.append({"record_id": record["record_id"], "decision": decision or "missing"})
            continue
        reviewed = record | {"review_decision": decision, "review_notes": notes}
        reviewed_records.append(reviewed)
        if decision == "rejected":
            if not notes:
                raise ValueError(f"rejected review requires notes: {record['record_id']}")
            rejected.append(reviewed)
            continue
        if (record.get("near_duplicate_matches") or record.get("box_repairs")) and not notes:
            raise ValueError(
                f"near-duplicate or repaired-box review requires notes: {record['record_id']}"
            )
        cross_split_distance_zero = []
        for match in record.get("near_duplicate_matches", []):
            matched = record_by_image_name.get(Path(match["path"]).name)
            if (
                matched
                and int(match["distance"]) == 0
                and matched["output_split"] != record["output_split"]
            ):
                cross_split_distance_zero.append(str(matched["record_id"]))
        if cross_split_distance_zero and "[cross-split-distinct]" not in notes.casefold():
            raise ValueError(
                "accepted cross-split perceptual-distance-0 match requires the explicit "
                f"[cross-split-distinct] review marker: {record['record_id']} vs "
                f"{cross_split_distance_zero}"
            )
        image = (root / record["image"]).resolve(strict=True)
        label = (root / record["label"]).resolve(strict=True)
        image.relative_to(root)
        label.relative_to(root)
        final_records.append(
            record
            | {
                "final_image_sha256": sha256(image),
                "final_pixel_sha256": pixel_sha256(image),
                "final_label_sha256": sha256(label),
                "review_decision": decision,
                "review_notes": notes,
            }
        )
    if unresolved:
        raise ValueError(f"all records require accepted/rejected decisions: {unresolved[:10]}")

    accepted_by_pixel_hash: dict[str, dict[str, Any]] = {}
    for record in final_records:
        matched = accepted_by_pixel_hash.get(record["final_pixel_sha256"])
        if matched and matched["output_split"] != record["output_split"]:
            raise ValueError(
                "decoded-pixel duplicate remains across tune/frozen: "
                f"{matched['record_id']} and {record['record_id']}"
            )
        accepted_by_pixel_hash[record["final_pixel_sha256"]] = record
    for split in ("tune", "frozen"):
        if not any(record["output_split"] == split for record in final_records):
            raise ValueError(f"no accepted records remain in split: {split}")

    for split in ("tune", "frozen"):
        entries = [record["image"] for record in final_records if record["output_split"] == split]
        (root / f"{split}.txt").write_text("\n".join(entries) + ("\n" if entries else ""), encoding="utf-8")

    manifest.update(
        {
            "human_review_status": "accepted_with_exclusions" if rejected else "accepted",
            "human_review_completed_at_utc": datetime.now(UTC).isoformat(),
            "review_csv_sha256": sha256(review_path),
            "calibration_eligible": True,
            "records": final_records,
            "reviewed_records": reviewed_records,
            "rejected_records": rejected,
        }
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "dataset_root": str(root),
                "reviewed_images": len(final_records),
                "rejected_images": len(rejected),
                "tune_images": sum(record["output_split"] == "tune" for record in final_records),
                "frozen_images": sum(record["output_split"] == "frozen" for record in final_records),
                "calibration_eligible": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
