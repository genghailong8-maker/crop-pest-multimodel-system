from __future__ import annotations

from dataclasses import replace
import asyncio

from app import database
from app import analysis
from app.main import CROP_OPTIONS, _format_public_evidence_conclusion
from app.official_knowledge import (
    knowledge_card,
    knowledge_document,
    severity_payload,
    treatment_payload,
    validate_bundle,
)
from app.taxonomy import (
    OFFICIAL_TAXONOMY_VERSION,
    OFFICIAL_CLASS_CATALOG,
    identity_for_detection,
    legacy_insect_id_for_key,
)
from app.search.evidence_extractor import EvidenceExtractor
from app.search.models import SearchEvidence, SearchSource
from app.search.tavily import _query


def test_official_10class_taxonomy_is_exact() -> None:
    assert len(OFFICIAL_CLASS_CATALOG) == 10
    assert [item["name_zh"] for item in OFFICIAL_CLASS_CATALOG] == [
        "水稻稻瘟病", "水稻褐斑病", "玉米大斑病", "水稻东格鲁病毒病", "玉米灰斑病",
        "芫菁", "蚜虫", "盲蝽科", "蝼蛄", "蛴螬",
    ]
    assert len({item["canonical_key"] for item in OFFICIAL_CLASS_CATALOG}) == 10


def test_new_5_disease_knowledge_treatment_and_images_contract() -> None:
    assert validate_bundle() == {"diseases": 5, "severity_tiers": 15, "treatment_tiers": 15, "images": 15}
    for class_id in (0, 1, 2, 3, 4):
        card = knowledge_card(class_id)
        document = knowledge_document(class_id)
        assert card and document
        assert [section["title"] for section in document["sections"]] == ["基础信息", "特征", "为害症状"]
        rubric = severity_payload(class_id)
        assert rubric["status"] == "available"
        assert set(rubric["references"]) == {"mild", "moderate", "severe"}
        for level in ("mild", "moderate", "severe"):
            treatment = treatment_payload(class_id, level)
            assert treatment["source"] == "local_knowledge_base"
            assert treatment["status"] == "available"
            assert treatment["source_ids"]
        assert treatment_payload(class_id, None)["reason"] == "severity_uncertain"


def test_new_case_persists_taxonomy_and_canonical_identity(tmp_path, monkeypatch) -> None:
    local_settings = replace(
        database.settings,
        storage_dir=tmp_path,
        database_path=tmp_path / "candidate.sqlite3",
        upload_dir=tmp_path / "uploads",
    )
    monkeypatch.setattr(database, "settings", local_settings)
    database.init_database()
    created = database.create_case({
        "id": "official-case",
        "crop": "水稻",
        "part": "叶片",
        "growth_stage": "vegetative",
        "environment": {},
        "notes": "",
        "image_filename": "case.png",
        "image_path": str(tmp_path / "case.png"),
        "image_width": 10,
        "image_height": 10,
        "status": "detected",
        "taxonomy_version": OFFICIAL_TAXONOMY_VERSION,
        "canonical_key": "rice_blast",
        "canonical_class_name": "水稻稻瘟病",
        "detector_model_sha256": "model-sha",
        "detections": [{"class_id": 0, "class_name": "水稻稻瘟病", "canonical_key": "rice_blast", "confidence": 0.9, "bbox": [0, 0, 1, 1]}],
    })
    assert created["taxonomy_version"] == OFFICIAL_TAXONOMY_VERSION
    assert created["canonical_key"] == "rice_blast"
    assert created["canonical_class_name"] == "水稻稻瘟病"
    assert created["detector_model_sha256"] == "model-sha"


def test_legacy_case_is_not_reinterpreted_and_collision_is_safe() -> None:
    legacy = identity_for_detection({"class_id": 0, "class_name": "玉米叶枯病"}, "legacy_16class")
    official = identity_for_detection({"class_id": 0}, OFFICIAL_TAXONOMY_VERSION)
    assert legacy and official
    assert legacy["canonical_class_name"] != official["canonical_class_name"]
    assert official["canonical_key"] == "rice_blast"


def test_retained_5_insect_identity_uses_canonical_key_adapter() -> None:
    assert [legacy_insect_id_for_key(key) for key in ("blister_beetle", "aphid", "miridae", "mole_cricket", "white_grub")] == [8, 9, 10, 11, 14]


def test_official_rice_crop_is_an_active_upload_option() -> None:
    assert "水稻" in CROP_OPTIONS


def test_official_disease_queries_preserve_canonical_entity_identity() -> None:
    for item in OFFICIAL_CLASS_CATALOG[:5]:
        tokens = [token for token in item["name_en"].lower().split() if len(token) > 2]
        for query_type in ("harms", "possible_causes"):
            query = _query(item["name_zh"], query_type).lower()
            # Retrieval may intentionally use the verified Chinese canonical
            # label to avoid cross-disease collisions.  The contract is an
            # entity anchor, not a requirement to use one language.
            assert item["name_zh"].lower() in query or all(token in query for token in tokens)


def test_official_numeric_collision_never_enters_legacy_curated_route(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_search(name: str) -> SearchEvidence:
        calls.append(name)
        return SearchEvidence(class_name=name, status="unavailable")

    monkeypatch.setattr(analysis, "collect_external_evidence", fake_search)
    result = asyncio.run(analysis.request_evidence_analysis({
        "taxonomy_version": OFFICIAL_TAXONOMY_VERSION,
        "detections": [{"class_id": 0, "class_name": "水稻稻瘟病", "confidence": 0.9}],
        "detector_summary": {
            "primary_candidate": {"class_id": 0, "class_name": "水稻稻瘟病", "max_confidence": 0.9},
            "review_reasons": [],
        },
    }))
    assert calls == ["水稻稻瘟病"]
    assert result["provenance"]["external_search"]["message"] != "本地精选知识库证据"


def test_official_gray_leaf_spot_public_evidence_is_chinese_and_source_bound() -> None:
    conclusion = _format_public_evidence_conclusion(
        "Gray leaf spot lesions are yellow at first and then turn tan to brown."
    )
    assert conclusion == "玉米灰斑病病斑可先呈黄色，随后变为黄褐色至褐色，并可能与其他叶部病害混淆。"


def test_brown_spot_extractor_rejects_narrow_brown_spot_cross_entity_evidence() -> None:
    evidence = SearchEvidence(
        class_name="水稻褐斑病",
        status="available",
        sources=[SearchSource(
            id="narrow-brown-spot",
            title="Narrow brown spot - IRRI Rice Knowledge Bank",
            site_name="knowledgebank.irri.org",
            url="https://example.invalid/narrow-brown-spot",
            content="Narrow brown spot lesions can damage rice leaves and occur in humid conditions.",
        )],
    )
    extracted = EvidenceExtractor().extract(evidence)
    assert extracted.harms == []
    assert extracted.possible_causes == []
