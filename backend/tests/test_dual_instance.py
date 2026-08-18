from __future__ import annotations

import io
from dataclasses import replace

import httpx
from fastapi.testclient import TestClient
from PIL import Image

from app import config, control, database, detector, main


def image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (72, 126, 66)).save(buffer, format="JPEG")
    return buffer.getvalue()


def isolated_settings(tmp_path, **changes):
    values = {
        "storage_dir": tmp_path,
        "database_path": tmp_path / "cases.sqlite3",
        "upload_dir": tmp_path / "uploads",
        "report_dir": tmp_path / "reports",
        "control_dir": tmp_path / "control",
        "model_path": None,
        "detector_endpoint": None,
        "vlm_endpoint": None,
        "instance_id": "lab_cpu",
        "gateway_mode": False,
        **changes,
    }
    return replace(config.settings, **values)


def install_settings(monkeypatch, settings):
    monkeypatch.setattr(database, "settings", settings)
    monkeypatch.setattr(detector, "settings", settings)
    monkeypatch.setattr(main, "settings", settings)
    monkeypatch.setattr(main, "vlm_semaphore", None)


def test_password_session_and_control_store(tmp_path):
    encoded = control.hash_password("correct horse")
    assert control.verify_password("correct horse", encoded)
    assert not control.verify_password("wrong", encoded)
    token = control.issue_session("session-secret", 300)
    assert control.valid_session(token, "session-secret")
    assert not control.valid_session(token, "different-secret")

    store = control.ControlStore(tmp_path / "control", "lab_cpu")
    assert store.active_instance() == "lab_cpu"
    event = store.switch("gpu_full")
    assert event["previous"] == "lab_cpu"
    assert store.active_instance() == "gpu_full"
    assert store.audit()[0]["target"] == "gpu_full"


def test_case_instance_prefix_and_immutable_report_snapshot(tmp_path, monkeypatch):
    settings = isolated_settings(tmp_path)
    install_settings(monkeypatch, settings)

    async def fake_analysis(_record, _path):
        return {
            "status": "ok",
            "primary_diagnosis": "玉米叶枯病",
            "detector_alignment": "agree",
            "field_severity": "low",
            "provenance": {"model": "cpu-test-vlm"},
        }

    monkeypatch.setattr(main, "request_multimodal_analysis", fake_analysis)
    monkeypatch.setattr(detector.detector, "detect", lambda _path: [])
    with TestClient(main.app) as client:
        created = client.post(
            "/api/cases",
            files={"image": ("corn.jpg", image_bytes(), "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "affected_ratio_percent": "10",
                "spread_speed": "slow",
            },
        ).json()
        assert created["id"].startswith("lab_cpu-")
        assert created["instance_id"] == "lab_cpu"
        client.post(f"/api/cases/{created['id']}/detect")
        analyzed = client.post(f"/api/cases/{created['id']}/analyze")
        assert analyzed.status_code == 200
        first = client.get(f"/api/cases/{created['id']}/report").json()
        second = client.get(f"/api/cases/{created['id']}/report").json()

    assert first == second
    assert first["instance_id"] == "lab_cpu"
    assert first["snapshot"]["format"] == "crop-report-json-v1"
    versions = [path for path in (tmp_path / "reports" / created["id"]).glob("*.json") if path.name != "latest.json"]
    assert len(versions) == 1


def test_admin_login_and_offline_switch_is_rejected(tmp_path, monkeypatch):
    settings = isolated_settings(
        tmp_path,
        gateway_mode=True,
        remote_backend_url=None,
        admin_password_hash=control.hash_password("admin-pass"),
        admin_session_secret="test-session-secret",
    )
    install_settings(monkeypatch, settings)

    with TestClient(main.app) as client:
        assert client.get("/api/admin/instances").status_code == 401
        assert client.get("/api/cases?record_scope=all").status_code == 401
        assert client.post("/api/admin/login", json={"password": "wrong"}).status_code == 401
        assert client.post("/api/admin/login", json={"password": "admin-pass"}).status_code == 200
        assert client.get("/api/cases?record_scope=all").status_code == 200
        status = client.get("/api/admin/instances")
        assert status.status_code == 200
        assert status.json()["active_instance"] == "lab_cpu"
        rejected = client.post(
            "/api/admin/instances/activate", json={"instance_id": "gpu_full"}
        )
        assert rejected.status_code == 409
        assert main.control_store().active_instance() == "lab_cpu"


def test_gateway_routes_active_remote_and_keeps_local_case_affinity(tmp_path, monkeypatch):
    settings = isolated_settings(
        tmp_path,
        gateway_mode=True,
        remote_backend_url="http://gpu-backend.test:8000",
    )
    install_settings(monkeypatch, settings)
    main.control_store().switch("gpu_full")
    calls: list[str] = []

    class FakeClient:
        def __init__(self, *_, **__):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def request(self, method, url, **_):
            calls.append(f"{method} {url}")
            return httpx.Response(200, json={"served_by": "gpu_full"})

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeClient)
    with TestClient(main.app) as client:
        remote = client.get("/api/cases?limit=5")
        local = client.get("/api/cases/lab_cpu-does-not-exist")

    assert remote.status_code == 200
    assert remote.json() == {"served_by": "gpu_full"}
    assert calls == ["GET http://gpu-backend.test:8000/api/cases?limit=5"]
    assert local.status_code == 404
