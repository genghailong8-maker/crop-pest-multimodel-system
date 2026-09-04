"""Runtime loader for the frozen Severity V2 rubric and alignment SSOT.

The module deliberately performs only exact class/tier lookups.  It does not
infer severity, synthesize treatment, or provide a fallback tier.
"""

from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


SEVERITY_V2_LEVELS = ("mild", "moderate", "severe", "uncertain")
_TIER_LEVELS = {"mild", "moderate", "severe"}
_ROOT = Path(__file__).resolve().parents[2]
_RUBRICS_PATH = _ROOT / "docs" / "competition" / "severity-v2-rubrics.json"
_ALIGNMENT_PATH = _ROOT / "docs" / "competition" / "severity-v2-treatment-alignment.tsv"
_REFERENCE_MANIFEST_PATH = _ROOT / "docs" / "competition" / "severity-v2-reference-manifest.json"


class SeverityV2ContractError(ValueError):
    """Raised when the frozen runtime contract is incomplete or inconsistent."""


@lru_cache(maxsize=1)
def _rubrics() -> dict[str, dict[str, Any]]:
    payload = json.loads(_RUBRICS_PATH.read_text(encoding="utf-8"))
    records = payload.get("rubrics")
    if not isinstance(records, list):
        raise SeverityV2ContractError("severity v2 rubrics are missing")
    resolved: dict[str, dict[str, Any]] = {}
    required = {"canonical_class", "assessment_unit", "observable_features", *SEVERITY_V2_LEVELS}
    for item in records:
        if not isinstance(item, dict) or not required <= set(item):
            raise SeverityV2ContractError("severity v2 rubric has required fields missing")
        canonical = item["canonical_class"]
        if not isinstance(canonical, str) or canonical in resolved:
            raise SeverityV2ContractError("severity v2 rubric canonical keys are invalid")
        resolved[canonical] = {key: item[key] for key in required | {"assessment_template"} if key in item}
    return resolved


@lru_cache(maxsize=1)
def _alignment() -> dict[tuple[str, str], str]:
    with _ALIGNMENT_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    resolved: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (row.get("canonical_class", ""), row.get("severity_level", ""))
        state = row.get("current_alignment", "")
        if not all(key) or state not in {"READY_KEEP", "READY_ADJUST", "NEEDS_RESEARCH"} or key in resolved:
            raise SeverityV2ContractError("severity v2 treatment alignment is invalid")
        resolved[key] = state
    return resolved


@lru_cache(maxsize=1)
def _references() -> dict[tuple[str, str], dict[str, Any]]:
    payload = json.loads(_REFERENCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    records = payload.get("slots")
    if not isinstance(records, list):
        raise SeverityV2ContractError("severity v2 reference manifest is missing")
    resolved: dict[tuple[str, str], dict[str, Any]] = {}
    required = {"class_id", "canonical_class", "severity", "rubric_reference", "image_type", "source", "license", "fallback_label"}
    for item in records:
        if not isinstance(item, dict) or not required <= set(item):
            raise SeverityV2ContractError("severity v2 reference manifest has required fields missing")
        key = (str(item["canonical_class"]), str(item["severity"]))
        if key in resolved or item["severity"] not in {"mild", "moderate", "severe"}:
            raise SeverityV2ContractError("severity v2 reference manifest keys are invalid")
        resolved[key] = dict(item)
    if len(resolved) != 48:
        raise SeverityV2ContractError("severity v2 reference manifest coverage is incomplete")
    return resolved


def rubric_for_canonical(canonical_class: str) -> dict[str, Any] | None:
    rubric = _rubrics().get(canonical_class)
    return dict(rubric) if rubric else None


def readiness_for(canonical_class: str, level: str) -> str | None:
    if level not in _TIER_LEVELS:
        return None
    return _alignment().get((canonical_class, {"mild": "轻度", "moderate": "中度", "severe": "重度"}[level]))


def references_for_canonical(canonical_class: str) -> dict[str, dict[str, Any]]:
    return {
        level: dict(_references()[(canonical_class, level)])
        for level in _TIER_LEVELS
        if (canonical_class, level) in _references()
    }


def severity_payload(level: str) -> dict[str, str]:
    if level not in SEVERITY_V2_LEVELS:
        raise SeverityV2ContractError("severity level is invalid")
    return {
        "status": "available",
        "level": level,
        "label": {"mild": "轻度", "moderate": "中度", "severe": "重度", "uncertain": "无法判断"}[level],
        "scope": "current_sample",
        "source": "user_guided_rubric",
        "algorithm_version": "severity-v2",
    }


def severity_pending_payload() -> dict[str, Any]:
    """Mark a new V2 case as awaiting a user selection, without a tier."""
    return {
        "status": "not_provided",
        "level": None,
        "label": None,
        "scope": "current_sample",
        "source": "user_guided_rubric",
        "algorithm_version": "severity-v2",
    }


def validate_contract() -> dict[str, int]:
    rubrics = _rubrics()
    alignment = _alignment()
    references = _references()
    if len(rubrics) != 16 or len(alignment) != 48 or len(references) != 48:
        raise SeverityV2ContractError("severity v2 coverage is incomplete")
    if any(readiness_for(canonical, level) is None for canonical in rubrics for level in _TIER_LEVELS):
        raise SeverityV2ContractError("severity v2 alignment does not cover every rubric tier")
    return {
        "rubrics": len(rubrics),
        "alignment": len(alignment),
        "ready_keep": sum(state == "READY_KEEP" for state in alignment.values()),
        "ready_adjust": sum(state == "READY_ADJUST" for state in alignment.values()),
        "needs_research": sum(state == "NEEDS_RESEARCH" for state in alignment.values()),
    }
