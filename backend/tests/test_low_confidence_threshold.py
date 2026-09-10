from __future__ import annotations

import io
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import config, database, drafts, main
from app.knowledge import _confidence_band


def _record(confidence: float) -> dict:
    return {
        "status": "detected",
        "detections": [{"class_id": 0, "class_name": "番茄早疫病", "confidence": confidence}],
        "detector_summary": {
            "primary_candidate": {
                "class_id": 0,
                "class_name": "番茄早疫病",
                "max_confidence": confidence,
            }
        },
        "analysis": {},
    }


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (0.20, "retake_required"),
        (0.49, "retake_required"),
        (0.50, "conclusive"),
        (0.60, "conclusive"),
        (0.74, "conclusive"),
        (0.75, "conclusive"),
        (0.90, "conclusive"),
    ],
)
def test_product_confidence_boundaries(confidence, expected, monkeypatch) -> None:
    monkeypatch.setattr(main, "severity_rubric_payload", lambda _record: {})
    monkeypatch.setattr(main, "local_treatment_payload", lambda _record: {})
    response = main.present_case(_record(confidence))
    assert response["resolution_status"] == expected
    if expected == "retake_required":
        assert "无法可靠判断" in response["user_summary"]
        assert "重新上传" in response["next_action"]
        assert "50%" in "".join(response["resolution_reasons"])
    else:
        assert response["next_action"] == "查看发现位置、判断依据和下一步处理建议。"


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [(0.20, "low"), (0.49, "low"), (0.50, "high"), (0.60, "high"), (0.74, "high"), (0.75, "high"), (0.90, "high")],
)
def test_explainability_confidence_band_uses_only_50_percent_split(confidence, expected) -> None:
    assert _confidence_band(confidence) == expected


def _image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (72, 126, 66)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _configure(tmp_path, monkeypatch, confidence: float) -> None:
    isolated = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "cases.sqlite3",
        upload_dir=tmp_path / "uploads",
        report_dir=tmp_path / "reports",
        control_dir=tmp_path / "control",
        public_mode=False,
        detector_endpoint=None,
        model_path=None,
    )
    monkeypatch.setattr(database, "settings", isolated)
    monkeypatch.setattr(main, "settings", isolated)
    monkeypatch.setattr(drafts, "settings", isolated)
    monkeypatch.setattr(
        main.detector,
        "detect",
        lambda _path: [{
            "class_id": 0,
            "class_name": "番茄早疫病",
            "class_name_en": "Tomato early blight",
            "category_type": "病害",
            "confidence": confidence,
            "bbox": [0.1, 0.1, 0.6, 0.6],
        }],
    )
    main.detector.last_metadata = {"mode": "test"}


def _upload_and_analyze(client: TestClient) -> dict:
    uploaded = client.post("/api/drafts", files={"image": ("plant.jpg", _image_bytes(), "image/jpeg")})
    assert uploaded.status_code == 201
    analyzed = client.post(f"/api/drafts/{uploaded.json()['id']}/analyze")
    assert analyzed.status_code == 200
    return analyzed.json()


def test_below_threshold_blocks_r3_context(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch, 0.49)
    monkeypatch.setattr(main, "infer_context", lambda _path: pytest.fail("blocked draft must not enter Context"))
    with TestClient(main.app) as client:
        draft = _upload_and_analyze(client)
        assert draft["status"] == "low_confidence"
        assert draft["confidence_gate"]["status"] == "blocked"
        assert draft["confidence_gate"]["threshold"] == 0.50
        assert "重新上传" in draft["confidence_gate"]["message"]
        assert client.get("/api/cases").json() == []
        confirm = client.post(
            f"/api/drafts/{draft['id']}/confirm",
            json={"subject_type": "plant", "crop_species": "番茄", "affected_part": "叶片"},
        )
        assert confirm.status_code == 409


def test_threshold_allows_r3_context_at_exact_boundary(tmp_path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch, 0.50)
    monkeypatch.setattr(
        main,
        "infer_context",
        lambda _path: {"status": "available", "subject_type": {"top1": "plant", "candidates": []}},
    )
    with TestClient(main.app) as client:
        draft = _upload_and_analyze(client)
        assert draft["status"] == "analyzed"
        assert draft["confidence_gate"] == {"status": "allowed", "threshold": 0.50, "confidence": 0.50}
        assert draft["context_prediction"]["status"] == "available"
