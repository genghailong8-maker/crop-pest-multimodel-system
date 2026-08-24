from __future__ import annotations

from app.search.evidence_extractor import EvidenceExtractor
from app.search.models import SearchEvidence, SearchSource


def source(source_id: str = "source-1", content: str | None = None, **updates) -> SearchSource:
    return SearchSource(
        id=source_id,
        title=updates.pop("title", "蛴螬农业部门资料"),
        site_name=updates.pop("site_name", "农业部门"),
        url=updates.pop("url", f"https://example.gov.cn/{source_id}"),
        content=content or "蛴螬幼虫咬食作物根部，可造成幼苗枯萎甚至死亡。地下害虫幼虫活动与有机肥管理条件有关。",
        reliability_level=updates.pop("reliability_level", "政府农业部门"),
        **updates,
    )


def evidence(*sources: SearchSource, status: str = "available") -> SearchEvidence:
    return SearchEvidence(class_name="蛴螬", status=status, sources=list(sources))


def test_unavailable_evidence_returns_empty_result() -> None:
    assert EvidenceExtractor().extract(evidence(status="unavailable")).model_dump() == {
        "status": "unavailable", "harms": [], "possible_causes": []
    }


def test_extracts_harm_sentence_verbatim() -> None:
    result = EvidenceExtractor().extract(evidence(source()))
    assert result.harms[0].conclusion == "蛴螬幼虫咬食作物根部，可造成幼苗枯萎甚至死亡。"


def test_extracts_possible_cause_sentence_verbatim() -> None:
    result = EvidenceExtractor().extract(evidence(source()))
    assert result.possible_causes[0].conclusion == "地下害虫幼虫活动与有机肥管理条件有关。"


def test_every_conclusion_has_only_its_source_id() -> None:
    result = EvidenceExtractor().extract(evidence(source("source-9")))
    assert all(item.source_ids == ["source-9"] for item in [*result.harms, *result.possible_causes])


def test_does_not_invent_when_no_keyword_sentence_exists() -> None:
    result = EvidenceExtractor().extract(evidence(source(content="这是一个普通页面介绍，没有可核验的农业结论。")))
    assert result.status == "unavailable"
    assert not result.harms and not result.possible_causes


def test_deduplicates_repeated_sentences() -> None:
    repeated = "蛴螬咬食根部，造成幼苗死亡。蛴螬咬食根部，造成幼苗死亡。"
    result = EvidenceExtractor().extract(evidence(source(content=repeated)))
    assert len(result.harms) == 1


def test_rejects_another_pest_sentence_from_a_generic_collection_page() -> None:
    item = source(
        title="园林病虫害防治",
        content="椰心叶甲危害嫩叶，严重时整叶枯死。蛴螬咬食根茎部，可导致幼苗死亡。",
    )
    result = EvidenceExtractor().extract(evidence(item))
    assert [conclusion.conclusion for conclusion in result.harms] == ["蛴螬咬食根茎部，可导致幼苗死亡。"]


def test_multi_entity_title_does_not_attribute_another_pest_body_to_target() -> None:
    item = source(title="蛴螬与椰心叶甲防治", content="椰心叶甲危害嫩叶，严重时整叶枯死。")
    result = EvidenceExtractor().extract(evidence(item))
    assert result.model_dump() == {"status": "unavailable", "harms": [], "possible_causes": []}


def test_single_subject_title_keeps_pronoun_like_harm_context() -> None:
    item = source(title="蛴螬的发生与防治", content="蛴螬主要生活在土壤中。幼虫咬食作物地下根部，严重时可造成幼苗死亡。")
    result = EvidenceExtractor().extract(evidence(item))
    assert [conclusion.conclusion for conclusion in result.harms] == ["幼虫咬食作物地下根部，严重时可造成幼苗死亡。"]


def test_multi_entity_title_does_not_attribute_other_pest_cause_to_target() -> None:
    item = source(title="蛴螬与椰心叶甲发生规律", content="高温有利于椰心叶甲发生。")
    result = EvidenceExtractor().extract(evidence(item))
    assert result.possible_causes == []


def test_rejects_a_generic_occurrence_statement_as_a_possible_cause() -> None:
    item = source(content="蛴螬在不同土壤中发生危害的种类有差异。蛴螬喜发生于有机质多的土壤中。")
    result = EvidenceExtractor().extract(evidence(item))
    assert [conclusion.conclusion for conclusion in result.possible_causes] == ["蛴螬喜发生于有机质多的土壤中。"]


def test_rejects_weak_harm_occurrence_statement() -> None:
    result = EvidenceExtractor().extract(evidence(source(content="蛴螬在不同土壤中发生危害的种类有差异。")))
    assert result.harms == []


def test_keeps_specific_harm_actions_and_effects() -> None:
    item = source(content="蛴螬幼虫咬食作物地下根部，严重时可造成幼苗死亡。蛴螬可造成根系损伤并导致植株生长受阻。")
    result = EvidenceExtractor().extract(evidence(item))
    assert [conclusion.conclusion for conclusion in result.harms] == [
        "蛴螬幼虫咬食作物地下根部，严重时可造成幼苗死亡。",
        "蛴螬可造成根系损伤并导致植株生长受阻。",
    ]


def test_ignores_navigation_noise() -> None:
    result = EvidenceExtractor().extract(evidence(source(content="首页导航危害信息。登录注册。")))
    assert result.status == "unavailable"


def test_keeps_at_most_two_conclusions_per_section() -> None:
    content = "蛴螬危害根部造成幼苗死亡。蛴螬为害根茎造成缺苗。蛴螬受害植株会枯萎。发生条件与高温有关。发生原因与土壤湿度有关。发生条件与连作有关。"
    result = EvidenceExtractor().extract(evidence(source(content=content)))
    assert len(result.harms) <= 2
    assert len(result.possible_causes) <= 2


def test_uses_stable_score_order() -> None:
    payload = evidence(source("source-2"), source("source-1"))
    first = EvidenceExtractor().extract(payload).model_dump()
    second = EvidenceExtractor().extract(payload).model_dump()
    assert first == second


def test_accepts_html_content_as_plain_text() -> None:
    result = EvidenceExtractor().extract(evidence(source(content="<p>蛴螬危害根部，造成幼苗枯萎。</p><p>发生条件与土壤湿度有关。</p>")))
    assert result.status == "available"


def test_uses_snippet_only_when_content_is_missing() -> None:
    item = source(content="")
    item = item.model_copy(update={"content": None, "snippet": "蛴螬危害根部，造成幼苗死亡。"})
    assert EvidenceExtractor().extract(evidence(item)).harms


def test_ignores_source_without_body() -> None:
    item = source(content="").model_copy(update={"content": None, "snippet": None})
    assert EvidenceExtractor().extract(evidence(item)).status == "unavailable"


def test_reliability_breaks_otherwise_equal_candidates() -> None:
    low = source("source-1", "蛴螬危害根部，造成幼苗死亡。", reliability_level="普通网页")
    high = source("source-2", "蛴螬危害根部，造成幼苗死亡。", reliability_level="政府农业部门")
    result = EvidenceExtractor().extract(evidence(low, high))
    assert result.harms[0].source_ids == ["source-2"]


def test_does_not_bind_unknown_source_ids() -> None:
    result = EvidenceExtractor().extract(evidence(source("source-1")))
    assert {source_id for item in [*result.harms, *result.possible_causes] for source_id in item.source_ids} == {"source-1"}
