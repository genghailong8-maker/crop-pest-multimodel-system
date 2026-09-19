from __future__ import annotations

import json
from pathlib import Path

from app import main
from app.search.evidence_extractor import EvidenceExtractor, _associate_candidate_with_target, _is_tomato_bacterial_spot_section_fragment, _sentences
from app.search.models import SearchEvidence, SearchSource
from app.search.normalizer import normalize_search_results


def source(source_id: str, title: str, content: str) -> SearchSource:
    return SearchSource(
        id=source_id,
        title=title,
        site_name="minimum-fix fixture",
        url=f"https://agri.gov.cn/minimum-fix/{source_id}",
        content=content,
        reliability_level="政府农业部门",
    )


def evidence(class_name: str, query_type: str, *items: SearchSource) -> SearchEvidence:
    return SearchEvidence(
        class_name=class_name,
        query_type=query_type,
        status="available",
        sources=list(items),
    )


def test_douyuanjing_parent_name_overlap_is_narrowly_preserved() -> None:
    result = normalize_search_results([
        evidence(
            "豆芫菁",
            "possible_causes",
            source("child", "豆芫菁生活习性", "豆芫菁成虫在夏季出现并危害豆科植物。"),
            source("parent", "芫菁科生活习性", "芫菁科成虫为害豆类作物。"),
        )
    ])

    assert [item.title for item in result.sources] == ["豆芫菁生活习性"]


def test_tomato_correct_harm_and_cause_are_kept_but_wrong_context_is_rejected() -> None:
    harm = source(
        "harm",
        "番茄细菌性斑点病危害",
        "番茄细菌性斑点病主要危害叶片和果实，初期出现水浸状斑点。",
    )
    wrong_context = source(
        "wrong-context",
        "番茄细菌性斑点病病徵与防治",
        "因花朵大、重量重，常會有花莖倒伏的現象，若為居家盆花栽培可立枝架支撐其生長。",
    )
    cause = source(
        "cause",
        "番茄细菌性斑点病发生规律",
        "病原菌可通过种子污染传播，导致番茄细菌性斑点病发生。",
    )

    output = EvidenceExtractor().extract(evidence("番茄细菌性斑点病", "harms", harm, wrong_context))
    causes = EvidenceExtractor().extract(evidence("番茄细菌性斑点病", "possible_causes", cause))

    assert [item.conclusion for item in output.harms] == [harm.content]
    assert not any("花朵大" in item.conclusion for item in output.harms)
    assert [item.conclusion for item in causes.possible_causes] == [cause.content]


def test_locust_natural_ecological_cause_uses_only_locust_alias_and_pattern() -> None:
    sentence = "据专家分析，当前蝗虫的暴发与虫源积累及降雨偏多有关。"
    output = EvidenceExtractor().extract(
        evidence("蝗总科", "possible_causes", source("locust", "蝗总科发生规律", sentence))
    )

    assert [item.conclusion for item in output.possible_causes] == [sentence]


def test_leafhopper_t08d_exact_guard_remains_closed() -> None:
    sentence = "温室附近种植白菜、萝卜等易发生，温室附近不种植十字花科蔬菜，以免除危害。"
    output = EvidenceExtractor().extract(evidence("叶蝉科", "possible_causes", source("leafhopper", "叶蝉科发生规律", sentence)))

    assert [item.conclusion for item in output.possible_causes] == ["温室附近种植白菜、萝卜等易发生"]


def test_source_scarcity_is_preserved_for_yuanjing_and_leafhopper() -> None:
    for class_name in ("芫菁", "叶蝉科"):
        output = EvidenceExtractor().extract(
            evidence(class_name, "possible_causes", source("scarce", f"{class_name}资料", "当前资料未提供可核验的自然生态证据。"))
        )
        assert output.status == "unavailable"
        assert output.possible_causes == []


def test_public_potato_language_translation_does_not_mutate_raw_analysis() -> None:
    english = "A shortage of nitrogen supply, increased humidity, appropriate temperature, and rainy weather all increase the possibility of an EB outbreak"
    analysis = {
        "evidence_analysis": {"status": "available", "harms": [], "possible_causes": [{"conclusion": english, "source_ids": ["source-1"]}]},
        "evidence_snapshots": [{"content": english}],
    }

    public = main.public_analysis_payload(analysis)

    assert public["evidence_analysis"]["possible_causes"][0]["conclusion"] == "氮素供应不足、湿度升高、温度适宜以及多雨天气，都会增加早疫病暴发的可能性。"
    assert analysis["evidence_analysis"]["possible_causes"][0]["conclusion"] == english
    assert "evidence_snapshots" not in public


def test_public_pumpkin_format_removes_table_residue_and_traditional_text() -> None:
    bad = "| 南瓜白粉病病斑覆蓋整個葉片影響光合作用 | 南瓜白粉病初期在葉背出現白色粉狀病徵 |"
    public = main.public_analysis_payload({
        "evidence_analysis": {"status": "available", "harms": [{"conclusion": bad, "source_ids": ["source-1"]}], "possible_causes": []}
    })

    conclusion = public["evidence_analysis"]["harms"][0]["conclusion"]
    assert "|" not in conclusion
    assert not any(char in conclusion for char in "蓋個葉響現狀徵")


def test_corn_toc_navigation_sample_is_not_extracted() -> None:
    toc = "| 1基本信息 2基本简介 3为害症状 | 4危害特点 5病原形态特征 6传播途径和发病条件 | 7 |"
    output = EvidenceExtractor().extract(evidence("玉米叶枯病", "possible_causes", source("toc", "玉米叶枯病发生规律", toc)))

    assert output.possible_causes == []


def test_r1_pumpkin_traditional_source_cause_keeps_provenance() -> None:
    item = source(
        "ba01-source-1",
        "農業部苗栗區農業改良場 - 【本週分享案例：南瓜-白粉病】",
        "白粉病通常於秋末乾季開始發生，冬季危害嚴重！",
    )
    result = EvidenceExtractor().extract(evidence("南瓜白粉病", "possible_causes", item))
    assert [entry.conclusion for entry in result.possible_causes] == [item.content]
    assert result.possible_causes[0].source_ids == [item.id]


def test_r1_tomato_bacterial_spot_source_aliases_bind_narrowly() -> None:
    harm = source(
        "ba03-harm",
        "番茄细菌性斑疹病_百度百科",
        "番茄细菌性斑疹病是由丁香假单孢菌番茄叶斑病致病型引起的、发生在番茄的病害。主要为害叶、茎、花、叶柄和果实，尤以叶缘及未成熟果实最明显。",
    )
    cause = source(
        "ba03-cause",
        "番茄与辣椒细菌性斑点病：病原、症状、流行规律与综合防治",
        "温度：最适发病温度为25–30°C。低于15°C或高于35°C时病害发展明显受抑。",
    )
    harms = EvidenceExtractor().extract(evidence("番茄细菌性斑点病", "harms", harm))
    causes = EvidenceExtractor().extract(evidence("番茄细菌性斑点病", "possible_causes", cause))
    assert harms.harms and harms.harms[0].source_ids == [harm.id]
    assert causes.possible_causes and causes.possible_causes[0].source_ids == [cause.id]


def test_r1_tomato_bacterial_spot_section_context_stops_at_competing_heading() -> None:
    source_item = source(
        "real-source-1",
        "【小果番茄】番茄病蟲害生態與發生條件-番茄病害（二） - 農傳媒",
        "15. 細菌性斑點病《Bacterial spot》病原菌可藉種子帶菌而造成苗期感染，田間則多藉雨水傳播。"
        "16. 細菌性軟腐病《Bacterial soft rot》病害多出現於高溫高濕之夏季，較易發生。",
    )
    causes = EvidenceExtractor().extract(evidence("番茄细菌性斑点病", "possible_causes", source_item))
    assert [item.conclusion for item in causes.possible_causes] == [
        "病原菌可藉種子帶菌而造成苗期感染，田間則多藉雨水傳播。"
    ]


def _r1_n1b_snapshot(source_id: str) -> SearchSource:
    trace = Path(__file__).parents[2] / "artifacts" / "r1-n1-tomato-bacterial-spot-cause-regression-20260902" / "bundle-staging" / "browser-case" / "exact-formal-browser-case-trace.json"
    payload = json.loads(trace.read_text(encoding="utf-8"))
    item = next(item for item in payload["evidence_snapshots"] if item["source_id"] == source_id)
    return SearchSource(id=source_id, **{key: value for key, value in item.items() if key != "source_id"})


def test_r1_n1b_exact_source_1_positive_is_accepted_from_persisted_trace() -> None:
    source_item = _r1_n1b_snapshot("source-1")
    sentence = next(sentence for sentence in _sentences(source_item) if "病原菌可藉種子帶菌而造成苗期感染" in sentence)

    assert _is_tomato_bacterial_spot_section_fragment("番茄细菌性斑点病", source_item, sentence)
    assert _associate_candidate_with_target("番茄细菌性斑点病", source_item, sentence, "possible_causes") == (True, False)
    output = EvidenceExtractor().extract(evidence("番茄细菌性斑点病", "possible_causes", source_item))
    assert any("病原菌可藉種子帶菌而造成苗期感染" in item.conclusion for item in output.possible_causes)


def test_r1_n1b_exact_source_3_mixed_page_sentence_is_rejected_from_persisted_trace() -> None:
    source_item = _r1_n1b_snapshot("source-3")
    sentence = next(sentence for sentence in _sentences(source_item) if sentence.startswith("臭虫在进食过程中会传播有害微生物"))

    assert not _is_tomato_bacterial_spot_section_fragment("番茄细菌性斑点病", source_item, sentence)
    assert _associate_candidate_with_target("番茄细菌性斑点病", source_item, sentence, "possible_causes") == (False, False)
    output = EvidenceExtractor().extract(evidence("番茄细菌性斑点病", "possible_causes", source_item))
    assert not any("臭虫" in item.conclusion for item in output.possible_causes)


def test_r1_n1b_adjacent_section_boundary_contract() -> None:
    target_heading = "15. 細菌性斑點病《Bacterial spot》"
    target_cause = "病原菌可藉種子帶菌而造成苗期感染，田間則多藉雨水傳播。"
    other_heading = "16. 細菌性軟腐病《Bacterial soft rot》"
    other_cause = "病害多出現於高溫高濕之夏季，颱風後較易發生。"
    alias_heading = "番茄與辣椒細菌性斑點病"

    accept = source("adjacent-a", "番茄病害资料", f"{target_heading}\n{target_cause}")
    reject = source("adjacent-b", "番茄病害资料", f"{target_heading}\n{target_cause}\n{other_heading}\n{other_cause}")
    alias = source("adjacent-c", "番茄病害资料", f"{alias_heading}\n{target_cause}")
    unrelated = source("adjacent-d", "番茄病害资料", f"番茄晚疫病\n{other_cause}")

    assert EvidenceExtractor().extract(evidence("番茄细菌性斑点病", "possible_causes", accept)).possible_causes
    assert not any("高温高湿" in item.conclusion for item in EvidenceExtractor().extract(evidence("番茄细菌性斑点病", "possible_causes", reject)).possible_causes)
    assert EvidenceExtractor().extract(evidence("番茄细菌性斑点病", "possible_causes", alias)).possible_causes
    assert not EvidenceExtractor().extract(evidence("番茄细菌性斑点病", "possible_causes", unrelated)).possible_causes


def test_r1_public_septoria_language_contract_preserves_source_ids() -> None:
    english = (
        "Symptoms appear on the leaves as circular, tan-to-gray spots with darker brown margins "
        "and dotted with dark, raised pycnidia inside the lesion"
    )
    analysis = {
        "evidence_analysis": {
            "status": "available",
            "harms": [{"conclusion": english, "source_ids": ["source-1"]}],
            "possible_causes": [{
                "conclusion": "Warm temperatures and high humidity are favorable conditions for this disease",
                "source_ids": ["source-2"],
            }],
        },
        "evidence_snapshots": [{"source_id": "source-1", "content": english}],
    }
    public = main.public_analysis_payload(analysis)
    assert public["evidence_analysis"]["harms"][0]["conclusion"].startswith("叶片上出现")
    assert public["evidence_analysis"]["possible_causes"][0]["conclusion"] == "温暖和高湿是该病发生的有利条件。"
    assert public["evidence_analysis"]["harms"][0]["source_ids"] == ["source-1"]
    assert analysis["evidence_analysis"]["harms"][0]["conclusion"] == english


def test_r1_research_method_fragments_are_not_user_evidence() -> None:
    leafhopper = source(
        "research-leafhopper",
        "叶蝉科前人研究进展",
        "【前人研究进展】有学者对假眼小绿叶蝉的迁飞扩散行为进行了研究。",
    )
    corn = source(
        "research-corn",
        "玉米锈病数据分析方法",
        "5 数据分析方法分级计数法：玉米锈病级别病害发生程度抗性。",
    )
    causes = EvidenceExtractor().extract(evidence("叶蝉科", "possible_causes", leafhopper))
    harms = EvidenceExtractor().extract(evidence("玉米锈病", "harms", corn))
    assert causes.possible_causes == []
    assert harms.harms == []


def test_r1_unknown_public_english_is_withheld_without_losing_raw_evidence() -> None:
    english = "An untranslated English evidence sentence"
    analysis = {
        "evidence_analysis": {
            "status": "available",
            "harms": [{"conclusion": english, "source_ids": ["source-unknown"]}],
            "possible_causes": [],
        },
        "evidence_snapshots": [{"source_id": "source-unknown", "content": english}],
    }
    public = main.public_analysis_payload(analysis)
    assert public["evidence_analysis"]["harms"] == []
    assert analysis["evidence_analysis"]["harms"][0]["conclusion"] == english
