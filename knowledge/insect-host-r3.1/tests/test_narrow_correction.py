"""Narrow tests for R3.1 User Knowledge Review correction."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from validate_narrow_correction import IOWA_SOY_APHID, audit, soybean_treatment_issues  # noqa: E402


class NarrowCorrectionTests(unittest.TestCase):
    def test_correction_audit_passes(self) -> None:
        result = audit()
        self.assertEqual(result["status"], "PASS")

    def test_expected_counts(self) -> None:
        counts = audit()["counts"]
        self.assertEqual(counts["prompt_traceable"], 39)
        self.assertEqual(counts["prompt_needs_evidence"], 75)
        self.assertEqual(counts["host_specific_treatment"], 38)
        self.assertEqual(counts["downgraded_to_insect_general"], 0)

    @staticmethod
    def treatment(text: str, mappings: list[dict] | None = None) -> dict:
        return {
            "sections": {"预防与监测": text},
            "source_ids": [IOWA_SOY_APHID],
            "source_entailment_review": {"clause_source_map": mappings or []},
        }

    def test_case_1_unmapped_spaced_scouting_fails(self) -> None:
        issues = soybean_treatment_issues(self.treatment("至少每 7–10 天巡查一次"))
        self.assertTrue(any("7–10 day scouting" in issue for issue in issues))

    def test_case_2_unmapped_natural_enemies_fail(self) -> None:
        issues = soybean_treatment_issues(self.treatment("保护瓢虫、食蚜蝇、蚜茧蜂"))
        self.assertTrue(any("lady beetles" in issue for issue in issues))
        self.assertTrue(any("hoverflies" in issue for issue in issues))
        self.assertTrue(any("aphidius wasps" in issue for issue in issues))

    def test_case_3_unmapped_variety_and_rotation_fail(self) -> None:
        issues = soybean_treatment_issues(self.treatment("抗虫品种和合理轮作"))
        self.assertTrue(any("resistant variety" in issue for issue in issues))
        self.assertTrue(any("crop rotation" in issue for issue in issues))

    def test_case_4_formatting_variants_do_not_bypass(self) -> None:
        issues = soybean_treatment_issues(self.treatment("至少 每7—10天，巡查一次；保护 瓢虫／食蚜蝇、蚜茧蜂。"))
        self.assertGreaterEqual(len(issues), 4)

    def test_case_5_approved_source_and_mapping_pass(self) -> None:
        text = "至少每 7—10 天巡查一次；保护瓢虫、草蛉、小花蝽和寄生性天敌；评估抗大豆蚜 Rag 品种。"
        concepts = [
            "scouting_every_7_10_days",
            "lady_beetles",
            "lacewings",
            "minute_pirate_bugs",
            "parasitoids_generic",
            "resistant_variety",
        ]
        mappings = [{"concept": concept, "source_ids": [IOWA_SOY_APHID]} for concept in concepts]
        self.assertEqual(soybean_treatment_issues(self.treatment(text, mappings)), [])


if __name__ == "__main__":
    unittest.main()
