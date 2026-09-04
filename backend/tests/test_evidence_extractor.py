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


def evidence(*sources: SearchSource, status: str = "available", class_name: str = "蛴螬") -> SearchEvidence:
    return SearchEvidence(class_name=class_name, status=status, sources=list(sources))


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


def test_possible_causes_reject_research_method_titles_but_keep_real_conditions() -> None:
    research = source(content="从马铃薯根际土中分离得到对茄链格孢菌具有较强抑制作用的菌株并对其发酵条件进行优化，为马铃薯早疫病生防菌的开发和应用提供菌种来源。利用单因素试验和正交试验对拮抗菌株的发酵条件进行优化。")
    real_cause = source("source-2", content="马铃薯早疫病在高温高湿或连续降雨条件下有利于发生和流行。")
    payload = evidence(research, real_cause, class_name="马铃薯早疫病")
    result = EvidenceExtractor().extract(payload)
    assert [item.conclusion for item in result.possible_causes] == ["马铃薯早疫病在高温高湿或连续降雨条件下有利于发生和流行。"]


def test_possible_causes_reject_management_advice_but_keep_declarative_causes() -> None:
    management = source(
        content="避免与茄科作物连作，实行轮作倒茬，减少病原菌积累。",
        title="马铃薯早疫病发生与防治",
    )
    result = EvidenceExtractor().extract(evidence(management, class_name="马铃薯早疫病"))
    assert result.possible_causes == []

    declarative_causes = (
        "连作会导致土壤中病原菌积累。",
        "长期连作有利于病害发生。",
        "病原菌积累可增加发病风险。",
        "高温高湿或连续降雨条件有利于早疫病发生。",
    )
    for index, sentence in enumerate(declarative_causes, start=2):
        item = source(
            f"source-{index}",
            content=sentence,
            title="马铃薯早疫病发生规律",
        )
        extracted = EvidenceExtractor().extract(evidence(item, class_name="马铃薯早疫病"))
        assert [cause.conclusion for cause in extracted.possible_causes] == [sentence]


def test_management_intervention_effect_is_rejected_from_both_sections() -> None:
    sentence = "有条件的地区，春播前农田浇灌后，可使土壤的温度、湿度发生变化，对地老虎、蛴螬等地下害虫生存不利，可使其死亡率在90%以上。"
    result = EvidenceExtractor().extract(
        evidence(source(content=sentence, title="蛴螬防治方法"), class_name="蛴螬")
    )
    assert result.harms == []
    assert result.possible_causes == []


def test_narrow_ecological_relation_markers_keep_natural_grub_causes() -> None:
    natural_causes = (
        "秋季的温湿度十分适合蛴螬的活动危害。",
        "土壤温湿度直接影响着蛴螬的活动。",
        "土壤含水量直接影响幼虫的活动和发生。",
        "降雨较多，湿度高有利于蛴螬出土和盛发。",
    )
    for index, sentence in enumerate(natural_causes, start=1):
        item = source(
            f"source-{index}",
            content=sentence,
            title="蛴螬发生规律",
        )
        result = EvidenceExtractor().extract(evidence(item, class_name="蛴螬"))
        assert [cause.conclusion for cause in result.possible_causes] == [sentence]
        assert result.possible_causes[0].source_ids == [f"source-{index}"]


def test_narrow_ecological_relation_markers_reject_intervention_contexts() -> None:
    intervention_sentences = (
        "灌溉后可改变土壤温湿度，对蛴螬生存不利。",
        "施肥能够改善土壤条件并减轻蛴螬危害。",
        "土壤温湿度会影响药剂防治效果。",
        "当前温度条件适合采用药剂进行防治。",
    )
    for sentence in intervention_sentences:
        result = EvidenceExtractor().extract(
            evidence(source(content=sentence, title="蛴螬防治方法"), class_name="蛴螬")
        )
        assert result.possible_causes == []


def test_fertilizer_intervention_sentence_is_rejected_without_rewriting_a_cause() -> None:
    sentence = "而腐熟的有机肥可改良土壤的透水、通气性状，提供土壤微生物活动的良好条件，使根系发育快、苗齐苗壮、增强作物的抗虫性，且由于蛴螬喜食腐熟的有机肥，也可减轻其对作物的为害。"
    result = EvidenceExtractor().extract(
        evidence(source(content=sentence, title="蛴螬发生与防治"), class_name="蛴螬")
    )
    assert result.harms == []
    assert result.possible_causes == []


def test_cross_section_duplicate_is_removed_after_normalization() -> None:
    sentence = "蛴螬咬食根部，造成幼苗死亡，并且湿度条件与其活动有关。"
    result = EvidenceExtractor().extract(
        evidence(source(content=sentence), class_name="蛴螬")
    )
    assert [item.conclusion for item in result.harms] == [sentence]
    assert result.possible_causes == []


def test_possible_causes_reject_english_research_and_management_fragments() -> None:
    research = source(
        content="Table 1 Factors and levels of orthogonal experiments for the optimization of fermentation conditions of strain LYB08. C: No.5 fermentation conditions. Screening，Identification and Optimization of Fermentation Conditions of Antagonistic Bacteria against Potato Early Blight.",
        title="马铃薯早疫病拮抗菌的筛选鉴定和发酵条件优化",
    )
    management = source(
        "source-2",
        content="Spot-check pathogens on potato leaves will provide timely guidance for EB control after the occurrence of optimal conditions for conidia invasion.",
        title="Detection of Alternaria solani during potato early blight",
    )
    result = EvidenceExtractor().extract(evidence(research, management, class_name="马铃薯早疫病"))
    assert result.possible_causes == []


def test_ellipsis_in_tavily_snippet_keeps_short_cause_fragment() -> None:
    cause = "A shortage of nitrogen supply, increased humidity, appropriate temperature, and rainy weather all increase the possibility of an EB outbreak"
    item = source(
        title="Detection of Alternaria solani during potato early blight",
        snippet=(
            "Background details before the excerpt. " * 12
            + cause
            + ", of [...] an omitted continuation. "
            + "Additional context after the excerpt. " * 12
        ),
    )
    result = EvidenceExtractor().extract(evidence(item, class_name="马铃薯早疫病"))
    assert any(conclusion.conclusion == cause for conclusion in result.possible_causes)
    assert all(len(conclusion.conclusion) <= 220 for conclusion in result.possible_causes)


def test_filters_leading_fragment_when_complete_same_source_harm_exists() -> None:
    fragment = "above ground, with symptoms ranging from small brownish to dark lesions to large ones that always begin on old leaves and grow upward (Sherf and MacNab, 1986; Dhaval et al., 2021)"
    complete = "EB affects plants above ground, with symptoms ranging from small brownish to dark lesions to large ones that always begin on old leaves and grow upward (Sherf and MacNab, 1986; Dhaval et al., 2021)"
    item = source(
        title="Detection of Alternaria solani during potato early blight",
        content=fragment + " [...] " + complete,
    )
    result = EvidenceExtractor().extract(evidence(item, class_name="马铃薯早疫病"))
    assert [harm.conclusion for harm in result.harms] == [complete]
    assert result.harms[0].source_ids == ["source-1"]


def test_lowercase_english_harm_is_not_globally_removed() -> None:
    item = source(
        title="马铃薯早疫病症状",
        content="in potato fields, infected leaves can develop dark lesions and cause yield loss.",
    )
    result = EvidenceExtractor().extract(evidence(item, class_name="马铃薯早疫病"))
    assert [harm.conclusion for harm in result.harms] == [item.content]


def test_english_catalog_alias_keeps_early_blight_evidence_but_not_late_blight() -> None:
    item = source(
        title="Detection of potato early blight symptoms",
        content=(
            "However, the existing methods cannot guarantee the accuracy as the sample size increases, "
            "so there is an urgent need to develop a method that can detect pathogens more sensitively. "
            "Alternaria solani causes early blight and leads to significant yield losses in potato crops "
            "(Suganthi et al., 2020). Increased humidity, appropriate temperature, and rainy weather "
            "increase the possibility of a potato early blight outbreak."
        ),
    )
    result = EvidenceExtractor().extract(evidence(item, class_name="马铃薯早疫病"))
    assert any("yield losses" in item.conclusion for item in result.harms)
    assert any("increase the possibility" in item.conclusion for item in result.possible_causes)
    assert not any(
        "existing methods" in item.conclusion.lower()
        for item in [*result.harms, *result.possible_causes]
    )


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


def test_rejects_baike_directory_and_footer_noise() -> None:
    item = source(
        title="马铃薯早疫病 - 百度百科",
        content="百度百科 马铃薯早疫病 订阅更新 目录 病原特征 为害症状 马铃薯早疫病 马铃薯早疫病 侵染循环 流行规律 防治方法 使用百度前必读 隐私政策 京ICP证。",
    )
    payload = SearchEvidence(class_name="马铃薯早疫病", status="available", sources=[item])
    result = EvidenceExtractor().extract(payload)
    assert result.model_dump() == {"status": "unavailable", "harms": [], "possible_causes": []}


def test_prefers_relevant_snippet_before_raw_page_noise() -> None:
    item = source(
        content="订阅更新 目录 为害症状 侵染循环 流行规律 使用百度前必读 隐私政策 京ICP证。",
        snippet="蛴螬幼虫咬食作物地下根部，严重时可造成幼苗死亡。",
    )
    result = EvidenceExtractor().extract(evidence(item))
    assert [conclusion.conclusion for conclusion in result.harms] == ["蛴螬幼虫咬食作物地下根部，严重时可造成幼苗死亡。"]


def test_keeps_single_subject_disease_harm_and_cause() -> None:
    item = source(
        title="马铃薯早疫病发生与防治",
        content="叶片发病后形成褐色同心轮纹病斑，严重时叶片枯死，并可导致产量下降。高温高湿或连续降雨条件有利于该病发生和流行。",
    )
    payload = SearchEvidence(class_name="马铃薯早疫病", status="available", sources=[item])
    result = EvidenceExtractor().extract(payload)
    assert [conclusion.conclusion for conclusion in result.harms] == ["叶片发病后形成褐色同心轮纹病斑，严重时叶片枯死，并可导致产量下降。"]
    assert [conclusion.conclusion for conclusion in result.possible_causes] == ["高温高湿或连续降雨条件有利于该病发生和流行。"]


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
