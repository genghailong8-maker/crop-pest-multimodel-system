from __future__ import annotations

import json
import io
from dataclasses import replace

from fastapi.testclient import TestClient
from PIL import Image

from app import config, database, knowledge_documents, main
from app.reports import save_snapshot


def image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (80, 130, 70)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_packaged_knowledge_maps_all_classes_and_images() -> None:
    manifest = json.loads((config.settings.knowledge_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "baidu-knowledge-v1"
    assert len(manifest["documents"]) == 16
    assert manifest["referenced_image_count"] == 61
    assert sum(len(item["images"]) for item in manifest["documents"]) == 61
    assert not any("E:\\" in path.read_text(encoding="utf-8") for path in (config.settings.knowledge_dir / "documents").glob("*.md"))

    for class_id in range(16):
        document = knowledge_documents.get_knowledge_document(class_id)
        assert document is not None
        assert document["class_id"] == class_id
        assert "<table" in document["full_html"]
        assert "<table" not in document["symptoms_html"]
        assert "<table" not in document["features_html"]
        assert "<table" not in document["prevention_html"]

    corn_leaf_blight = knowledge_documents.get_knowledge_document(0)
    assert corn_leaf_blight is not None
    assert corn_leaf_blight["features_html"] == "<p>知识库暂未收录该项</p>\n"


def test_knowledge_document_and_asset_endpoints(tmp_path, monkeypatch) -> None:
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
    monkeypatch.setattr(knowledge_documents, "settings", settings)
    knowledge_documents.clear_knowledge_cache()

    with TestClient(main.app) as client:
        response = client.get("/api/catalog/classes/12/knowledge-document")
        assert response.status_code == 200
        payload = response.json()
        assert payload["class_name"] == "叶蝉科"
        assert payload["source"]["title"] == "百度百科"
        assert "/api/catalog/knowledge/assets/baidu-baike-20260818/12/1.jpg" in payload["full_html"]
        assert client.get("/api/catalog/classes/99/knowledge-document").status_code == 404
        assert client.get("/api/catalog/knowledge/assets/baidu-baike-20260818/12/1.jpg").status_code == 200
        assert client.get("/api/catalog/knowledge/assets/wrong-version/12/1.jpg").status_code == 404

    assert knowledge_documents.resolve_knowledge_asset("baidu-baike-20260818", "../manifest.json") is None
    knowledge_documents.clear_knowledge_cache()


def test_v1_report_is_upgraded_once_without_overwriting_history(tmp_path, monkeypatch) -> None:
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
    monkeypatch.setattr(knowledge_documents, "settings", settings)
    knowledge_documents.clear_knowledge_cache()

    with TestClient(main.app) as client:
        created = client.post(
            "/api/cases",
            files={"image": ("leaf.jpg", image_bytes(), "image/jpeg")},
            data={"crop": "玉米", "part": "叶片", "growth_stage": "苗期"},
        ).json()
        record = database.update_case(
            created["id"],
            status="analyzed",
            quality={"acceptable": True, "flags": []},
            detections=[{"class_id": 0, "class_name": "玉米叶枯病", "confidence": 0.91}],
            detector_summary={"primary_candidate": {"class_id": 0, "class_name": "玉米叶枯病", "max_confidence": 0.91}},
            analysis={"detector_alignment": "agree", "primary_diagnosis": "玉米叶枯病"},
        )
        legacy = main.build_case_report(record)
        legacy.pop("knowledge_document", None)
        save_snapshot(settings.report_dir, record["id"], settings.instance_id, legacy)

        case_dir = settings.report_dir / record["id"]
        assert len([path for path in case_dir.glob("*.json") if path.name != "latest.json"]) == 1
        upgraded = client.get(f"/api/cases/{record['id']}/report").json()
        assert upgraded["snapshot"]["format"] == "crop-report-json-v2"
        assert upgraded["knowledge_document"]["class_name"] == "玉米叶枯病"
        versions = [path for path in case_dir.glob("*.json") if path.name != "latest.json"]
        assert len(versions) == 2
        assert any(json.loads(path.read_text(encoding="utf-8"))["snapshot"]["format"] == "crop-report-json-v1" for path in versions)
        assert client.get(f"/api/cases/{record['id']}/report").json() == upgraded
        assert len([path for path in case_dir.glob("*.json") if path.name != "latest.json"]) == 2

    knowledge_documents.clear_knowledge_cache()
