"""T-08C research-analysis language closure regression tests."""

from __future__ import annotations

import pytest

from app.search.evidence_extractor import EvidenceExtractor, _is_research_context_fragment
from app.search.models import SearchEvidence, SearchSource


HYSPLIT_TITLE = "[PDF] 利用HYSPLIT 模型分析茶园假眼小绿叶蝉迁飞扩散行为"
HYSPLIT_URL = "https://www.fjnyxb.cn/cn/article/pdf/preview/10.19303.j.issn.1008-0384.2024.05.011.pdf"
RESEARCH_SENTENCE = (
    "种群密度与扩散系数分析表明，假眼小绿叶蝉有聚集分布和随机分布两种分布型，"
    "迁飞和扩散是导致两种分布型转化的重要因素。"
)
NATURAL_MIGRATION_SENTENCE = (
    "每年早春，随着气温回升，夏寄主新梢萌发，假眼小绿叶蝉逐步由越冬寄主迁飞、"
    "扩散转移至夏寄主危害，表现出典型的迁飞行为。"
)


def fixture_source(content: str, *, title: str = HYSPLIT_TITLE) -> SearchSource:
    return SearchSource(
        id="tavily-1",
        title=title,
        site_name="www.fjnyxb.cn",
        url=HYSPLIT_URL,
        content=content,
        reliability_level="其他可信农业专业站点",
    )


def fixture_evidence(content: str, *, title: str = HYSPLIT_TITLE) -> SearchEvidence:
    return SearchEvidence(
        class_name="叶蝉科",
        query_type="possible_causes",
        status="available",
        sources=[fixture_source(content, title=title)],
    )


def test_t08c_exact_hysplit_research_sentence_is_rejected_from_final_causes() -> None:
    source = fixture_source(f"{NATURAL_MIGRATION_SENTENCE}\n{RESEARCH_SENTENCE}")

    assert _is_research_context_fragment(source, RESEARCH_SENTENCE) is True

    output = EvidenceExtractor().extract(
        fixture_evidence(f"{NATURAL_MIGRATION_SENTENCE}\n{RESEARCH_SENTENCE}")
    )

    conclusions = [item.conclusion for item in output.possible_causes]
    assert RESEARCH_SENTENCE not in conclusions
    assert NATURAL_MIGRATION_SENTENCE in conclusions


@pytest.mark.parametrize(
    "sentence",
    (
        RESEARCH_SENTENCE,
        "模型分析结果表明，叶蝉科在适宜温度下活动增强。",
        "相关性分析显示，叶蝉科迁飞与气温回升相关。",
        "参数分析结果显示，叶蝉科在高湿条件下发生。",
    ),
)
def test_t08c_research_analysis_result_language_is_rejected(sentence: str) -> None:
    source = fixture_source(sentence, title="叶蝉科发生规律资料")

    assert _is_research_context_fragment(source, sentence) is True
    assert EvidenceExtractor().extract(fixture_evidence(sentence, title="叶蝉科发生规律资料")).possible_causes == []


@pytest.mark.parametrize(
    "sentence",
    (
        NATURAL_MIGRATION_SENTENCE,
        "气温回升后，假眼小绿叶蝉由越冬寄主迁飞扩散至夏寄主危害。",
        "温度适宜时，叶蝉科活动增强并可自然迁飞扩散。",
        "温度和湿度适宜时，叶蝉科种群容易发生并扩大。",
    ),
)
def test_t08c_natural_leafhopper_facts_remain_accepted(sentence: str) -> None:
    output = EvidenceExtractor().extract(fixture_evidence(sentence, title="叶蝉科发生规律资料"))

    assert sentence in [item.conclusion for item in output.possible_causes]


def test_t08c_natural_overwinter_fact_is_not_research_rejected() -> None:
    sentence = "假眼小绿叶蝉以成虫在针叶木本植物上越冬，无休眠现象。"
    source = fixture_source(sentence, title="叶蝉科发生规律资料")

    assert _is_research_context_fragment(source, sentence) is False


def test_t08c_plain_analysis_word_alone_does_not_trigger_research_guard() -> None:
    sentence = "根据发生情况分析，叶蝉科在高湿条件下容易发生。"

    source = fixture_source(sentence, title="叶蝉科发生规律资料")
    assert _is_research_context_fragment(source, sentence) is False
    assert [item.conclusion for item in EvidenceExtractor().extract(fixture_evidence(sentence, title="叶蝉科发生规律资料")).possible_causes] == [sentence]
