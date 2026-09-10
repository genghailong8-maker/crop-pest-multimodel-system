from __future__ import annotations

import asyncio
import io
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import analysis, config, database, detector, main
from app.case_context import (
    CLASS_CROP_MAPPING,
    GROWTH_STAGE_LABELS,
    SYSTEM_DEFAULT_ENVIRONMENT,
    build_case_context,
    crop_context,
)
from app.severity import severity_for_record


def _record(class_id: int, crop: str = "玉米", growth_stage: str = "flowering") -> dict:
    item = next(entry for entry in main.CLASS_CATALOG if entry["id"] == class_id)
    primary = {
        "class_id": class_id,
        "class_name": item["name_zh"],
        "max_confidence": 0.91,
    }
    return {
        "crop": crop,
        "growth_stage": growth_stage,
        "environment": {"scene": "温室"},
        "affected_ratio_percent": 20,
        "spread_speed": "ongoing",
        "detector_summary": {"primary_candidate": primary},
        "analysis": {"severity": {"status": "available", "level": "moderate"}},
    }


def test_growth_stage_has_six_formal_values_and_distinguishes_missing_uncertain() -> None:
    assert set(GROWTH_STAGE_LABELS) == {
        "seedling", "vegetative", "flowering", "fruiting_or_seed_setting", "maturity", "uncertain"
    }
    assert build_case_context({"growth_stage": ""})["growth_stage"] == {
        "status": "not_provided", "value": None, "label": None, "source": "user"
    }
    uncertain = build_case_context({"growth_stage": "uncertain"})["growth_stage"]
    assert uncertain == {"status": "available", "value": "uncertain", "label": "不确定", "source": "user"}


@pytest.mark.parametrize("stage", sorted(GROWTH_STAGE_LABELS))
def test_formal_growth_stage_values_are_available(stage: str) -> None:
    result = build_case_context({"growth_stage": stage})["growth_stage"]
    assert result["status"] == "available"
    assert result["value"] == stage
    assert result["label"] == GROWTH_STAGE_LABELS[stage]


def test_crop_mapping_is_catalog_derived_and_has_sixteen_explicit_rows() -> None:
    assert len(CLASS_CROP_MAPPING) == 16
    assert [row["class_id"] for row in CLASS_CROP_MAPPING] == list(range(16))
    assert crop_context(_record(6, crop="玉米")) == {
        "status": "available", "value": "番茄", "source": "yolo_class_mapping"
    }
    legacy_record = _record(6, crop="玉米")
    legacy_record["detector_summary"] = {}
    legacy_record["detections"] = [{"class_id": 6, "class_name": "番茄晚疫病"}]
    assert crop_context(legacy_record)["source"] == "yolo_class_mapping"


def test_generic_pest_uses_reported_crop_or_unavailable_without_guessing() -> None:
    assert crop_context(_record(9, crop="玉米")) == {
        "status": "available", "value": "玉米", "source": "user_reported"
    }
    assert crop_context(_record(9, crop="")) == {
        "status": "unavailable", "value": None, "source": None
    }


def test_context_environment_is_server_owned_and_legacy_scene_is_retained() -> None:
    context = build_case_context(_record(6, crop="玉米"))
    assert context["environment"] == SYSTEM_DEFAULT_ENVIRONMENT
    assert context["environment"]["source"] == "system_default"
    assert context["environment"]["cultivation_scene"] == "常规田间种植环境"
    assert context["crop"]["value"] == "番茄"


@pytest.mark.parametrize(
    ("ratio", "spread", "expected_level"),
    [(None, "unknown", None), (0, "none", "mild"), (20, "ongoing", "moderate"), (60, "rapid", "severe")],
)
def test_case_context_severity_reuses_b_source_of_truth(ratio, spread, expected_level) -> None:
    record = _record(6)
    record.pop("analysis")
    record["affected_ratio_percent"] = ratio
    record["spread_speed"] = spread
    response = main.present_case(record)
    expected = severity_for_record(record).as_dict()
    assert response["severity"] == expected
    assert response["case_context"]["severity"] == expected
    assert response["severity"]["level"] == expected_level


def test_context_does_not_change_analysis_search_or_severity(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_search(class_name: str):
        calls.append(class_name)
        from app.search.models import SearchEvidence

        return SearchEvidence(class_name=class_name, status="unavailable")

    monkeypatch.setattr(analysis, "collect_external_evidence", fake_search)
    original = _record(9, crop="玉米", growth_stage="flowering")
    changed = {**original, "environment": {"scene": "室内样本"}, "growth_stage": "maturity"}
    first = asyncio.run(analysis.request_evidence_analysis(original))
    second = asyncio.run(analysis.request_evidence_analysis(changed))
    assert calls == ["蚜虫", "蚜虫"]
    assert first["severity"] == second["severity"]
    assert first["evidence_analysis"] == second["evidence_analysis"]
    assert crop_context(original) == crop_context(changed)


def test_environment_and_growth_context_do_not_change_local_treatment() -> None:
    from app import main as main_module

    original = _record(6, crop="玉米", growth_stage="flowering")
    changed = {**original, "environment": {"scene": "露地"}, "growth_stage": "maturity"}
    assert main_module.local_treatment_payload(original) == main_module.local_treatment_payload(changed)


def _image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), (72, 126, 66)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_case_context_persists_growth_and_is_returned_on_read_and_analysis(tmp_path, monkeypatch) -> None:
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "cases.sqlite3",
        upload_dir=tmp_path / "uploads",
        report_dir=tmp_path / "reports",
        control_dir=tmp_path / "control",
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    async def fake_analysis(record):
        return {
            "status": "completed",
            "schema_version": "evidence-extractor-v1",
            "primary_diagnosis": "番茄晚疫病",
            "candidate_diagnoses": ["番茄晚疫病"],
            "symptoms": [],
            "harm_level": "unknown",
            "uncertainty": [],
            "detector_alignment": "not_applicable",
            "field_input_consistency": "not_evaluated",
            "content_sufficiency": "sufficient",
            "diagnostic_risk": "low",
            "field_severity": "medium",
            "severity_basis": "test",
            "severity": severity_for_record(record).as_dict(),
            "needs_human_review": False,
            "review_reasons": [],
            "evidence_analysis": {"status": "unavailable", "harms": [], "possible_causes": []},
            "sources": [],
            "evidence_snapshots": [],
            "provenance": {"engine": "test"},
        }

    monkeypatch.setattr(main, "request_evidence_analysis", fake_analysis)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/cases",
            files={"image": ("leaf.jpg", _image_bytes(), "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "flowering",
                "environment_json": '{"scene":"温室"}',
            },
        )
        assert response.status_code == 201
        created = response.json()
        assert created["growth_stage"] == "flowering"
        assert created["case_context"]["growth_stage"]["value"] == "flowering"
        assert created["case_context"]["environment"] == SYSTEM_DEFAULT_ENVIRONMENT
        upload_severity = created["severity"]
        assert created["case_context"]["severity"] == upload_severity
        read = client.get(f"/api/cases/{created['id']}")
        assert read.status_code == 200
        assert read.json()["case_context"]["growth_stage"]["value"] == "flowering"

        database.update_case(
            created["id"],
            status="detected",
            detections=[{"class_id": 6, "class_name": "番茄晚疫病", "confidence": 0.91}],
            detector_summary={
                "primary_candidate": {
                    "class_id": 6,
                    "class_name": "番茄晚疫病",
                    "max_confidence": 0.91,
                },
                "needs_review": False,
                "review_reasons": [],
            },
        )
        analyzed = client.post(f"/api/cases/{created['id']}/analyze")
        assert analyzed.status_code == 200
        analyzed_payload = analyzed.json()
        assert analyzed_payload["case_context"]["growth_stage"] == {
            "status": "available",
            "value": "flowering",
            "label": "开花期",
            "source": "user",
        }
        assert analyzed_payload["case_context"]["severity"] == analyzed_payload["severity"]


def test_historical_missing_growth_case_can_read_and_analyze(tmp_path, monkeypatch) -> None:
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "cases.sqlite3",
        upload_dir=tmp_path / "uploads",
        report_dir=tmp_path / "reports",
        control_dir=tmp_path / "control",
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    async def fake_analysis(record):
        return {
            "status": "completed",
            "schema_version": "evidence-extractor-v1",
            "primary_diagnosis": "玉米叶枯病",
            "candidate_diagnoses": ["玉米叶枯病"],
            "symptoms": [],
            "harm_level": "unknown",
            "uncertainty": [],
            "detector_alignment": "not_applicable",
            "field_input_consistency": "not_evaluated",
            "content_sufficiency": "sufficient",
            "diagnostic_risk": "low",
            "field_severity": "unknown",
            "severity_basis": "test",
            "severity": severity_for_record(record).as_dict(),
            "needs_human_review": True,
            "review_reasons": [],
            "evidence_analysis": {"status": "unavailable", "harms": [], "possible_causes": []},
            "sources": [],
            "evidence_snapshots": [],
            "provenance": {"engine": "test"},
        }

    monkeypatch.setattr(main, "request_evidence_analysis", fake_analysis)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/cases",
            files={"image": ("leaf.jpg", _image_bytes(), "image/jpeg")},
            data={"crop": "玉米", "part": "叶片", "environment_json": '{"scene":"露地"}'},
        )
        assert response.status_code == 201
        case_id = response.json()["id"]
        assert client.get(f"/api/cases/{case_id}").json()["case_context"]["growth_stage"]["status"] == "not_provided"
        database.update_case(
            case_id,
            status="detected",
            detections=[{"class_id": 0, "class_name": "玉米叶枯病", "confidence": 0.91}],
            detector_summary={"primary_candidate": {"class_id": 0, "class_name": "玉米叶枯病", "max_confidence": 0.91}},
        )
        analyzed = client.post(f"/api/cases/{case_id}/analyze")
        assert analyzed.status_code == 200
        assert analyzed.json()["case_context"]["growth_stage"]["status"] == "not_provided"


def test_real_upload_response_keeps_severity_consistent_with_case_context(tmp_path, monkeypatch) -> None:
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "cases.sqlite3",
        upload_dir=tmp_path / "uploads",
        report_dir=tmp_path / "reports",
        control_dir=tmp_path / "control",
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/cases",
            files={"image": ("leaf.jpg", _image_bytes(), "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "flowering",
                "environment_json": '{"scene":"温室"}',
                "affected_ratio_percent": "20",
                "spread_speed": "ongoing",
            },
        )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["severity"] == payload["case_context"]["severity"]
    assert payload["severity"]["status"] == "available"
    assert payload["case_context"]["severity"]["status"] == "available"
    assert payload["severity"]["level"] == "moderate"
    assert payload["severity"]["label"] == "中度"
    assert payload["severity"]["score"] == 28
    assert payload["severity"]["affected_ratio"] == 20
    assert payload["severity"]["spread_speed"] == "ongoing"
    assert payload["severity"]["algorithm_version"] == "severity_v1"
    assert payload["severity"]["decision_rule"] == "composite_score"


def _isolated_api_settings(tmp_path, base_settings):
    return replace(
        base_settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "cases.sqlite3",
        upload_dir=tmp_path / "uploads",
        report_dir=tmp_path / "reports",
        control_dir=tmp_path / "control",
    )


def _upload_data(**overrides: str) -> dict[str, str]:
    data = {
        "crop": "番茄",
        "part": "叶片",
        "growth_stage": "flowering",
        "affected_ratio_percent": "20",
        "spread_speed": "ongoing",
    }
    data.update(overrides)
    return data


def test_omitted_legacy_environment_creates_case_with_system_default_context(tmp_path, monkeypatch) -> None:
    test_settings = _isolated_api_settings(tmp_path, config.settings)
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/cases",
            files={"image": ("tomato.jpg", _image_bytes(), "image/jpeg")},
            data=_upload_data(),
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["environment"] == {}
    assert payload["case_context"]["environment"] == SYSTEM_DEFAULT_ENVIRONMENT
    assert payload["case_context"]["growth_stage"] == {
        "status": "available",
        "value": "flowering",
        "label": "开花期",
        "source": "user",
    }
    assert payload["severity"]["level"] == "moderate"
    assert payload["severity"]["score"] == 28
    assert payload["case_context"]["severity"] == payload["severity"]
    assert database.get_case(payload["id"])["environment"] == {}


def test_legacy_environment_is_preserved_but_does_not_override_effective_context(tmp_path, monkeypatch) -> None:
    test_settings = _isolated_api_settings(tmp_path, config.settings)
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/cases",
            files={"image": ("tomato.jpg", _image_bytes(), "image/jpeg")},
            data=_upload_data(environment_json='{"scene":"温室"}'),
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["environment"] == {"scene": "温室"}
    assert database.get_case(payload["id"])["environment"] == {"scene": "温室"}
    assert payload["case_context"]["environment"] == SYSTEM_DEFAULT_ENVIRONMENT


@pytest.mark.parametrize("environment_json", ["{", "[]", "{}"])
def test_provided_invalid_or_incomplete_legacy_environment_is_rejected(tmp_path, monkeypatch, environment_json) -> None:
    test_settings = _isolated_api_settings(tmp_path, config.settings)
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/cases",
            files={"image": ("tomato.jpg", _image_bytes(), "image/jpeg")},
            data=_upload_data(environment_json=environment_json),
        )

    assert response.status_code == 422
