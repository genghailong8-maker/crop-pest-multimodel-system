from __future__ import annotations

import asyncio

from app import analysis, knowledge_documents, main
from app.search.curated import curated_evidence_for_class
from app.search.models import SearchEvidence, SearchSource


CURATED = {
    0: "玉米叶枯病",
    8: "芫菁",
    15: "豆芫菁",
}


def record(class_id: int, class_name: str | None = None, confidence: float = 0.91) -> dict:
    name = class_name or CURATED[class_id]
    return {
        "detections": [{"class_id": class_id, "class_name": name, "confidence": confidence}],
        "detector_summary": {
            "primary_candidate": {"class_id": class_id, "class_name": name, "max_confidence": confidence},
            "review_reasons": [],
        },
        "affected_ratio_percent": 12.5,
        "spread_speed": "slow",
    }


def test_three_exact_classes_have_curated_harms_and_possible_causes() -> None:
    for class_id, class_name in CURATED.items():
        evidence = curated_evidence_for_class(class_id, class_name)
        assert evidence is not None
        harms, causes = evidence
        assert harms.class_name == class_name
        assert causes.class_name == class_name
        assert harms.sources[0].content
        assert causes.sources[0].content
        assert "local_knowledge_base" not in {source.url for source in (*harms.sources, *causes.sources)}


def test_exact_class_isolation_does_not_use_parent_substring_matching() -> None:
    bean = curated_evidence_for_class(15, "豆芫菁")
    parent = curated_evidence_for_class(8, "芫菁")
    assert bean is not None and parent is not None
    assert bean[0].class_name == "豆芫菁"
    assert parent[0].class_name == "芫菁"
    assert curated_evidence_for_class(15, "芫菁") is None
    assert curated_evidence_for_class(8, "豆芫菁") is None


def test_corn_curated_sources_are_target_entity_only() -> None:
    evidence = curated_evidence_for_class(0, "玉米叶枯病")
    assert evidence is not None
    sources = [source for item in evidence for source in item.sources]
    assert any(source.title == "玉米链格孢菌叶枯病" for source in sources)
    assert any("Alternaria spp. Associated with Leaf Blight of Maize" in source.title for source in sources)
    assert not any(any(token in source.title for token in ("大斑病", "小斑病", "青枯病", "灰斑病")) for source in sources)


def test_corn_knowledge_alias_is_exact_and_product_identity_stays_canonical() -> None:
    evidence = curated_evidence_for_class(0, "玉米叶枯病")
    assert evidence is not None
    assert all(item.class_name == "玉米叶枯病" for item in evidence)
    assert curated_evidence_for_class(0, "玉米叶枯") is None


def test_corn_knowledge_alias_is_eligible_at_60_percent_without_tavily(monkeypatch) -> None:
    async def fail_if_called(_name: str):
        raise AssertionError("curated class must not call Tavily")

    monkeypatch.setattr(analysis, "collect_external_evidence", fail_if_called)
    result = asyncio.run(analysis.request_evidence_analysis(record(0, confidence=0.60)))
    assert result["primary_diagnosis"] == "玉米叶枯病"
    assert result["evidence_analysis"]["status"] == "available"
    assert result["evidence_analysis"]["harms"]
    assert result["evidence_analysis"]["possible_causes"]
    assert result["provenance"]["external_search"]["message"] == "本地精选知识库证据"


def test_source_ids_resolve_to_returned_sources() -> None:
    for class_id, class_name in CURATED.items():
        evidence = curated_evidence_for_class(class_id, class_name)
        assert evidence is not None
        source_map = {source.id: source for item in evidence for source in item.sources}
        for item in evidence:
            assert item.sources
            assert item.sources[0].id in source_map


def test_curated_analysis_is_independent_of_tavily(monkeypatch) -> None:
    async def fail_if_called(_name: str):
        raise AssertionError("curated class must not call Tavily")

    monkeypatch.setattr(analysis, "collect_external_evidence", fail_if_called)
    result = asyncio.run(analysis.request_evidence_analysis(record(15)))
    assert result["evidence_analysis"]["status"] == "available"
    assert result["evidence_analysis"]["harms"]
    assert result["evidence_analysis"]["possible_causes"]
    source_ids = {
        source["id"] for source in result["sources"]
    }
    assert all(
        source_id in source_ids
        for section in ("harms", "possible_causes")
        for conclusion in result["evidence_analysis"][section]
        for source_id in conclusion["source_ids"]
    )


def test_curated_analysis_is_eligible_at_60_percent(monkeypatch) -> None:
    async def fail_if_called(_name: str):
        raise AssertionError("curated class must not call Tavily")

    monkeypatch.setattr(analysis, "collect_external_evidence", fail_if_called)
    result = asyncio.run(analysis.request_evidence_analysis(record(15, confidence=0.60)))
    assert result["primary_diagnosis"] == "豆芫菁"
    assert result["evidence_analysis"]["status"] == "available"
    assert result["evidence_analysis"]["harms"]
    assert result["evidence_analysis"]["possible_causes"]
    assert result["provenance"]["external_search"]["message"] == "本地精选知识库证据"


def test_curated_override_survives_controlled_tavily_error(monkeypatch) -> None:
    async def fail_if_called(_name: str):
        raise RuntimeError("Tavily unavailable")

    monkeypatch.setattr(analysis, "collect_external_evidence", fail_if_called)
    result = asyncio.run(analysis.request_evidence_analysis(record(8)))
    assert result["evidence_analysis"]["status"] == "available"
    assert result["evidence_analysis"]["possible_causes"]


def test_three_curated_classes_return_complete_analysis_and_source_mapping(monkeypatch) -> None:
    async def fail_if_called(_name: str):
        raise AssertionError("curated classes must not call Tavily")

    monkeypatch.setattr(analysis, "collect_external_evidence", fail_if_called)
    for class_id, class_name in CURATED.items():
        result = asyncio.run(analysis.request_evidence_analysis(record(class_id, class_name)))
        analysis_payload = result["evidence_analysis"]
        source_map = {source["id"]: source for source in result["sources"]}
        assert analysis_payload["status"] == "available"
        assert analysis_payload["harms"]
        assert analysis_payload["possible_causes"]
        assert all(
            source_id in source_map
            for section in ("harms", "possible_causes")
            for conclusion in analysis_payload[section]
            for source_id in conclusion["source_ids"]
        )
        assert result["provenance"]["external_search"]["message"] == "本地精选知识库证据"


def test_non_special_class_keeps_tavily_normalizer_extractor_control(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_search(name: str) -> SearchEvidence:
        calls.append(name)
        return SearchEvidence(
            class_name="蛴螬",
            query_type="harms",
            status="available",
            sources=[
                SearchSource(
                    id="control-source",
                    title="蛴螬危害",
                    site_name="control",
                    url="https://example.invalid/grub",
                    content="蛴螬幼虫咬食作物根部，可造成幼苗枯萎。",
                )
            ],
        )

    monkeypatch.setattr(analysis, "collect_external_evidence", fake_search)
    result = asyncio.run(analysis.request_evidence_analysis({
        **record(14, "蛴螬"),
    }))
    assert calls == ["蛴螬"]
    assert result["evidence_analysis"]["status"] == "available"
    assert result["evidence_analysis"]["harms"]


def test_treatment_payload_remains_the_existing_knowledge_path() -> None:
    for class_id in CURATED:
        payload = main.local_treatment_payload({
            "detections": [{"class_id": class_id}],
            "detector_summary": {"primary_candidate": {"class_id": class_id}},
        })
        document = knowledge_documents.get_knowledge_document(class_id)
        assert document is not None
        assert payload["source"] == "local_knowledge_base"
        assert payload["content"]["prevention_html"] == document["prevention_html"]
        assert "<h2>危害</h2>" not in payload["content"]["prevention_html"]
        assert "<h2>可能诱因</h2>" not in payload["content"]["prevention_html"]
