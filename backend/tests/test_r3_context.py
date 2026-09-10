from __future__ import annotations

import io
from dataclasses import replace

from fastapi.testclient import TestClient
from PIL import Image

from app import config, database, drafts, main
from app.context_inference import ContextInferenceUnavailable


def image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (72, 126, 66)).save(buffer, format="JPEG")
    return buffer.getvalue()


def isolated_settings(tmp_path):
    return replace(
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


def fake_detection(_path):
    return [{
        "class_id": 0,
        "class_name": "番茄早疫病",
        "class_name_en": "Tomato early blight",
        "category_type": "病害",
        "confidence": 0.91,
        "bbox": [0.1, 0.1, 0.6, 0.6],
    }]


def configure(tmp_path, monkeypatch):
    isolated = isolated_settings(tmp_path)
    monkeypatch.setattr(database, "settings", isolated)
    monkeypatch.setattr(main, "settings", isolated)
    monkeypatch.setattr(drafts, "settings", isolated)
    monkeypatch.setattr(main.detector, "detect", fake_detection)
    main.detector.last_metadata = {"mode": "test"}
    return isolated


def upload_and_analyze(client: TestClient):
    uploaded = client.post(
        "/api/drafts",
        files={"image": ("plant.jpg", image_bytes(), "image/jpeg")},
    )
    assert uploaded.status_code == 201
    draft = uploaded.json()
    assert client.get("/api/cases").json() == []
    analyzed = client.post(f"/api/drafts/{draft['id']}/analyze")
    assert analyzed.status_code == 200
    return analyzed.json()


def test_r3_plant_draft_confirm_creates_one_case_and_persists_context(tmp_path, monkeypatch):
    configure(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "infer_context", lambda _path: {
        "status": "available",
        "model": "openai/clip-vit-base-patch32",
        "subject_type": {"top1": "plant", "candidates": [{"value": "plant", "score": 0.9}], "margin": None},
        "crop_species": {"top1": "番茄", "candidates": [{"value": "番茄", "score": 0.9}], "margin": None},
        "affected_part": {"top1": "叶片", "candidates": [{"value": "叶片", "score": 0.9}], "margin": None},
        "insect_species": None,
    })
    with TestClient(main.app) as client:
        draft = upload_and_analyze(client)
        assert draft["context_prediction"]["status"] == "available"
        confirmed = client.post(
            f"/api/drafts/{draft['id']}/confirm",
            json={"subject_type": "plant", "crop_species": "番茄", "affected_part": "叶片"},
        )
        assert confirmed.status_code == 201
        case = confirmed.json()
        assert case["context"]["authority"] == "user_confirmed"
        assert case["context"]["crop_species"] == "番茄"
        assert case["context"]["affected_part"] == "叶片"
        assert case["detections"] == draft["detections"]
        assert case["detector_summary"] == draft["detector_summary"]
        assert len(client.get("/api/cases").json()) == 1
        again = client.post(
            f"/api/drafts/{draft['id']}/confirm",
            json={"subject_type": "plant", "crop_species": "番茄", "affected_part": "叶片"},
        )
        assert again.status_code == 201
        assert again.json()["id"] == case["id"]
        assert len(client.get("/api/cases").json()) == 1
        reloaded = client.get(f"/api/cases/{case['id']}").json()
        assert reloaded["context"]["crop_species"] == "番茄"
        assert reloaded["detections"] == draft["detections"]
        assert reloaded["detector_summary"] == draft["detector_summary"]
        assert again.json()["detections"] == draft["detections"]
        assert again.json()["detector_summary"] == draft["detector_summary"]


def test_r3_insect_context_clears_plant_fields(tmp_path, monkeypatch):
    configure(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "infer_context", lambda _path: {"status": "unavailable", "reason": "test"})
    with TestClient(main.app) as client:
        draft = upload_and_analyze(client)
        confirmed = client.post(
            f"/api/drafts/{draft['id']}/confirm",
            json={"subject_type": "insect", "insect_species": "蚜虫", "crop_species": "番茄", "affected_part": "叶片"},
        )
        assert confirmed.status_code == 201
        context = confirmed.json()["context"]
        assert context["subject_type"] == "insect"
        assert context["insect_species"] == "蚜虫"
        assert context["crop_species"] is None
        assert context["affected_part"] is None


def test_r3_context_failure_still_allows_manual_confirmation(tmp_path, monkeypatch):
    configure(tmp_path, monkeypatch)
    def unavailable(_path):
        raise ContextInferenceUnavailable("offline")
    monkeypatch.setattr(main, "infer_context", unavailable)
    with TestClient(main.app) as client:
        draft = upload_and_analyze(client)
        assert draft["context_prediction"]["status"] == "unavailable"
        confirmed = client.post(
            f"/api/drafts/{draft['id']}/confirm",
            json={"subject_type": "plant", "crop_species": "玉米", "affected_part": "整株"},
        )
        assert confirmed.status_code == 201
        assert confirmed.json()["context"]["source"] == "user_confirmed"
