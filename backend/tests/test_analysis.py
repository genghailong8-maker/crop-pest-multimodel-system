from __future__ import annotations

import asyncio

from app import analysis
from app.search.models import SearchEvidence


def record(confidence: float) -> dict:
    return {
        "detections": [{"class_id": 14, "class_name": "蛴螬", "confidence": confidence}],
        "detector_summary": {"primary_candidate": {"class_id": 14, "class_name": "蛴螬", "max_confidence": confidence}, "review_reasons": []},
        "affected_ratio_percent": 12.5,
        "spread_speed": "slow",
    }


def test_low_confidence_skips_external_search(monkeypatch) -> None:
    async def fail_if_called(_name: str):
        raise AssertionError("低置信度不应检索外部资料")

    monkeypatch.setattr(analysis, "collect_external_evidence", fail_if_called)
    result = asyncio.run(analysis.request_evidence_analysis(record(0.49)))
    assert result["primary_diagnosis"] is None
    assert result["evidence_analysis"]["status"] == "unavailable"


def test_mid_confidence_requests_retake_without_strong_conclusion(monkeypatch) -> None:
    async def fail_if_called(_name: str):
        raise AssertionError("中等置信度不应检索外部资料")

    monkeypatch.setattr(analysis, "collect_external_evidence", fail_if_called)
    result = asyncio.run(analysis.request_evidence_analysis(record(0.50)))
    assert result["primary_diagnosis"] is None
    assert result["needs_human_review"] is True
    assert "50%–75%" in result["uncertainty"][0]


def test_high_confidence_uses_normalized_search_and_extractor(monkeypatch) -> None:
    async def fake_search(_name: str):
        return SearchEvidence(class_name="蛴螬", status="unavailable")

    monkeypatch.setattr(analysis, "collect_external_evidence", fake_search)
    result = asyncio.run(analysis.request_evidence_analysis(record(0.75)))
    assert result["primary_diagnosis"] == "蛴螬"
    assert result["provenance"]["engine"] == "deterministic_evidence_extractor"
    assert result["evidence_analysis"]["status"] == "unavailable"
