"""YOLO-first deterministic analysis orchestration."""

from __future__ import annotations

from typing import Any

from .catalog import CLASS_BY_ID
from .config import LOW_CONFIDENCE_THRESHOLD
from .search import collect_external_evidence, persisted_evidence_snapshots, public_sources
from .search.curated import curated_analysis, curated_evidence_for_class, curated_public_sources
from .search.evidence_extractor import EvidenceExtractor
from .severity import severity_for_record


ANALYSIS_SCHEMA_VERSION = "evidence-extractor-v1"


def _confidence(primary: dict[str, Any]) -> float:
    value = primary.get("max_confidence", primary.get("confidence", 0))
    return float(value) if isinstance(value, (int, float)) else 0.0


def _severity_values(record: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    persisted = record.get("severity")
    if isinstance(persisted, dict) and persisted.get("algorithm_version") == "severity-v2":
        return persisted, "unknown", "用户依据当前样本可观察症状选择受害程度。"
    severity = severity_for_record(record)
    if severity.status != "available":
        return severity.as_dict(), "unknown", "缺少受害比例或扩散速度，无法判断田间严重度。"
    legacy_level = {"mild": "low", "moderate": "medium", "severe": "high"}[severity.level]
    basis = (
        f"项目设计的确定性综合严重度规则：受害比例 {severity.affected_ratio:g}%、"
        f"扩散速度 {severity.spread_speed}、综合分数 {severity.score:g}。"
    )
    return severity.as_dict(), legacy_level, basis


async def request_evidence_analysis(record: dict[str, Any]) -> dict[str, Any]:
    """Build an honest analysis without looking at the image a second time."""
    detections = record.get("detections") or []
    summary = record.get("detector_summary") or {}
    primary = summary.get("primary_candidate") or (detections[0] if detections else {})
    class_id = primary.get("class_id") if isinstance(primary, dict) else None
    class_name = str(primary.get("class_name") or "") if isinstance(primary, dict) else ""
    confidence = _confidence(primary if isinstance(primary, dict) else {})
    if not class_name and isinstance(class_id, int) and class_id in CLASS_BY_ID:
        class_name = str(CLASS_BY_ID[class_id]["name_zh"])

    if confidence < LOW_CONFIDENCE_THRESHOLD:
        uncertainty = ["最高视觉置信度低于 50%，当前不形成明确病虫害结论。"]
    else:
        uncertainty = []

    curated = (
        curated_evidence_for_class(class_id, class_name)
        if isinstance(class_id, int) and class_name and confidence >= LOW_CONFIDENCE_THRESHOLD
        else None
    )
    if curated is not None:
        external_analysis = curated_analysis(curated)
        sources = curated_public_sources(curated)
        evidence_snapshots = [
            snapshot
            for item in curated
            for snapshot in persisted_evidence_snapshots(item)
        ]
        external_search_status = "available"
        external_search_queries: list[str] = []
        external_search_message = "本地精选知识库证据"
    elif class_name and confidence >= LOW_CONFIDENCE_THRESHOLD:
        evidence = await collect_external_evidence(class_name)
        external_analysis = EvidenceExtractor().extract(evidence)
        sources = public_sources(evidence)
        evidence_snapshots = persisted_evidence_snapshots(evidence)
        external_search_status = evidence.status
        external_search_queries = evidence.queries
        external_search_message = evidence.message
    else:
        from .search.models import SearchEvidence

        evidence = SearchEvidence(
            class_name=class_name or "未知",
            status="unavailable",
            message="当前 YOLO 置信度不足，未整理外部资料。",
        )
        external_analysis = EvidenceExtractor().extract(evidence)
        sources = public_sources(evidence)
        evidence_snapshots = persisted_evidence_snapshots(evidence)
        external_search_status = evidence.status
        external_search_queries = evidence.queries
        external_search_message = evidence.message

    severity, field_severity, severity_basis = _severity_values(record)
    needs_review = confidence < LOW_CONFIDENCE_THRESHOLD
    return {
        "status": "completed",
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "primary_diagnosis": class_name if confidence >= LOW_CONFIDENCE_THRESHOLD else None,
        "candidate_diagnoses": [class_name] if class_name else [],
        "symptoms": [],
        "harm_level": "unknown",
        "uncertainty": uncertainty,
        "detector_alignment": "not_applicable",
        "field_input_consistency": "not_evaluated",
        "content_sufficiency": "sufficient" if confidence >= LOW_CONFIDENCE_THRESHOLD else "incomplete",
        "diagnostic_risk": "low" if confidence >= LOW_CONFIDENCE_THRESHOLD else "high",
        "field_severity": field_severity,
        "severity_basis": severity_basis,
        "severity": severity,
        "needs_human_review": needs_review,
        "review_reasons": list((summary.get("review_reasons") or [])) + uncertainty,
        "evidence_analysis": external_analysis.model_dump(),
        "sources": sources,
        "evidence_snapshots": evidence_snapshots,
        "provenance": {
            "engine": "deterministic_evidence_extractor",
            "protocol": ANALYSIS_SCHEMA_VERSION,
            "detector_class_id": class_id,
            "detector_confidence": confidence,
            "external_search": {
                "status": external_search_status,
                "queries": external_search_queries,
                "message": external_search_message,
            },
        },
    }
