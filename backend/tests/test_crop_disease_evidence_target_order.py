from __future__ import annotations

import unittest

from app.search.evidence_extractor import EvidenceExtractor
from app.search.models import SearchEvidence, SearchSource


class CropDiseaseEvidenceTargetOrderTests(unittest.TestCase):
    def extract(self, class_name: str, section: str, clause: str, title: str) -> list[str]:
        source = SearchSource(
            id="official-source",
            title=title,
            site_name="official agricultural source",
            url="https://example.test/official-source",
            snippet=clause,
            content=clause,
            reliability_level="权威农业数据库",
        )
        evidence = SearchEvidence(
            class_name=class_name,
            query_type=section,
            status="available",
            sources=[source],
        )
        result = EvidenceExtractor().extract(evidence)
        values = result.harms if section == "harms" else result.possible_causes
        return [item.conclusion for item in values]

    def test_tungro_harm_with_disease_before_symptoms(self) -> None:
        clause = "Plants affected by tungro exhibit stunting and reduced tillering."
        self.assertIn(
            clause,
            self.extract(
                "水稻东格鲁病毒病",
                "harms",
                clause,
                "Diagnosis of Common Diseases of Rice — IRRI",
            ),
        )

    def test_tungro_transmission_with_disease_before_vector(self) -> None:
        clause = "Tungro are transmitted by the green leafhoppers."
        self.assertIn(
            clause,
            self.extract(
                "水稻东格鲁病毒病",
                "possible_causes",
                clause,
                "Diagnosis of Common Diseases of Rice — IRRI",
            ),
        )

    def test_gray_leaf_spot_harm_accepts_capitalized_lesion_sentence(self) -> None:
        clause = "Lesions may eventually coalesce killing the leaves."
        self.assertIn(
            clause,
            self.extract("玉米灰斑病", "harms", clause, "Gray Leaf Spot — Cornell CALS"),
        )

    def test_gray_leaf_spot_accepts_favorable_weather_and_cropping_conditions(self) -> None:
        clauses = (
            "Gray leaf spot is favored by wet humid weather.",
            "Additionally, it is favored in situations with reduced tillage and continuous corn.",
            "Continuous corn and no-till systems are at high risk for disease development.",
        )
        for clause in clauses:
            with self.subTest(clause=clause):
                self.assertIn(
                    clause,
                    self.extract(
                        "玉米灰斑病",
                        "possible_causes",
                        clause,
                        "Gray Leaf Spot — Cornell CALS",
                    ),
                )


if __name__ == "__main__":
    unittest.main()
