"""Project-defined deterministic severity and frozen treatment selection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


SPREAD_SPEED_VALUES: dict[str, Decimal] = {
    "none": Decimal("0"),
    "slow": Decimal("30"),
    "ongoing": Decimal("60"),
    "rapid": Decimal("100"),
}
_LEGACY_SPREAD_SPEED_ALIASES = {"moderate": "ongoing"}
SEVERITY_LABELS = {"mild": "轻度", "moderate": "中度", "severe": "重度"}
_TIER_HEADINGS = {"mild": "轻度", "moderate": "中度", "severe": "重度"}
_SOURCE_HEADING = "防治措施来源"
_SOURCE_ID = re.compile(r"\*\*\[(?P<id>[^\]]+)\]")
_SOURCE_FIELD = re.compile(r"^(?P<field>title|site|url):\s*(?P<value>.+?)\s*$")
_TREATMENT_REF = re.compile(r"\[(?P<id>\d{2}-T\d+)\]")


class SeverityInputError(ValueError):
    """Raised when severity inputs cannot be interpreted deterministically."""


class TierTreatmentError(ValueError):
    """Raised when frozen treatment structure or source references are invalid."""


def _decimal_ratio(value: Any) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise SeverityInputError("affected_ratio must be a finite number")
    try:
        ratio = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SeverityInputError("affected_ratio must be a finite number") from exc
    if not ratio.is_finite() or ratio < Decimal("0") or ratio > Decimal("100"):
        raise SeverityInputError("affected_ratio must be between 0 and 100")
    return ratio


def _number(value: Decimal | None) -> int | float | None:
    if value is None:
        return None
    if value == value.to_integral_value():
        return int(value)
    return float(value)


@dataclass(frozen=True)
class SeverityResult:
    status: str
    level: str | None
    label: str | None
    affected_ratio: Decimal | None
    spread_speed: str | None
    score: Decimal | None
    algorithm_version: str = "severity_v1"
    decision_rule: str = "not_provided"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "level": self.level,
            "label": self.label,
            "affected_ratio": _number(self.affected_ratio),
            "spread_speed": self.spread_speed,
            "score": _number(self.score),
            "algorithm_version": self.algorithm_version,
            "decision_rule": self.decision_rule,
        }


def severity_not_provided() -> SeverityResult:
    return SeverityResult(
        status="not_provided",
        level=None,
        label=None,
        affected_ratio=None,
        spread_speed=None,
        score=None,
    )


def is_spread_speed_missing(value: Any) -> bool:
    """Treat legacy unknown and omitted spread values as missing input."""
    return value is None or value == "unknown"


def calculate_severity(affected_ratio: Any, spread_speed: str) -> SeverityResult:
    """Apply the project-defined deterministic severity rule, without I/O."""
    ratio = _decimal_ratio(affected_ratio)
    if spread_speed not in SPREAD_SPEED_VALUES:
        raise SeverityInputError("spread_speed must be one of none, slow, ongoing, rapid")
    velocity = SPREAD_SPEED_VALUES[spread_speed]
    score = Decimal("0.8") * ratio + Decimal("0.2") * velocity
    if ratio >= Decimal("50"):
        level = "severe"
        decision_rule = "affected_ratio_ge_50"
    elif ratio <= Decimal("5") and spread_speed == "none":
        level = "mild"
        decision_rule = "affected_ratio_le_5_and_no_spread"
    elif score < Decimal("15"):
        level = "mild"
        decision_rule = "composite_score"
    elif score < Decimal("40"):
        level = "moderate"
        decision_rule = "composite_score"
    else:
        level = "severe"
        decision_rule = "composite_score"
    return SeverityResult(
        status="available",
        level=level,
        label=SEVERITY_LABELS[level],
        affected_ratio=ratio,
        spread_speed=spread_speed,
        score=score,
        decision_rule=decision_rule,
    )


def severity_for_record(record: dict[str, Any]) -> SeverityResult:
    """Read persisted inputs while preserving the partial-input contract."""
    ratio = record.get("affected_ratio_percent")
    speed = record.get("spread_speed")
    if ratio is None and is_spread_speed_missing(speed):
        return severity_not_provided()
    if ratio is None or is_spread_speed_missing(speed):
        raise SeverityInputError("affected_ratio and spread_speed must be provided together")
    return calculate_severity(ratio, _LEGACY_SPREAD_SPEED_ALIASES.get(speed, speed))


@dataclass(frozen=True)
class TreatmentSource:
    id: str
    title: str
    site: str
    url: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "title": self.title, "site": self.site, "url": self.url}


@dataclass(frozen=True)
class TierTreatment:
    level: str
    label: str
    content: str
    source_ids: tuple[str, ...]
    sources: tuple[TreatmentSource, ...]


def _finish_source(current: dict[str, str] | None, records: dict[str, TreatmentSource]) -> None:
    if current is None:
        return
    if set(current) != {"id", "title", "site", "url"}:
        raise TierTreatmentError("treatment source must contain id/title/site/url")
    source = TreatmentSource(**current)
    if source.id in records:
        raise TierTreatmentError(f"duplicate treatment source: {source.id}")
    records[source.id] = source


def parse_tiered_treatment(markdown: str) -> dict[str, TierTreatment]:
    """Parse only the exact frozen prevention hierarchy and resolve tier refs."""
    lines = markdown.splitlines()
    prevention = next((i for i, line in enumerate(lines) if line.strip() == "## 防治方法"), None)
    if prevention is None:
        raise TierTreatmentError("missing exact ## 防治方法")
    end = next((i for i in range(prevention + 1, len(lines)) if lines[i].startswith("## ") and not lines[i].startswith("### ")), len(lines))
    headings: list[tuple[int, str]] = []
    for index in range(prevention + 1, end):
        if lines[index].strip() in {f"### {_TIER_HEADINGS[level]}" for level in _TIER_HEADINGS} | {f"### {_SOURCE_HEADING}"}:
            headings.append((index, lines[index].strip()[4:]))
    required = {"轻度", "中度", "重度", _SOURCE_HEADING}
    if {title for _, title in headings} != required:
        raise TierTreatmentError("treatment hierarchy must contain exact three tiers and source heading")
    source_start = next(index for index, title in headings if title == _SOURCE_HEADING)
    source_end = next((index for index in range(source_start + 1, end) if lines[index].startswith("## ") and not lines[index].startswith("### ")), end)
    sources: dict[str, TreatmentSource] = {}
    current: dict[str, str] | None = None
    for line in lines[source_start + 1:source_end]:
        source_match = _SOURCE_ID.search(line)
        if source_match:
            _finish_source(current, sources)
            current = {"id": source_match.group("id")}
            continue
        if not line.strip():
            continue
        field_match = _SOURCE_FIELD.match(line.strip())
        if field_match is None or current is None:
            raise TierTreatmentError("invalid treatment source field")
        field, value = field_match.group("field"), field_match.group("value")
        if field in current:
            raise TierTreatmentError(f"duplicate treatment source field: {field}")
        current[field] = value
    _finish_source(current, sources)

    result: dict[str, TierTreatment] = {}
    for index, title in headings:
        if title == _SOURCE_HEADING:
            continue
        level = next(level for level, label in _TIER_HEADINGS.items() if label == title)
        next_heading = next(position for position, _ in headings if position > index)
        content = "\n".join(lines[index + 1:next_heading]).strip()
        if not content:
            raise TierTreatmentError(f"empty treatment tier: {level}")
        inline_source_ids = tuple(dict.fromkeys(match.group("id") for match in _TREATMENT_REF.finditer(content)))
        # Some frozen knowledge tiers intentionally cite the document-level
        # 防治措施来源 block rather than repeating inline IDs.  Keep inline
        # references exact when present; otherwise associate only the sources
        # already parsed and validated from this same document.
        source_ids = inline_source_ids or tuple(sources)
        missing = [source_id for source_id in source_ids if source_id not in sources]
        if missing:
            raise TierTreatmentError(f"unresolved treatment sources: {missing}")
        result[level] = TierTreatment(
            level=level,
            label=title,
            content=content,
            source_ids=source_ids,
            sources=tuple(sources[source_id] for source_id in source_ids),
        )
    return result


def select_tier_treatment(markdown: str, level: str) -> TierTreatment:
    if level not in _TIER_HEADINGS:
        raise TierTreatmentError(f"unknown severity tier: {level}")
    tiers = parse_tiered_treatment(markdown)
    try:
        return tiers[level]
    except KeyError as exc:
        raise TierTreatmentError(f"missing treatment tier: {level}") from exc
