"""T-08D mixed factual/management clause safety closure fixtures."""

from __future__ import annotations

import pytest

from app.search.evidence_extractor import EvidenceExtractor, _is_management_advice_fragment
from app.search.models import SearchEvidence, SearchSource


def fixture_source(content: str, *, source_id: str = "t08d-1", title: str = "叶蝉科发生规律") -> SearchSource:
    return SearchSource(
        id=source_id,
        title=title,
        site_name="T-08D safety fixture",
        url=f"https://example.test/t08d/{source_id}",
        content=content,
        reliability_level="其他可信农业专业站点",
    )


def fixture_evidence(content: str, *, class_name: str = "叶蝉科", query_type: str = "possible_causes") -> SearchEvidence:
    return SearchEvidence(
        class_name=class_name,
        query_type=query_type,
        status="available",
        sources=[fixture_source(content)],
    )


FORMAL_REGRESSION = "叶蝉为秋季向树干部产卵危害桃树，温室附近种植白菜、萝卜等易发生，温室附近不种植十字花科蔬菜，以免除危害。"
NATURAL_CLAUSE = "温室附近种植白菜、萝卜等易发生"
MANAGEMENT_TAIL = "温室附近不种植十字花科蔬菜，以免除危害"


def possible_causes(content: str):
    return [item.conclusion for item in EvidenceExtractor().extract(fixture_evidence(content)).possible_causes]


def test_t08d_exact_formal_leafhopper_regression_rejects_management_tail() -> None:
    conclusions = possible_causes(FORMAL_REGRESSION)

    assert NATURAL_CLAUSE in conclusions
    assert MANAGEMENT_TAIL not in conclusions
    assert all("不种植" not in item and "以免" not in item for item in conclusions)


def test_t08d_same_sentence_retains_natural_ecological_clause() -> None:
    assert possible_causes(FORMAL_REGRESSION) == [NATURAL_CLAUSE]


@pytest.mark.parametrize(
    "sentence",
    (
        "温室附近不种植十字花科蔬菜，以免除危害。",
        "避免种植叶蝉科寄主，防止危害发生。",
        "建议及时清除寄主并加强管理，减少叶蝉科危害。",
    ),
)
def test_t08d_pure_management_and_purpose_clauses_are_rejected(sentence: str) -> None:
    assert possible_causes(sentence) == []


def test_t08d_management_guard_covers_formal_tail_when_isolated() -> None:
    assert _is_management_advice_fragment(MANAGEMENT_TAIL) is True


def test_t08d_natural_ecological_cause_remains_accepted() -> None:
    sentence = "温度适宜、寄主丰富有利于叶蝉科发生。"

    assert possible_causes(sentence) == [sentence]


@pytest.mark.parametrize(
    "sentence",
    (
        "气温回升后，假眼小绿叶蝉由越冬寄主迁飞扩散至夏寄主危害。",
        "温度和湿度适宜时，叶蝉科种群容易发生并扩大。",
    ),
)
def test_t08d_migration_temperature_and_humidity_facts_remain_accepted(sentence: str) -> None:
    assert possible_causes(sentence) == [sentence]


def test_t08d_hysplit_research_analysis_remains_rejected() -> None:
    sentence = "种群密度与扩散系数分析表明，假眼小绿叶蝉有聚集分布和随机分布两种分布型，迁飞和扩散是导致两种分布型转化的重要因素。"

    assert possible_causes(sentence) == []


def test_t08d_reversed_mixed_order_keeps_only_natural_fact() -> None:
    sentence = "避免种植叶蝉科寄主，温度适宜时叶蝉科容易发生。"

    assert possible_causes(sentence) == ["温度适宜时叶蝉科容易发生。"]


def test_t08d_semicolon_mixed_sentence_keeps_natural_fact() -> None:
    sentence = "建议加强田间管理；温度适宜时，叶蝉科种群容易发生。"

    assert possible_causes(sentence) == ["温度适宜时，叶蝉科种群容易发生。"]


def test_t08d_comma_mixed_sentence_removes_management_clause() -> None:
    sentence = "温度适宜时叶蝉科容易发生，防止叶蝉科危害应及时防治。"

    assert possible_causes(sentence) == ["温度适宜时叶蝉科容易发生"]


def test_t08d_outputs_have_no_short_or_malformed_fragments() -> None:
    sentences = (
        FORMAL_REGRESSION,
        "避免种植叶蝉科寄主，温度适宜时叶蝉科容易发生。",
        "建议加强田间管理；温度适宜时，叶蝉科种群容易发生。",
    )

    conclusions = [item for sentence in sentences for item in possible_causes(sentence)]
    assert conclusions
    assert all(12 <= len(item) <= 220 for item in conclusions)
    assert all(not item.startswith(("以免", "避免", "建议", "防止")) for item in conclusions)
