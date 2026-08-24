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
_SPACE = re.compile(r"\s+")
_SENTENCE = re.compile(r"(?<=[。！？；!?])|\n+")
_NOISE = ("首页", "导航", "版权", "相关阅读", "上一页", "下一页", "登录", "注册", "cookie")
_TOKENS: dict[Section, tuple[str, ...]] = {
    "harms": ("危害", "为害", "症状", "损害", "损伤", "受损", "咬食", "受害", "枯萎", "死亡", "减产", "病斑", "失绿", "腐烂", "黄化", "倒伏", "枯死"),
    "possible_causes": ("发生", "原因", "条件", "高温", "高湿", "降雨", "湿度", "土壤", "连作", "幼虫", "传播", "虫源"),
}
_CAUSE_MARKERS = ("原因", "条件", "有利于", "易发生", "喜发生", "促进", "导致", "相关", "病原", "虫源")
_RELIABILITY = {"政府农业部门": 5, "农业科研院所": 4, "高校农学院/植保学院": 3, "农技推广/植保机构": 3, "权威农业数据库": 2, "其他可信农业专业站点": 1}
_HARM_ACTIONS = ("咬食", "取食", "侵染", "蛀食", "吸食", "危害根", "危害叶", "为害根", "为害叶")
_HARM_EFFECTS = ("死亡", "枯萎", "腐烂", "黄化", "病斑", "根系损伤", "叶片受损", "减产", "品质下降", "倒伏", "损伤", "受损", "缺苗", "生长受阻", "枯死", "断裂")


def _plain_text(value: str) -> str:
    value = html.unescape(_HTML.sub(" ", value))
    return _SPACE.sub(" ", value).strip()


def _normalized(value: str) -> str:
    return re.sub(r"[\W_]+", "", value).lower()


_KNOWN_CLASS_TOKENS = tuple(sorted({_normalized(item["name_zh"]) for item in CLASS_CATALOG}, key=len, reverse=True))


def _sentences(source: SearchSource) -> list[str]:
    body = _plain_text(source.content or source.snippet or "")
    return [piece.strip(" \t-—") for piece in _SENTENCE.split(body) if 12 <= len(piece.strip()) <= 220]


def _mentioned_classes(value: str, target: str) -> set[str]:
    normalized = _normalized(value)
    tokens = sorted({*_KNOWN_CLASS_TOKENS, target}, key=len, reverse=True)
    matches: set[str] = set()
    occupied: list[tuple[int, int]] = []
    for token in tokens:
        start = normalized.find(token)
        while start >= 0:
            end = start + len(token)
            if not any(start < other_end and end > other_start for other_start, other_end in occupied):
                matches.add(token)
                occupied.append((start, end))
            start = normalized.find(token, start + 1)
    return matches


def _title_has_competing_entity(title: str, class_name: str) -> bool:
    return bool(re.search(
        rf"{re.escape(class_name)}\s*(?:与|和|及|、|/)\s*[^\s，。；、/]{{1,20}}(?:病|虫|甲|螟|蝽|蝉|蛄|螬|科)",
        title,
    ))


def _associate_candidate_with_target(class_name: str, source: SearchSource, sentence: str) -> tuple[bool, bool]:
    """Return whether a sentence belongs to the target and whether it names it explicitly."""
    target = _normalized(class_name)
    sentence_mentions = _mentioned_classes(sentence, target)
    if target in sentence_mentions:
        return not bool(sentence_mentions - {target}), True
    if sentence_mentions:
        return False, False
    title_mentions = _mentioned_classes(source.title, target)
    single_subject_title = (
        target in title_mentions
        and not bool(title_mentions - {target})
        and not _title_has_competing_entity(source.title, class_name)
    )
    return single_subject_title, False


@dataclass(frozen=True)
class _Candidate:
    text: str
    source: SearchSource
    score: int


class EvidenceExtractor:
    """Extract short, source-bound evidence in a stable ordering."""

    def _score(self, section: Section, class_name: str, source: SearchSource, sentence: str) -> int:
        lowered = sentence.lower()
        hits = sum(token in lowered for token in _TOKENS[section])
        if not hits or any(token in lowered for token in _NOISE):
            return 0
        if section == "possible_causes" and not any(marker in sentence for marker in _CAUSE_MARKERS):
            return 0
        associated, explicit_target = _associate_candidate_with_target(class_name, source, sentence)
        if not associated:
            return 0
        if section == "harms" and not any(token in sentence for token in (*_HARM_ACTIONS, *_HARM_EFFECTS)):
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
                score = self._score(section, evidence.class_name, source, sentence)
                if score:
                    candidates.append(_Candidate(sentence, source, score * 10_000 - source_index * 100 - sentence_index))
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
        if not harms and not possible_causes:
            return ExternalEvidenceAnalysis()
        return ExternalEvidenceAnalysis(status="available", harms=harms, possible_causes=possible_causes)
