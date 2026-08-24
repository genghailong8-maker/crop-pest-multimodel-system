"""YOLO-first deterministic analysis orchestration."""

from __future__ import annotations

from typing import Any

from .catalog import CLASS_BY_ID
from .search import collect_external_evidence, persisted_evidence_snapshots, public_sources
from .search.evidence_extractor import EvidenceExtractor


ANALYSIS_SCHEMA_VERSION = "evidence-extractor-v1"


def _confidence(primary: dict[str, Any]) -> float:
    value = primary.get("max_confidence", primary.get("confidence", 0))
    return float(value) if isinstance(value, (int, float)) else 0.0


def _field_severity(record: dict[str, Any]) -> tuple[str, str]:
    ratio = record.get("affected_ratio_percent")
    speed = record.get("spread_speed")
    if not isinstance(ratio, (int, float)) or speed in {None, "unknown"}:
        return "unknown", "缺少受害比例或扩散速度，无法判断田间严重度。"
    if ratio >= 30 or speed in {"rapid", "moderate"}:
        return "high", f"用户填写受害比例 {ratio:g}%、扩散速度 {speed}。"
    if ratio >= 10 or speed == "slow":
        return "medium", f"用户填写受害比例 {ratio:g}%、扩散速度 {speed}。"
    return "low", f"用户填写受害比例 {ratio:g}%、扩散速度 {speed}。"


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

    if confidence < 0.50:
        uncertainty = ["最高视觉置信度低于 50%，当前不形成明确病虫害结论。"]
    elif confidence < 0.75:
        uncertainty = ["视觉置信度处于 50%–75%，建议补拍后再判断。"]
    else:
        uncertainty = []

    if class_name and confidence >= 0.75:
        evidence = await collect_external_evidence(class_name)
        external_analysis = EvidenceExtractor().extract(evidence)
    else:
        from .search.models import SearchEvidence

        evidence = SearchEvidence(
            class_name=class_name or "未知",
            status="unavailable",
            message="当前 YOLO 置信度不足，未整理外部资料。",
        )
        external_analysis = EvidenceExtractor().extract(evidence)

    field_severity, severity_basis = _field_severity(record)
    needs_review = confidence < 0.75
    return {
        "status": "completed",
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "primary_diagnosis": class_name if confidence >= 0.75 else None,
        "candidate_diagnoses": [class_name] if class_name else [],
        "symptoms": [],
        "harm_level": "unknown",
        "uncertainty": uncertainty,
        "detector_alignment": "not_applicable",
        "field_input_consistency": "not_evaluated",
        "content_sufficiency": "sufficient" if confidence >= 0.75 else "incomplete",
        "diagnostic_risk": "low" if confidence >= 0.75 else "high" if confidence < 0.50 else "medium",
        "field_severity": field_severity,
        "severity_basis": severity_basis,
        "needs_human_review": needs_review,
        "review_reasons": list((summary.get("review_reasons") or [])) + uncertainty,
        "evidence_analysis": external_analysis.model_dump(),
        "sources": public_sources(evidence),
        "evidence_snapshots": persisted_evidence_snapshots(evidence),
        "provenance": {
            "engine": "deterministic_evidence_extractor",
            "protocol": ANALYSIS_SCHEMA_VERSION,
            "detector_class_id": class_id,
            "detector_confidence": confidence,
            "external_search": {
                "status": evidence.status,
                "queries": evidence.queries,
                "message": evidence.message,
            },
        },
    }
