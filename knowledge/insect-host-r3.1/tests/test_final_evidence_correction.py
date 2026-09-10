"""Narrow data-driven Backend smoke for the Final Evidence Review correction."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "backend"))

from app.r31_host_knowledge import clear_cache, host_knowledge_payload  # noqa: E402


def record(class_id: int, crop: str, severity: str = "mild") -> dict:
    return {
        "detections": [{"class_id": class_id, "class_name": "test", "confidence": 0.99}],
        "detector_summary": {"primary_candidate": {"class_id": class_id, "class_name": "test", "max_confidence": 0.99}},
        "severity": {"level": severity},
        "context": {"host_selection": {"confirmed_host": crop}},
    }


def test_wheat_same_species_evidence_remains_full() -> None:
    clear_cache()
    payload = host_knowledge_payload(record(9, "小麦"))
    assert payload["host"]["status"] == "FULL"
    assert payload["host_knowledge"]["severity_available"] is True
    assert set(payload["host_knowledge"]["severity"]["levels"]) == {"mild", "moderate", "severe"}
    assert payload["treatment"]["treatment_level"] == "host_general"


def test_peanut_severity_is_fail_closed_but_direct_host_treatment_remains() -> None:
    clear_cache()
    payload = host_knowledge_payload(record(11, "花生"))
    assert payload["host"]["status"] == "PARTIAL"
    assert payload["host_knowledge"]["severity_available"] is False
    assert payload["host_knowledge"]["severity"]["levels"] == {}
    assert payload["treatment"]["treatment_level"] == "host_general"
    assert "R31-11-HAMI-PEANUT-IPM" in payload["treatment"]["source_ids"]
