"""Deterministic, extractive summaries for normalized external evidence.

This module deliberately performs no model inference and never invents text.  A
visible conclusion is always a sentence taken from one accepted source and is
linked to that source's stable ID.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from ..catalog import CLASS_CATALOG
from ..taxonomy import OFFICIAL_CLASS_CATALOG
from .models import SearchEvidence, SearchSource


ShortText = Field(min_length=1, max_length=220)
Section = Literal["harms", "possible_causes"]


class ExternalEvidenceConclusion(BaseModel):
    conclusion: str = ShortText
    source_ids: list[str] = Field(min_length=1, max_length=1)


class ExternalEvidenceAnalysis(BaseModel):
    status: Literal["available", "unavailable"] = "unavailable"
    harms: list[ExternalEvidenceConclusion] = Field(default_factory=list, max_length=2)
    possible_causes: list[ExternalEvidenceConclusion] = Field(default_factory=list, max_length=2)


_HTML = re.compile(r"<[^>]+>")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_BRACKET_ELLIPSIS = re.compile(r"\[\s*(?:\.{3}|…+)\s*\]")
_REFERENCE_MARK = re.compile(r"\[\s*\d+(?:\s+\d+)*\s*\]")
_SPACED_LATIN_PAREN = re.compile(r"\(\s*(?:[A-Za-z]\s+){5,}[A-Za-z]\s*\)")
_CJK_GAP = re.compile(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])")
_SPACE_BEFORE_CJK_PUNCT = re.compile(r"\s+(?=[，。；：！？、])")
_SPACE_AFTER_CJK_PUNCT = re.compile(r"(?<=[，。；：！？、])\s+")
_SPACE = re.compile(r"\s+")
_OMISSION_PATTERN = r"(?:\[\s*(?:\.{3,}|…+)\s*\]|\.{3,}|…+)"
_OMISSION_MARK = re.compile(_OMISSION_PATTERN)
_SENTENCE = re.compile(rf"(?<=[。！？；!?])|\n+|(?<=[a-z0-9\)])\.\s+(?=[A-Z])|{_OMISSION_PATTERN}")
_TRAILING_OMITTED_CONNECTOR = re.compile(r",\s*of\s*$", re.IGNORECASE)
_OBVIOUS_LEADING_FRAGMENT = re.compile(r"^(?:and|or|but|because|which|cereus|under)\b", re.IGNORECASE)
_LEADING_NUMBERED_LABEL = re.compile(
    r"^(?:(?:\d+(?:[.．]\d+)*)[\s、．.]*){1,4}"
    r"(?=(?:为害症状|危害症状|发生规律|流行规律|发生条件|发病条件|药效试验|施药方法|试验方法|试验设计))"
)
_LEADING_SECTION_LABEL = re.compile(r"^(?:为害症状|危害症状|发生规律|流行规律|发生条件|发病条件)\s*[:：]?\s*")
_TOMATO_BACTERIAL_SPOT_HEADING = re.compile(
    r"^\d+[.．]\s*(?:細菌性斑點病|细菌性斑点病)(?:《[^》]*》)?\s*"
)
_TOC_NUMBERED_SECTION = re.compile(
    r"(?:^|\|)\s*\d+(?:[.．]\d+)?\s*(?="
    r"基本信息|基本简介|为害症状|危害症状|危害特点|病原形态特征|"
    r"传播途径|发病条件|发生规律|流行规律|防治方法|农业防治|化学防治)"
)
_NOISE = ("首页", "导航", "版权", "相关阅读", "上一篇", "下一篇", "上一页", "下一页", "登录", "注册", "cookie")
_BOILERPLATE_MARKERS = (
    "订阅更新", "使用百度前必读", "百科协议", "隐私政策", "版权声明", "网站地图",
    "责任编辑", "京ICP备", "京公网安备", "公安网备", "登录", "注册", "相关推荐", "相关阅读",
)
_SECTION_LABELS = frozenset({"目录", "病原特征", "为害症状", "侵染循环", "流行规律", "防治方法", "农业防治", "化学防治"})
_TOKENS: dict[Section, tuple[str, ...]] = {
    "harms": ("危害", "为害", "症状", "损害", "损伤", "受损", "咬食", "受害", "枯萎", "死亡", "减产", "病斑", "失绿", "腐烂", "黄化", "倒伏", "枯死", "symptom", "lesion", "necrosis", "defoliation", "yield loss", "damage"),
    "possible_causes": ("发生", "发病", "原因", "条件", "高温", "高湿", "降雨", "湿度", "土壤", "连作", "幼虫", "传播", "虫源", "condition", "humidity", "temperature", "rain", "soil", "pathogen", "favorable"),
}
_CAUSE_MARKERS = ("原因", "条件", "有利于", "易发生", "喜发生", "促进", "导致", "相关", "病原", "虫源")
_CONTROL_DIFFICULTY_CAUSE_PATTERN = re.compile(
    r"(?:这就是|这也是|这也正是|因此(?:也)?是).{0,32}"
    r"(?:很难|难以|难)(?:彻底)?(?:根除|防治|控制|消灭).{0,12}原因"
    r"|(?:根除|防治|控制|消灭).{0,10}(?:很难|困难|难以).{0,8}原因"
)
_ENGLISH_CAUSE_MARKER = re.compile(r"\b(?:conditions?|favo(?:u)?rable|caus(?:e|es|ed)|lead(?:s|ing)?\s+to|result(?:s|ing)?\s+in|increase(?:s|d)?|promote(?:s|d)?|outbreak)\b", re.IGNORECASE)
_CHINESE_ECOLOGICAL_CAUSE_PATTERN = re.compile(
    r"(?:土壤温湿度|土壤含水量|土壤温度|土壤湿度|温湿度|温度|湿度|降雨|雨水|气候|土壤条件|虫源|越冬条件)"
    r".{0,24}(?:影响着?|适合|有利于|利于|促进)"
    r".{0,24}(?:发生|活动|幼虫活动|出土|盛发|生存|繁殖|发育|越冬)",
)
_RESEARCH_METHOD_MARKERS = (
    "拮抗菌筛选", "筛选鉴定", "发酵条件优化", "菌株筛选", "培养条件优化",
    "生防菌开发", "线粒体基因组特征分析", "实验设计", "前人研究进展",
    "数据分析方法", "分级计数法",
)
_RESEARCH_METHOD_PATTERN = re.compile(
    r"(?:拮抗菌(?:株)?(?:的)?(?:筛选|鉴定)|发酵条件.{0,8}优化|"
    r"菌株筛选|培养条件.{0,8}优化|生防菌.{0,8}(?:开发|应用)|"
    r"线粒体基因组特征分析|实验设计|单因素试验|正交试验|"
    r"\b(?:detection|detecting|rna-based|qpcr|keywords?|primer|isolates?|specificity|our\s+work|sensitive|accurate|diagnosis|"
    r"experimental\s+design|orthogonal\s+experiments?|(?:fermentation|culture)\s+conditions?.{0,24}optimization|"
    r"optimization\s+of\s+(?:fermentation|culture)\s+conditions?|(?:[A-Z]:\s*)?No\.\s*\d+\s+(?:fermentation|culture)\s+conditions?|"
    r"screening[\s，,]+identification(?:\s+and)?|"
    r"(?:existing|new|novel)\s+methods?|sample\s+size|(?:urgent\s+need|need)\s+to\s+develop\s+(?:a|an|the)\s+method)\b)",
    re.IGNORECASE,
)
_RESEARCH_RESULT_PATTERN = re.compile(
    r"(?:(?:种群密度|扩散系数|分布型).{0,24}(?:分析|模型).{0,24}(?:表明|显示|指出)|(?:模型分析|参数分析|相关性分析).{0,24}(?:结果)?(?:表明|显示|指出)|"
    r"研究表明|研究发现|研究结果(?:表明|显示|指出)|本研究.{0,48}(?:发现|指出|显示|探讨)|相关研究|调查结果|试验结果(?:表明|显示|指出)?|相关性分析|防效|发病率测定|测定结果|接种试验|"
    r"不同处理|处理组|机制研究|機制研究|探讨.{0,36}(?:机制|影响)|外施.{0,28}(?:抑制剂|激素)|"
    r"基因微阵列|酵素活性测试|基因表达分析|显微(?:层次)?(?:观察|检查|分析)|高通量测序|拮抗作用|加入拮抗菌|"
    r"防御酶(?:活性|活力)|酶活性(?:变化|表现|活力)?|生理指标|喷施.{0,24}(?:处理|后)|处理后.{0,32}(?:防效|病斑|活性|变化|死亡率|抑制)|"
    r"\b(?:suppression|efficacy|effect(?:s)?|control).{0,72}\b(?:spray|sprays|foliar|treatment|application|greenhouse|field)\b|"
    r"\b(?:mechanism\s+study|this\s+research|research\s+attempts?|gene\s+expression\s+analysis|"
    r"microscop(?:ical|y)\s+(?:examination|analysis)|experimental\s+results?|study\s+found|"
    r"inoculat(?:ed|ion)|treated\s+(?:group|plants?)|treatment\s+group|investigat(?:e|ed|ing))\b)",
    re.IGNORECASE,
)
_RESEARCH_INTERVENTION_PATTERN = re.compile(
    r"(?:研究|试验|实验).{0,24}(?:喷施|施药|药剂|处理)|"
    r"(?:喷施|施药|药剂|处理).{0,24}(?:研究|试验|实验)",
    re.IGNORECASE,
)
_RESEARCH_ABSTRACT_PATTERN = re.compile(
    r"(?:摘要|目的|结果|测定|酶活力|含水量|蛋白质|糖原).{0,36}(?:研究|试验|测定|分析|活力)",
    re.IGNORECASE,
)
_RESEARCH_TITLE_PATTERN = re.compile(
    r"(?:机制研究|機制研究|防御酶|防禦酶|酶活性|酵素活性|生理指标|生理指標|相关性分析|相關性分析|"
    r"测定|測定|试验|試驗|experimental|efficacy|suppression|foliar\s+spray)",
    re.IGNORECASE,
)
_RESEARCH_METADATA_PATTERN = re.compile(
    r"(?:作者简介|收稿日期|修回日期|摘要\s*[:：]|【(?:目的|方法|结果|结论)】|模型分析|"
    r"本期.{0,64}(?:专题.{0,16}形式)?集中发表.{0,16}论文|(?:\d+\s*篇)?论文各有侧重|"
    r"\[[Jj]\]|\b(?:abstract|methods?|results?|conclusions?)\b)",
    re.IGNORECASE,
)
_RELIABILITY = {"政府农业部门": 5, "农业科研院所": 4, "高校农学院/植保学院": 3, "农技推广/植保机构": 3, "权威农业数据库": 2, "其他可信农业专业站点": 1}
_HARM_ACTIONS = ("咬食", "取食", "侵染", "蛀食", "吸食", "危害根", "危害叶", "为害根", "为害叶", "infect", "feed", "feeding")
_HARM_EFFECTS = ("死亡", "枯萎", "腐烂", "黄化", "病斑", "根系损伤", "叶片受损", "减产", "品质下降", "倒伏", "损伤", "受损", "缺苗", "生长受阻", "枯死", "断裂", "lesion", "necrosis", "defoliation", "yield loss", "damage", "damaging", "wilt")
_EXPERIMENT_METHOD_MARKERS = ("药效试验", "施药方法", "试验方法", "试验设计", "试验处理", "处理设置", "小区试验")
_EXPERIMENT_CONTEXT_MARKERS = ("土壤类型", "栽培条件", "管理水平", "小区", "重复", "对照", "施药")
_MANAGEMENT_ADVICE_MARKERS = ("适时灌溉", "合理施肥", "增施", "腐熟肥", "防治措施", "防治技术措施", "防治方法", "农业防治", "化学防治", "生物防治", "物理防治", "药剂防治", "拌种", "喷药", "喷施", "用药", "抗虫能力", "抗病能力", "壮苗")
_MANAGEMENT_ADVICE_PATTERN = re.compile(
    r"^\s*(?:避免|实行|采用|采取|清除|及时|加强(?:管理|防治)?|选用|不要|建议|"
    r"合理(?:密植|施肥|灌溉|浇水)|喷药|喷施|减少(?:病原菌|病残体|初侵染源)|"
    r"spot[- ]check|monitor|inspect|scout)|轮作倒茬",
    re.IGNORECASE,
)
_MANAGEMENT_IMPERATIVE_PATTERN = re.compile(
    r"^\s*.{0,24}?(?:不种植|不宜(?:种植|栽培)?|不应(?:种植|栽培)?|避免(?:种植|栽培)?|应避免|建议|应及时|及时清除|加强(?:管理|防治)?|"
    r"防治|防止|预防|可采取|可使用|应采取|采取措施|以免|从而避免|以防|喷施|用药|施药|清除病残体|合理轮作|轮作防治|消灭虫源)"
    r"|^\s*.{0,24}?(?:减少|控制).{0,80}(?:危害|发生|病原|虫源|病害)"
    r"|^\s*(?:要|应|需).{0,40}(?:掌握|了解|熟悉)",
    re.IGNORECASE,
)
_MANAGEMENT_PURPOSE_PATTERN = re.compile(
    r"(?:因此|所以|从而|有助于|有利于).{0,48}(?:对|于).{0,24}(?:控制|防控|防治|管理).{0,24}"
    r"(?:至关重要|很重要|重要|必要|有效)",
    re.IGNORECASE,
)
_MANAGEMENT_ACTION_PATTERN = re.compile(
    r"(?:悬挂|诱杀|诱捕|清除|施用|喷施|选用|采用|利用|栽植|轮作).{0,64}"
    r"(?:防治|防控|控制|减少|降低|消灭|虫源|危害|发生)",
    re.IGNORECASE,
)
_INTERVENTION_EFFECT_PATTERN = re.compile(
    r"(?:春播前|播前).{0,24}(?:浇灌|灌溉|浇水)|"
    r"(?:浇灌|灌溉|浇水).{0,48}(?:死亡率|生存不利|减轻.{0,8}危害)|"
    r"(?:施用|使用|采用|采取|处理).{0,28}(?:可|能够|有利于|导致|减轻|增强).{0,36}(?:死亡|危害|抗虫|抗病|病害)|"
    r"(?:改善|改良)土壤.{0,48}(?:抗虫性|抗病性|减轻.{0,8}危害)|"
    r"(?:腐熟的?有机肥|有机肥).{0,56}(?:增强.{0,8}抗虫性|减轻.{0,8}危害|改良土壤)|"
    r"(?:irrigation|watering|treatment|application|control\s+measures?).{0,80}(?:mortality|death|reduce|decrease|control)",
    re.IGNORECASE,
)
_STRONG_CAUSAL_MARKERS = ("导致", "诱发", "易发生", "有利于", "盛发", "高发", "发生严重")
_PESTICIDE_MECHANISM_PATTERN = re.compile(
    r"(?:氟啶虫酰胺|杀虫剂|杀菌剂|农药|药剂|有效成分|insecticide|pesticide|fungicide|flonicamid)"
    r".{0,100}(?:阻止|抑制|停止|药效|防效|死亡率|因饥饿而死亡|mortality|efficacy)|"
    r"(?:阻止|抑制|停止|药效|防效|死亡率|因饥饿而死亡|mortality|efficacy)"
    r".{0,100}(?:氟啶虫酰胺|杀虫剂|杀菌剂|农药|药剂|有效成分|insecticide|pesticide|fungicide|flonicamid)",
    re.IGNORECASE,
)
_NON_OCCURRENCE_CAUSE_PATTERN = re.compile(
    r"(?:难治|难以防治|防治困难|难以控制|难防治|防控困难|防治效果差|药效.{0,8}(?:差|不佳|低)|"
    r"difficult\s+to\s+control|hard\s+to\s+control)",
    re.IGNORECASE,
)
_LIFECYCLE_NARRATIVE_PATTERN = re.compile(
    r"(?:生殖|繁殖|产卵|卵期|幼虫|蛹期|羽化|越冬|世代|寿命|生活史|生活周期|"
    r"无翅|有翅|后代|生长季.{0,16}(?:孤雌|生殖|繁殖))"
)
_EXPLICIT_ECOLOGICAL_DRIVER_PATTERN = re.compile(
    r"(?:温度|湿度|气温|降雨|雨水|土壤|环境|气候|季节|营养条件).{0,24}"
    r"(?:影响|适宜|适合|有利|导致|促进|升高|降低|回升|下降|降至|升至)|"
    r"(?:高温|干旱|温暖).{0,24}(?:繁殖(?:速度)?更快|繁殖能力增强|种群(?:数量)?(?:增加|增长|暴发))|"
    r"(?:回升|降至|升至).{0,24}(?:开始|迁飞|扩散|越冬|出土|盛发|发生|活动|繁殖)|"
    r"(?:影响|适宜|适合|有利于|导致|促进).{0,24}(?:发生|迁飞|扩散|越冬|盛发|虫源|种群|繁殖|活动|危害)|"
    r"(?:活动|发生|繁殖|出土|迁飞|扩散).{0,24}(?:与|受).{0,24}(?:条件|影响|有关)|"
    r"(?:越冬|卵越冬).{0,36}(?:场所|残茬|病残枝|剪口|树皮|组织|寄主|栖息|找到|发现)"
)
_CAUSE_CONTEXT_MARKERS = ("发生条件", "发病条件", "发生规律", "流行规律", "发生原因", "高温", "低温", "温度", "高湿", "湿度", "降雨", "雨水", "积水", "土壤", "连作", "密植", "通风", "虫源", "病原", "传播", "虫卵", "成虫", "有利于", "易发生", "盛发", "高发", "because", "increase", "favorable")

# Matching-only normalization for source text. Raw/persisted evidence stays
# verbatim; only conservative token/entity matching sees this translation.
_MATCH_TRADITIONAL_TO_SIMPLIFIED = str.maketrans({
    "細": "细", "點": "点", "軟": "软",
    "於": "于", "發": "发", "乾": "干", "氣": "气", "溫": "温", "濕": "湿",
    "與": "与", "傳": "传", "飛": "飞", "濺": "溅", "適": "适",
    "葉": "叶", "現": "现", "狀": "状", "徵": "征", "為": "为", "蟲": "虫",
    "農": "农", "業": "业", "區": "区", "嚴": "严",
})


def _normalize_pdf_width(value: str) -> str:
    result: list[str] = []
    for char in value:
        code = ord(char)
        if 0xFF10 <= code <= 0xFF19 or 0xFF21 <= code <= 0xFF3A or 0xFF41 <= code <= 0xFF5A or char in "（）［］．":
            result.append(chr(code - 0xFEE0))
        else:
            result.append(char)
    return "".join(result)


def _plain_text(value: str) -> str:
    value = html.unescape(_HTML.sub(" ", value))
    value = _normalize_pdf_width(value)
    value = _BRACKET_ELLIPSIS.sub(" ", value)
    value = _CONTROL.sub(" ", value)
    value = _REFERENCE_MARK.sub(" ", value)
    value = _SPACED_LATIN_PAREN.sub(" ", value)
    value = _CJK_GAP.sub("", value)
    value = _SPACE_BEFORE_CJK_PUNCT.sub("", value)
    value = _SPACE_AFTER_CJK_PUNCT.sub("", value)
    return _SPACE.sub(" ", value).strip()


def _strip_pdf_heading_prefix(text: str) -> str:
    if not re.match(r"^\d", text):
        return text
    cycle_index = text.find("病害循环")
    if cycle_index < 0 or cycle_index > 160 or "发生规律" not in text[:cycle_index]:
        return text
    remainder = text[cycle_index + len("病害循环"):].lstrip(" \t:：-—")
    return remainder if len(remainder) >= 12 else text


def _clean_candidate_fragment(value: str) -> str:
    text = _plain_text(value)
    text = _TRAILING_OMITTED_CONNECTOR.sub("", text)
    text = _LEADING_NUMBERED_LABEL.sub("", text)
    text = _LEADING_SECTION_LABEL.sub("", text)
    text = _TOMATO_BACTERIAL_SPOT_HEADING.sub("", text)
    return _strip_pdf_heading_prefix(text).strip()


def _is_experimental_method_fragment(value: str) -> bool:
    text = _plain_text(value)
    if (
        _RESEARCH_METHOD_PATTERN.search(text)
        or _RESEARCH_RESULT_PATTERN.search(text)
        or _RESEARCH_INTERVENTION_PATTERN.search(text)
        or _RESEARCH_ABSTRACT_PATTERN.search(text)
    ):
        return True
    if any(marker in text for marker in (*_EXPERIMENT_METHOD_MARKERS, *_RESEARCH_METHOD_MARKERS)):
        return True
    return "试验" in text and any(marker in text for marker in _EXPERIMENT_CONTEXT_MARKERS)


def _is_research_context_fragment(source: SearchSource, sentence: str) -> bool:
    """Reject narrow research-result contamination signalled by the source title."""
    if _is_experimental_method_fragment(sentence) or _RESEARCH_METADATA_PATTERN.search(sentence):
        return True
    title = _plain_text(source.title)
    return bool(_RESEARCH_TITLE_PATTERN.search(title) and _RESEARCH_RESULT_PATTERN.search(sentence))


def _is_management_advice_fragment(value: str) -> bool:
    text = _plain_text(value)
    if re.search(r"\b(?:control|threshold|insecticide|pre[- ]harvest interval|pyrethroid|spinosad|spray|application)\b", text, re.IGNORECASE):
        return True
    if (
        _MANAGEMENT_ADVICE_PATTERN.search(text)
        or _MANAGEMENT_IMPERATIVE_PATTERN.search(text)
        or _MANAGEMENT_PURPOSE_PATTERN.search(text)
        or _MANAGEMENT_ACTION_PATTERN.search(text)
    ):
        return True
    is_advice = (
        bool(_INTERVENTION_EFFECT_PATTERN.search(text))
        or any(marker in text for marker in _MANAGEMENT_ADVICE_MARKERS)
    )
    return is_advice and not any(marker in text for marker in _STRONG_CAUSAL_MARKERS)


def _is_pesticide_mechanism_fragment(value: str) -> bool:
    return bool(_PESTICIDE_MECHANISM_PATTERN.search(_plain_text(value)))


def _is_harm_only_fragment(value: str) -> bool:
    text = _plain_text(value)
    harm_like = any(marker in text for marker in _HARM_ACTIONS) or any(marker in text for marker in _HARM_EFFECTS)
    return harm_like and not any(marker in text for marker in _CAUSE_CONTEXT_MARKERS)


def _has_cause_marker(sentence: str) -> bool:
    sentence = sentence.translate(_MATCH_TRADITIONAL_TO_SIMPLIFIED)
    return (
        any(marker in sentence for marker in _CAUSE_MARKERS)
        or bool(_CHINESE_ECOLOGICAL_CAUSE_PATTERN.search(sentence))
        or bool(_ENGLISH_CAUSE_MARKER.search(sentence))
    )


def _is_obvious_leading_fragment(value: str) -> bool:
    return bool(_OBVIOUS_LEADING_FRAGMENT.search(value.strip()))


def _is_obvious_toc_fragment(value: str) -> bool:
    text = _plain_text(value)
    if text.startswith(("目录", "导航")):
        return True
    return text.count("|") >= 2 and len(_TOC_NUMBERED_SECTION.findall(text)) >= 2


def _is_leading_fragment(value: str) -> bool:
    """Identify a likely lower-case continuation only for paired duplicate checks."""
    return bool(re.match(r"^[a-z]", value.strip()))


def _normalized(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.translate(_MATCH_TRADITIONAL_TO_SIMPLIFIED)).lower()


_CLASS_EXTRA_ALIASES = {
    "水稻稻瘟病": ("稻瘟病", "rice blast", "Magnaporthe oryzae", "Pyricularia oryzae"),
    "水稻褐斑病": ("褐斑病", "rice brown spot", "brown spot", "brown spot of rice", "Bipolaris oryzae"),
    "玉米大斑病": ("大斑病", "northern corn leaf blight", "Exserohilum turcicum"),
    "水稻东格鲁病毒病": ("东格鲁病", "tungro", "rice tungro", "tungro virus", "rice tungro virus"),
    "玉米灰斑病": ("灰斑病", "gray leaf spot", "gray leaf spot of corn", "corn gray leaf spot", "Cercospora zeae-maydis"),
    "玉米叶枯病": ("玉米链格孢菌叶枯病",),
    # The frozen knowledge entity explicitly documents 斑疹病 as the
    # maintained Tomato bacterial speck wording; the second alias is the
    # exact title returned by the current formal HuizaoBio source.
    "番茄细菌性斑点病": ("番茄細菌性斑點病", "番茄细菌性斑疹病", "番茄与辣椒细菌性斑点病"),
    "马铃薯早疫病": ("Alternaria solani",),
    "盲蝽科": ("绿盲蝽", "条赤须盲蝽", "牧草盲蝽", "棉盲蝽"),
    "叶蝉科": ("叶蝉", "葉蝉", "葉蟬", "大青叶蝉", "扁喙叶蝉", "二点小绿叶蝉", "二點小綠葉蟬", "假眼小绿叶蝉"),
    "蝗总科": (),
}
_CLASS_ALIASES = {
    _normalized(item["name_zh"]): tuple(sorted({_normalized(item["name_zh"]), _normalized(item["name_en"]), *(_normalized(alias) for alias in _CLASS_EXTRA_ALIASES.get(item["name_zh"], ()))}, key=len, reverse=True))
    for item in (*CLASS_CATALOG, *OFFICIAL_CLASS_CATALOG)
}
_CLASS_SUBTYPES = {
    # The legacy catalog contains 豆芫菁 as a separate leaf label, while the
    # current official taxonomy uses the broader 芫菁 family-level identity.
    "芫菁": {"豆芫菁"},
}


def _mentions_target_or_subtype(mentioned: set[str], target: str) -> bool:
    allowed = {target, *(_normalized(item) for item in _CLASS_SUBTYPES.get(target, set()))}
    return bool(mentioned & allowed) and mentioned <= allowed


_CLASS_SECTION_ALIASES = {
    ("蝗总科", "harms"): ("蝗虫", "蚱蜢"),
    ("蝗总科", "possible_causes"): ("蝗虫", "蚱蜢"),
}

_WRONG_ENTITY_MARKERS = {
    "水稻褐斑病": ("narrow brown spot", "narrow brown leaf spot", "rice cercospora leaf spot", "sphaerulina oryzina", "cercospora janseana"),
    "玉米叶枯病": ("南方玉米叶枯病", "南方玉米葉枯病", "southern corn leaf blight", "cochliobolus heterostrophus", "sclb"),
}
_CLASS_HARM_PATTERNS = {
    "水稻褐斑病": re.compile(r"(?:褐斑|brown spot|lesion|病斑).{0,80}(?:叶片|稻穗|谷粒|产量|枯死|leaf|grain|yield|damage|damaging)"),
    "水稻东格鲁病毒病": re.compile(
        r"(?:矮化|黄化|分蘖|穗|籽粒|stunt(?:ing)?|yellow|tiller(?:ing)?|panicles?|grain|yield)"
        r".{0,80}(?:水稻|东格鲁|rice|tungro|reduction|loss|sterile)"
        r"|(?:水稻东格鲁病毒病|东格鲁|rice\s+tungro|tungro)"
        r".{0,100}(?:矮化|黄化|分蘖|穗|籽粒|stunt(?:ing)?|yellow|tiller(?:ing)?|panicles?|grain|yield|reduction|loss|sterile)",
        re.IGNORECASE,
    ),
    "玉米灰斑病": re.compile(
        r"(?:灰斑|gray leaf spot|lesions?|病斑).{0,100}"
        r"(?:叶片|枯死|产量|leaf|kill|yield|damage|coalesce|blight|rectangular|elongat)",
        re.IGNORECASE,
    ),
    "芫菁": re.compile(r"(?:(?:取食|啃食|咬食|危害|为害).{0,45}(?:豆科|叶片|作物|植物|legume|leaf|crop|plant|damage|damaging)|(?:beetle|adult).{0,45}(?:feed|damage|damaging))"),
    "玉米叶枯病": re.compile(r"玉米链格孢菌叶枯病.{0,48}主要侵染.{0,36}(?:叶片|叶鞘|苞叶)"),
    "南瓜白粉病": re.compile(r"(?:主要侵染(?:叶片|叶柄|茎)|白色粉状小霉点)"),
    "盲蝽科": re.compile(r"刺吸.{0,36}(?:坏死|畸形|穿孔|皱缩|焦枯)"),
    "叶蝉科": re.compile(r"(?:刺吸|吸食).{0,48}(?:皱缩|变黄|黄化|焦枯|受害)"),
    "蝗总科": re.compile(r"(?:重大害虫|极大危害|吃掉大量.{0,24}植物枝叶)"),
}
_CLASS_CAUSE_PATTERNS = {
    "蚜虫": re.compile(
        r"蚜虫.{0,96}(?:高温|干旱|温暖).{0,36}(?:繁殖速度|繁殖|种群数量|暴发).{0,16}(?:更快|增加|增长|爆发)?"
        r"|(?:高温|干旱|温暖).{0,36}蚜虫.{0,36}(?:繁殖速度|繁殖|种群数量|暴发)"
    ),
    "水稻稻瘟病": re.compile(r"(?:稻瘟病|rice blast).{0,70}(?:发生|发病|流行|爆发|传播).{0,80}(?:条件|温度|湿度|降雨|湿润|病原|菌源|品种|孢子)|(?:菌源|病原菌|叶面湿润|高湿度).{0,60}(?:稻瘟病|rice blast|发生|传播|发病)"),
    "水稻褐斑病": re.compile(r"(?:高相对湿度|湿度|温度|降雨|叶片湿|病残体|带菌种子|种子).{0,60}(?:发生|发病|传播|流行|有利|感染)|(?:发生|发病).{0,60}(?:温度|湿度|降雨|土壤|肥力)|(?:disease can develop|high relative humidity|temperature between).{0,100}(?:humidity|temperature|soil|infection|develop)"),
    "玉米大斑病": re.compile(r"(?:温度|雨水|湿度|病残体|分生孢子|气流|传播).{0,60}(?:发生|发病|流行|决定|传播|有利)|(?:发病|发生).{0,60}(?:温度|雨水|湿度|病残体)"),
    "水稻东格鲁病毒病": re.compile(
        r"(?:叶蝉|病毒源|感染水稻|媒介|传播).{0,60}(?:传播|感染|发生|发病|取食|媒介)"
        r"|(?:incidence|transmit(?:ted|s|ting)?|vector|leafhoppers?).{0,80}(?:tungro|virus|plant|rice)"
        r"|(?:水稻东格鲁病毒病|东格鲁|rice\s+tungro|tungro)"
        r".{0,100}(?:叶蝉|leafhoppers?|媒介|vector|transmit(?:ted|s|ting)?|传播|感染)",
        re.IGNORECASE,
    ),
    "玉米灰斑病": re.compile(
        r"(?:温度|湿度|降雨|病残体|孢子|病原|weather|humidity|rain|residue)"
        r".{0,70}(?:发生|发病|流行|传播|有利|development|infection|disease)"
        r"|(?:disease|infection).{0,70}(?:humidity|rain|residue|temperature)"
        r"|(?:玉米灰斑病|灰斑病|gray leaf spot|Cercospora\s+zea(?:e)?-maydis)"
        r".{0,110}(?:favou?r(?:ed)?|wet|humid|weather|humidity|leaf wetness|rain|temperature|"
        r"连续种植|连作|病残体|免耕|continuous corn|reduced tillage|residue|high[- ]risk|风险)"
        r"|(?:favou?r(?:ed)?|favo[u]?rable|high[- ]risk|有利|适宜)"
        r".{0,90}(?:wet|humid|weather|humidity|leaf wetness|rain|temperature|"
        r"连续种植|连作|病残体|免耕|continuous corn|reduced tillage|residue|disease development|病害发生)",
        re.IGNORECASE,
    ),
    "芫菁": re.compile(
        r"(?:芫菁|成虫|幼虫).{0,50}(?:季节发生|出现于|发生于|越冬|温度|湿度|寄主条件|虫源|易发生|有利于)"
        r"|(?:芫菁|成虫).{0,40}(?:春季|夏季|秋季|冬季).{0,24}(?:出现|活动|群聚|成群)"
        r"|(?:芫菁|成虫).{0,40}(?:成群|群聚|群集).{0,32}(?:出没|出现|危害|取食|啃食)"
        r"|(?:beetle|adult|larva).{0,60}(?:host conditions|soil conditions|occur during|overwinter|favorable conditions)"
    ),
    "番茄斑枯病": re.compile(r"(?:病残体.{0,24}越冬|阴雨.{0,24}(?:流行|发生)|气温.{0,24}阴雨.{0,24}(?:流行|发生))"),
    "南瓜白粉病": re.compile(r"(?:高温干旱|高温高湿|高温.{0,12}高湿).{0,36}(?:易暴发|暴发|适发温度|相对湿度)|(?:秋末干季|冬季).{0,20}发生"),
    "番茄细菌性斑点病": re.compile(r"(?:传播途径|種子傳播|种子传播|雨水飞溅|雨水飛濺|适宜发病|適宜發病|最适发病温度|高湿高降雨量|高濕高降雨量|病原菌.{0,24}(?:种子|種子).{0,24}(?:污染|帶菌|带菌).{0,24}(?:传|傳播))"),
    "蝗总科": re.compile(r"(?:虫源积累|蟲源累積|降雨偏多|降雨量.{0,24}(?:影响|影響).{0,24}蝗虫|气候.{0,24}蝗虫).{0,32}(?:有关|相關|发生|發生|暴发|爆发)"),
    "豆芫菁": re.compile(
        r"(?:豆芫菁|Epicauta\s+gorhami).{0,48}(?:"
        r"一年发生[一二三四五六七八九十\d]+代|年生[一二三四五六七八九十\d]+代|"
        r"发生规律|季节发生|生活史|越冬|化蛹|羽化|成虫.{0,24}(?:出现|发生|活动))"
    ),
    "盲蝽科": re.compile(r"(?:一年发生\d+(?:~|-|～)\d+代|以卵.{0,16}越冬|气温.{0,32}相对湿度.{0,24}孵化|相对湿度.{0,24}大发生|寄主.{0,32}(?:迁飞|发生))"),
    "蝼蛄": re.compile(r"(?:地温|温度).{0,32}(?:越冬|活动|取食)|(?:潮湿土地|湿润土壤).{0,20}发生|越冬.{0,24}(?:活动|取食)"),
    "叶蝉科": re.compile(r"(?:一年发生多代|各种虫态越冬|(?:温度|湿度|气象因素).{0,36}(?:发生|繁殖)|迁飞.{0,24}(?:扩散|转移))"),
}
_REVERSE_LOCUST_HARM_PATTERN = re.compile(
    r"(?:(?:病原|真菌|细菌|病毒|寄生|天敌|捕食者|药剂|农药|处理|喷施).{0,32}蝗(?:虫|总科).{0,32}(?:感染|侵染|寄生|捕食|杀死|致死|死亡|抑制|减少|控制)|"
    r"(?:病原|真菌|细菌|病毒|寄生|天敌|捕食者|药剂|农药|处理|喷施).{0,32}(?:感染|侵染|寄生|捕食|杀死|致死|死亡|抑制|减少|控制)的?蝗(?:虫|总科)|"
    r"蝗(?:虫|总科).{0,32}(?:被|受到).{0,16}(?:病原|真菌|细菌|病毒|寄生|天敌|捕食者|药剂|农药).{0,32}(?:感染|侵染|寄生|捕食|杀死|致死|死亡|抑制|减少|控制))",
    re.IGNORECASE,
)
_LOCUST_INTERVENTION_PATTERN = re.compile(
    r"(?:人类活动.{0,32}(?:蝗虫|发生|生境|作用|关系)|"
    r"(?:研究表明|研究发现|研究结果|调查结果|模型分析|相关性分析).{0,32}(?:蝗虫|发生|生境)|"
    r"(?:等\s*\[\d+(?:[-–]\d+)?\]\s*的研究(?:也)?(?:均)?指出)|"
    r"(?:利用|使用|喷施|施用).{0,24}(?:农药|杀虫剂|药剂)|"
    r"(?:改变|改造).{0,24}(?:蝗虫的)?生境|"
    r"人工(?:防治|干预)|(?:防治|防控).{0,24}蝗(?:虫|总科)|"
    r"(?:采取|加强|实施).{0,16}(?:管理措施|田间管理)|"
    r"(?:管理措施|田间管理).{0,32}(?:减少|控制|防治|蝗))",
    re.IGNORECASE,
)


def _has_class_cause_pattern(class_name: str, sentence: str) -> bool:
    pattern = _CLASS_CAUSE_PATTERNS.get(_normalized(class_name))
    return bool(pattern and pattern.search(sentence.translate(_MATCH_TRADITIONAL_TO_SIMPLIFIED)))


def _has_class_harm_pattern(class_name: str, sentence: str) -> bool:
    pattern = _CLASS_HARM_PATTERNS.get(_normalized(class_name))
    return bool(pattern and pattern.search(sentence.translate(_MATCH_TRADITIONAL_TO_SIMPLIFIED)))


def _is_wrong_entity_fragment(class_name: str, source: SearchSource, sentence: str) -> bool:
    markers = _WRONG_ENTITY_MARKERS.get(_normalized(class_name), ())
    haystack = f"{source.title} {sentence}".lower()
    return any(marker.lower() in haystack for marker in markers)


_NAMED_INSECT_ENTITY = re.compile(
    r"[\u4e00-\u9fff]{1,5}?(?:翅虫|蚜虫|瓢虫|蝶|牛|蜂|蛾|螟|蚜|蝽|蝉|蛄|螬|甲)"
)
_GENERIC_INSECT_TERMS = {"昆虫", "害虫", "幼虫", "若虫", "成虫", "虫卵", "天敌"}
_HUMAN_MEDICAL_ONLY_MARKERS = (
    "人体", "人类", "患者", "临床", "中毒", "血尿", "肾脏衰竭", "皮肤接触",
    "皮肤损伤", "治疗神经性", "药理作用", "抗癌", "肿瘤", "白细胞",
)
_AGRICULTURE_CONTEXT_MARKERS = (
    "农业", "田间", "农田", "作物", "农作物", "寄主", "植物", "叶片", "叶面",
    "茎叶", "嫩梢", "花瓣", "植食", "啃食", "取食", "为害", "危害", "发生",
)


def _has_foreign_leading_insect_subject(class_name: str, sentence: str, section: Section | None = None) -> bool:
    """Reject a clause led by a different explicitly named insect, not title context."""
    if _normalized(class_name) != "芫菁" and _normalized(class_name) in _mentioned_classes(sentence, _normalized(class_name), section):
        return False
    target_class = next((item for item in CLASS_CATALOG if item["name_zh"] == class_name), None)
    if target_class and target_class.get("type") != "害虫":
        return False
    named_entities = set()
    for match in _NAMED_INSECT_ENTITY.finditer(sentence):
        entity = _normalized(match.group(0))
        if match.group(0).endswith("甲") and sentence[match.end():match.end() + 1] == "虫":
            continue
        if entity in _GENERIC_INSECT_TERMS or entity.endswith(("幼虫", "若虫", "成虫", "虫卵")):
            continue
        named_entities.add(entity)
    target_aliases = _CLASS_ALIASES.get(_normalized(class_name), (_normalized(class_name),))
    target_aliases = tuple(alias for alias in target_aliases if alias)
    return any(
        not any(alias in entity for alias in target_aliases)
        for entity in named_entities
    )


def _is_human_medical_only_fragment(sentence: str) -> bool:
    """Reject human/medical-only claims unless the same clause has crop/agriculture context."""
    return (
        any(marker in sentence for marker in _HUMAN_MEDICAL_ONLY_MARKERS)
        and not any(marker in sentence for marker in _AGRICULTURE_CONTEXT_MARKERS)
    )


_TOMATO_WRONG_CONTEXT_MARKERS = ("花朵大", "花莖倒伏", "花茎倒伏", "居家盆花", "立枝架")

_TOMATO_BACTERIAL_SPOT_SECTION_MARKERS = ("細菌性斑點病", "细菌性斑点病")


def _is_wrong_context_fragment(class_name: str, sentence: str) -> bool:
    return (
        _normalized(class_name) == "番茄细菌性斑点病"
        and any(marker in sentence for marker in _TOMATO_WRONG_CONTEXT_MARKERS)
    )


def _is_tomato_bacterial_spot_section_fragment(
    class_name: str, source: SearchSource, sentence: str
) -> bool:
    """Bind an unlabelled sentence only within its own source-field section.

    Tavily may return a semantic ``snippet`` that is not a prefix of
    ``content``.  Joining those fields before looking for a heading lets a
    heading from the snippet authorize an unrelated sentence in the content.
    Each raw field is therefore evaluated independently.  Within a field,
    inheritance stops at the next standalone section heading, regardless of
    which entity that heading names.
    """
    if _normalized(class_name) != "番茄细菌性斑点病":
        return False
    title = _normalized(source.title)
    if "番茄" not in title:
        return False
    normalized_sentence = _normalized(sentence)
    if not normalized_sentence:
        return False
    target_aliases = tuple({
        *_CLASS_ALIASES.get("番茄细菌性斑点病", ()),
        *(_normalized(marker) for marker in _TOMATO_BACTERIAL_SPOT_SECTION_MARKERS),
    })

    def is_standalone_heading(line: str) -> bool:
        plain = _plain_text(line)
        if not plain or len(plain) > 120:
            return False
        if any(mark in plain for mark in ("。", "！", "？", "；", "!", "?", "：", ":")):
            return False
        return bool(re.match(r"^(?:\d+[.．、]\s*)?\S", plain))

    for field in (source.snippet, source.content):
        if not field:
            continue
        normalized_field = _normalized(field)
        sentence_pos = normalized_field.find(normalized_sentence)
        if sentence_pos < 0:
            continue

        cursor = 0
        target_heading_pos = -1
        other_heading_positions: list[int] = []
        for raw_line in field.splitlines():
            line = _plain_text(raw_line)
            normalized_line = _normalized(line)
            if normalized_line and is_standalone_heading(raw_line):
                line_pos = normalized_field.find(normalized_line, cursor)
                if line_pos >= 0:
                    if any(alias in normalized_line for alias in target_aliases):
                        if line_pos <= sentence_pos:
                            target_heading_pos = line_pos
                    elif line_pos < sentence_pos:
                        other_heading_positions.append(line_pos)
            cursor += len(normalized_line)

        # Some providers flatten a numbered heading and its first paragraph
        # onto one line.  Retain that structural boundary without treating
        # any disease/pest word as a blacklist token.
        inline_heading = re.compile(r"(?<!\d)(?:\d+[.．、]\s*)[^\n。！？；]{1,120}")
        for match in inline_heading.finditer(field):
            header = _plain_text(match.group(0))
            normalized_header = _normalized(header)
            if not normalized_header:
                continue
            heading_pos = normalized_field.find(normalized_header)
            if heading_pos < 0 or heading_pos > sentence_pos:
                continue
            if any(alias in normalized_header for alias in target_aliases):
                target_heading_pos = max(target_heading_pos, heading_pos)
            else:
                other_heading_positions.append(heading_pos)

        if target_heading_pos < 0:
            continue
        if any(position > target_heading_pos for position in other_heading_positions):
            continue
        return True
    return False


def _is_reverse_locust_harm(class_name: str, sentence: str) -> bool:
    return _normalized(class_name) == "蝗总科" and bool(_REVERSE_LOCUST_HARM_PATTERN.search(sentence))


def _is_locust_intervention_fragment(class_name: str, sentence: str) -> bool:
    """Reject only locust research/intervention semantics in the candidate sentence."""
    if _normalized(class_name) != "蝗总科":
        return False
    return bool(_LOCUST_INTERVENTION_PATTERN.search(sentence))


def _is_boilerplate_fragment(value: str) -> bool:
    text = _plain_text(value)
    if not text:
        return True
    if text in _SECTION_LABELS:
        return True
    marker_hits = sum(marker.lower() in text.lower() for marker in _BOILERPLATE_MARKERS)
    return marker_hits >= 2


def clean_source_text_for_extraction(value: str) -> str:
    """Remove generic page chrome only for extraction, never for persisted snapshots."""
    raw = _CONTROL.sub(" ", html.unescape(_HTML.sub(" ", value))).replace("\r", "\n")
    lines = [line.strip(" \t-—") for line in raw.split("\n")]
    return "\n".join(line for line in lines if line and not _is_boilerplate_fragment(line))


def _iter_sentence_pieces(value: str):
    last = 0
    for match in _SENTENCE.finditer(value):
        yield value[last:match.start()], bool(_OMISSION_MARK.fullmatch(match.group(0)))
        last = match.end()
    yield value[last:], False


def _sentences(source: SearchSource) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in (source.snippet, source.content):
        if not value:
            continue
        for piece, cut_by_omission in _iter_sentence_pieces(clean_source_text_for_extraction(value)):
            raw_piece = _plain_text(piece)
            sentence = _clean_candidate_fragment(piece).strip(" \t-—")
            key = _normalized(sentence)
            connector_removed = bool(_TRAILING_OMITTED_CONNECTOR.search(raw_piece))
            if cut_by_omission and not connector_removed and not sentence.endswith(("。", "！", "？", "；", "!", "?")):
                continue
            if 12 <= len(sentence) <= 220 and key and key not in seen and not _is_boilerplate_fragment(sentence):
                seen.add(key)
                result.append(sentence)
    return result


def _possible_cause_fragments(sentence: str) -> list[str]:
    """Split only mixed cause/management sentences at safe Chinese clause boundaries."""
    clauses = [part.strip(" \t-—，；：") for part in re.split(r"[，；：]", sentence)]
    if len(clauses) <= 1 or not any(_is_management_advice_fragment(part) for part in clauses):
        return [sentence]
    return [part for part in clauses if len(part) >= 12]


def _mentioned_classes(value: str, target: str, section: Section | None = None) -> set[str]:
    normalized = _normalized(value)
    aliases = dict(_CLASS_ALIASES)
    for (class_name, alias_section), extra_aliases in _CLASS_SECTION_ALIASES.items():
        if section == alias_section:
            class_token = _normalized(class_name)
            aliases[class_token] = (*aliases.get(class_token, ()), *(_normalized(alias) for alias in extra_aliases))
    aliases[target] = aliases.get(target, (target,))
    tokens = sorted(((alias, class_token) for class_token, names in aliases.items() for alias in names), key=lambda item: len(item[0]), reverse=True)
    matches: set[str] = set()
    occupied: list[tuple[int, int]] = []
    for alias, class_token in tokens:
        start = normalized.find(alias)
        while start >= 0:
            end = start + len(alias)
            if not any(start < other_end and end > other_start for other_start, other_end in occupied):
                matches.add(class_token)
                occupied.append((start, end))
            start = normalized.find(alias, start + 1)
    return matches


def _title_has_competing_entity(title: str, class_name: str) -> bool:
    return bool(re.search(
        rf"{re.escape(class_name)}\s*(?:与|和|及|、|/)\s*[^\s，。；、/]{{1,20}}(?:病|虫|甲|螟|蝽|蝉|蛄|螬|科)",
        title,
    ))


def _same_line_target_context(class_name: str, source: SearchSource, sentence: str, section: Section | None) -> bool:
    """Allow a nearby subject only when the same source line has one unambiguous target anchor."""
    normalized_sentence = _normalized(sentence)
    target = _normalized(class_name)
    if not normalized_sentence:
        return False
    target_class = next((item for item in CLASS_CATALOG if item["name_zh"] == class_name), None)
    if not target_class or target_class.get("type") != "害虫":
        return False

    for field in (source.snippet, source.content):
        if not field:
            continue
        for raw_line in field.splitlines():
            line = _plain_text(raw_line)
            normalized_line = _normalized(line)
            if normalized_sentence not in normalized_line or len(normalized_line) > 900:
                continue
            sentence_start = normalized_line.find(normalized_sentence)
            context_prefix = normalized_line[:sentence_start]
            # Reset inherited context after visible page-section/entity headers.
            boundaries = list(re.finditer(r"(?:image\d+|图片\d+|生活习性|生长繁殖|形态特征|分布范围|栖息环境)", context_prefix, re.IGNORECASE))
            if boundaries:
                context_prefix = context_prefix[boundaries[-1].end():]
            context_window = (context_prefix[-360:] + normalized_sentence)
            mentioned = _mentioned_classes(context_window, target, section)
            if not _mentions_target_or_subtype(mentioned, target):
                continue
            # Do not widen a child-species fact to the official family-level
            # 芫菁 identity when the child name is only inherited from nearby
            # source context. The clause must carry its own subject scope.
            scoped_subtypes = _CLASS_SUBTYPES.get(target, set())
            inherited_subtype = any(subtype in context_prefix for subtype in scoped_subtypes)
            sentence_names_scope = any(subtype in normalized_sentence for subtype in scoped_subtypes)
            sentence_names_target = target in _mentioned_classes(normalized_sentence, target, section)
            if inherited_subtype and not (sentence_names_scope or sentence_names_target):
                continue
            # A heading/topic boundary or another explicitly named insect in
            # the same line makes inheritance ambiguous; never use page title.
            if re.search(r"(?:Image\s*\d+|图片\s*\d+|第\s*\d+\s*条)", line, re.IGNORECASE):
                continue
            aliases = _CLASS_ALIASES.get(target, (target,))
            named_entities = []
            for match in _NAMED_INSECT_ENTITY.finditer(context_window):
                entity = _normalized(match.group(0))
                # The heuristic's terminal 甲 pattern can otherwise classify
                # the generic word 甲虫 as a named competing entity.
                if match.group(0).endswith("甲") and context_window[match.end():match.end() + 1] == "虫":
                    continue
                if entity not in _GENERIC_INSECT_TERMS:
                    named_entities.append(entity)
            if any(not any(alias in entity for alias in aliases) for entity in named_entities):
                continue
            if _has_foreign_leading_insect_subject(class_name, context_window, section):
                continue
            return True
    return False


def _associate_candidate_with_target(class_name: str, source: SearchSource, sentence: str, section: Section | None = None) -> tuple[bool, bool]:
    """Return whether a sentence belongs to the target and whether it names it explicitly."""
    target = _normalized(class_name)
    sentence_mentions = _mentioned_classes(sentence, target, section)
    if target in sentence_mentions:
        return _mentions_target_or_subtype(sentence_mentions, target), True
    if sentence_mentions:
        return False, False
    title_mentions = _mentioned_classes(source.title, target, section)
    single_subject_title = (
        target in title_mentions
        and not bool(title_mentions - {target})
        and not _title_has_competing_entity(source.title, class_name)
    )
    target_class = next((item for item in CLASS_CATALOG if item["name_zh"] == class_name), None)
    # Preserve accepted attribution behavior for other classes; this candidate
    # review is limited to the observed blister-beetle collision.
    is_insect_target = bool(target_class and target_class.get("type") == "害虫" and target == "芫菁")
    if single_subject_title and not is_insect_target:
        return True, False
    if is_insect_target and _same_line_target_context(class_name, source, sentence, section):
        return True, False
    if target == "番茄细菌性斑点病":
        if _is_tomato_bacterial_spot_section_fragment(class_name, source, sentence):
            return True, False
    return False, False


@dataclass(frozen=True)
class _Candidate:
    text: str
    source: SearchSource
    score: int


class EvidenceExtractor:
    """Extract short, source-bound evidence in a stable ordering."""

    def _score(self, section: Section, class_name: str, source: SearchSource, sentence: str) -> int:
        lowered = sentence.translate(_MATCH_TRADITIONAL_TO_SIMPLIFIED).lower()
        if _is_locust_intervention_fragment(class_name, sentence):
            return 0
        if _is_research_context_fragment(source, sentence):
            return 0
        if _is_management_advice_fragment(sentence) and not (section == "harms" and _has_class_harm_pattern(class_name, sentence)):
            return 0
        if _is_pesticide_mechanism_fragment(sentence):
            return 0
        if section == "possible_causes" and _NON_OCCURRENCE_CAUSE_PATTERN.search(sentence):
            return 0
        # Difficulty of controlling an established infestation is not itself
        # an occurrence driver. Keep these management-framed conclusions out
        # of the causes field even when they contain the word "原因".
        if section == "possible_causes" and _CONTROL_DIFFICULTY_CAUSE_PATTERN.search(sentence):
            return 0
        if (
            section == "possible_causes"
            and _LIFECYCLE_NARRATIVE_PATTERN.search(sentence)
            and not _EXPLICIT_ECOLOGICAL_DRIVER_PATTERN.search(sentence)
        ):
            return 0
        if _is_wrong_entity_fragment(class_name, source, sentence):
            return 0
        if _has_foreign_leading_insect_subject(class_name, sentence, section):
            return 0
        if _is_human_medical_only_fragment(sentence):
            return 0
        if _is_wrong_context_fragment(class_name, sentence):
            return 0
        if section == "harms" and _is_reverse_locust_harm(class_name, sentence):
            return 0
        if _is_obvious_leading_fragment(sentence):
            return 0
        if re.match(r"^\s*(?:fig(?:ure)?\.?|图\s*\d+)", sentence, re.IGNORECASE):
            return 0
        if _is_obvious_toc_fragment(sentence):
            return 0
        if section == "possible_causes" and _is_harm_only_fragment(sentence):
            return 0
        hits = sum(token in lowered for token in _TOKENS[section])
        if section == "harms" and _has_class_harm_pattern(class_name, sentence):
            hits = max(hits, 1)
        if section == "possible_causes" and _has_class_cause_pattern(class_name, sentence):
            hits = max(hits, 1)
        if not hits or any(token in lowered for token in _NOISE):
            return 0
        if section == "possible_causes" and not (_has_cause_marker(sentence) or _has_class_cause_pattern(class_name, sentence)):
            return 0
        if section == "possible_causes" and any(marker in sentence for marker in _RESEARCH_METHOD_MARKERS):
            return 0
        associated, explicit_target = _associate_candidate_with_target(class_name, source, sentence, section)
        if not associated:
            return 0
        if section == "harms" and not (_has_class_harm_pattern(class_name, sentence) or any(token in sentence for token in (*_HARM_ACTIONS, *_HARM_EFFECTS))):
            return 0
        title_hit = int(any(token in source.title.lower() for token in _TOKENS[section]))
        reliability = _RELIABILITY.get(source.reliability_level or "", 0)
        return hits * 20 + int(explicit_target) * 12 + int(not explicit_target) * 4 + title_hit * 4 + reliability

    def _select(self, section: Section, evidence: SearchEvidence) -> list[ExternalEvidenceConclusion]:
        candidates: list[_Candidate] = []
        for source_index, source in enumerate(evidence.sources):
            if not (source.content or source.snippet) or not source.id:
                continue
            for sentence_index, sentence in enumerate(_sentences(source)):
                can_split = (
                    section == "possible_causes"
                    and not _has_class_cause_pattern(evidence.class_name, sentence)
                    and not _is_research_context_fragment(source, sentence)
                    and not _is_wrong_entity_fragment(evidence.class_name, source, sentence)
                    and not _INTERVENTION_EFFECT_PATTERN.search(sentence)
                )
                fragments = _possible_cause_fragments(sentence) if can_split else [sentence]
                for fragment_index, fragment in enumerate(fragments):
                    score = self._score(section, evidence.class_name, source, fragment)
                    if score:
                        order = sentence_index * 10 + fragment_index
                        candidates.append(_Candidate(fragment, source, score * 10_000 - source_index * 100 - order))
        fragment_keys = {
            _normalized(candidate.text)
            for candidate in candidates
            if _is_leading_fragment(candidate.text)
        }
        candidates = [
            candidate
            for candidate in candidates
            if not any(
                candidate.source.id == other.source.id
                and candidate.text != other.text
                and len(_normalized(candidate.text)) < len(_normalized(other.text))
                and len(_normalized(candidate.text)) / max(1, len(_normalized(other.text))) >= 0.75
                and _normalized(candidate.text) in _normalized(other.text)
                and _is_leading_fragment(candidate.text)
                and not _is_leading_fragment(other.text)
                for other in candidates
            )
        ]
        selected: list[ExternalEvidenceConclusion] = []
        seen: set[str] = set()
        for candidate in sorted(candidates, key=lambda item: (-item.score, item.source.id, item.text)):
            key = _normalized(candidate.text)
            if key in seen:
                continue
            seen.add(key)
            selected.append(ExternalEvidenceConclusion(conclusion=candidate.text, source_ids=[candidate.source.id]))
            if len(selected) == 2:
                break
        return selected

    def extract(self, evidence: SearchEvidence) -> ExternalEvidenceAnalysis:
        if evidence.status != "available":
            return ExternalEvidenceAnalysis()
        harms = self._select("harms", evidence)
        possible_causes = self._select("possible_causes", evidence)
        harm_keys = {_normalized(item.conclusion) for item in harms}
        possible_causes = [item for item in possible_causes if _normalized(item.conclusion) not in harm_keys]
        if not harms and not possible_causes:
            return ExternalEvidenceAnalysis()
        return ExternalEvidenceAnalysis(status="available", harms=harms, possible_causes=possible_causes)
