"""Server-owned context assembled around an existing diagnosis record.

This module deliberately does not participate in search, severity, or treatment
decisions.  It only exposes the effective context that is safe for downstream
consumers while preserving the legacy fields stored on a case.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .catalog import CLASS_CATALOG
from .severity import severity_for_record


SYSTEM_DEFAULT_ENVIRONMENT: dict[str, Any] = {
    "source": "system_default",
    "cultivation_scene": "常规田间种植环境",
    "temperature_c": 25,
    "relative_humidity_percent": 70,
    "soil_moisture": "适中",
    "light_condition": "自然光照",
    "ventilation": "自然通风",
    "recent_extreme_weather": "无",
}

GROWTH_STAGE_LABELS: dict[str, str] = {
    "seedling": "苗期",
    "vegetative": "营养生长期",
    "flowering": "开花期",
    "fruiting_or_seed_setting": "结果或结实期",
    "maturity": "成熟期",
    "uncertain": "不确定",
}
GROWTH_STAGE_INPUTS: dict[str, str] = {
    **{value: key for key, value in GROWTH_STAGE_LABELS.items()},
    "结果期": "fruiting_or_seed_setting",
}


def normalize_growth_stage(value: str) -> str:
    """Return the persisted formal enum for a user-provided stage."""
    stripped = value.strip()
    return GROWTH_STAGE_INPUTS.get(stripped, stripped)


def growth_stage_context(value: Any) -> dict[str, Any]:
    """Represent missing, legacy, and formal growth values without inference."""
    if not isinstance(value, str) or not value.strip() or value.strip() == "不适用":
        return {"status": "not_provided", "value": None, "label": None, "source": "user"}
    formal_value = normalize_growth_stage(value)
    label = GROWTH_STAGE_LABELS.get(formal_value)
    if label is None:
        return {"status": "not_provided", "value": None, "label": None, "source": "user"}
    return {"status": "available", "value": formal_value, "label": label, "source": "user"}


def _build_class_crop_mapping() -> tuple[dict[str, Any], ...]:
    """Derive the mapping from the existing catalog; pest hosts are not guessed."""
    mapping: list[dict[str, Any]] = []
    for item in CLASS_CATALOG:
        if item.get("type") == "病害" and item.get("crop"):
            unique_crop = str(item["crop"])
            mapping_source = "catalog_class_crop"
            status = "available_from_yolo"
            rule = "YOLO disease class has a unique crop in the existing class catalog."
        else:
            unique_crop = None
            mapping_source = "catalog_class_name_only"
            status = "user_reported_fallback"
            rule = "YOLO pest class has no unique host; use user crop when provided, otherwise unavailable."
        mapping.append(
            {
                "class_id": int(item["id"]),
                "class_name": str(item["name_zh"]),
                "unique_crop": unique_crop,
                "effective_rule": rule,
                "mapping_source": mapping_source,
                "status": status,
            }
        )
    return tuple(mapping)


CLASS_CROP_MAPPING = _build_class_crop_mapping()
CLASS_CROP_BY_ID = {item["class_id"]: item for item in CLASS_CROP_MAPPING}


def crop_context(record: dict[str, Any]) -> dict[str, Any]:
    """Resolve R3 user context first, retaining the legacy mapping for old cases."""
    r3_context = record.get("context")
    if isinstance(r3_context, dict):
        subject_type = r3_context.get("subject_type")
        crop_species = r3_context.get("crop_species")
        if subject_type == "plant" and isinstance(crop_species, str) and crop_species.strip():
            return {
                "status": "available",
                "value": crop_species.strip(),
                "source": r3_context.get("source") or "user_confirmed",
            }
        if subject_type == "insect":
            return {"status": "not_applicable", "value": None, "source": r3_context.get("source")}
    summary = record.get("detector_summary") or {}
    detections = record.get("detections") or []
    primary = summary.get("primary_candidate") or (detections[0] if detections else {})
    class_id = primary.get("class_id") if isinstance(primary, dict) else None
    mapping = CLASS_CROP_BY_ID.get(class_id) if isinstance(class_id, int) else None
    if mapping and mapping["status"] == "available_from_yolo":
        return {
            "status": "available",
            "value": mapping["unique_crop"],
            "source": "yolo_class_mapping",
        }
    reported = record.get("crop")
    if isinstance(reported, str) and reported.strip() and reported.strip() != "昆虫":
        return {"status": "available", "value": reported.strip(), "source": "user_reported"}
    return {"status": "unavailable", "value": None, "source": None}


def build_case_context(
    record: dict[str, Any], *, severity: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build only response context; no value here is fed back into analysis."""
    if severity is None:
        persisted = record.get("severity")
        severity = deepcopy(persisted) if isinstance(persisted, dict) else severity_for_record(record).as_dict()
    return {
        "crop": crop_context(record),
        "growth_stage": growth_stage_context(record.get("growth_stage")),
        "affected_ratio_percent": record.get("affected_ratio_percent"),
        "spread_speed": record.get("spread_speed"),
        "severity": deepcopy(severity),
        "environment": deepcopy(SYSTEM_DEFAULT_ENVIRONMENT),
    }
