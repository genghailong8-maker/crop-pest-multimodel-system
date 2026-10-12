import sys
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import finalize_adaptive_capability as generator  # noqa: E402


class SeverityControlSectionTests(unittest.TestCase):
    def test_parser_preserves_mapping_and_source(self):
        parsed = generator._severity_control_parts(
            "##### 轻度\n"
            "###### 农业防治\n"
            "葡萄园清理杂草。[R31-10-XILINGOL]\n"
            "<!-- mapping_type: PROJECT_TIER_MAPPING -->\n"
            "<!-- evidence_scope: DIRECT_HOST -->\n"
            "<!-- taxon_scope: REPRESENTATIVE_SPECIES -->"
        )
        self.assertEqual(
            parsed["mild"]["agricultural_control"],
            {
                "text": "葡萄园清理杂草。",
                "source_ids": ["R31-10-XILINGOL"],
                "mapping_type": "PROJECT_TIER_MAPPING",
                "evidence_scope": "DIRECT_HOST",
                "taxon_scope": "REPRESENTATIVE_SPECIES",
            },
        )

    def test_parser_rejects_empty_or_uncited_control(self):
        for body in (
            "<!-- mapping_type: PROJECT_TIER_MAPPING -->",
            "只有文本，没有来源。\n<!-- mapping_type: PROJECT_TIER_MAPPING -->",
            "有文本和来源。[R31-10-XILINGOL]\n<!-- mapping_type: PROJECT_TIER_MAPPING -->\n<!-- evidence_scope: UNSUPPORTED -->",
            "有文本和来源。[R31-10-XILINGOL]\n<!-- mapping_type: PROJECT_TIER_MAPPING -->\n<!-- evidence_scope: DIRECT_HOST -->\n<!-- taxon_scope: FAMILY_WIDE -->",
        ):
            with self.subTest(body=body), self.assertRaises(ValueError):
                generator._severity_control_parts(f"##### 轻度\n###### 生物防治\n{body}")

    def test_official_five_subset_has_72_severity_rows_and_uncertain_null(self):
        manifest = generator._read_json(generator.MANIFEST_PATH)
        evidence = generator._read_json(generator.EVIDENCE_PATH)
        registry = generator.build_registry(manifest, evidence)
        official_legacy_ids = {8, 9, 10, 11, 14}
        records = [
            item for item in registry["records"]
            if item.get("object_type") == "insect_host_capability"
            and item["class_id"] in official_legacy_ids
        ]
        levels = [
            level
            for item in records
            for level in item["host_severity_treatment"].get("levels", {}).values()
        ]
        self.assertEqual(len(records), 24)
        self.assertEqual(len(levels), 72)
        for item in records:
            treatment = item["host_severity_treatment"]
            self.assertEqual(treatment["treatment_level"], "host_severity")
            self.assertTrue(treatment["available"])
            self.assertEqual(set(treatment["levels"]), {"mild", "moderate", "severe"})
        self.assertEqual(registry["treatment_fallback_order"], ["host_severity", "host_general", "insect_general"])
        self.assertEqual(registry["uncertain"]["treatment"], None)
        self.assertEqual(registry["uncertain"]["treatment_level"], "none")

    def test_only_source_supported_sections_are_emitted(self):
        manifest = generator._read_json(generator.MANIFEST_PATH)
        evidence = generator._read_json(generator.EVIDENCE_PATH)
        registry = generator.build_registry(manifest, evidence)
        official_legacy_ids = {8, 9, 10, 11, 14}
        records = [
            item for item in registry["records"]
            if item.get("object_type") == "insect_host_capability"
            and item["class_id"] in official_legacy_ids
        ]
        category_counts = {key: 0 for key in generator.CONTROL_HEADINGS.values()}
        for item in records:
            for level in item["host_severity_treatment"].get("levels", {}).values():
                body = level.get("body", {})
                sections = body.get("sections", {})
                provenance = body.get("section_provenance", {})
                for key in category_counts:
                    if key not in sections:
                        self.assertNotIn(key, body.get("section_source_ids", {}))
                        self.assertNotIn(key, provenance)
                        continue
                    category_counts[key] += 1
                    self.assertTrue(sections[key].strip())
                    self.assertTrue(body["section_source_ids"][key])
                    self.assertEqual(provenance[key]["mapping_type"], "PROJECT_TIER_MAPPING")
                    self.assertTrue(all(provenance[key]["scope"]))
        self.assertEqual(category_counts, {
            "agricultural_control": 45,
            "physical_control": 39,
            "biological_control": 43,
        })

    def test_tnau_paddy_controls_are_scoped_only_to_rice_mole_cricket(self):
        source = (ROOT / "insects" / "11-蝼蛄.md").read_text(encoding="utf-8")
        host_sections = {}
        for section in re.split(r"(?m)(?=^### 寄主：)", source):
            match = re.search(r"(?m)^### 寄主：([^\r\n]+)", section)
            if match:
                host_sections[match.group(1).strip()] = section
        source_id = "R31-11-TNAU-EXPERT-PADDY-MOLECRICKET"
        self.assertNotIn(source_id, host_sections["玉米"])
        self.assertNotIn("#### 分级防治措施", host_sections["玉米"])
        self.assertIn(source_id, host_sections["水稻"])


if __name__ == "__main__":
    unittest.main()
