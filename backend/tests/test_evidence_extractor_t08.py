from __future__ import annotations

import pytest

from app.search.evidence_extractor import EvidenceExtractor
from app.search.models import SearchEvidence, SearchSource


def source(source_id: str, title: str, content: str, url: str) -> SearchSource:
    return SearchSource(
        id=source_id,
        title=title,
        site_name="T-07B normalized evidence fixture",
        url=url,
        content=content,
        reliability_level="其他可信农业专业站点",
    )


def evidence(class_name: str, query_type: str, item: SearchSource) -> SearchEvidence:
    return SearchEvidence(
        class_name=class_name,
        query_type=query_type,
        status="available",
        sources=[item],
    )


POSITIVE_FIXTURES = (
    (
        "玉米叶枯病",
        "harms",
        "玉米链格孢菌叶枯病是由半知菌亚门链格孢属真菌引发的玉米叶片病害，主要侵染玉米生长后期的叶片、叶鞘及苞叶。",
        "玉米链格孢菌叶枯病",
        "https://example.test/t07b/class-0-source-2",
    ),
    (
        "番茄斑枯病",
        "possible_causes",
        "病菌随病残体在土中越冬，可借雨水溅到 ... 当气温在15℃以上，遇阴雨天气，病害容易流行。",
        "作物生病不要慌，植物医生来帮忙-番茄篇（五）——番茄斑枯病",
        "https://nyncj.beijing.gov.cn/nyj/zwgk/ztgk/zwbhxx/436225712/index.html",
    ),
    (
        "南瓜白粉病",
        "harms",
        "主要侵染叶片，叶柄和茎也有发病。",
        "防治南瓜白粉病的技术",
        "https://nmj.xlgl.gov.cn/nmj/nmyw/syjs/7f5f36f9efe04d3cbc802e39ee067424/index.html",
    ),
    (
        "南瓜白粉病",
        "possible_causes",
        "该病在高温干旱与高温高湿交替环境下易暴发，适发温度为16-25℃、相对湿度80%以上。",
        "南瓜白粉病",
        "https://baike.baidu.com/item/%E5%8D%97%E7%93%9C%E7%99%BD%E7%B2%89%E7%97%85/873818",
    ),
    (
        "番茄细菌性斑点病",
        "harms",
        "番茄細菌性斑點病\n高雄農改場戴順發場長指出，番茄細菌性斑點病在連續風雨的環境中容易發生。病原細菌可透過雨水飛濺傳播，葉片在罹病初期出現水浸狀小斑點，逐漸擴大呈不規則圓形病斑，嚴重",
        "風雨過後，多加留意番茄病蟲害",
        "https://azai.tari.gov.tw/datasheet.aspx?id=t07b-class-5-source-4",
    ),
    (
        "番茄细菌性斑点病",
        "possible_causes",
        "茄細菌性斑點病Xanthomonas axonopodis pv.主要傳播途徑為種子傳播及雨水飛濺。",
        "番茄細菌性斑點病病徵與防治",
        "https://kmweb.moa.gov.tw/knowledgebase.php?func=0&type=0&id=t07b-class-5-source-2",
    ),
    (
        "盲蝽科",
        "harms",
        "其若虫和成虫通过刺吸茶树嫩梢、幼芽的汁液，造成叶片穿孔、皱缩畸形，",
        "咸宁地区主要茶树病虫——绿盲蝽",
        "https://example.test/t07b/class-10-source-5",
    ),
    (
        "盲蝽科",
        "possible_causes",
        "绿盲蝽一年发生4~5代，以卵越冬且有多种场所，在苜蓿、蒿子、蓖麻残茬内及冬枣的病残枝、剪口、多年生枣股处、有疤痕的树皮下和石榴、木槿、苹果、桃的组织内，野菜的残茬处都能找到。",
        "绿盲蝽的发生危害与常用防治药剂",
        "https://example.test/t07b/class-10-source-3",
    ),
    (
        "蝼蛄",
        "possible_causes",
        "| 冬眠阶段 | 每年11月份起，当10厘米地温降至8℃左右时，蝼蛄开始下潜越冬。",
        "蝼蛄（昆虫纲直翅目下的一科）",
        "https://baike.baidu.com/item/%E8%9E%BC%E8%9E%BA/880645",
    ),
    (
        "叶蝉科",
        "harms",
        "其危害狀如下說明：蔬菜：若蟲或成蟲在蔬菜如茄子的新芽或嫩葉上吸食植物汁液，新芽受害輕者嫩葉皺縮變黃，嚴重者嫩葉無法展開焦枯如火燒狀；",
        "二點小綠葉蟬",
        "https://azai.tari.gov.tw/datasheet.aspx?id=t07b-class-12-source-3",
    ),
    (
        "叶蝉科",
        "possible_causes",
        "叶蝉科的种类一年发生多代，如在关中大青叶蝉3代，棉叶蝉4代。",
        "叶蝉科_百度百科",
        "https://baike.baidu.com/item/%E5%8F%B6%E8%9D%89%E7%A7%91/5481132",
    ),
    (
        "蝗总科",
        "harms",
        "by L Zhang · 2020 · Cited by 7 — 蝗虫是全世界范围内的重大害虫,自人类文. 明以来,蝗虫就是最为严重的害虫,给农业生产. 带来极大危害。",
        "蝗虫的发生与防控",
        "https://www.cabidigitallibrary.org/doi/pdf/10.5555/20219832537",
    ),
)


@pytest.mark.parametrize("class_name,query_type,content,title,url", POSITIVE_FIXTURES)
def test_t08_preserved_evidence_positive_fixture(
    class_name: str,
    query_type: str,
    content: str,
    title: str,
    url: str,
) -> None:
    item = source("source-1", title, content, url)
    result = EvidenceExtractor().extract(evidence(class_name, query_type, item))
    conclusions = result.harms if query_type == "harms" else result.possible_causes
    expected = content
    if class_name == "番茄细菌性斑点病" and query_type == "harms":
        expected = content.split("。", 1)[1]
    if class_name == "番茄斑枯病" and query_type == "possible_causes":
        expected = content.split("...", 1)[1].strip()
    assert [conclusion.conclusion for conclusion in conclusions] == [expected]
    assert conclusions[0].source_ids == ["source-1"]


@pytest.mark.parametrize(
    "class_name,content,title",
    (
        ("马铃薯早疫病", "避免与茄科作物连作，实行轮作倒茬，减少病原菌积累。", "马铃薯早疫病发生与防治"),
        ("番茄斑枯病", "合理密植可减轻病害发生，加强管理有利于控制病害。", "番茄斑枯病防治方法"),
    ),
)
def test_t08_management_advice_never_becomes_possible_cause(
    class_name: str,
    content: str,
    title: str,
) -> None:
    item = source("source-management", title, content, "https://example.test/management")
    result = EvidenceExtractor().extract(evidence(class_name, "possible_causes", item))
    assert result.possible_causes == []


@pytest.mark.parametrize(
    "class_name,content,title",
    (
        ("番茄斑枯病", "研究表明，高温高湿有利于番茄斑枯病发生。", "番茄斑枯病发生规律研究"),
        ("玉米叶枯病", "采用处理后可降低病斑大小，试验结果显示防效明显。", "玉米叶枯病药效试验"),
    ),
)
def test_t08_research_results_are_not_user_facing_evidence(
    class_name: str,
    content: str,
    title: str,
) -> None:
    item = source("source-research", title, content, "https://example.test/research")
    result = EvidenceExtractor().extract(evidence(class_name, "possible_causes", item))
    assert result.possible_causes == []
    assert result.harms == []


@pytest.mark.parametrize(
    "content",
    (
        "本研究发现，高温高湿有利于番茄斑枯病发生。",
        "试验结果显示，番茄斑枯病发病率在处理组中下降。",
        "调查结果表明，不同处理之间的防效存在差异。",
        "相关性分析显示，湿度与叶蝉科发生相关。",
        "发病率测定结果显示，接种试验后的病斑扩大。",
    ),
)
def test_t08_research_result_vocabulary_remains_excluded(content: str) -> None:
    item = source("source-research-vocabulary", "番茄斑枯病发生规律研究", content, "https://example.test/research-vocabulary")
    result = EvidenceExtractor().extract(evidence("番茄斑枯病", "possible_causes", item))
    assert result.harms == []
    assert result.possible_causes == []


def test_t08_class_0_southern_corn_leaf_blight_paper_is_rejected() -> None:
    item = source(
        "source-4",
        "臘狀芽孢桿菌誘導玉米系統性抗葉枯病之機制研究 = The mechanism study of Bacillus cereus-induced systemic resistance against southern corn leaf blight｜Airiti Library 華藝線上圖書館",
        "南方玉米葉枯病由病原真菌Cochliobolus heterostrophus所引起，其孢子可藉空氣傳播，玉米受到感染後，病斑可快速擴展相連致使葉片枯死，對產量有顯著影響，目前以抗病品種或施用錳乃浦藥劑為主要防治方式。其次，探討植物荷爾蒙誘導物及荷爾蒙生合成抑制劑對玉米葉枯病罹病程度的影響，發現外施乙烯生合成抑制劑艾微激素能降低感染葉枯病之病斑大小；",
        "https://www.airitilibrary.com/Article/Detail/U0001-1908201513570000",
    )
    result = EvidenceExtractor().extract(evidence("玉米叶枯病", "harms", item))
    assert result.harms == []
    assert result.possible_causes == []


@pytest.mark.parametrize(
    "class_name,content,title",
    (
        ("马铃薯早疫病", "Potato late blight causes lesions and yield loss.", "Potato late blight symptoms"),
        ("盲蝽科", "蝗虫刺吸叶片，造成坏死和畸形。", "盲蝽科发生与危害"),
    ),
)
def test_t08_wrong_entity_does_not_cross_bind(
    class_name: str,
    content: str,
    title: str,
) -> None:
    item = source("source-wrong-entity", title, content, "https://example.test/wrong-entity")
    result = EvidenceExtractor().extract(evidence(class_name, "harms", item))
    assert result.harms == []
    assert result.possible_causes == []


def test_t08_leading_fragment_does_not_become_a_cause() -> None:
    item = source(
        "source-fragment",
        "Detection of Alternaria solani during potato early blight",
        "A complete context before the excerpt. [...] and rainy weather increase the possibility of an outbreak.",
        "https://example.test/fragment",
    )
    result = EvidenceExtractor().extract(evidence("马铃薯早疫病", "possible_causes", item))
    assert result.possible_causes == []


@pytest.mark.parametrize(
    "fragment",
    ("and rainy weather increase the possibility of an outbreak.", "because humidity is high, disease occurrence increases."),
)
def test_t08_obvious_english_continuation_fragment_is_rejected(fragment: str) -> None:
    item = source(
        "source-fragment-2",
        "Detection of Alternaria solani during potato early blight",
        fragment,
        "https://example.test/fragment-2",
    )
    result = EvidenceExtractor().extract(evidence("马铃薯早疫病", "possible_causes", item))
    assert result.possible_causes == []


@pytest.mark.parametrize(
    "class_name,query_type,content,title",
    (
        (
            "番茄细菌性斑点病",
            "possible_causes",
            "番茄细菌性斑点病防治研究与喷施试验表明，温暖高湿高降雨量有利于病害发生。",
            "番茄细菌性斑点病防治研究与喷施试验",
        ),
        (
            "盲蝽科",
            "harms",
            "摘要：[目的]测定盲蝽科防御酶活力，研究盲蝽科危害水平。",
            "盲蝽科防御酶活性研究",
        ),
        (
            "叶蝉科",
            "possible_causes",
            "不种植叶蝉科寄主作物，以免发生危害。",
            "叶蝉科管理建议",
        ),
        (
            "蝗总科",
            "harms",
            "病原真菌感染蝗虫，导致蝗虫死亡。",
            "蝗虫天敌与病原体",
        ),
    ),
)
def test_t08_live_pollution_signals_are_not_user_facing_evidence(
    class_name: str,
    query_type: str,
    content: str,
    title: str,
) -> None:
    item = source("source-live-pollution", title, content, "https://example.test/live-pollution")
    result = EvidenceExtractor().extract(evidence(class_name, query_type, item))
    assert result.harms == []
    assert result.possible_causes == []
