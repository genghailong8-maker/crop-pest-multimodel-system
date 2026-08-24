from __future__ import annotations

import io
from dataclasses import replace

from fastapi.testclient import TestClient
from PIL import Image

from app import config, database, main
from app.search import persisted_evidence_snapshots
from app.search.models import SearchEvidence, SearchSource


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
        instance_id="lab_cpu",
        gateway_mode=False,
    )


def install_settings(monkeypatch, settings) -> None:
    monkeypatch.setattr(database, "settings", settings)
    monkeypatch.setattr(main, "settings", settings)


def create_case(settings, case_id: str = "lab_cpu-evidence") -> dict:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    image_path = settings.upload_dir / f"{case_id}.jpg"
    image_path.write_bytes(image_bytes())
    return database.create_case(
        {
            "id": case_id,
            "crop": "玉米",
            "part": "叶片",
            "growth_stage": "苗期",
            "environment": {"scene": "露地"},
            "notes": "",
            "image_filename": image_path.name,
            "image_path": str(image_path),
            "image_width": 640,
            "image_height": 480,
            "status": "analyzed",
            "detections": None,
        }
    )


def evidence_analysis() -> dict:
    return {
        "status": "available",
        "harms": [{"conclusion": "叶片出现可见斑痕", "source_ids": ["source-1"]}],
        "possible_causes": [{"conclusion": "田间条件与该现象相关", "source_ids": ["source-2"]}],
    }


def evidence_snapshots() -> list[dict[str, str]]:
    return [
        {
            "source_id": "source-1",
            "title": "农业部门资料 A",
            "site_name": "农业部门",
            "url": "https://example.gov.cn/a",
            "retrieved_at": "2026-08-21T00:00:00+00:00",
            "reliability_level": "政府农业部门",
            "content": "完整网页证据正文 A，不是生成摘要。",
        },
        {
            "source_id": "source-2",
            "title": "农业研究资料 B",
            "site_name": "农业研究机构",
            "url": "https://example.edu.cn/b",
            "retrieved_at": "2026-08-21T00:00:01+00:00",
            "reliability_level": "农业科研院所",
            "content": "完整网页证据正文 B，与正文 A 不同。",
        },
    ]


def test_normalized_sources_create_stable_persisted_snapshots() -> None:
    evidence = SearchEvidence(
        class_name="蛴螬",
        sources=[
            SearchSource(
                id="source-1",
                title="资料 A",
                site_name="站点 A",
                url="https://example.gov.cn/a",
                content="正文 A",
            ),
            SearchSource(
                id="source-2",
                title="资料 B",
                site_name="站点 B",
                url="https://example.edu.cn/b",
                content="正文 B",
            ),
            SearchSource(
                id="source-3",
                title="无正文",
                site_name="站点 C",
                url="https://example.org/c",
            ),
        ],
    )
    snapshots = persisted_evidence_snapshots(evidence)
    assert [item["source_id"] for item in snapshots] == ["source-1", "source-2"]
    assert snapshots[0]["content"] == "正文 A"
    assert snapshots[1]["content"] == "正文 B"


def test_case_detail_and_report_restore_evidence_after_reopen(tmp_path, monkeypatch) -> None:
    settings = isolated_settings(tmp_path)
    install_settings(monkeypatch, settings)
    database.init_database()
    record = create_case(settings)
    sources = [
        {
            "id": "source-1",
            "title": "农业部门资料 A",
            "site_name": "农业部门",
            "url": "https://example.gov.cn/a",
            "retrieved_at": "2026-08-21T00:00:00+00:00",
            "reliability_level": "政府农业部门",
        },
        {
            "id": "source-2",
            "title": "农业研究资料 B",
            "site_name": "农业研究机构",
            "url": "https://example.edu.cn/b",
            "retrieved_at": "2026-08-21T00:00:01+00:00",
            "reliability_level": "农业科研院所",
        },
    ]
    database.update_case(
        record["id"],
        detections=[{"class_id": 0, "class_name": "玉米叶枯病", "confidence": 0.91}],
        detector_summary={
            "primary_candidate": {
                "class_id": 0,
                "class_name": "玉米叶枯病",
                "max_confidence": 0.91,
            }
        },
        analysis={
            "status": "completed",
            "evidence_analysis": evidence_analysis(),
            "sources": sources,
            "evidence_snapshots": evidence_snapshots(),
        },
    )

    with TestClient(main.app) as client:
        detail = client.get(f"/api/cases/{record['id']}")
        report = client.get(f"/api/cases/{record['id']}/report")
    assert detail.status_code == 200
    assert [item["source_id"] for item in detail.json()["evidence_snapshots"]] == [
        "source-1",
        "source-2",
    ]
    assert "正文 A" in detail.json()["evidence_snapshots"][0]["content"]
    assert report.status_code == 200
    assert [item["source_id"] for item in report.json()["evidence_snapshots"]] == [
        "source-1",
        "source-2",
    ]

    # New clients/connections read the same SQLite and report files after a restart.
    async def fail_if_reanalyzed(*_args, **_kwargs):
        raise AssertionError("历史病例读取不得重新执行外部检索或多模态分析")

    monkeypatch.setattr(main, "request_evidence_analysis", fail_if_reanalyzed)
    reloaded = database.get_case(record["id"])
    assert reloaded is not None
    assert "正文 B" in reloaded["analysis"]["evidence_snapshots"][1]["content"]
    with TestClient(main.app) as client:
        reopened = client.get(f"/api/cases/{record['id']}")
        reopened_report = client.get(f"/api/cases/{record['id']}/report")
    assert reopened.status_code == 200
    assert reopened_report.status_code == 200
    assert reopened_report.json()["evidence_analysis"] == evidence_analysis()
    assert reopened_report.json()["evidence_snapshots"] == evidence_snapshots()

    # The lightweight list response does not carry full webpage content.
    with TestClient(main.app) as client:
        listed = client.get("/api/cases")
    assert listed.status_code == 200
    assert "evidence_snapshots" not in listed.json()[0]
    assert "content" not in listed.json()[0]["sources"][0]


def test_legacy_case_without_snapshots_is_compatible(tmp_path, monkeypatch) -> None:
    settings = isolated_settings(tmp_path)
    install_settings(monkeypatch, settings)
    database.init_database()
    record = create_case(settings, "lab_cpu-legacy")
    database.update_case(
        record["id"],
        analysis={
            "status": "completed",
            "evidence_analysis": evidence_analysis(),
            "sources": [
                {
                    "id": "source-1",
                    "title": "历史来源",
                    "site_name": "历史站点",
                    "url": "https://example.org/legacy",
                    "retrieved_at": "2026-08-20T00:00:00+00:00",
                }
            ],
        },
    )
    with TestClient(main.app) as client:
        detail = client.get(f"/api/cases/{record['id']}")
        report = client.get(f"/api/cases/{record['id']}/report")
    assert detail.status_code == 200
    assert detail.json()["evidence_snapshots"] == []
    assert detail.json()["sources"][0]["id"] == "source-1"
    assert report.status_code == 200
    assert report.json()["evidence_snapshots"] == []
    assert report.json()["evidence_analysis"] == evidence_analysis()


def test_search_failure_keeps_local_treatment_and_no_sensitive_snapshot(tmp_path, monkeypatch) -> None:
    settings = isolated_settings(tmp_path)
    install_settings(monkeypatch, settings)
    database.init_database()
    record = create_case(settings, "lab_cpu-unavailable")
    updated = database.update_case(
        record["id"],
        detections=[{"class_id": 0, "class_name": "玉米叶枯病", "confidence": 0.9}],
        detector_summary={
            "primary_candidate": {"class_id": 0, "class_name": "玉米叶枯病"}
        },
        analysis={
            "status": "completed",
            "evidence_analysis": {
                "status": "unavailable",
                "harms": [],
                "possible_causes": [],
            },
            "sources": [],
            "evidence_snapshots": [],
        },
    )
    payload = main.present_case(updated, include_evidence_snapshots=True)
    assert payload["evidence_snapshots"] == []
    assert payload["treatment"]["source"] == "local_knowledge_base"
    assert "TAVILY_API_KEY" not in str(payload)
    assert "Authorization" not in str(payload)
    assert "cookie" not in str(payload).lower()
