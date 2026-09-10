"""Backend-only adapter for the R3.1 adaptive host knowledge contract.

This module reads the independent R3.1 knowledge artifacts and never changes
the frozen R1 evidence pipeline.  It is intentionally fail-closed: missing or
incomplete host evidence is represented as unavailable rather than synthesized.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from .catalog import CLASS_BY_ID


R31_ROOT = Path(__file__).resolve().parents[2] / "knowledge" / "insect-host-r3.1"
OTHER_HOST = "OTHER"
SEVERITY_LEVELS = ("mild", "moderate", "severe")
FALLBACK_ORDER = ("host_severity", "host_general", "insect_general")
SEVERITY_LABELS = {"mild": "轻度", "moderate": "中度", "severe": "重度"}

FALLBACK_MESSAGES = {
    "host_severity": "当前资料支持按受害阶段或行动级别调整管理强度，并不代表来源采用本项目三级 Severity 分级。",
    "host_general": "当前审核资料支持该寄主的严重程度判断，但未支持按轻/中/重进一步区分防治措施，因此显示该害虫在当前作物上的通用防治方案。",
    "insect_general": "当前寄主暂无完整的作物特异防治资料，以下显示该害虫的通用防治建议。",
    "other": "当前作物暂未收录，以下仅显示该害虫的通用危害、可能诱因和通用防治建议。",
    "uncertain": "当前受害程度无法判断，因此不提供防治措施。",
}
UNGRADED_HOST_GENERAL_MESSAGE = "当前受害程度分级资料不可用，以下显示该害虫在当前作物上的通用防治方案。"
_SOURCE_REF = re.compile(r"\[(R31-[^\]]+)\]")


class R31HostKnowledgeError(ValueError):
    """Raised when the R3.1 adapter artifacts are structurally unusable."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise R31HostKnowledgeError(f"R3.1 knowledge artifact unavailable: {path}") from exc
    if not isinstance(value, dict):
        raise R31HostKnowledgeError(f"R3.1 knowledge artifact is not an object: {path}")
    return value


def _refs(text: str) -> list[str]:
    return list(dict.fromkeys(_SOURCE_REF.findall(text)))


def _section(markdown: str, heading: str, *, level: int) -> str:
    lines = markdown.splitlines()
    marker = f"{'#' * level} {heading}"
    start = next((index for index, line in enumerate(lines) if line.strip() == marker), None)
    if start is None:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("#") and not stripped.startswith("#" * (level + 1)):
            if len(stripped) - len(stripped.lstrip("#")) <= level:
                end = index
                break
    return "\n".join(lines[start + 1:end]).strip()


def _host_blocks(markdown: str) -> dict[str, str]:
    lines = markdown.splitlines()
    starts = [
        (index, line.removeprefix("### 寄主：").strip())
        for index, line in enumerate(lines)
        if line.startswith("### 寄主：")
    ]
    blocks: dict[str, str] = {}
    for position, (start, crop) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        for index in range(start + 1, len(lines)):
            if lines[index].startswith("## ") and not lines[index].startswith("### "):
                end = min(end, index)
                break
        blocks[crop] = "\n".join(lines[start:end]).strip()
    return blocks


def _bullet_value(text: str, prefix: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped.removeprefix(prefix).strip()
    return ""


def _vector_blocks(markdown: str) -> dict[str, str]:
    section = _section(markdown, "可能传播的相关病害", level=2)
    lines = section.splitlines()
    starts = [
        (index, line.removeprefix("### 病害：").strip())
        for index, line in enumerate(lines)
        if line.startswith("### 病害：")
    ]
    result: dict[str, str] = {}
    for position, (start, disease) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        result[disease] = "\n".join(lines[start:end]).strip()
    return result


def _source_payload(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": source.get("source_id"),
        "title": source.get("title"),
        "organization": source.get("organization"),
        "url": source.get("url"),
        "doi": source.get("doi") or "",
        "tier": source.get("tier"),
        "support_scope": source.get("support_scope"),
    }


def _sources(source_ids: list[str], source_by_id: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [_source_payload(source_by_id[source_id]) for source_id in source_ids if source_id in source_by_id]


def _severity_records(
    records: list[dict[str, Any]], class_id: int, crop: str, disease: str | None = None
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in records:
        if item.get("object_type") != ("vector_disease" if disease else "insect_host"):
            continue
        if int(item.get("class_id", -1)) != class_id or item.get("crop") != crop:
            continue
        if disease is not None and item.get("disease") != disease:
            continue
        severity = item.get("severity")
        if severity in SEVERITY_LEVELS:
            result[str(severity)] = item
    return result


@lru_cache(maxsize=1)
def _dataset() -> dict[str, Any]:
    manifest = _read_json(R31_ROOT / "manifest.json")
    evidence = _read_json(R31_ROOT / "severity-evidence.json")
    registry = _read_json(R31_ROOT / "capability-fallback.json")
    if manifest.get("capability_registry") != "capability-fallback.json":
        raise R31HostKnowledgeError("manifest capability registry pointer is invalid")
    if registry.get("treatment_fallback_order") != list(FALLBACK_ORDER):
        raise R31HostKnowledgeError("R3.1 treatment fallback order is invalid")
    source_by_id = {str(item["source_id"]): item for item in manifest.get("sources", []) if isinstance(item, dict) and item.get("source_id")}
    documents = {int(item["class_id"]): item for item in manifest.get("documents", []) if isinstance(item, dict)}
    capabilities = {
        (int(item["class_id"]), str(item["crop"])): item
        for item in registry.get("records", [])
        if isinstance(item, dict) and item.get("class_id") is not None and item.get("crop")
    }
    host_general = {
        (int(item["class_id"]), str(item["crop"])): item
        for item in registry.get("host_general_treatments", [])
        if isinstance(item, dict) and item.get("class_id") is not None and item.get("crop")
    }
    general_insect = {
        int(item["class_id"]): item
        for item in registry.get("general_insect_treatments", [])
        if isinstance(item, dict) and item.get("class_id") is not None
    }
    severity_records = [item for item in evidence.get("records", []) if isinstance(item, dict)]
    document_markdown: dict[int, str] = {}
    host_blocks: dict[tuple[int, str], str] = {}
    vector_blocks: dict[tuple[int, str], str] = {}
    for class_id, entry in documents.items():
        path = R31_ROOT / str(entry.get("document", ""))
        try:
            markdown = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise R31HostKnowledgeError(f"R3.1 insect document unavailable: {path}") from exc
        document_markdown[class_id] = markdown
        for crop, block in _host_blocks(markdown).items():
            host_blocks[(class_id, crop)] = block
        for disease, block in _vector_blocks(markdown).items():
            vector_blocks[(class_id, disease)] = block
    return {
        "manifest": manifest,
        "registry": registry,
        "source_by_id": source_by_id,
        "documents": documents,
        "capabilities": capabilities,
        "host_general": host_general,
        "general_insect": general_insect,
        "severity_records": severity_records,
        "document_markdown": document_markdown,
        "host_blocks": host_blocks,
        "vector_blocks": vector_blocks,
    }


def clear_cache() -> None:
    _dataset.cache_clear()


def is_insect_class(class_id: Any) -> bool:
    try:
        item = CLASS_BY_ID.get(int(class_id))
    except (TypeError, ValueError):
        return False
    return bool(item and item.get("type") == "害虫" and int(class_id) in _dataset()["documents"])


def _primary(record: Mapping[str, Any]) -> dict[str, Any]:
    summary = record.get("detector_summary")
    if isinstance(summary, dict) and isinstance(summary.get("primary_candidate"), dict):
        return dict(summary["primary_candidate"])
    detections = record.get("detections")
    if isinstance(detections, list) and detections and isinstance(detections[0], dict):
        return dict(detections[0])
    return {}


def _confirmed_host(record: Mapping[str, Any]) -> str | None:
    context = record.get("context")
    if not isinstance(context, dict):
        return None
    selection = context.get("host_selection")
    if isinstance(selection, dict) and isinstance(selection.get("confirmed_host"), str):
        return selection["confirmed_host"]
    return None


def _generic_evidence(record: Mapping[str, Any]) -> dict[str, Any]:
    analysis = record.get("analysis")
    analysis = analysis if isinstance(analysis, dict) else {}
    evidence = analysis.get("evidence_analysis")
    evidence = evidence if isinstance(evidence, dict) else {}
    return {
        "status": evidence.get("status", "unavailable"),
        "harms": deepcopy(evidence.get("harms") or []),
        "possible_causes": deepcopy(evidence.get("possible_causes") or []),
        "source_ids": list(analysis.get("source_ids") or []),
        "sources": deepcopy(analysis.get("sources") or []),
        "authority": "current R1 evidence semantics",
    }


def _host_option(item: Mapping[str, Any]) -> dict[str, Any]:
    capabilities = deepcopy(item.get("capabilities") or {})
    return {
        "crop": item.get("crop"),
        "status": item.get("status"),
        "capabilities": capabilities,
        "severity_available": bool(item.get("severity_available")),
    }


def _catalog(record: Mapping[str, Any], data: Mapping[str, Any], class_id: int) -> dict[str, Any]:
    entry = data["documents"].get(class_id) or {}
    supported: list[str] = []
    options: list[dict[str, Any]] = []
    for crop in entry.get("supported_hosts", []):
        capability = data["capabilities"].get((class_id, crop))
        if not isinstance(capability, dict) or capability.get("status") not in {"FULL", "PARTIAL"}:
            continue
        supported.append(str(crop))
        options.append(_host_option(capability))
    recommended = entry.get("recommended_host") if entry.get("recommended_host") in supported else None
    confirmed = _confirmed_host(record)
    return {
        "schema_version": "r31-backend-host-v1",
        "available": True,
        "class_id": class_id,
        "insect": entry.get("class_name") or CLASS_BY_ID[class_id]["name_zh"],
        "recommended_host": recommended,
        "recommended_label": f"推荐：常见寄主之一——{recommended}" if recommended else None,
        "supported_hosts": supported,
        "host_options": options,
        "other": {"value": OTHER_HOST, "label": "其他/暂未收录"},
        "confirmed_host": confirmed,
        "selection_required": confirmed is None,
        "host_authority": {
            "recommended_host_is_confirmed_host": False,
            "confirmation": "用户必须显式提交 supported_hosts 中的作物或固定 OTHER",
            "rejected_hosts_returned": False,
        },
        "generic_evidence": _generic_evidence(record),
    }


def _severity_payload(data: Mapping[str, Any], class_id: int, crop: str) -> dict[str, Any]:
    records = _severity_records(data["severity_records"], class_id, crop)
    available = all(records.get(level, {}).get("status") == "COMPLETE" and records[level].get("source_ids") for level in SEVERITY_LEVELS)
    if not available:
        return {"available": False, "levels": {}, "source_ids": [], "sources": [], "provenance": {"complete": False}}
    levels: dict[str, dict[str, Any]] = {}
    source_ids: list[str] = []
    for level in SEVERITY_LEVELS:
        item = records[level]
        ids = list(item.get("source_ids") or [])
        source_ids.extend(ids)
        levels[level] = {
            "level": level,
            "label": SEVERITY_LABELS[level],
            "rubric": item.get("rubric_text"),
            "rubric_text": item.get("rubric_text"),
            "observable_features": deepcopy(item.get("observable_features") or []),
            "source_ids": ids,
            "sources": _sources(ids, data["source_by_id"]),
            "evidence_type": item.get("evidence_type"),
            "synthesis_note": item.get("synthesis_note"),
        }
    source_ids = list(dict.fromkeys(source_ids))
    return {
        "available": True,
        "levels": levels,
        "source_ids": source_ids,
        "sources": _sources(source_ids, data["source_by_id"]),
        "provenance": {"complete": True, "source_ids": source_ids, "evidence_type": "item_level"},
    }


def _vector_diseases(data: Mapping[str, Any], class_id: int, crop: str, capability: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    blocks = data["vector_blocks"]
    for relation in (capability.get("vector_disease") or {}).get("relations", []):
        if not isinstance(relation, dict) or not relation.get("disease"):
            continue
        disease = str(relation["disease"])
        block = blocks.get((class_id, disease), "")
        source_ids = list(relation.get("source_ids") or [])
        severity_records = _severity_records(data["severity_records"], class_id, crop, disease)
        severity_available = all(
            severity_records.get(level, {}).get("status") == "COMPLETE" and severity_records[level].get("source_ids")
            for level in SEVERITY_LEVELS
        )
        severity = _severity_payload_for_records(data, severity_records) if severity_available else {"available": False, "levels": {}, "source_ids": [], "sources": []}
        result.append(
            {
                "disease": disease,
                "relationship": _bullet_value(block, "- 关系："),
                "symptoms": _bullet_value(block, "- 症状："),
                "general_disease_treatment": _bullet_value(block, "- 病害级通用控制："),
                "source_ids": source_ids,
                "sources": _sources(source_ids, data["source_by_id"]),
                "disease_severity_available": severity_available,
                "severity": severity,
            }
        )
    return result


def _severity_payload_for_records(data: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    levels: dict[str, dict[str, Any]] = {}
    source_ids: list[str] = []
    for level in SEVERITY_LEVELS:
        item = records[level]
        ids = list(item.get("source_ids") or [])
        source_ids.extend(ids)
        levels[level] = {
            "level": level,
            "label": SEVERITY_LABELS[level],
            "rubric": item.get("rubric_text"),
            "rubric_text": item.get("rubric_text"),
            "observable_features": deepcopy(item.get("observable_features") or []),
            "source_ids": ids,
            "sources": _sources(ids, data["source_by_id"]),
            "evidence_type": item.get("evidence_type"),
            "synthesis_note": item.get("synthesis_note"),
        }
    source_ids = list(dict.fromkeys(source_ids))
    return {"available": True, "levels": levels, "source_ids": source_ids, "sources": _sources(source_ids, data["source_by_id"])}


def _host_specific(data: Mapping[str, Any], class_id: int, crop: str, capability: Mapping[str, Any]) -> dict[str, Any]:
    block = data["host_blocks"].get((class_id, crop), "")
    damage_text = _section(block, "当前作物受害表现", level=3)
    relation_text = _bullet_value(block, "- 寄主关系：")
    damage_ids = list((capability.get("provenance") or {}).get("host_damage_source_ids") or [])
    relation_ids = list((capability.get("provenance") or {}).get("host_relation_source_ids") or [])
    host_damage = {
        "available": bool(capability.get("host_damage_available") and damage_text),
        "text": damage_text if capability.get("host_damage_available") else None,
        "source_ids": damage_ids if capability.get("host_damage_available") else [],
        "sources": _sources(damage_ids, data["source_by_id"]) if capability.get("host_damage_available") else [],
    }
    return {
        "relation": {
            "available": bool(capability.get("host_relation_available") and relation_text),
            "text": relation_text if capability.get("host_relation_available") else None,
            "source_ids": relation_ids if capability.get("host_relation_available") else [],
            "sources": _sources(relation_ids, data["source_by_id"]) if capability.get("host_relation_available") else [],
        },
        "damage": host_damage,
        "severity_available": bool(capability.get("severity_available")),
        "severity": _severity_payload(data, class_id, crop) if capability.get("severity_available") else {"available": False, "levels": {}, "source_ids": [], "sources": [], "provenance": {"complete": False}},
        "vector_diseases": _vector_diseases(data, class_id, crop, capability) if capability.get("vector_disease_available") else [],
        "provenance": deepcopy(capability.get("provenance") or {}),
    }


def _none_treatment(message: str) -> dict[str, Any]:
    return {
        "treatment_level": "none",
        "body": None,
        "source_ids": [],
        "provenance": {"type": "none", "complete": False},
        "fallback_message": message,
    }


def resolve_treatment(
    capability: Mapping[str, Any] | None,
    host_general: Mapping[str, Any] | None,
    host_severity: Mapping[str, Any] | None,
    insect_general: Mapping[str, Any] | None,
    severity: str | None,
) -> dict[str, Any]:
    """Resolve treatment without making severity or host claims."""
    capabilities = capability.get("capabilities") if isinstance(capability, Mapping) else {}
    capabilities = capabilities if isinstance(capabilities, Mapping) else {}
    severity_available = bool(capability.get("severity_available")) if isinstance(capability, Mapping) else False
    if severity in SEVERITY_LEVELS and capabilities.get("host_severity_treatment") and isinstance(host_severity, Mapping) and host_severity.get("available") and severity in (host_severity.get("supported_severities") or []):
        ids = list(host_severity.get("source_ids") or [])
        body = {
            "mode": "severity_adjusted_ipm",
            "sections": deepcopy((host_general or {}).get("sections") or {}),
            "pesticide_policy": (host_general or {}).get("pesticide_policy"),
            "severity_note": host_severity.get("note"),
        }
        return {
            "treatment_level": "host_severity",
            "body": body,
            "source_ids": ids,
            "provenance": {"type": "host_severity", "source_ids": ids, "complete": True},
            "fallback_message": FALLBACK_MESSAGES["host_severity"],
        }
    if isinstance(host_general, Mapping) and host_general.get("available"):
        ids = list(host_general.get("source_ids") or [])
        return {
            "treatment_level": "host_general",
            "treatment_mode": "generic",
            "body": {"sections": deepcopy(host_general.get("sections") or {}), "pesticide_policy": host_general.get("pesticide_policy")},
            "source_ids": ids,
            "provenance": {"type": "host_general", "source_ids": ids, "complete": bool(ids)},
            "fallback_message": FALLBACK_MESSAGES["host_general"] if severity_available else UNGRADED_HOST_GENERAL_MESSAGE,
        }
    if isinstance(insect_general, Mapping) and insect_general.get("available"):
        ids = list(insect_general.get("source_ids") or [])
        return {
            "treatment_level": "insect_general",
            "treatment_mode": "generic",
            "body": {"measures": deepcopy(insect_general.get("measures") or {}), "pesticide_policy": insect_general.get("pesticide_policy")},
            "source_ids": ids,
            "provenance": {"type": "insect_general", "source_ids": ids, "complete": bool(ids)},
            "fallback_message": FALLBACK_MESSAGES["insect_general"],
        }
    return _none_treatment("当前没有可用的防治资料。")


def _selected_severity(record: Mapping[str, Any]) -> str | None:
    severity = record.get("severity")
    if not isinstance(severity, dict):
        analysis = record.get("analysis")
        severity = analysis.get("severity") if isinstance(analysis, dict) else None
    value = severity.get("level") if isinstance(severity, dict) else None
    return value if value in (*SEVERITY_LEVELS, "uncertain") else None


def host_knowledge_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return catalog-only or confirmed-host knowledge for an insect case."""
    primary = _primary(record)
    class_id = primary.get("class_id")
    try:
        if not is_insect_class(class_id):
            return {"available": False, "reason": "not_insect"}
        class_id = int(class_id)
        data = _dataset()
        payload = _catalog(record, data, class_id)
    except R31HostKnowledgeError:
        return {"available": False, "reason": "knowledge_unavailable"}
    confirmed = payload["confirmed_host"]
    payload["host"] = None
    payload["host_knowledge"] = None
    payload["treatment"] = None
    if confirmed is None:
        return payload
    if confirmed == OTHER_HOST:
        general = data["general_insect"].get(class_id)
        payload["host"] = {"value": OTHER_HOST, "status": OTHER_HOST, "capabilities": {name: False for name in ("host_relation", "host_damage", "severity", "host_general_treatment", "host_severity_treatment", "vector_disease")}}
        payload["host_knowledge"] = {
            "host_relation": {"available": False},
            "damage": {"available": False},
            "severity_available": False,
            "severity": {"available": False, "levels": {}, "source_ids": [], "sources": []},
            "vector_diseases": [],
            "provenance": {"type": "other", "source_ids": []},
        }
        payload["treatment"] = {
            **resolve_treatment(None, None, None, general, _selected_severity(record)),
            "fallback_message": FALLBACK_MESSAGES["other"],
        }
        return payload
    capability = data["capabilities"].get((class_id, confirmed))
    if not isinstance(capability, dict) or capability.get("status") not in {"FULL", "PARTIAL"}:
        return {**payload, "confirmed_host": None, "selection_required": True, "host_selection_error": "confirmed_host_not_supported"}
    payload["host"] = _host_option(capability)
    payload["host_knowledge"] = _host_specific(data, class_id, confirmed, capability)
    payload["treatment"] = resolve_treatment(
        capability,
        data["host_general"].get((class_id, confirmed)),
        capability.get("host_severity_treatment"),
        data["general_insect"].get(class_id),
        _selected_severity(record),
    )
    return payload


def host_selection_snapshot(record: Mapping[str, Any], confirmed_host: str) -> dict[str, Any]:
    """Build the persisted, auditable selection snapshot after explicit confirmation."""
    primary = _primary(record)
    class_id = int(primary["class_id"])
    data = _dataset()
    capability = data["capabilities"].get((class_id, confirmed_host)) if confirmed_host != OTHER_HOST else None
    return {
        "schema_version": "r31-host-selection-v1",
        "authority": "user_confirmed",
        "confirmed_host": confirmed_host,
        "class_id": class_id,
        "insect": CLASS_BY_ID[class_id]["name_zh"],
        "catalog_closure": data["manifest"].get("closure"),
        "capability_snapshot": deepcopy(capability.get("capabilities") if isinstance(capability, dict) else {name: False for name in ("host_relation", "host_damage", "severity", "host_general_treatment", "host_severity_treatment", "vector_disease")}),
        "status_snapshot": capability.get("status") if isinstance(capability, dict) else OTHER_HOST,
    }


def confirmable_hosts(record: Mapping[str, Any]) -> set[str]:
    current_context = record.get("context")
    context = deepcopy(current_context) if isinstance(current_context, dict) else {}
    context["host_selection"] = {"confirmed_host": None}
    payload = host_knowledge_payload({**record, "context": context})
    if not payload.get("available"):
        return set()
    return set(payload.get("supported_hosts") or []) | {OTHER_HOST}
