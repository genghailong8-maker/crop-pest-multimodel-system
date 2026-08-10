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


def test_phase6_knowledge_contract_is_source_registered():
    from app.knowledge import KNOWLEDGE_SCHEMA_VERSION, knowledge_contract

    contract = knowledge_contract()
    assert contract["schema_version"] == KNOWLEDGE_SCHEMA_VERSION
    assert len(contract["classes"]) == 16
    assert {item["class_id"] for item in contract["classes"]} == set(range(16))
    assert len(contract["sources"]) >= 4
    assert contract["safety_boundary"]["scope"] == "general_ipm_orientation_only"
    assert contract["safety_boundary"]["chemical_limit"]
    assert all(card["source_ids"] for card in contract["classes"])


def test_case_review_queue_and_audit_history(tmp_path, monkeypatch):
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
        upload = client.post(
            "/api/cases",
            files={"image": ("corn.jpg", image_bytes(), "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "environment_json": "{}",
            },
        )
        case_id = upload.json()["id"]
        database.update_case(
            case_id,
            status="detected",
            quality={"flags": []},
            detections=[
                {
                    "class_id": 0,
                    "class_name": "玉米叶枯病",
                    "confidence": 0.41,
                    "bbox": [0.1, 0.2, 0.3, 0.4],
                }
            ],
            detector_summary={
                "target_count": 1,
                "needs_review": True,
                "review_reasons": ["最高视觉置信度较低"],
            },
        )

        queue = client.get("/api/cases/review-queue")
        assert queue.status_code == 200
        assert queue.json()["total"] == 1
        assert queue.json()["items"][0]["id"] == case_id

        review = client.post(
            f"/api/cases/{case_id}/review",
            json={
                "decision": "needs_more_evidence",
                "accepted_detection_indexes": [0],
                "reviewer_notes": "请补拍叶背和整株",
                "reviewer_id": "tester",
            },
        )
        assert review.status_code == 200
        assert review.json()["status"] == "review_pending"
        assert review.json()["review"]["decision"] == "needs_more_evidence"
        assert len(review.json()["review_events"]) == 1
        assert review.json()["review_events"][0]["reviewer_id"] == "tester"

        events = client.get(f"/api/cases/{case_id}/review-events")
        assert events.status_code == 200
        assert events.json()["events"][0]["notes"] == "请补拍叶背和整株"

        invalid = client.post(
            f"/api/cases/{case_id}/review",
            json={"accepted_detection_indexes": [9]},
        )
        assert invalid.status_code == 422


def test_detection_attaches_phase6_explainability(tmp_path, monkeypatch):
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
    monkeypatch.setattr(main, "settings", test_settings)
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(
        detector.detector,
        "detect",
        lambda _: [
            {
                "class_id": 0,
                "class_name": "玉米叶枯病",
                "class_name_en": "Corn leaf blight",
                "category_type": "病害",
                "confidence": 0.41,
                "bbox": [0.1, 0.2, 0.3, 0.4],
            }
        ],
    )
    monkeypatch.setattr(
        detector.detector,
        "last_metadata",
        {
            "mode": "remote",
            "model_sha256": "main-sha",
            "routing": {"mode": "shadow", "candidate_count": 1},
        },
    )

    with TestClient(main.app) as client:
        upload = client.post(
            "/api/cases",
            files={"image": ("corn.jpg", image_bytes(), "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "environment_json": "{}",
            },
        )
        detected = client.post(f"/api/cases/{upload.json()['id']}/detect")
        assert detected.status_code == 200
        explainability = detected.json()["detector_summary"]["explainability"]
        assert explainability["primary_confidence_band"] == "low"
        assert explainability["knowledge_card"]["class_id"] == 0
        assert explainability["model_evidence"]["routing_is_shadow"] is True
        assert explainability["human_review"]["required"] is True
        assert explainability["safety"]["chemical_recommendations"] == "not_provided"


def test_case_analysis_success_is_saved_and_reloaded(tmp_path, monkeypatch):
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "test.sqlite3",
        upload_dir=tmp_path / "uploads",
        vlm_endpoint="http://127.0.0.1:8890/v1/chat/completions",
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    async def fake_analysis(record, _image_path):
        assert record["crop"] == "玉米"
        return {
            "status": "completed",
            "schema_version": "phase8-multimodal-v1",
            "primary_diagnosis": "玉米叶枯病",
            "candidate_diagnoses": ["玉米叶枯病"],
            "symptoms": ["叶片出现斑点"],
            "harm_level": "medium",
            "possible_causes": ["高湿环境"],
            "evidence": ["视觉模型候选与原图症状一致"],
            "uncertainty": [],
            "detector_alignment": "agree",
            "needs_human_review": False,
            "review_reasons": [],
            "provenance": {"model": "crop-pest-vlm", "latency_ms": 42.0},
        }

    monkeypatch.setattr(main, "request_multimodal_analysis", fake_analysis)

    with TestClient(main.app) as client:
        upload = client.post(
            "/api/cases",
            files={"image": ("corn.jpg", image_bytes(), "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "environment_json": '{"scene":"露地"}',
            },
        )
        case_id = upload.json()["id"]
        database.update_case(
            case_id,
            status="detected",
            quality={"acceptable": True, "flags": []},
            detections=[{"class_id": 0, "class_name": "玉米叶枯病", "confidence": 0.87}],
            detector_summary={"needs_review": False, "review_reasons": []},
        )

        analyzed = client.post(f"/api/cases/{case_id}/analyze")
        assert analyzed.status_code == 200
        assert analyzed.json()["status"] == "analyzed"
        assert analyzed.json()["analysis"]["primary_diagnosis"] == "玉米叶枯病"

        reloaded = client.get(f"/api/cases/{case_id}")
        assert reloaded.status_code == 200
        assert reloaded.json()["analysis"]["provenance"]["model"] == "crop-pest-vlm"
