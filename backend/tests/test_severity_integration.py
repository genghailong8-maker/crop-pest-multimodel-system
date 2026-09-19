from __future__ import annotations

import asyncio
import io
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import analysis, config, database, detector, main
from app.search.models import SearchEvidence


def record(class_id: int, class_name: str, ratio=None, speed=None) -> dict:
    return {
        "detections": [{"class_id": class_id, "class_name": class_name, "confidence": 0.91}],
        "detector_summary": {"primary_candidate": {"class_id": class_id, "class_name": class_name, "max_confidence": 0.91}, "review_reasons": []},
        "affected_ratio_percent": ratio,
        "spread_speed": speed or "unknown",
    }


def image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (72, 126, 66)).save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("class_id", "class_name", "ratio", "speed", "expected"),
    [
        (0, "玉米叶枯病", 0, "none", "mild"),
        (8, "芫菁", 20, "ongoing", "moderate"),
        (15, "豆芫菁", 50, "none", "severe"),
    ],
)
def test_special_classes_keep_curated_evidence_and_select_local_tier(class_id, class_name, ratio, speed, expected) -> None:
    item = record(class_id, class_name, ratio, speed)
    result = asyncio.run(analysis.request_evidence_analysis(item))
    assert result["evidence_analysis"]["status"] == "available"
    assert result["severity"]["level"] == expected
    payload = main.local_treatment_payload({**item, "analysis": result})
    assert payload["source"] == "local_knowledge_base"
    assert payload["status"] == "available"
    assert payload["severity_level"] == expected
    assert payload["content"]["markdown"]
    assert payload["source_ids"] == [source["id"] for source in payload["sources"]]


def test_no_severity_inputs_keep_legacy_treatment_and_do_not_guess(monkeypatch) -> None:
    async def fail_if_called(_name: str):
        raise AssertionError("special class should use curated evidence")

    monkeypatch.setattr(analysis, "collect_external_evidence", fail_if_called)
    item = record(0, "玉米叶枯病")
    result = asyncio.run(analysis.request_evidence_analysis(item))
    assert result["severity"]["status"] == "not_provided"
    payload = main.local_treatment_payload({**item, "analysis": result})
    assert payload["source"] == "local_knowledge_base"
    assert "prevention" in payload["content"]


def test_ordinary_tavily_path_is_isolated_from_severity(monkeypatch) -> None:
    async def fake_search(_name: str):
        return SearchEvidence(class_name="蛴螬", status="unavailable")

    monkeypatch.setattr(analysis, "collect_external_evidence", fake_search)
    item = record(14, "蛴螬", 25, "rapid")
    result = asyncio.run(analysis.request_evidence_analysis(item))
    assert result["evidence_analysis"]["status"] == "unavailable"
    assert result["severity"]["level"] == "severe"
    payload = main.local_treatment_payload({**item, "analysis": result})
    assert payload["severity_level"] == "severe"
    assert payload["source"] == "local_knowledge_base"


def test_upload_keeps_legacy_no_input_and_rejects_partial_input(tmp_path, monkeypatch) -> None:
    settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "cases.sqlite3",
        upload_dir=tmp_path / "uploads",
        report_dir=tmp_path / "reports",
        control_dir=tmp_path / "control",
    )
    monkeypatch.setattr(database, "settings", settings)
    monkeypatch.setattr(main, "settings", settings)
    monkeypatch.setattr(detector, "settings", settings)
    base = {"crop": "玉米", "part": "叶片", "growth_stage": "苗期", "environment_json": '{"scene":"露地"}'}
    with TestClient(main.app) as client:
        no_input = client.post("/api/cases", files={"image": ("leaf.jpg", image_bytes(), "image/jpeg")}, data=base)
        ratio_only = client.post("/api/cases", files={"image": ("leaf.jpg", image_bytes(), "image/jpeg")}, data={**base, "affected_ratio_percent": "10"})
        ratio_unknown = client.post("/api/cases", files={"image": ("leaf.jpg", image_bytes(), "image/jpeg")}, data={**base, "affected_ratio_percent": "10", "spread_speed": "unknown"})
        speed_only = client.post("/api/cases", files={"image": ("leaf.jpg", image_bytes(), "image/jpeg")}, data={**base, "spread_speed": "slow"})
    assert no_input.status_code == 201
    assert no_input.json()["severity"]["status"] == "not_provided"
    assert ratio_only.status_code == 422
    assert ratio_unknown.status_code == 422
    assert speed_only.status_code == 422
