from __future__ import annotations

from decimal import Decimal

import pytest

from app.knowledge_documents import get_knowledge_document
from app.severity import (
    SeverityInputError,
    calculate_severity,
    is_spread_speed_missing,
    parse_tiered_treatment,
    severity_for_record,
)


@pytest.mark.parametrize(
    ("ratio", "speed", "level", "score"),
    [
        (0, "none", "mild", 0),
        (5, "none", "mild", 4),
        (10, "slow", "mild", 14),
        (11.25, "slow", "moderate", 15),
        (20, "ongoing", "moderate", 28),
        (30, "none", "moderate", 24),
        (25, "rapid", "severe", 40),
        (50, "none", "severe", 40),
        (100, "rapid", "severe", 100),
    ],
)
def test_project_severity_boundaries(ratio, speed, level, score) -> None:
    result = calculate_severity(ratio, speed)
    assert result.status == "available"
    assert result.level == level
    assert result.label in {"轻度", "中度", "重度"}
    assert result.score == Decimal(str(score))


@pytest.mark.parametrize(
    ("ratio", "speed"),
    [
        (-0.1, "none"),
        (100.1, "none"),
        (float("nan"), "none"),
        (float("inf"), "none"),
        (20, "unknown"),
        (20, "free text"),
    ],
)
def test_severity_rejects_invalid_inputs(ratio, speed) -> None:
    with pytest.raises(SeverityInputError):
        calculate_severity(ratio, speed)


def test_legacy_records_without_both_inputs_are_not_guessed() -> None:
    assert severity_for_record({}).status == "not_provided"
    assert severity_for_record({"affected_ratio_percent": None, "spread_speed": "unknown"}).status == "not_provided"
    with pytest.raises(SeverityInputError):
        severity_for_record({"affected_ratio_percent": 20})
    with pytest.raises(SeverityInputError):
        severity_for_record({"spread_speed": "rapid"})
    with pytest.raises(SeverityInputError):
        severity_for_record({"affected_ratio_percent": 20, "spread_speed": "unknown"})


def test_spread_missing_definition_is_none_or_unknown_only() -> None:
    assert is_spread_speed_missing(None)
    assert is_spread_speed_missing("unknown")
    assert not is_spread_speed_missing("none")


def test_severity_determinism_matrix_and_monotonicity() -> None:
    speeds = ("none", "slow", "ongoing", "rapid")
    matrix = []
    for ratio in range(101):
        for speed in speeds:
            first = calculate_severity(ratio, speed).as_dict()
            second = calculate_severity(ratio, speed).as_dict()
            assert first == second
            assert first["level"] in {"mild", "moderate", "severe"}
            matrix.append(first)
    assert len(matrix) == 404
    for speed in speeds:
        levels = [calculate_severity(ratio, speed).level for ratio in range(101)]
        order = {"mild": 0, "moderate": 1, "severe": 2}
        assert all(order[left] <= order[right] for left, right in zip(levels, levels[1:]))
    order = {"mild": 0, "moderate": 1, "severe": 2}
    for ratio in range(101):
        levels = [calculate_severity(ratio, speed).level for speed in speeds]
        assert all(order[left] <= order[right] for left, right in zip(levels, levels[1:]))


@pytest.mark.parametrize(
    ("class_id", "level"),
    [(class_id, level) for class_id in range(16) for level in ("mild", "moderate", "severe")],
)
def test_all_48_frozen_tiers_parse_and_resolve_sources(class_id: int, level: str) -> None:
    document = get_knowledge_document(class_id)
    assert document is not None
    tiers = parse_tiered_treatment(document["markdown"])
    assert set(tiers) == {"mild", "moderate", "severe"}
    selected = tiers[level]
    assert selected.content
    assert len(selected.source_ids) == len(selected.sources)
    assert all(source.id in selected.source_ids for source in selected.sources)
    other_headings = {"### 轻度", "### 中度", "### 重度"} - {f"### {selected.label}"}
    assert not any(heading in selected.content for heading in other_headings)
