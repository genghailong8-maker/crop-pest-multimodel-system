from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import validate_r31  # noqa: E402


class R31ValidatorTests(unittest.TestCase):
    def test_manifest_is_structurally_valid_but_fails_closed_on_missing_severity_evidence(self) -> None:
        result = validate_r31.validate_manifest(ROOT / "manifest.json")
        self.assertEqual(result["status"], validate_r31.NEEDS)
        self.assertEqual(len(result["documents"]), 8)
        self.assertEqual(result["evidence_summary"]["record_count"], 150)
        self.assertEqual(result["evidence_summary"]["treatment_audit_count"], 38)
        self.assertEqual(result["capability_summary"]["record_count"], 38)
        self.assertEqual(result["capability_summary"]["status_counts"], {"FULL": 13, "PARTIAL": 25, "REJECTED": 0})
        self.assertEqual(result["capability_summary"]["severity_available_hosts"], 13)
        self.assertEqual(result["capability_summary"]["host_general_treatments"], 38)
        self.assertEqual(result["capability_summary"]["general_insect_treatments"], 8)
        self.assertFalse(any(item["level"] == validate_r31.INVALID for item in result["issues"]))
        self.assertTrue(any(item["status"] == validate_r31.NEEDS for item in result["documents"].values()))
        self.assertEqual(result["documents"]["12"]["status"], validate_r31.NEEDS)

    def test_dangling_source_reference_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "knowledge"
            shutil.copytree(ROOT, staging)
            document = staging / "insects" / "08-芫菁.md"
            document.write_text(document.read_text(encoding="utf-8").replace("[R31-08-NCSU-SOY]", "[R31-NOT-REGISTERED]", 1), encoding="utf-8")
            result = validate_r31.validate_manifest(staging / "manifest.json")
            self.assertEqual(result["status"], validate_r31.INVALID)
            self.assertTrue(any("dangling source reference" in item["message"] for item in result["issues"]))

    def test_cross_host_treatment_source_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "knowledge"
            shutil.copytree(ROOT, staging)
            document = staging / "insects" / "09-蚜虫.md"
            text = document.read_text(encoding="utf-8")
            text = text.replace("[R31-09-UMN-CORN][R31-09-BEIJING-CROPS][R31-GLOBAL-IPM-MOA]", "[R31-09-PEACH][R31-09-BEIJING-CROPS][R31-GLOBAL-IPM-MOA]", 1)
            document.write_text(text, encoding="utf-8")
            result = validate_r31.validate_manifest(staging / "manifest.json")
            self.assertEqual(result["status"], validate_r31.INVALID)
            self.assertTrue(any("out of scope for host:9:玉米" in item["message"] for item in result["issues"]))

    def test_duplicate_host_heading_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "knowledge"
            shutil.copytree(ROOT, staging)
            document = staging / "insects" / "08-芫菁.md"
            text = document.read_text(encoding="utf-8")
            marker = "### 寄主：大豆"
            text = text.replace(marker, marker + "\n\n### 寄主：大豆", 1)
            document.write_text(text, encoding="utf-8")
            result = validate_r31.validate_manifest(staging / "manifest.json")
            self.assertEqual(result["status"], validate_r31.INVALID)
            self.assertTrue(any("duplicate host heading" in item["message"] for item in result["issues"]))

    def test_complete_synthesized_record_requires_source_and_note(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "knowledge"
            shutil.copytree(ROOT, staging)
            registry_path = staging / "severity-evidence.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            complete = next(item for item in registry["records"] if item["status"] == validate_r31.COMPLETE)
            complete["source_ids"] = []
            complete["synthesis_note"] = ""
            registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
            result = validate_r31.validate_manifest(staging / "manifest.json")
            self.assertEqual(result["status"], validate_r31.INVALID)
            self.assertTrue(any("COMPLETE record has no source_ids" in item["message"] for item in result["issues"]))
            self.assertTrue(any("synthesized COMPLETE record has no synthesis_note" in item["message"] for item in result["issues"]))

    def test_unsupported_quantitative_claim_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "knowledge"
            shutil.copytree(ROOT, staging)
            registry_path = staging / "severity-evidence.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            complete = next(item for item in registry["records"] if item["status"] == validate_r31.COMPLETE)
            complete["rubric_text"] += " 受害面积为10%。"
            registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
            result = validate_r31.validate_manifest(staging / "manifest.json")
            self.assertEqual(result["status"], validate_r31.INVALID)
            self.assertTrue(any("unsupported quantitative claim" in item["message"] for item in result["issues"]))

    def test_duplicate_complete_rubric_is_review_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "knowledge"
            shutil.copytree(ROOT, staging)
            registry_path = staging / "severity-evidence.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            complete = [item for item in registry["records"] if item["object_type"] == "insect_host" and item["status"] == validate_r31.COMPLETE]
            complete[3]["rubric_text"] = complete[0]["rubric_text"]
            registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
            result = validate_r31.validate_manifest(staging / "manifest.json")
            self.assertEqual(result["status"], validate_r31.NEEDS)
            self.assertTrue(any(item["level"] == validate_r31.REVIEW_REQUIRED for item in result["issues"]))

    def test_uncertain_must_resolve_to_no_treatment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "knowledge"
            shutil.copytree(ROOT, staging)
            registry_path = staging / "capability-fallback.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["uncertain"]["treatment_level"] = "host_general"
            registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
            result = validate_r31.validate_manifest(staging / "manifest.json")
            self.assertEqual(result["status"], validate_r31.INVALID)
            self.assertTrue(any("uncertain policy must be NO_TREATMENT" in item["message"] for item in result["issues"]))

    def test_severity_capability_requires_all_three_complete_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "knowledge"
            shutil.copytree(ROOT, staging)
            registry_path = staging / "capability-fallback.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            partial = next(item for item in registry["records"] if item["status"] == "PARTIAL")
            partial["severity_available"] = True
            partial["capabilities"]["severity"] = True
            partial["status"] = "FULL"
            registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
            result = validate_r31.validate_manifest(staging / "manifest.json")
            self.assertEqual(result["status"], validate_r31.INVALID)
            self.assertTrue(any("severity_available does not equal complete three-tier evidence" in item["message"] for item in result["issues"]))


if __name__ == "__main__":
    unittest.main()
