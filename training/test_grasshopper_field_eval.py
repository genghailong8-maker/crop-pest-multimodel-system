from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from evaluate_weak_reranker import read_images
from prepare_grasshopper_field_eval import comparison_index, parse_label


TRAINING_DIR = Path(__file__).resolve().parent
PREPARE = TRAINING_DIR / "prepare_grasshopper_field_eval.py"
FINALIZE = TRAINING_DIR / "finalize_grasshopper_field_review.py"


class GrasshopperFieldEvaluationTest(unittest.TestCase):
    def test_empty_labels_are_valid_negative_images(self) -> None:
        boxes, repairs = parse_label("", 1)
        self.assertEqual(boxes, [])
        self.assertEqual(repairs, [])

    def test_small_edge_overflow_is_clipped_and_recorded(self) -> None:
        boxes, repairs = parse_label("0 0.92626953125 0.5 0.1500244140625 0.2\n", 1)
        self.assertEqual(len(boxes), 1)
        self.assertEqual(len(repairs), 1)
        cx, _, width, _ = boxes[0]
        self.assertLessEqual(cx + width / 2, 1.0)
        self.assertEqual(repairs[0]["reason"], "clip_small_edge_overflow")

    def test_large_edge_overflow_still_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than tolerance"):
            parse_label("0 0.95 0.5 0.2 0.2\n", 1)

    def test_comparison_index_skips_broken_images(self) -> None:
        with tempfile.TemporaryDirectory(prefix="crop-pest-comparison-index-") as directory:
            root = Path(directory)
            (root / "broken.jpg").write_bytes(b"not a decodable image")
            valid = Image.new("RGB", (16, 16), (12, 34, 56))
            valid.save(root / "valid.png")

            exact, perceptual, count, skipped = comparison_index([root])

            self.assertEqual(count, 1)
            self.assertEqual(len(exact), 1)
            self.assertEqual(len(perceptual), 1)
            self.assertEqual(len(skipped), 1)
            self.assertEqual(Path(skipped[0]["path"]).name, "broken.jpg")
            self.assertIn("image", skipped[0]["error"].lower())

    def make_archive(self, path: Path) -> None:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as output:
            output.writestr(
                "data.yaml",
                "train: ../train/images\nval: ../valid/images\ntest: ../test/images\n"
                "nc: 1\nnames: ['grasshopper']\n",
            )
            for split, count in (("valid", 70), ("test", 72)):
                for index in range(count):
                    image = Image.new(
                        "RGB",
                        (80, 60),
                        (
                            (index * 17) % 255,
                            (index * 31 + (0 if split == "valid" else 9)) % 255,
                            (index * 47) % 255,
                        ),
                    )
                    ImageDraw.Draw(image).rectangle(
                        (10 + index % 8, 8, 45, 42), outline=(255, 255, 255), width=2
                    )
                    buffer = BytesIO()
                    image.save(buffer, format="PNG")
                    stem = f"{split}_{index:03d}"
                    output.writestr(f"{split}/images/{stem}.png", buffer.getvalue())
                    output.writestr(
                        f"{split}/labels/{stem}.txt",
                        "0 0.500000 0.500000 0.500000 0.500000\n",
                    )

    def accept_review(self, path: Path) -> None:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
            fieldnames = list(rows[0])
        for row in rows:
            row["review_decision"] = "accepted"
            row["review_notes"] = "[cross-split-distinct] synthetic visual review"
        with path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def reject_first_review(self, path: Path) -> None:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
            fieldnames = list(rows[0])
        for index, row in enumerate(rows):
            row["review_decision"] = "rejected" if index == 0 else "accepted"
            row["review_notes"] = (
                "synthetic duplicate exclusion"
                if index == 0
                else "[cross-split-distinct] reviewed"
            )
        with path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_prepare_review_finalize_70_72(self) -> None:
        with tempfile.TemporaryDirectory(prefix="crop-pest-field-audit-") as directory:
            root = Path(directory)
            archive = root / "grasshopper.zip"
            prepared = root / "prepared"
            self.make_archive(archive)

            subprocess.run(
                [sys.executable, str(PREPARE), "--archive", str(archive), "--output-root", str(prepared)],
                check=True,
                capture_output=True,
                text=True,
            )
            pending = json.loads((prepared / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(pending["automated_gate_passed"])
            self.assertFalse(pending["calibration_eligible"])
            self.assertEqual(
                [item["selected_image_count"] for item in pending["split_summaries"]], [70, 72]
            )

            self.accept_review(prepared / "review.csv")
            finalized_process = subprocess.run(
                [sys.executable, str(FINALIZE), "--dataset-root", str(prepared)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(finalized_process.returncode, 0, finalized_process.stderr)
            finalized = json.loads((prepared / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(finalized["calibration_eligible"])
            self.assertEqual(finalized["human_review_status"], "accepted")
            self.assertEqual(len(read_images(prepared / "tune.txt")), 70)
            self.assertEqual(len(read_images(prepared / "frozen.txt")), 72)
            self.assertTrue(all(path.is_absolute() and path.is_file() for path in read_images(prepared / "tune.txt")))

    def test_finalize_allows_documented_rejection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="crop-pest-field-rejection-") as directory:
            root = Path(directory)
            archive = root / "grasshopper.zip"
            prepared = root / "prepared"
            self.make_archive(archive)
            subprocess.run(
                [sys.executable, str(PREPARE), "--archive", str(archive), "--output-root", str(prepared)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.reject_first_review(prepared / "review.csv")
            finalized_process = subprocess.run(
                [sys.executable, str(FINALIZE), "--dataset-root", str(prepared)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(finalized_process.returncode, 0, finalized_process.stderr)
            finalized = json.loads((prepared / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(finalized["calibration_eligible"])
            self.assertEqual(finalized["human_review_status"], "accepted_with_exclusions")
            self.assertEqual(len(finalized["rejected_records"]), 1)
            self.assertEqual(len(read_images(prepared / "tune.txt")), 69)
            self.assertEqual(len(read_images(prepared / "frozen.txt")), 72)


if __name__ == "__main__":
    unittest.main()
