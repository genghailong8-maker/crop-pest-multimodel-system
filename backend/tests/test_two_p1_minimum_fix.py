from __future__ import annotations

from app.search.evidence_extractor import EvidenceExtractor
from app.search.models import SearchEvidence, SearchSource
from app.search.normalizer import normalize_search_results


def raw_source(source_id: str, title: str, url: str, content: str) -> SearchSource:
    """Convert one captured raw Tavily result into the production model boundary."""
    return SearchSource(
        id=source_id,
        title=title,
        site_name="农业专业资料",
        url=url,
        content=content,
        reliability_level="",
    )


def raw_evidence(class_name: str, query_type: str, *sources: SearchSource) -> SearchEvidence:
    return SearchEvidence(
        class_name=class_name,
        query_type=query_type,
        status="available",
        sources=list(sources),
    )


def test_douyuanjing_raw_normalizer_extractor_full_chain_keeps_safe_life_cycle_cause() -> None:
    raw = raw_evidence(
        "豆芫菁",
        "possible_causes",
        raw_source(
            "raw-tavily-1",
            "豆芫菁发生规律",
            "https://www.pwsannong.com/c/2016-04-13/550260.shtml",
            "豆芫菁在东北、华北一年发生一代，成虫于夏季出现。",
        ),
    )

    normalized = normalize_search_results([raw])
    extracted = EvidenceExtractor().extract(normalized)

    assert normalized.status == "available"
    assert [item.title for item in normalized.sources] == ["豆芫菁发生规律"]
    assert extracted.possible_causes
    assert extracted.possible_causes[0].conclusion == "豆芫菁在东北、华北一年发生一代，成虫于夏季出现。"
    assert not any(marker in extracted.possible_causes[0].conclusion for marker in ("取食", "危害", "喷施", "研究表明"))


def test_douyuanjing_narrow_pattern_does_not_promote_harm_or_management() -> None:
    unsafe = raw_evidence(
        "豆芫菁",
        "possible_causes",
        raw_source(
            "unsafe",
            "豆芫菁危害与防治",
            "https://agri.gov.cn/douyuanjing-unsafe",
            "豆芫菁成虫取食豆叶造成缺刻，建议及时喷施药剂防治。",
        ),
    )

    extracted = EvidenceExtractor().extract(normalize_search_results([unsafe]))

    assert extracted.possible_causes == []


def test_locust_natural_ecological_causes_are_still_accepted() -> None:
    evidence = raw_evidence(
        "蝗总科",
        "possible_causes",
        raw_source(
            "natural",
            "加强蝗情监测与防控 理性应对蝗虫灾害威胁",
            "https://agri.gov.cn/locust-natural",
            "据专家分析，当前沙漠蝗的暴发与虫源积累及降雨偏多有关。",
        ),
    )

    extracted = EvidenceExtractor().extract(normalize_search_results([evidence]))

    assert [item.conclusion for item in extracted.possible_causes] == [
        "据专家分析，当前沙漠蝗的暴发与虫源积累及降雨偏多有关。"
    ]


def test_locust_source5_research_and_management_intervention_is_rejected_without_pollution() -> None:
    source5_intervention = raw_source(
        "source-5-intervention",
        "遥感与GIS在蝗虫生境研究中的应用进展",
        "https://www.jeesci.com/locust-habitat-research",
        "虽然人类活动对蝗虫的发生起着至关重要的作用，但究其原因，除了利用农药直接杀死蝗虫外，更多的方法仍然是通过改变蝗虫的生境，进而间接影响蝗虫或蝗卵的数量。",
    )
    source5_research = raw_source(
        "source-5-research",
        "遥感与GIS在蝗虫生境研究中的应用进展",
        "https://www.jeesci.com/locust-habitat-research-analysis",
        "巩爱歧、Lockwood 等[19-20]的研究也均指出，蝗虫发生具有一定的随机性和突然性。",
    )
    natural = raw_source(
        "natural-2",
        "蝗总科自然发生条件",
        "https://agri.gov.cn/locust-natural-2",
        "温度适宜且降雨偏多时，蝗虫容易发生。",
    )

    extracted = EvidenceExtractor().extract(
        normalize_search_results([
            raw_evidence("蝗总科", "possible_causes", source5_intervention, source5_research, natural)
        ])
    )
    conclusions = [item.conclusion for item in extracted.possible_causes]
    research_pollution = sum(
        1
        for item in conclusions
        if any(marker in item for marker in ("等[", "的研究也均指出", "人类活动"))
    )
    management_pollution = sum(1 for item in conclusions if any(marker in item for marker in ("农药", "防治", "改生境", "生境")))

    assert conclusions == ["温度适宜且降雨偏多时，蝗虫容易发生。"]
    assert research_pollution == 0
    assert management_pollution == 0
