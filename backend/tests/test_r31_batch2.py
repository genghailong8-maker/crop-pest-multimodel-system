from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app import config, database, main
from app.r31_host_knowledge import (
    FALLBACK_MESSAGES,
    OTHER_HOST,
    host_knowledge_payload,
    resolve_treatment,
)
from app.severity import parse_tiered_treatment
from app.severity_v2 import severity_payload


def _record(class_id: int, *, crop: str | None = None, severity: str = "mild") -> dict:
    item = next(row for row in main.CLASS_CATALOG if row["id"] == class_id)
    return {
        "id": f"test-{class_id}",
        "status": "detected",
        "crop": crop or item["crop"],
        "part": "不适用",
        "growth_stage": "不适用",
        "environment": {},
        "notes": "",
        "detections": [{"class_id": class_id, "class_name": item["name_zh"], "confidence": 0.91}],
        "detector_summary": {
            "primary_candidate": {"class_id": class_id, "class_name": item["name_zh"], "max_confidence": 0.91}
        },
        "analysis": {
            "evidence_analysis": {
                "status": "completed",
                "harms": [{"conclusion": "通用危害"}],
                "possible_causes": [{"conclusion": "通用诱因"}],
            },
            "sources": [],
        },
        "severity": severity_payload(severity),
        "context": {
            "host_selection": {"confirmed_host": crop} if crop else {},
        },
    }


def _settings(tmp_path: Path):
    return replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "cases.sqlite3",
        upload_dir=tmp_path / "uploads",
        report_dir=tmp_path / "reports",
        control_dir=tmp_path / "control",
        public_mode=False,
    )


def _persisted_case(tmp_path: Path, monkeypatch, *, class_id: int = 8) -> str:
    settings = _settings(tmp_path)
    monkeypatch.setattr(database, "settings", settings)
    monkeypatch.setattr(main, "settings", settings)
    database.init_database()
    image_path = settings.upload_dir / "placeholder.jpg"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"placeholder")
    record = _record(class_id)
    record.update(
        {
            "id": f"local-{class_id}",
            "created_at": "2026-09-07T00:00:00+00:00",
            "updated_at": "2026-09-07T00:00:00+00:00",
            "image_filename": image_path.name,
            "image_path": str(image_path),
            "image_width": 32,
            "image_height": 32,
            "quality": {"acceptable": True, "flags": []},
            "public_consent": False,
            "expires_at": None,
            "diagnostic_risk": "low",
            "field_severity": "unknown",
            "is_test": True,
            "instance_id": settings.instance_id,
        }
    )
    return database.create_case(record)["id"]


def test_full_host_uses_host_severity_and_preserves_recommendation_authority() -> None:
    payload = host_knowledge_payload(_record(8, crop="大豆"))
    assert payload["recommended_host"] == "大豆"
    assert payload["confirmed_host"] == "大豆"
    assert payload["recommended_host"] != payload["host"]["crop"] or payload["host_authority"]["recommended_host_is_confirmed_host"] is False
    assert payload["host"]["status"] == "FULL"
    assert payload["host_knowledge"]["severity_available"] is True
    assert set(payload["host_knowledge"]["severity"]["levels"]) == {"mild", "moderate", "severe"}
    assert payload["treatment"]["treatment_level"] == "host_severity"
    assert payload["treatment"]["fallback_message"] == FALLBACK_MESSAGES["host_severity"]


def test_full_host_falls_back_to_host_general_when_severity_treatment_is_unavailable() -> None:
    payload = host_knowledge_payload(_record(8, crop="大豆"))
    capability = deepcopy(next(option for option in payload["host_options"] if option["crop"] == "大豆"))
    capability["capabilities"]["host_severity_treatment"] = False
    treatment = resolve_treatment(
        capability,
        {"available": True, "source_ids": ["host-source"], "sections": {"prevention_monitoring": "monitor"}, "pesticide_policy": "principle_only"},
        {"available": False, "supported_severities": [], "source_ids": []},
        None,
        "mild",
    )
    assert treatment["treatment_level"] == "host_general"
    assert treatment["body"]["sections"]["prevention_monitoring"] == "monitor"


def test_partial_host_exposes_unavailable_severity_but_uses_host_general() -> None:
    payload = host_knowledge_payload(_record(8, crop="马铃薯", severity="moderate"))
    assert payload["host"]["status"] == "PARTIAL"
    assert payload["host_knowledge"]["severity_available"] is False
    assert payload["host_knowledge"]["severity"]["levels"] == {}
    assert payload["treatment"]["treatment_level"] == "host_general"
    assert payload["treatment"]["fallback_message"] != FALLBACK_MESSAGES["host_general"]


def test_missing_host_general_falls_back_to_insect_general() -> None:
    treatment = resolve_treatment(
        {"capabilities": {"host_severity_treatment": False}, "severity_available": False},
        {"available": False},
        {"available": False},
        {"available": True, "source_ids": ["global"], "measures": {"monitoring": "monitor"}, "pesticide_policy": "principle_only"},
        "moderate",
    )
    assert treatment["treatment_level"] == "insect_general"
    assert treatment["body"]["measures"]["monitoring"] == "monitor"


def test_other_and_uncertain_use_only_allowed_generic_treatment() -> None:
    other = host_knowledge_payload(_record(8, crop=OTHER_HOST))
    assert other["host"]["status"] == OTHER_HOST
    assert other["host_knowledge"]["severity_available"] is False
    assert other["host_knowledge"]["vector_diseases"] == []
    assert other["treatment"]["treatment_level"] == "insect_general"
    assert other["treatment"]["fallback_message"] == FALLBACK_MESSAGES["other"]

    uncertain = host_knowledge_payload(_record(8, crop="大豆", severity="uncertain"))
    assert uncertain["treatment"]["treatment_level"] == "host_general"
    assert uncertain["treatment"]["treatment_mode"] == "generic"
    assert uncertain["treatment"]["body"]["sections"]
    assert uncertain["treatment"].get("severity_level") is None


def test_vector_available_and_vector_severity_unavailable_is_not_synthesized() -> None:
    available = host_knowledge_payload(_record(9, crop="大豆"))
    assert available["host"]["capabilities"]["vector_disease"] is True
    assert available["host_knowledge"]["vector_diseases"]
    assert available["host_knowledge"]["vector_diseases"][0]["disease_severity_available"] is True
    assert set(available["host_knowledge"]["vector_diseases"][0]["severity"]["levels"]) == {"mild", "moderate", "severe"}

    unavailable = host_knowledge_payload(_record(9, crop="小麦"))
    assert unavailable["host_knowledge"]["vector_diseases"][0]["disease_severity_available"] is False
    assert unavailable["host_knowledge"]["vector_diseases"][0]["severity"]["levels"] == {}


def test_host_confirmation_api_persists_only_explicit_supported_host_and_refreshes_report(tmp_path, monkeypatch) -> None:
    case_id = _persisted_case(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        before = client.get(f"/api/cases/{case_id}/host-knowledge")
        assert before.status_code == 200
        assert before.json()["confirmed_host"] is None
        assert before.json()["recommended_host"] == "大豆"

        rejected = client.post(f"/api/cases/{case_id}/host-confirmation", json={"confirmed_host": "自由文本"})
        assert rejected.status_code == 422

        confirmed = client.post(f"/api/cases/{case_id}/host-confirmation", json={"confirmed_host": "马铃薯"})
        assert confirmed.status_code == 200
        payload = confirmed.json()
        assert payload["host_knowledge"]["confirmed_host"] == "马铃薯"
        assert payload["host_knowledge"]["recommended_host"] == "大豆"
        assert payload["host_knowledge"]["host"]["status"] == "PARTIAL"
        assert payload["host_knowledge"]["host"]["crop"] == "马铃薯"
        assert database.get_case(case_id)["context"]["host_selection"]["confirmed_host"] == "马铃薯"

        detail = client.get(f"/api/cases/{case_id}")
        assert detail.status_code == 200
        assert detail.json()["host_knowledge"]["confirmed_host"] == "马铃薯"
        report = client.get(f"/api/cases/{case_id}/report")
        assert report.status_code == 200
        assert report.json()["case"]["host_knowledge"]["confirmed_host"] == "马铃薯"


def test_other_confirmation_is_fixed_and_plant_legacy_response_has_no_host_contract(tmp_path, monkeypatch) -> None:
    case_id = _persisted_case(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        confirmed = client.post(f"/api/cases/{case_id}/host-confirmation", json={"confirmed_host": "OTHER"})
        assert confirmed.status_code == 200
        payload = confirmed.json()["host_knowledge"]
        assert payload["confirmed_host"] == "OTHER"
        assert payload["host"]["capabilities"] == {
            "host_relation": False,
            "host_damage": False,
            "severity": False,
            "host_general_treatment": False,
            "host_severity_treatment": False,
            "vector_disease": False,
        }
        assert payload["treatment"]["treatment_level"] == "insect_general"

    plant = main.present_case(
        {
            **_record(0, severity="mild"),
            "crop": "玉米",
            "part": "叶片",
        }
    )
    assert "host_knowledge" not in plant
    assert plant["treatment"]["status"] == "available"
    assert plant["treatment"]["content"]["tier"] == "轻度"


def test_r2_plant_treatment_parser_remains_exactly_24_cells() -> None:
    root = Path(__file__).resolve().parents[2] / "knowledge" / "baidu-baike-20260818" / "documents"
    parsed = 0
    for class_id in range(8):
        markdown = (root / f"{class_id:02d}.md").read_text(encoding="utf-8")
        tiers = parse_tiered_treatment(markdown)
        assert set(tiers) == {"mild", "moderate", "severe"}
        parsed += len(tiers)
    assert parsed == 24
