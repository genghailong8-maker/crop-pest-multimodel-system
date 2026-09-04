from __future__ import annotations

from app.catalog import CLASS_CATALOG
from app.main import local_treatment_payload, present_case, severity_rubric_payload
from app.severity import severity_for_record
from app.severity_v2 import (
    SEVERITY_V2_LEVELS,
    readiness_for,
    references_for_canonical,
    rubric_for_canonical,
    severity_payload,
    validate_contract,
)


def _record(class_id: int, level: str) -> dict:
    item = next(row for row in CLASS_CATALOG if row["id"] == class_id)
    return {
        "detections": [{"class_id": class_id, "class_name": item["name_zh"]}],
        "detector_summary": {"primary_candidate": {"class_id": class_id, "class_name": item["name_zh"]}},
        "severity": severity_payload(level),
    }


def test_v2_contract_has_exact_16_by_3_coverage() -> None:
    counts = validate_contract()
    assert counts == {"rubrics": 16, "alignment": 48, "ready_keep": 35, "ready_adjust": 0, "needs_research": 13}
    for item in CLASS_CATALOG:
        rubric = rubric_for_canonical(item["name_zh"])
        assert rubric is not None
        assert {"assessment_unit", "observable_features", "mild", "moderate", "severe", "uncertain"} <= set(rubric)
        assert set(references_for_canonical(item["name_zh"])) == {"mild", "moderate", "severe"}
        assert [readiness_for(item["name_zh"], level) for level in ("mild", "moderate", "severe")] .count(None) == 0
    assert rubric_for_canonical("玉米") is None


def test_v2_payload_has_no_v1_numeric_score() -> None:
    for level in SEVERITY_V2_LEVELS:
        payload = severity_payload(level)
        assert payload["level"] == level
        assert payload["source"] == "user_guided_rubric"
        assert payload["scope"] == "current_sample"
        assert payload["algorithm_version"] == "severity-v2"
        assert "score" not in payload and "affected_ratio" not in payload and "spread_speed" not in payload


def test_all_48_pairs_use_exact_local_kb_tier_regardless_of_historical_alignment() -> None:
    expected = {"READY_KEEP": 0, "READY_ADJUST": 0, "NEEDS_RESEARCH": 0}
    for item in CLASS_CATALOG:
        canonical = item["name_zh"]
        for level in ("mild", "moderate", "severe"):
            state = readiness_for(canonical, level)
            assert state in expected
            expected[state] += 1
            treatment = local_treatment_payload(_record(item["id"], level))
            assert treatment["source"] == "local_knowledge_base"
            assert treatment["status"] == "available"
            assert treatment["severity_level"] == level
            assert treatment["content"].get("markdown")
            assert treatment["content"].get("markdown_html")
            assert "防治措施来源" not in treatment["content"]["markdown"]
            assert treatment["content"]["tier"] == {"mild": "轻度", "moderate": "中度", "severe": "重度"}[level]
    assert expected == {"READY_KEEP": 35, "READY_ADJUST": 0, "NEEDS_RESEARCH": 13}


def test_historical_needs_research_pair_is_available_from_exact_local_kb() -> None:
    treatment = local_treatment_payload(_record(10, "moderate"))
    assert readiness_for("盲蝽科", "moderate") == "NEEDS_RESEARCH"
    assert treatment["status"] == "available"
    assert treatment["severity_level"] == "moderate"
    assert treatment["content"]["tier"] == "中度"
    assert treatment["content"]["markdown"]
    assert treatment["content"]["markdown_html"]
    assert treatment["source"] == "local_knowledge_base"


def test_mole_cricket_severe_resolves_document_level_sources() -> None:
    treatment = local_treatment_payload(_record(11, "severe"))
    assert treatment["source"] == "local_knowledge_base"
    assert treatment["status"] == "available"
    assert treatment["severity_level"] == "severe"
    assert treatment["source_ids"] == ["13-T1", "13-T2"]
    assert treatment["source_ids"] == [source["id"] for source in treatment["sources"]]
    assert "防治措施来源" not in treatment["content"]["markdown"]


def test_uncertain_never_selects_or_falls_back_to_a_tier() -> None:
    treatment = local_treatment_payload(_record(0, "uncertain"))
    assert treatment["status"] == "unavailable"
    assert treatment["reason"] == "severity_uncertain"
    assert treatment["content"] == {} and treatment["source_ids"] == []


def test_historical_v1_record_remains_readable_and_unchanged() -> None:
    result = severity_for_record({"affected_ratio_percent": 20, "spread_speed": "ongoing"}).as_dict()
    assert result["algorithm_version"] == "severity_v1"
    assert result["level"] == "moderate"
    assert result["score"] == 28


def test_v2_overrides_legacy_values_and_partial_legacy_read_is_safe() -> None:
    v2_record = {
        **_record(0, "mild"),
        "affected_ratio_percent": 90,
        "spread_speed": "rapid",
    }
    presented = present_case(v2_record)
    assert presented["severity"]["level"] == "mild"
    assert presented["treatment"]["severity_level"] == "mild"

    partial = {
        "detections": [{"class_id": 0, "class_name": "玉米叶枯病"}],
        "detector_summary": {"primary_candidate": {"class_id": 0, "class_name": "玉米叶枯病"}},
        "affected_ratio_percent": 20,
        "spread_speed": "unknown",
    }
    safe = present_case(partial)
    assert safe["severity"]["status"] == "not_provided"
    assert safe["severity"]["decision_rule"] == "legacy_inputs_incomplete"
    assert safe["treatment"]["reason"] == "legacy_severity_input_incomplete"
