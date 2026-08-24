from __future__ import annotations

import io
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import httpx
from fastapi.testclient import TestClient
from PIL import Image

from app import config, database, detector, main


def image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (72, 126, 66)).save(buffer, format="JPEG")
    return buffer.getvalue()


def valid_case_data(**overrides: str) -> dict[str, str]:
    data = {
        "crop": "玉米",
        "part": "叶片",
        "growth_stage": "苗期",
        "environment_json": '{"scene":"露地"}',
        "affected_ratio_percent": "12.5",
        "spread_speed": "slow",
    }
    data.update(overrides)
    return data


def test_upload_history_and_model_unavailable(tmp_path, monkeypatch):
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "test.sqlite3",
        upload_dir=tmp_path / "uploads",
        model_path=None,
        detector_endpoint=None,
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    with TestClient(main.app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["model_configured"] is False
        assert health.json()["detector_mode"] == "unconfigured"
        assert health.json()["active_instance_id"] == test_settings.instance_id
        assert health.json()["active_instance_label"] == test_settings.instance_label
        assert health.json()["active_instance_mode"] == "cpu"

        upload = client.post(
            "/api/cases",
            files={"image": ("corn.jpg", image_bytes(), "image/jpeg")},
            data=valid_case_data(notes="叶片出现斑点"),
        )
        assert upload.status_code == 201
        created = upload.json()
        assert created["status"] == "uploaded"
        assert created["image_width"] == 640
        assert created["crop"] == "玉米"
        assert created["part"] == "叶片"
        assert created["growth_stage"] == "苗期"
        assert created["public_consent"] is False
        assert created["expires_at"] is None
        assert created["is_test"] is False
        assert created["resolution_status"] == "conclusive"

        detection = client.post(f"/api/cases/{created['id']}/detect")
        assert detection.status_code == 200
        detected = detection.json()
        assert detected["status"] == "model_unavailable"
        assert detected["quality"]["width"] == 640
        assert detected["detector_summary"]["needs_review"] is True
        assert detected["resolution_status"] == "service_unavailable"

        history = client.get("/api/cases")
        assert history.status_code == 200
        assert len(history.json()) == 1

        expired_at = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        database.update_case(
            created["id"],
            public_consent=True,
            expires_at=expired_at,
        )
        image_path = test_settings.upload_dir / f"{created['id']}.jpg"

        local_history = client.get("/api/cases")
        assert [item["id"] for item in local_history.json()] == [created["id"]]
        assert image_path.exists()

        database.update_case(created["id"], is_test=True)
        assert client.get("/api/cases").json() == []
        admin_test = client.get("/api/cases?record_scope=test")
        assert [item["id"] for item in admin_test.json()] == [created["id"]]
        assert client.get("/api/trends?days=30").json()["total"] == 0
        database.update_case(created["id"], is_test=False)

        trend = client.get("/api/trends?days=30")
        assert trend.status_code == 200
        assert trend.json()["total"] == 1
        assert "本机保存的诊断记录" in trend.json()["scope"]
        assert image_path.exists()

    with TestClient(main.app) as restarted_client:
        restarted_history = restarted_client.get("/api/cases")
        assert [item["id"] for item in restarted_history.json()] == [created["id"]]
        assert image_path.exists()


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
            data=valid_case_data(),
        )
        assert response.status_code == 422


def test_upload_validates_required_fields_and_insect_condition(tmp_path, monkeypatch):
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "test.sqlite3",
        upload_dir=tmp_path / "uploads",
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    with TestClient(main.app) as client:
        missing_common = client.post(
            "/api/cases",
            files={"image": ("corn.jpg", image_bytes(), "image/jpeg")},
            data={"crop": "玉米"},
        )
        assert missing_common.status_code == 422

        missing_plant_context = client.post(
            "/api/cases",
            files={"image": ("corn.jpg", image_bytes(), "image/jpeg")},
            data=valid_case_data(part="", growth_stage=""),
        )
        assert missing_plant_context.status_code == 422

        invalid_scene = client.post(
            "/api/cases",
            files={"image": ("corn.jpg", image_bytes(), "image/jpeg")},
            data=valid_case_data(environment_json='{"scene":"实验室"}'),
        )
        assert invalid_scene.status_code == 422

        insect = client.post(
            "/api/cases",
            files={"image": ("insect.jpg", image_bytes(), "image/jpeg")},
            data=valid_case_data(crop="昆虫", part="任意旧值", growth_stage="任意旧值"),
        )
        assert insect.status_code == 201
        assert insect.json()["part"] == "不适用"
        assert insect.json()["growth_stage"] == "不适用"


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
    from app.knowledge import KNOWLEDGE_SCHEMA_VERSION, knowledge_contract, prioritized_guidance

    contract = knowledge_contract()
    assert contract["schema_version"] == KNOWLEDGE_SCHEMA_VERSION
    assert len(contract["classes"]) == 16
    assert {item["class_id"] for item in contract["classes"]} == set(range(16))
    assert len(contract["sources"]) >= 4
    assert contract["safety_boundary"]["scope"] == "general_ipm_orientation_only"
    assert contract["safety_boundary"]["chemical_limit"]
    assert all(card["source_ids"] for card in contract["classes"])
    source_by_id = {item["id"]: item for item in contract["sources"]}
    for card in contract["classes"]:
        class_sources = [
            source_by_id[source_id]
            for source_id in card["source_ids"]
            if source_by_id[source_id]["evidence_level"].startswith("class_specific")
        ]
        assert class_sources, card["class_id"]
        assert all(source["url"].startswith("https://") for source in class_sources)
        assert all(source["retrieved_at"] == "2026-08-11" for source in class_sources)
        assert set(card["management"]) == {
            "agronomic",
            "physical",
            "biological",
            "monitoring_and_escalation",
        }
        assert all(card["management"][key] for key in card["management"])
        assert "具体产品" in card["chemical_safety"]
    guidance = prioritized_guidance(0, "high", "unknown")
    assert guidance is not None
    assert "人工复核" in "".join(guidance["immediate"])
    assert "无法判断" in "".join(guidance["immediate"])


def test_case_review_queue_and_audit_history(tmp_path, monkeypatch):
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "test.sqlite3",
        upload_dir=tmp_path / "uploads",
        model_path=None,
        detector_endpoint=None,
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    with TestClient(main.app) as client:
        upload = client.post(
            "/api/cases",
            files={"image": ("corn.jpg", image_bytes(), "image/jpeg")},
            data=valid_case_data(),
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
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)
    monkeypatch.setattr(detector, "settings", test_settings)
    monkeypatch.setattr(
        detector.detector,
        "detect",
        lambda _: [
            {
                "class_id": 14,
                "class_name": "蛴螬",
                "class_name_en": "White grub",
                "category_type": "害虫",
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
            data=valid_case_data(crop="番茄"),
        )
        assert upload.status_code == 201
        assert upload.json()["crop"] == "番茄"
        detected = client.post(f"/api/cases/{upload.json()['id']}/detect")
        assert detected.status_code == 200
        assert detected.json()["crop"] == "番茄"
        explainability = detected.json()["detector_summary"]["explainability"]
        assert explainability["primary_confidence_band"] == "low"
        assert explainability["knowledge_card"]["class_id"] == 14
        assert explainability["model_evidence"]["routing_is_shadow"] is True
        assert explainability["human_review"]["required"] is True
        assert explainability["safety"]["chemical_recommendations"] == "not_provided"


def test_case_analysis_success_is_saved_and_reloaded(tmp_path, monkeypatch):
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "test.sqlite3",
        upload_dir=tmp_path / "uploads",
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    async def fake_analysis(record):
        assert record["crop"] == "玉米"
        return {
            "status": "completed",
            "schema_version": "evidence-extractor-v1",
            "primary_diagnosis": "玉米叶枯病",
            "candidate_diagnoses": ["玉米叶枯病"],
            "symptoms": ["叶片出现斑点"],
            "harm_level": "medium",
            "grounded_assessment": {
                "harms": [
                    {
                        "conclusion": "叶片可见区域存在受损",
                        "evidence": [
                            {
                                "source": "image",
                                "reference": "original_image",
                                "observation": "原图可见叶片斑点",
                            }
                        ],
                    }
                ],
                "causes": [
                    {
                        "conclusion": "当前证据支持玉米叶枯病候选",
                        "evidence": [
                            {
                                "source": "yolo",
                                "reference": "yolo_primary",
                                "observation": "YOLO主候选为玉米叶枯病",
                            }
                        ],
                    }
                ],
            },
            "uncertainty": [],
            "detector_alignment": "agree",
            "needs_human_review": False,
            "review_reasons": [],
            "provenance": {"engine": "deterministic_evidence_extractor"},
            "independent_judgment": {
                "observed_part": "叶片",
                "observed_growth_stage": "营养生长期",
            },
        }

    monkeypatch.setattr(main, "request_evidence_analysis", fake_analysis)

    with TestClient(main.app) as client:
        upload = client.post(
            "/api/cases",
            files={"image": ("corn.jpg", image_bytes(), "image/jpeg")},
            data=valid_case_data(),
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
        assert analyzed.json()["part"] == "叶片"
        assert analyzed.json()["growth_stage"] == "苗期"
        assert analyzed.json()["evidence_analysis"]["status"] == "unavailable"
        assert analyzed.json()["treatment"]["source"] == "local_knowledge_base"

        reloaded = client.get(f"/api/cases/{case_id}")
        assert reloaded.status_code == 200
        assert reloaded.json()["analysis"]["provenance"]["engine"] == "deterministic_evidence_extractor"
