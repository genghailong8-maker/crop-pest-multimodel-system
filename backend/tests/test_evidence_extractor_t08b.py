"""T-08B safety closure fixtures and decision-path regression tests."""

from __future__ import annotations

import pytest

from app.search.evidence_extractor import (
    EvidenceExtractor,
    _associate_candidate_with_target,
    _has_cause_marker,
    _is_harm_only_fragment,
    _is_management_advice_fragment,
    _is_research_context_fragment,
    _is_reverse_locust_harm,
    _sentences,
)
from app.search.models import SearchEvidence, SearchSource


def fixture_source(source_id: str, title: str, content: str) -> SearchSource:
    return SearchSource(
        id=source_id,
        title=title,
        site_name="T-08B preserved retrieval fixture",
        url=f"https://example.test/t08b/{source_id}",
        content=content,
        reliability_level="其他可信农业专业站点",
    )


def fixture_evidence(class_name: str, query_type: str, item: SearchSource) -> SearchEvidence:
    return SearchEvidence(class_name=class_name, query_type=query_type, status="available", sources=[item])


NEGATIVE_FIXTURES = (
    (
        "tomato-research-spray",
        "番茄细菌性斑点病",
        "possible_causes",
        "番茄细菌性斑点病防治研究与喷施试验",
        "Suppression of bacterial spot of tomato with foliar sprays of compost extracts under greenhouse and field conditions.",
    ),
    (
        "mirid-defense-enzyme",
        "盲蝽科",
        "harms",
        "不同生长时期冬枣受绿盲蝽危害后应激防御酶活性的变化",
        "随着绿盲蝽的危害加重，冬枣不同组织的受损程度不同，不同的酶活性表现不同。",
    ),
    (
        "leafhopper-management",
        "叶蝉科",
        "possible_causes",
        "叶蝉科管理建议",
        "不种植叶蝉科寄主作物，以免发生危害。",
    ),
    (
        "locust-reverse-relation",
        "蝗总科",
        "harms",
        "蝗虫病原真菌生物防治资料",
        "被天然存在的真菌蝗绿僵菌杀死的蝗虫，是一种环保的生物控制手段。",
    ),
)


@pytest.mark.parametrize("source_id,class_name,query_type,title,content", NEGATIVE_FIXTURES)
def test_t08b_four_negative_classes_are_safe(
    source_id: str,
    class_name: str,
    query_type: str,
    title: str,
    content: str,
) -> None:
    result = EvidenceExtractor().extract(fixture_evidence(class_name, query_type, fixture_source(source_id, title, content)))
    assert result.harms == []
    assert result.possible_causes == []


RESEARCH_RESULT_FIXTURES = (
    "研究结果表明，高温高湿有利于番茄斑枯病发生。",
    "试验结果显示，番茄斑枯病发病率在处理组中下降。",
    "处理后病斑大小和防效发生变化。",
    "测定结果显示，盲蝽科防御酶活性发生变化。",
    "盲蝽科酶活性变化与受害程度相关。",
    "盲蝽科生理指标在接种试验后发生变化。",
    "接种试验显示，盲蝽科相关指标发生变化。",
    "喷施药剂处理后，病害防效明显。",
    "防效在不同处理组之间存在差异。",
    "相关性分析显示，湿度与叶蝉科发生相关。",
)


@pytest.mark.parametrize("content", RESEARCH_RESULT_FIXTURES)
def test_t08b_research_vocabulary_never_becomes_user_evidence(content: str) -> None:
    item = fixture_source("research-vocabulary", "病害与盲蝽科研究试验", content)
    result = EvidenceExtractor().extract(fixture_evidence("盲蝽科", "possible_causes", item))
    assert result.harms == []
    assert result.possible_causes == []


MANAGEMENT_IMPERATIVE_FIXTURES = (
    "不种植叶蝉科寄主作物，以免发生危害。",
    "避免种植叶蝉科寄主，防止危害发生。",
    "应加强叶蝉科的田间管理。",
    "宜及时清除叶蝉科危害的病残体。",
    "建议合理轮作，减少叶蝉科发生。",
    "可采用喷施药剂控制叶蝉科危害。",
    "以免叶蝉科危害作物，应及时防治。",
    "防止叶蝉科危害发生，应加强监测。",
    "减少叶蝉科危害，建议及时清除寄主。",
    "控制叶蝉科发生，宜加强田间管理。",
)


@pytest.mark.parametrize("content", MANAGEMENT_IMPERATIVE_FIXTURES)
def test_t08b_management_imperatives_never_become_possible_causes(content: str) -> None:
    item = fixture_source("management-imperative", "叶蝉科防控建议", content)
    result = EvidenceExtractor().extract(fixture_evidence("叶蝉科", "possible_causes", item))
    assert result.possible_causes == []


@pytest.mark.parametrize(
    "content",
    (
        "高湿条件有利于叶蝉科发生。",
        "温度适宜、寄主丰富有利于叶蝉科发生。",
        "叶蝉科一年发生多代，温度和湿度影响其繁殖。",
    ),
)
def test_t08b_natural_cause_controls_remain_available(content: str) -> None:
    item = fixture_source("natural-cause", "叶蝉科发生规律", content)
    result = EvidenceExtractor().extract(fixture_evidence("叶蝉科", "possible_causes", item))
    assert [entry.conclusion for entry in result.possible_causes] == [content]


STABLE_POSITIVE_FIXTURES = (
    ("马铃薯早疫病", "harms", "马铃薯早疫病叶片出现深褐色坏死病斑，严重时叶片黄化脱落。"),
    ("蛴螬", "harms", "蛴螬幼虫咬食作物根部，可造成幼苗枯萎甚至死亡。"),
    ("玉米锈病", "harms", "玉米锈病叶片出现锈色病斑，严重时早衰并减产。"),
    ("番茄晚疫病", "harms", "番茄晚疫病叶片出现水浸状病斑，湿度高时迅速腐烂。"),
    ("马铃薯晚疫病", "harms", "马铃薯晚疫病使叶片出现褐色病斑并迅速枯死。"),
    ("蚜虫", "harms", "蚜虫刺吸嫩叶汁液，造成叶片卷曲和黄化。"),
)


@pytest.mark.parametrize("class_name,query_type,content", STABLE_POSITIVE_FIXTURES)
def test_t08b_stable_positive_controls_remain_available(class_name: str, query_type: str, content: str) -> None:
    item = fixture_source("stable-positive", class_name, content)
    result = EvidenceExtractor().extract(fixture_evidence(class_name, query_type, item))
    assert [entry.conclusion for entry in result.harms] == [content]


def test_t08b_root_cause_decision_path_is_explicit_for_four_negatives() -> None:
    expected = {
        "tomato-research-spray": {"research": True, "management": False, "cause": True, "harm_only": False, "reverse": False},
        "mirid-defense-enzyme": {"research": True, "management": False, "cause": False, "harm_only": True, "reverse": False},
        "leafhopper-management": {"research": False, "management": True, "cause": False, "harm_only": False, "reverse": False},
        "locust-reverse-relation": {"research": False, "management": False, "cause": False, "harm_only": False, "reverse": True},
    }
    extractor = EvidenceExtractor()
    for source_id, class_name, query_type, title, content in NEGATIVE_FIXTURES:
        item = fixture_source(source_id, title, content)
        sentences = _sentences(item)
        assert sentences == [content]
        sentence = sentences[0]
        associated, explicit_target = _associate_candidate_with_target(class_name, item, sentence, query_type)
        assert associated or explicit_target or source_id == "tomato-research-spray"
        path = {
            "sentence": True,
            "entity": associated,
            "research": _is_research_context_fragment(item, sentence),
            "management": _is_management_advice_fragment(sentence),
            "cause": _has_cause_marker(sentence),
            "harm_only": _is_harm_only_fragment(sentence),
            "reverse": _is_reverse_locust_harm(class_name, sentence),
        }
        assert {key: path[key] for key in expected[source_id]} == expected[source_id]
        assert extractor._score(query_type, class_name, item, sentence) == 0
