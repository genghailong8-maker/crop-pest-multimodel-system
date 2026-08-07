from __future__ import annotations

import io
from dataclasses import replace

from fastapi.testclient import TestClient
from PIL import Image

from app import config, database, detector, main


def image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (72, 126, 66)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_upload_history_and_model_unavailable(tmp_path, monkeypatch):
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "test.sqlite3",
        upload_dir=tmp_path / "uploads",
        model_path=None,
        detector_endpoint=None,
        vlm_endpoint=None,
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    with TestClient(main.app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["model_configured"] is False
        assert health.json()["detector_mode"] == "unconfigured"

        upload = client.post(
            "/api/cases",
            files={"image": ("corn.jpg", image_bytes(), "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "environment_json": '{"scene":"露地"}',
                "notes": "叶片出现斑点",
            },
        )
        assert upload.status_code == 201
        created = upload.json()
        assert created["status"] == "uploaded"
        assert created["image_width"] == 640

        detection = client.post(f"/api/cases/{created['id']}/detect")
        assert detection.status_code == 200
        detected = detection.json()
        assert detected["status"] == "model_unavailable"
        assert detected["quality"]["width"] == 640
        assert detected["detector_summary"]["needs_review"] is True

        history = client.get("/api/cases")
        assert history.status_code == 200
        assert len(history.json()) == 1


def test_rejects_non_image(tmp_path, monkeypatch):
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "test.sqlite3",
        upload_dir=tmp_path / "uploads",
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/cases",
            files={"image": ("fake.jpg", b"not an image", "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "environment_json": "{}",
            },
        )
        assert response.status_code == 422


def test_remote_detection_payload_validation():
    parsed = detector.validate_remote_detections(
        {
            "detections": [
                {
                    "class_id": 0,
                    "confidence": 0.91,
                    "bbox": [0.1, 0.2, 0.3, 0.4],
                }
            ]
        }
    )
    assert parsed[0]["class_id"] == 0
    assert parsed[0]["confidence"] == 0.91
    assert parsed[0]["class_name"]


def test_remote_detector_preserves_routing_metadata(tmp_path, monkeypatch):
    image_path = tmp_path / "leaf.jpg"
    image_path.write_bytes(image_bytes())

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "detections": [],
                "model_sha256": "main-sha",
                "speed_ms": {"request_model_ms": 12.3},
                "routing": {"mode": "shadow", "candidate_count": 1},
            }

    test_settings = replace(
        config.settings,
        detector_endpoint="http://inference.test/v1/detect",
        detector_api_key=None,
    )
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(detector.httpx, "post", lambda *_, **__: FakeResponse())
    remote = detector.RemoteDetector()
    assert remote.detect(image_path) == []
    assert remote.last_metadata["routing"]["mode"] == "shadow"
    assert remote.last_metadata["model_sha256"] == "main-sha"
