"""Narrow data-driven smoke for the final knowledge expansion."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "backend"))

from app.r31_host_knowledge import clear_cache, host_knowledge_payload  # noqa: E402


def record(crop: str, severity: str = "mild", *, confirmed: bool = True) -> dict:
    return {
        "detections": [{"class_id": 12, "class_name": "叶蝉科", "confidence": 0.99}],
        "detector_summary": {"primary_candidate": {"class_id": 12, "class_name": "叶蝉科", "max_confidence": 0.99}},
        "severity": {"level": severity},
        "context": {"host_selection": {"confirmed_host": crop} if confirmed else {}},
    }


def test_leafhopper_tea_is_full_and_data_driven() -> None:
    clear_cache()
    payload = host_knowledge_payload(record("茶"))
    assert payload["host"]["status"] == "FULL"
    assert payload["host_knowledge"]["severity_available"] is True
    assert set(payload["host_knowledge"]["severity"]["levels"]) == {"mild", "moderate", "severe"}
    assert payload["treatment"]["treatment_level"] == "host_general"


def test_leafhopper_rice_remains_fail_closed() -> None:
    clear_cache()
    payload = host_knowledge_payload(record("水稻"))
    assert payload["host"]["status"] == "PARTIAL"
    assert payload["host_knowledge"]["severity_available"] is False
    assert payload["host_knowledge"]["severity"]["levels"] == {}


def test_authority_and_uncertain_contract_are_unchanged() -> None:
    clear_cache()
    selector = host_knowledge_payload(record("茶", confirmed=False))
    assert selector["recommended_host"] == "茶"
    assert selector["confirmed_host"] is None
    assert selector["selection_required"] is True
    assert selector["host_authority"]["recommended_host_is_confirmed_host"] is False

    uncertain = host_knowledge_payload(record("茶", severity="uncertain"))
    assert uncertain["treatment"]["treatment_level"] == "none"
    assert uncertain["treatment"]["body"] is None
