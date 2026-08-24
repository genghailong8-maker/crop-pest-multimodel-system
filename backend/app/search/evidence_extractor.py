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
    "harms": ("危害", "为害", "症状", "损害", "咬食", "受害", "枯萎", "死亡", "减产", "病斑", "失绿"),
    "possible_causes": ("发生", "原因", "条件", "高温", "高湿", "降雨", "湿度", "土壤", "连作", "幼虫", "传播", "虫源"),
}
_CAUSE_MARKERS = ("原因", "条件", "有利于", "易发生", "喜发生", "促进", "导致", "相关", "病原", "虫源")
_RELIABILITY = {"政府农业部门": 5, "农业科研院所": 4, "高校农学院/植保学院": 3, "农技推广/植保机构": 3, "权威农业数据库": 2, "其他可信农业专业站点": 1}


def _plain_text(value: str) -> str:
    value = html.unescape(_HTML.sub(" ", value))
    return _SPACE.sub(" ", value).strip()


def _normalized(value: str) -> str:
    return re.sub(r"[\W_]+", "", value).lower()


def _sentences(source: SearchSource) -> list[str]:
    body = _plain_text(source.content or source.snippet or "")
    return [piece.strip(" \t-—") for piece in _SENTENCE.split(body) if 12 <= len(piece.strip()) <= 220]


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
        class_token = _normalized(class_name)
        class_hit = int(class_token in _normalized(sentence))
        title_class_hit = int(class_token in _normalized(source.title))
        if not class_hit and not title_class_hit:
            return 0
        title_hit = int(any(token in source.title.lower() for token in _TOKENS[section]))
        reliability = _RELIABILITY.get(source.reliability_level or "", 0)
        return hits * 20 + class_hit * 12 + title_class_hit * 8 + title_hit * 4 + reliability

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
