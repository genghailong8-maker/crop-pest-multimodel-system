from __future__ import annotations

import io
import sqlite3
import pytest
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from PIL import Image

from app import config, database, detector, main


def image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (72, 126, 66)).save(buffer, format="JPEG")
    return buffer.getvalue()


def public_settings(tmp_path):
    return replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "test.sqlite3",
        upload_dir=tmp_path / "uploads",
        model_path=None,
        detector_endpoint=None,
        public_mode=True,
        public_origin_secret="worker-secret",
        public_retention_days=30,
    )


def headers(**extra: str) -> dict[str, str]:
    return {"X-Crop-Origin-Secret": "worker-secret", **extra}


def test_public_consent_token_visibility_and_trends(tmp_path, monkeypatch):
    settings = public_settings(tmp_path)
    monkeypatch.setattr(database, "settings", settings)
    monkeypatch.setattr(detector, "settings", settings)
    monkeypatch.setattr(main, "settings", settings)

    with TestClient(main.app) as client:
        assert client.get("/api/cases").status_code == 403
        rejected = client.post(
            "/api/cases",
            headers=headers(),
            files={"image": ("leaf.jpg", image_bytes(), "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "environment_json": '{"scene":"露地"}',
                "affected_ratio_percent": "10",
                "spread_speed": "slow",
            },
        )
        assert rejected.status_code == 422

        upload = client.post(
            "/api/cases",
            headers=headers(),
            files={"image": ("leaf.jpg", image_bytes(), "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "environment_json": '{"scene":"露地"}',
                "affected_ratio_percent": "12.5",
                "spread_speed": "slow",
                "public_consent": "true",
            },
        )
        assert upload.status_code == 201
        created = upload.json()
        token = created["case_edit_token"]
        assert created["affected_ratio_percent"] == 12.5
        assert created["public_consent"] is True
        assert created["expires_at"]
        assert "edit_token_hash" not in created

        assert client.post(f"/api/cases/{created['id']}/detect", headers=headers()).status_code == 403
        detected = client.post(
            f"/api/cases/{created['id']}/detect",
            headers=headers(**{"X-Case-Edit-Token": token}),
        )
        assert detected.status_code == 200
        assert detected.json()["diagnostic_risk"] == "high"
        database.update_case(
            created["id"],
            detections=[{"class_id": 0, "class_name": "玉米叶枯病", "confidence": 0.9}],
        )

        private_image = settings.upload_dir / "legacy-private.jpg"
        private_image.write_bytes(image_bytes())
        database.create_case(
            {
                "id": "legacy-private",
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "environment": {},
                "notes": "",
                "image_filename": private_image.name,
                "image_path": str(private_image),
                "image_width": 640,
                "image_height": 480,
                "status": "uploaded",
            }
        )

        history = client.get("/api/cases", headers=headers())
        assert [item["id"] for item in history.json()] == [created["id"]]
        assert client.get("/api/cases?scope=all", headers=headers()).status_code == 404
        report = client.get(f"/api/cases/{created['id']}/report", headers=headers())
        assert report.status_code == 200
        assert report.json()["report_number"].startswith("TZ-")
        assert report.json()["sources"]
        assert all(source["url"].startswith("https://") for source in report.json()["sources"])
        trend = client.get("/api/trends?days=30", headers=headers())
        assert trend.status_code == 200
        assert trend.json()["total"] == 1
        assert trend.json()["trace_cases"][0]["id"] == created["id"]
        assert "不代表真实地区疫情趋势" in trend.json()["scope"]
        assert client.get("/api/prelabels/queue", headers=headers()).status_code == 404


def test_public_upload_rate_limit_returns_429(tmp_path, monkeypatch):
    settings = replace(public_settings(tmp_path), public_uploads_per_hour=1)
    monkeypatch.setattr(database, "settings", settings)
    monkeypatch.setattr(detector, "settings", settings)
    monkeypatch.setattr(main, "settings", settings)
    main.rate_limiter._events.clear()

    payload = {
        "crop": "玉米",
        "part": "叶片",
        "growth_stage": "苗期",
        "environment_json": '{"scene":"露地"}',
        "affected_ratio_percent": "10",
        "spread_speed": "slow",
        "public_consent": "true",
    }
    with TestClient(main.app) as client:
        first = client.post(
            "/api/cases",
            headers=headers(),
            files={"image": ("one.jpg", image_bytes(), "image/jpeg")},
            data=payload,
        )
        second = client.post(
            "/api/cases",
            headers=headers(),
            files={"image": ("two.jpg", image_bytes(), "image/jpeg")},
            data=payload,
        )
        assert first.status_code == 201
        assert second.status_code == 429


def test_unknown_spread_forces_unknown_severity(tmp_path, monkeypatch):
    settings = public_settings(tmp_path)
    monkeypatch.setattr(database, "settings", settings)
    monkeypatch.setattr(detector, "settings", settings)
    monkeypatch.setattr(main, "settings", settings)

    async def fake_analysis(_record):
        return {
            "field_severity": "high",
            "detector_alignment": "agree",
            "needs_human_review": False,
            "review_reasons": [],
        }

    monkeypatch.setattr(main, "request_evidence_analysis", fake_analysis)
    with TestClient(main.app) as client:
        upload = client.post(
            "/api/cases",
            headers=headers(),
            files={"image": ("leaf.jpg", image_bytes(), "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "environment_json": '{"scene":"露地"}',
                "affected_ratio_percent": "10",
                "spread_speed": "unknown",
                "public_consent": "true",
            },
        )
        assert upload.status_code == 422
        assert "扩散速度" in upload.json()["detail"]


def test_migration_backup_restore_and_expiry_cleanup(tmp_path, monkeypatch):
    settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "legacy.sqlite3",
        upload_dir=tmp_path / "uploads",
    )
    monkeypatch.setattr(database, "settings", settings)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            """
            CREATE TABLE diagnosis_cases (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                crop TEXT NOT NULL, part TEXT NOT NULL, growth_stage TEXT NOT NULL,
                environment_json TEXT NOT NULL, notes TEXT NOT NULL,
                image_filename TEXT NOT NULL, image_path TEXT NOT NULL,
                image_width INTEGER NOT NULL, image_height INTEGER NOT NULL,
                status TEXT NOT NULL, quality_json TEXT, detections_json TEXT,
                detector_summary_json TEXT, analysis_json TEXT, review_json TEXT
            )
            """
        )
    database.init_database()
    columns = {
        row[1]
        for row in sqlite3.connect(settings.database_path).execute(
            "PRAGMA table_info(diagnosis_cases)"
        )
    }
    assert {"public_consent", "expires_at", "diagnostic_risk", "field_severity", "is_test"} <= columns

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    image_path = settings.upload_dir / "expired.jpg"
    image_path.write_bytes(image_bytes())
    record = database.create_case(
        {
            "id": "expired",
            "crop": "玉米",
            "part": "叶片",
            "growth_stage": "苗期",
            "environment": {},
            "notes": "",
            "image_filename": image_path.name,
            "image_path": str(image_path),
            "image_width": 640,
            "image_height": 480,
            "status": "uploaded",
            "public_consent": True,
            "expires_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        }
    )
    assert record["public_consent"] is True
    backup = database.backup_database(tmp_path / "backup.sqlite3")
    assert backup.is_file()
    assert database.integrity_check() == "ok"
    assert database.purge_expired_cases() == {"cases": 1, "images": 1}
    assert not image_path.exists()
    database.restore_database(backup)
    assert database.get_case("expired") is not None


def test_mark_existing_cases_as_test_requires_exact_snapshot(tmp_path, monkeypatch):
    settings = replace(
        config.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "test.sqlite3",
        upload_dir=tmp_path / "uploads",
    )
    monkeypatch.setattr(database, "settings", settings)
    database.init_database()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    for case_id in ("old-a", "old-b"):
        image_path = settings.upload_dir / f"{case_id}.jpg"
        image_path.write_bytes(image_bytes())
        database.create_case(
            {
                "id": case_id,
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "environment": {},
                "notes": "",
                "image_filename": image_path.name,
                "image_path": str(image_path),
                "image_width": 640,
                "image_height": 480,
                "status": "uploaded",
            }
        )
    cutoff = database.utc_now()
    with pytest.raises(ValueError, match="与预期 3 不一致"):
        database.mark_existing_cases_as_test(cutoff, 3)
    assert len(database.list_cases(record_scope="user")) == 2

    result = database.mark_existing_cases_as_test(cutoff, 2)
    assert result["marked"] == 2
    assert database.list_cases(record_scope="user") == []
    assert len(database.list_cases(record_scope="test")) == 2
    assert database.validate_image_paths() == {
        "checked": 2,
        "missing_case_ids": [],
        "ok": True,
    }
