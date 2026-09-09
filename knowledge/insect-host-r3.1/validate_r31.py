"""Deterministic validator for the R3.1 insect × host-crop knowledge layer.

This validator is deliberately independent from the frozen product knowledge
runtime.  It validates the Markdown SSOT against the R3.1 manifest/source
ledger and fails closed: NEEDS_EVIDENCE is never promoted to COMPLETE.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


SOURCE_REF = re.compile(r"\[(R31-[A-Z0-9-]+)\]")
HOST_HEADING = re.compile(r"^### 寄主：(.+?)\s*$")
DISEASE_HEADING = re.compile(r"^### 病害：(.+?)\s*$")
TOP_HEADING = re.compile(r"^## (.+?)\s*$")
SUB_HEADING = re.compile(r"^#### (.+?)\s*$")
SECTION_HEADING = re.compile(r"^### (?!#)(.+?)\s*$")
NEEDS = "NEEDS_EVIDENCE"
COMPLETE = "COMPLETE"
INVALID = "INVALID"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
EVIDENCE_TYPES = {"DIRECT_GRADE", "EVIDENCE_SYNTHESIZED"}
TAXONOMIC_LEVELS = {"family", "superfamily", "genus", "species", "source_named_group"}
SOURCE_SEMANTIC_REVIEW_VALUES = {"PASS", "NEEDS_REVIEW"}
GLOBAL_SOURCE_IDS = {"R31-GLOBAL-IPM-MOA", "R31-GLOBAL-IPM-FAO"}

SEVERITY_HEADINGS = ("轻度", "中度", "重度")
TREATMENT_HEADINGS = ("预防与监测", "生物与物理", "化学防治边界")
REQUIRED_HOST_SECTIONS = ("当前作物受害表现", "严重程度", "防治方法")
QUANTITATIVE_MARKERS = re.compile(
    r"(?:%|％|百分比|每株|每叶|虫口|株率|面积比例|产量(?:下降|损失)?\s*\d|\d+(?:\.\d+)?\s*(?:头|只|株|叶|亩|克|毫升|倍液|天|次))"
)


@dataclass(frozen=True)
class Issue:
    level: str
    message: str


@dataclass(frozen=True)
class Result:
    status: str
    issues: tuple[Issue, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "issues": [{"level": item.level, "message": item.message} for item in self.issues],
        }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sections(markdown: str) -> dict[str, str]:
    lines = markdown.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = TOP_HEADING.match(line)
        if match:
            starts.append((index, match.group(1)))
    result: dict[str, str] = {}
    for position, (start, title) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        result[title] = "\n".join(lines[start + 1 : end]).strip()
    return result


def _host_blocks(section: str) -> dict[str, str]:
    lines = section.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = HOST_HEADING.match(line)
        if match:
            starts.append((index, match.group(1).strip()))
    result: dict[str, str] = {}
    for position, (start, crop) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        result[crop] = "\n".join(lines[start + 1 : end]).strip()
    return result


def _subsections(section: str, *, level: int = 4) -> dict[str, str]:
    lines = section.splitlines()
    starts: list[tuple[int, str]] = []
    heading = SECTION_HEADING if level == 3 else SUB_HEADING
    for index, line in enumerate(lines):
        match = heading.match(line)
        if match:
            starts.append((index, match.group(1).strip()))
    result: dict[str, str] = {}
    for position, (start, title) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        result[title] = "\n".join(lines[start + 1 : end]).strip()
    return result


def _refs(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(match.group(1) for match in SOURCE_REF.finditer(text)))


def _has_evidence_marker(text: str) -> bool:
    return NEEDS in text or "待补证" in text or "尚无逐项证据" in text


def _source_context_allowed(source: dict[str, Any], context: str, class_id: int, crop: str | None = None) -> bool:
    allowed = set(source.get("allowed_contexts", []))
    if "global:ipm" in allowed or f"class:{class_id}" in allowed:
        return True
    if crop is not None and f"host:{class_id}:{crop}" in allowed:
        return True
    return context in allowed


def _validate_sources(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[Issue]]:
    issues: list[Issue] = []
    records: dict[str, dict[str, Any]] = {}
    for source in manifest.get("sources", []):
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id.startswith("R31-"):
            issues.append(Issue(INVALID, f"invalid source_id: {source_id!r}"))
            continue
        if source_id in records:
            issues.append(Issue(INVALID, f"duplicate source_id: {source_id}"))
            continue
        url = str(source.get("url", ""))
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            issues.append(Issue(INVALID, f"source has invalid url: {source_id}"))
        for field in ("title", "organization", "accessed_at", "support_scope", "tier", "allowed_contexts"):
            if not source.get(field):
                issues.append(Issue(INVALID, f"source missing {field}: {source_id}"))
        if source.get("critical") and not (
            str(source.get("source_reachability", "")).startswith(("REACHABLE", "LIVE_URL", "STABLE_DOI", "OFFICIAL_ARCHIVE"))
            or source.get("verified_backup_source_ids")
        ):
            issues.append(Issue(REVIEW_REQUIRED, f"critical source reachability requires review: {source_id}"))
        records[source_id] = source
    return records, issues


def _validate_refs(
    text: str,
    source_records: dict[str, dict[str, Any]],
    class_id: int,
    crop: str | None,
    context: str,
    issues: list[Issue],
) -> tuple[str, ...]:
    refs = _refs(text)
    for source_id in refs:
        source = source_records.get(source_id)
        if source is None:
            issues.append(Issue(INVALID, f"dangling source reference: {source_id}"))
            continue
        if not _source_context_allowed(source, context, class_id, crop):
            issues.append(Issue(INVALID, f"source {source_id} is out of scope for {context}"))
    return refs


def _registry_path(manifest: dict[str, Any], root: Path) -> Path:
    relative = manifest.get("evidence_registry")
    if not isinstance(relative, str) or not relative:
        raise ValueError("manifest evidence_registry is missing")
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    return path


def _record_key(record: dict[str, Any]) -> tuple[Any, ...]:
    object_type = record.get("object_type")
    if object_type == "insect_host":
        return (object_type, record.get("class_id"), record.get("crop"), record.get("severity"))
    if object_type == "plant_disease":
        return (object_type, record.get("class_id"), record.get("crop"), record.get("severity"))
    if object_type == "vector_disease":
        return (object_type, record.get("class_id"), record.get("crop"), record.get("disease"), record.get("severity"))
    return (object_type, record.get("class_id"), record.get("severity"))


def _record_text(record: dict[str, Any]) -> str:
    features = record.get("observable_features", [])
    if not isinstance(features, list):
        features = [str(features)]
    return " ".join(str(value) for value in [record.get("rubric_text", ""), *features, record.get("synthesis_note", "")])


def _has_unsupported_quantitative_claim(text: str) -> bool:
    for match in QUANTITATIVE_MARKERS.finditer(text):
        prefix = text[max(0, match.start() - 16) : match.start()]
        if re.search(r"(?:不|未|无|禁止|不得|不应|不将).{0,10}$", prefix):
            continue
        return True
    return False


def _validate_taxonomic_scope(record: dict[str, Any], source_records: dict[str, dict[str, Any]], prefix: str, issues: list[Issue]) -> None:
    """Validate explicit taxon/rank provenance without pretending to prove entailment."""
    taxon = record.get("evidence_taxon")
    levels = record.get("evidence_taxon_level")
    scopes = record.get("evidence_taxon_scope")
    if not isinstance(taxon, list) or not taxon or not all(isinstance(value, str) and value.strip() for value in taxon):
        issues.append(Issue(INVALID, f"{prefix}: evidence_taxon must be a non-empty text list"))
    if not isinstance(levels, list) or not levels or not all(value in TAXONOMIC_LEVELS for value in levels):
        issues.append(Issue(INVALID, f"{prefix}: evidence_taxon_level must use explicit taxonomic levels"))
    if not isinstance(scopes, list) or not scopes:
        issues.append(Issue(INVALID, f"{prefix}: evidence_taxon_scope must map sources to taxon/rank"))
        return
    source_ids = set(record.get("source_ids", []))
    for scope in scopes:
        if not isinstance(scope, dict):
            issues.append(Issue(INVALID, f"{prefix}: evidence_taxon_scope item must be an object"))
            continue
        source_id = scope.get("source_id")
        if source_id not in source_ids:
            issues.append(Issue(INVALID, f"{prefix}: taxon scope source is not in source_ids: {source_id}"))
        if source_id not in source_records:
            issues.append(Issue(INVALID, f"{prefix}: taxon scope has dangling source: {source_id}"))
        if not isinstance(scope.get("evidence_taxon"), str) or not scope.get("evidence_taxon"):
            issues.append(Issue(INVALID, f"{prefix}: taxon scope missing evidence_taxon: {source_id}"))
        if scope.get("evidence_taxon_level") not in TAXONOMIC_LEVELS:
            issues.append(Issue(INVALID, f"{prefix}: taxon scope has invalid rank: {source_id}"))
        if not isinstance(scope.get("scope_note"), str) or not scope.get("scope_note"):
            issues.append(Issue(INVALID, f"{prefix}: taxon scope missing scope_note: {source_id}"))
    if record.get("SOURCE_SEMANTIC_REVIEW") not in SOURCE_SEMANTIC_REVIEW_VALUES:
        issues.append(Issue(INVALID, f"{prefix}: SOURCE_SEMANTIC_REVIEW must be PASS or NEEDS_REVIEW"))


def _validate_evidence_registry(
    manifest: dict[str, Any],
    source_records: dict[str, dict[str, Any]],
    root: Path,
) -> tuple[dict[str, Any], list[Issue]]:
    issues: list[Issue] = []
    try:
        registry_path = _registry_path(manifest, root)
        registry = _read_json(registry_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {}, [Issue(INVALID, f"cannot read evidence registry: {exc}")]

    if registry.get("schema_version") != "r31-severity-evidence-v1":
        issues.append(Issue(INVALID, "unsupported evidence registry schema_version"))
    if registry.get("notice") != manifest.get("policy", {}).get("severity_notice"):
        issues.append(Issue(INVALID, "evidence registry severity notice does not match manifest policy"))

    records = registry.get("records")
    if not isinstance(records, list):
        return registry, issues + [Issue(INVALID, "evidence registry records must be a list")]

    expected_hosts = {
        (int(entry["class_id"]), str(crop))
        for entry in manifest.get("documents", [])
        for crop in entry.get("supported_hosts", [])
    }
    expected_vectors = {
        (9, "大豆", "大豆花叶病"),
        (9, "小麦", "小麦黄矮病"),
        (12, "水稻", "水稻橙叶病"),
        (12, "水稻", "水稻矮缩病毒"),
    }
    seen: set[tuple[Any, ...]] = set()
    rubric_groups: dict[str, list[dict[str, Any]]] = {}
    status_counts: dict[str, int] = {}

    for index, record in enumerate(records):
        prefix = f"evidence record {index}"
        if not isinstance(record, dict):
            issues.append(Issue(INVALID, f"{prefix} must be an object"))
            continue
        object_type = record.get("object_type")
        if object_type not in {"insect_host", "plant_disease", "vector_disease"}:
            issues.append(Issue(INVALID, f"{prefix}: invalid object_type"))
            continue
        key = _record_key(record)
        if key in seen:
            issues.append(Issue(INVALID, f"duplicate evidence record: {key}"))
        seen.add(key)

        status = record.get("status")
        count_key = f"{object_type}:{status}"
        status_counts[count_key] = status_counts.get(count_key, 0) + 1
        if status not in {COMPLETE, NEEDS}:
            issues.append(Issue(INVALID, f"{prefix}: invalid status {status!r}"))
        severity = record.get("severity")
        if severity not in {"mild", "moderate", "severe"}:
            issues.append(Issue(INVALID, f"{prefix}: invalid severity"))

        for field in ("rubric_text", "synthesis_note"):
            if not isinstance(record.get(field), str):
                issues.append(Issue(INVALID, f"{prefix}: {field} must be text"))
        features = record.get("observable_features")
        source_ids = record.get("source_ids")
        if not isinstance(features, list) or not all(isinstance(value, str) and value.strip() for value in features):
            issues.append(Issue(INVALID, f"{prefix}: observable_features must be a non-empty text list"))
        if not isinstance(source_ids, list) or not all(isinstance(value, str) and value.strip() for value in source_ids):
            issues.append(Issue(INVALID, f"{prefix}: source_ids must be a non-empty text list"))
            source_ids = []
        evidence_type = record.get("evidence_type")
        if evidence_type not in EVIDENCE_TYPES:
            issues.append(Issue(INVALID, f"{prefix}: invalid evidence_type"))
        if status == COMPLETE:
            if not source_ids:
                issues.append(Issue(INVALID, f"{prefix}: COMPLETE record has no source_ids"))
            if evidence_type == "EVIDENCE_SYNTHESIZED" and (
                not str(record.get("synthesis_note", "")).strip()
                or "evidence_synthesized" not in str(record.get("synthesis_note", ""))
            ):
                issues.append(Issue(INVALID, f"{prefix}: synthesized COMPLETE record has no synthesis_note"))

        if object_type == "insect_host":
            host_key = (record.get("class_id"), record.get("crop"))
            if host_key not in expected_hosts:
                issues.append(Issue(INVALID, f"{prefix}: host is not in manifest: {host_key}"))
            context = f"host:{record.get('class_id')}:{record.get('crop')}"
            rubric_groups.setdefault(re.sub(r"\s+", " ", str(record.get("rubric_text", "")).strip()), []).append(record)
            _validate_taxonomic_scope(record, source_records, prefix, issues)
        elif object_type == "plant_disease":
            if not isinstance(record.get("class_id"), int) or record.get("class_id") not in range(8):
                issues.append(Issue(INVALID, f"{prefix}: plant disease class_id must be 0..7"))
            context = f"plant:{record.get('class_id')}"
        else:
            vector_key = (record.get("class_id"), record.get("crop"), record.get("disease"))
            if vector_key not in expected_vectors:
                issues.append(Issue(INVALID, f"{prefix}: vector relation is not an approved relation: {vector_key}"))
            context = f"vector:{record.get('class_id')}:{record.get('disease')}"
            _validate_taxonomic_scope(record, source_records, prefix, issues)

        for source_id in source_ids:
            source = source_records.get(source_id)
            if source is None:
                issues.append(Issue(INVALID, f"{prefix}: dangling source reference: {source_id}"))
            elif not _source_context_allowed(source, context, int(record.get("class_id", -1)), record.get("crop") if object_type == "insect_host" else None):
                issues.append(Issue(INVALID, f"{prefix}: source {source_id} is out of scope for {context}"))

        text = _record_text(record)
        if _has_unsupported_quantitative_claim(text):
            supported = bool(record.get("quantitative_support")) and all(
                bool(source_records.get(source_id, {}).get("quantitative_support")) for source_id in source_ids
            )
            if not supported:
                issues.append(Issue(INVALID, f"{prefix}: unsupported quantitative claim"))

    expected_counts = {"insect_host": 114, "plant_disease": 24, "vector_disease": 12}
    for object_type, expected in expected_counts.items():
        actual = sum(1 for record in records if isinstance(record, dict) and record.get("object_type") == object_type)
        if actual != expected:
            issues.append(Issue(INVALID, f"evidence registry {object_type} count {actual} != {expected}"))

    for normalized_text, group in rubric_groups.items():
        host_pairs = {(record.get("class_id"), record.get("crop")) for record in group}
        if normalized_text and len(host_pairs) > 1:
            issues.append(Issue(REVIEW_REQUIRED, f"duplicate rubric across insect×host records: {normalized_text}"))

    treatment = registry.get("treatment_audit")
    if not isinstance(treatment, list) or len(treatment) != 38:
        issues.append(Issue(INVALID, "treatment_audit must contain exactly 38 host records"))
    else:
        treatment_keys: set[tuple[Any, Any]] = set()
        for index, item in enumerate(treatment):
            prefix = f"treatment audit {index}"
            key = (item.get("class_id"), item.get("crop"))
            if key in treatment_keys or key not in expected_hosts:
                issues.append(Issue(INVALID, f"{prefix}: invalid or duplicate host key {key}"))
            treatment_keys.add(key)
            if item.get("status") not in {"BASE_IPM_ONLY", "SEVERITY_SPECIFIC_SUPPORTED"}:
                issues.append(Issue(INVALID, f"{prefix}: invalid treatment status"))
            item_source_ids = item.get("source_ids", [])
            if not isinstance(item_source_ids, list) or not item_source_ids:
                issues.append(Issue(INVALID, f"{prefix}: missing source_ids"))
                continue
            context = f"host:{item.get('class_id')}:{item.get('crop')}"
            for source_id in item_source_ids:
                source = source_records.get(source_id)
                if source is None:
                    issues.append(Issue(INVALID, f"{prefix}: dangling source reference: {source_id}"))
                elif not _source_context_allowed(source, context, int(item.get("class_id", -1)), item.get("crop")):
                    issues.append(Issue(INVALID, f"{prefix}: source {source_id} is out of scope for {context}"))
            if item.get("status") == "BASE_IPM_ONLY" and "基础" not in str(item.get("note", "")):
                issues.append(Issue(INVALID, f"{prefix}: BASE_IPM_ONLY lacks explicit base-IPM note"))
            if item.get("SOURCE_SEMANTIC_REVIEW") not in SOURCE_SEMANTIC_REVIEW_VALUES:
                issues.append(Issue(INVALID, f"{prefix}: SOURCE_SEMANTIC_REVIEW must be PASS or NEEDS_REVIEW"))
            specific = item.get("host_specific_source_ids")
            if not isinstance(specific, list) or any(source_id in GLOBAL_SOURCE_IDS for source_id in specific):
                issues.append(Issue(INVALID, f"{prefix}: host_specific_source_ids must contain only non-global sources"))
            if bool(item.get("host_specific_evidence")) != bool(specific):
                issues.append(Issue(INVALID, f"{prefix}: host_specific_evidence does not mirror host_specific_source_ids"))

    summary = {
        "counts": status_counts,
        "record_count": len(records),
        "treatment_audit_count": len(treatment) if isinstance(treatment, list) else 0,
        "registry_path": str(registry_path),
    }
    return summary, issues


def _validate_capability_registry(
    manifest: dict[str, Any],
    source_records: dict[str, dict[str, Any]],
    root: Path,
    severity_records: list[dict[str, Any]],
    treatment_records: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[Issue]]:
    issues: list[Issue] = []
    relative = manifest.get("capability_registry")
    if not isinstance(relative, str) or not relative:
        return {}, [Issue(INVALID, "manifest capability_registry is missing")]
    capability_path = (root / relative).resolve()
    try:
        capability_path.relative_to(root.resolve())
        registry = _read_json(capability_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {}, [Issue(INVALID, f"cannot read capability registry: {exc}")]

    if registry.get("schema_version") != "r31-adaptive-capability-v1":
        issues.append(Issue(INVALID, "unsupported capability registry schema_version"))
    expected_order = ["host_severity", "host_general", "insect_general"]
    if registry.get("treatment_fallback_order") != expected_order or manifest.get("treatment_fallback_order") != expected_order:
        issues.append(Issue(INVALID, "treatment fallback order is not the approved order"))
    if manifest.get("uncertain_treatment_level") != "none":
        issues.append(Issue(INVALID, "manifest uncertain_treatment_level must be none"))
    policy = manifest.get("policy", {})
    if policy.get("severity_treatment_decoupled") is not True or policy.get("uncertain_treatment") != "NO_TREATMENT":
        issues.append(Issue(INVALID, "manifest policy does not declare severity/treatment decoupling and uncertain=NO_TREATMENT"))

    expected_hosts = {
        (int(entry["class_id"]), str(crop))
        for entry in manifest.get("documents", [])
        for crop in entry.get("supported_hosts", [])
    }
    expected_insects = {int(entry["class_id"]): entry["class_name"] for entry in manifest.get("documents", [])}
    severity_complete: dict[tuple[int, str], bool] = {}
    severity_seen: dict[tuple[int, str], set[str]] = {}
    for item in severity_records:
        if item.get("object_type") != "insect_host":
            continue
        key = (item.get("class_id"), item.get("crop"))
        severity_seen.setdefault(key, set()).add(item.get("severity"))
        if item.get("status") == COMPLETE and item.get("source_ids"):
            severity_complete.setdefault(key, set())
            severity_complete[key].add(item.get("severity"))
    severity_available = {key: values == {"mild", "moderate", "severe"} for key, values in severity_complete.items()}
    severity_treatment_audited = {
        (item.get("class_id"), item.get("crop")): item.get("status") == "SEVERITY_SPECIFIC_SUPPORTED"
        for item in treatment_records
        if isinstance(item, dict)
    }

    records = registry.get("records")
    if not isinstance(records, list) or len(records) != len(expected_hosts):
        issues.append(Issue(INVALID, f"capability records count must be {len(expected_hosts)}"))
        records = records if isinstance(records, list) else []
    seen_hosts: set[tuple[Any, Any]] = set()
    capability_names = {"host_relation", "host_damage", "severity", "host_general_treatment", "host_severity_treatment", "vector_disease"}
    for index, item in enumerate(records):
        prefix = f"capability record {index}"
        if not isinstance(item, dict):
            issues.append(Issue(INVALID, f"{prefix} must be an object"))
            continue
        key = (item.get("class_id"), item.get("crop"))
        if key in seen_hosts or key not in expected_hosts:
            issues.append(Issue(INVALID, f"{prefix}: invalid or duplicate host key {key}"))
        seen_hosts.add(key)
        if item.get("insect") != expected_insects.get(item.get("class_id")):
            issues.append(Issue(INVALID, f"{prefix}: insect/class mismatch"))
        status = item.get("status")
        if status not in {"FULL", "PARTIAL", "REJECTED"}:
            issues.append(Issue(INVALID, f"{prefix}: invalid host status"))
        capabilities = item.get("capabilities")
        if not isinstance(capabilities, dict) or set(capabilities) != capability_names or not all(isinstance(value, bool) for value in capabilities.values()):
            issues.append(Issue(INVALID, f"{prefix}: capabilities must contain six boolean fields"))
            capabilities = {name: False for name in capability_names}
        aliases = {
            "host_relation_available": "host_relation",
            "host_damage_available": "host_damage",
            "severity_available": "severity",
            "host_general_treatment_available": "host_general_treatment",
            "host_severity_treatment_available": "host_severity_treatment",
            "vector_disease_available": "vector_disease",
        }
        for alias, capability_name in aliases.items():
            if item.get(alias) is not capabilities[capability_name]:
                issues.append(Issue(INVALID, f"{prefix}: {alias} does not mirror capabilities.{capability_name}"))
        expected_severity = severity_available.get(key, False)
        if item.get("severity_available") is not expected_severity or capabilities["severity"] is not expected_severity:
            issues.append(Issue(INVALID, f"{prefix}: severity_available does not equal complete three-tier evidence"))
        host_general = item.get("host_general_treatment")
        if not isinstance(host_general, dict) or host_general.get("treatment_level") != "host_general":
            issues.append(Issue(INVALID, f"{prefix}: malformed host_general_treatment"))
            host_general = {}
        if host_general.get("available") is not capabilities["host_general_treatment"]:
            issues.append(Issue(INVALID, f"{prefix}: host_general capability mismatch"))
        host_general_sources = host_general.get("source_ids", [])
        if capabilities["host_general_treatment"] and not host_general_sources:
            issues.append(Issue(INVALID, f"{prefix}: available host_general_treatment has no source_ids"))
        for source_id in host_general_sources:
            source = source_records.get(source_id)
            if source is None:
                issues.append(Issue(INVALID, f"{prefix}: dangling host_general source {source_id}"))
            elif not _source_context_allowed(source, f"host:{item.get('class_id')}:{item.get('crop')}", int(item.get("class_id", -1)), item.get("crop")):
                issues.append(Issue(INVALID, f"{prefix}: host_general source {source_id} is out of scope"))

        host_severity = item.get("host_severity_treatment")
        if not isinstance(host_severity, dict) or host_severity.get("treatment_level") != "host_severity":
            issues.append(Issue(INVALID, f"{prefix}: malformed host_severity_treatment"))
            host_severity = {}
        if host_severity.get("available") is not capabilities["host_severity_treatment"]:
            issues.append(Issue(INVALID, f"{prefix}: host_severity capability mismatch"))
        if capabilities["host_severity_treatment"] is not severity_treatment_audited.get(key, False):
            issues.append(Issue(INVALID, f"{prefix}: host_severity capability is not backed by the treatment audit"))
        supported_severities = host_severity.get("supported_severities", [])
        expected_supported = ["mild", "moderate", "severe"] if capabilities["host_severity_treatment"] else []
        if supported_severities != expected_supported:
            issues.append(Issue(INVALID, f"{prefix}: host_severity supported_severities mismatch"))
        for source_id in host_severity.get("source_ids", []):
            source = source_records.get(source_id)
            if source is None:
                issues.append(Issue(INVALID, f"{prefix}: dangling host_severity source {source_id}"))
            elif not _source_context_allowed(source, f"host:{item.get('class_id')}:{item.get('crop')}", int(item.get("class_id", -1)), item.get("crop")):
                issues.append(Issue(INVALID, f"{prefix}: host_severity source {source_id} is out of scope"))

        vector = item.get("vector_disease")
        if not isinstance(vector, dict) or vector.get("available") is not capabilities["vector_disease"]:
            issues.append(Issue(INVALID, f"{prefix}: vector capability mismatch"))
            vector = {}
        relations = vector.get("relations", [])
        if not capabilities["vector_disease"] and relations:
            issues.append(Issue(INVALID, f"{prefix}: vector=false must not expose relations"))
        for relation in relations:
            if not isinstance(relation, dict) or not relation.get("disease") or not relation.get("source_ids"):
                issues.append(Issue(INVALID, f"{prefix}: malformed vector relation"))
                continue
            context = f"vector:{item.get('class_id')}:{relation.get('disease')}"
            for source_id in relation["source_ids"]:
                source = source_records.get(source_id)
                if source is None:
                    issues.append(Issue(INVALID, f"{prefix}: dangling vector source {source_id}"))
                elif not _source_context_allowed(source, context, int(item.get("class_id", -1))):
                    issues.append(Issue(INVALID, f"{prefix}: vector source {source_id} is out of scope"))

        provenance = item.get("provenance")
        if not isinstance(provenance, dict) or provenance.get("complete") is not bool(provenance.get("host_relation_source_ids")) or provenance.get("complete") is not bool(provenance.get("host_damage_source_ids")) or provenance.get("complete") is not bool(provenance.get("host_general_treatment_source_ids")):
            issues.append(Issue(INVALID, f"{prefix}: provenance completeness mismatch"))
        if isinstance(provenance, dict):
            provenance_contexts = {
                "host_relation_source_ids": f"host:{item.get('class_id')}:{item.get('crop')}",
                "host_damage_source_ids": f"host:{item.get('class_id')}:{item.get('crop')}",
                "host_general_treatment_source_ids": f"host:{item.get('class_id')}:{item.get('crop')}",
                "host_severity_treatment_source_ids": f"host:{item.get('class_id')}:{item.get('crop')}",
            }
            for field, context in provenance_contexts.items():
                values = provenance.get(field, [])
                if not isinstance(values, list):
                    issues.append(Issue(INVALID, f"{prefix}: {field} must be a source-id list"))
                    continue
                for source_id in values:
                    source = source_records.get(source_id)
                    if source is None:
                        issues.append(Issue(INVALID, f"{prefix}: dangling provenance source {source_id}"))
                    elif not _source_context_allowed(source, context, int(item.get("class_id", -1)), item.get("crop")):
                        issues.append(Issue(INVALID, f"{prefix}: provenance source {source_id} is out of scope"))
            vector_values = provenance.get("vector_disease_source_ids", [])
            if not isinstance(vector_values, list):
                issues.append(Issue(INVALID, f"{prefix}: vector_disease_source_ids must be a source-id list"))
            else:
                for source_id in vector_values:
                    if source_id not in source_records:
                        issues.append(Issue(INVALID, f"{prefix}: dangling vector provenance source {source_id}"))
        expected_full = capabilities["host_relation"] and capabilities["host_damage"] and expected_severity and (capabilities["host_general_treatment"] or capabilities["host_severity_treatment"]) and bool(provenance.get("complete"))
        expected_status = "REJECTED" if not capabilities["host_relation"] else ("FULL" if expected_full else "PARTIAL")
        if status != expected_status:
            issues.append(Issue(INVALID, f"{prefix}: status {status!r} does not match capabilities ({expected_status})"))

        fallback = item.get("effective_treatment_fallback")
        if not isinstance(fallback, dict) or set(fallback) != {"mild", "moderate", "severe", "uncertain"}:
            issues.append(Issue(INVALID, f"{prefix}: malformed effective_treatment_fallback"))
            fallback = {}
        expected_level = "host_severity" if capabilities["host_severity_treatment"] else ("host_general" if capabilities["host_general_treatment"] else "insect_general")
        for severity in ("mild", "moderate", "severe"):
            if fallback.get(severity) != expected_level:
                issues.append(Issue(INVALID, f"{prefix}: {severity} fallback must be {expected_level}"))
        if fallback.get("uncertain") != "none" or item.get("fallback_level") != expected_level:
            issues.append(Issue(INVALID, f"{prefix}: uncertain/fallback_level semantics are invalid"))

    if set(seen_hosts) != expected_hosts:
        issues.append(Issue(INVALID, "capability registry host set does not match manifest"))

    host_general_records = registry.get("host_general_treatments")
    if not isinstance(host_general_records, list) or len(host_general_records) != len(expected_hosts):
        issues.append(Issue(INVALID, "host_general_treatments must contain one record per manifest host"))
        host_general_records = host_general_records if isinstance(host_general_records, list) else []
    seen_general: set[tuple[Any, Any]] = set()
    for index, item in enumerate(host_general_records):
        prefix = f"host_general treatment {index}"
        key = (item.get("class_id"), item.get("crop")) if isinstance(item, dict) else (None, None)
        if key in seen_general or key not in expected_hosts:
            issues.append(Issue(INVALID, f"{prefix}: invalid or duplicate host key {key}"))
        seen_general.add(key)
        if not isinstance(item, dict) or item.get("object_type") != "HOST_GENERAL_TREATMENT" or item.get("treatment_level") != "host_general" or item.get("available") is not True:
            issues.append(Issue(INVALID, f"{prefix}: malformed available HOST_GENERAL_TREATMENT"))
            continue
        source_ids = item.get("source_ids", [])
        if not isinstance(source_ids, list) or not source_ids:
            issues.append(Issue(INVALID, f"{prefix}: missing source_ids"))
            continue
        for source_id in source_ids:
            source = source_records.get(source_id)
            if source is None:
                issues.append(Issue(INVALID, f"{prefix}: dangling source {source_id}"))
            elif not _source_context_allowed(source, f"host:{item.get('class_id')}:{item.get('crop')}", int(item.get("class_id", -1)), item.get("crop")):
                issues.append(Issue(INVALID, f"{prefix}: source {source_id} is out of scope"))

    general_records = registry.get("general_insect_treatments")
    if not isinstance(general_records, list) or len(general_records) != len(expected_insects):
        issues.append(Issue(INVALID, f"general_insect_treatments must contain {len(expected_insects)} records"))
        general_records = general_records if isinstance(general_records, list) else []
    seen_classes: set[Any] = set()
    for index, item in enumerate(general_records):
        prefix = f"general insect treatment {index}"
        if not isinstance(item, dict):
            issues.append(Issue(INVALID, f"{prefix} must be an object"))
            continue
        class_id = item.get("class_id")
        if class_id in seen_classes or class_id not in expected_insects:
            issues.append(Issue(INVALID, f"{prefix}: invalid or duplicate class_id"))
        seen_classes.add(class_id)
        if item.get("insect") != expected_insects.get(class_id) or item.get("object_type") != "GENERAL_INSECT_TREATMENT" or item.get("treatment_level") != "insect_general" or item.get("available") is not True:
            issues.append(Issue(INVALID, f"{prefix}: malformed GENERAL_INSECT_TREATMENT"))
        source_ids = item.get("source_ids", [])
        if not isinstance(source_ids, list) or not source_ids:
            issues.append(Issue(INVALID, f"{prefix}: missing source_ids"))
        for source_id in source_ids:
            source = source_records.get(source_id)
            if source is None:
                issues.append(Issue(INVALID, f"{prefix}: dangling source {source_id}"))
            elif "global:ipm" not in set(source.get("allowed_contexts", [])):
                issues.append(Issue(INVALID, f"{prefix}: general treatment source must be global IPM: {source_id}"))
        measures = item.get("measures", {})
        if not isinstance(measures, dict) or not measures or _has_unsupported_quantitative_claim(" ".join(str(value) for value in measures.values())):
            issues.append(Issue(INVALID, f"{prefix}: general treatment contains unsupported quantitative content"))

    other = registry.get("other")
    if not isinstance(other, dict) or other.get("free_input") is not False or other.get("host_damage") is not False or other.get("severity") is not False or other.get("vector_disease") is not False or other.get("host_specific_treatment") is not False or other.get("treatment_level") != "insect_general":
        issues.append(Issue(INVALID, "OTHER policy is not fail-closed"))
    uncertain = registry.get("uncertain")
    if not isinstance(uncertain, dict) or uncertain.get("treatment_level") != "none" or uncertain.get("treatment") is not None:
        issues.append(Issue(INVALID, "uncertain policy must be NO_TREATMENT"))

    manifest_capabilities = manifest.get("host_capabilities")
    if not isinstance(manifest_capabilities, list) or len(manifest_capabilities) != len(records):
        issues.append(Issue(INVALID, "manifest host_capabilities must mirror the 38 registry records"))
    else:
        registry_projection = [(item.get("class_id"), item.get("crop"), item.get("status"), item.get("capabilities")) for item in records if isinstance(item, dict)]
        manifest_projection = [(item.get("class_id"), item.get("crop"), item.get("status"), item.get("capabilities")) for item in manifest_capabilities if isinstance(item, dict)]
        if manifest_projection != registry_projection:
            issues.append(Issue(INVALID, "manifest host_capabilities does not mirror capability registry"))

    summary = {
        "record_count": len(records),
        "status_counts": {status: sum(1 for item in records if isinstance(item, dict) and item.get("status") == status) for status in ("FULL", "PARTIAL", "REJECTED")},
        "severity_available_hosts": sum(1 for item in records if isinstance(item, dict) and item.get("severity_available") is True),
        "host_general_treatments": len(host_general_records),
        "general_insect_treatments": len(general_records),
        "registry_path": str(capability_path),
    }
    return summary, issues


def _validate_host(
    class_id: int,
    crop: str,
    block: str,
    source_records: dict[str, dict[str, Any]],
) -> tuple[str, list[Issue]]:
    issues: list[Issue] = []
    status = COMPLETE
    sections = _subsections(block, level=3)
    for required in REQUIRED_HOST_SECTIONS:
        if required not in sections:
            issues.append(Issue(INVALID, f"{class_id}/{crop}: missing {required}"))
            status = INVALID

    relation_refs = _validate_refs(block.split("### 当前作物受害表现", 1)[0], source_records, class_id, crop, f"host:{class_id}:{crop}", issues)
    if not relation_refs:
        issues.append(Issue(INVALID, f"{class_id}/{crop}: host relation has no source"))
        status = INVALID

    damage = sections.get("当前作物受害表现", "")
    damage_refs = _validate_refs(damage, source_records, class_id, crop, f"host:{class_id}:{crop}", issues)
    if not damage_refs and not _has_evidence_marker(damage):
        issues.append(Issue(NEEDS, f"{class_id}/{crop}: damage evidence missing"))
        status = NEEDS if status != INVALID else status

    severity = sections.get("严重程度", "")
    severity_parts = _subsections(severity)
    if set(severity_parts) != set(SEVERITY_HEADINGS):
        issues.append(Issue(INVALID, f"{class_id}/{crop}: severity must have exact three tiers"))
        status = INVALID
    for heading in SEVERITY_HEADINGS:
        content = severity_parts.get(heading, "")
        refs = _validate_refs(content, source_records, class_id, crop, f"host:{class_id}:{crop}", issues)
        if not refs:
            if not _has_evidence_marker(content):
                issues.append(Issue(NEEDS, f"{class_id}/{crop}/{heading}: severity evidence missing"))
            status = NEEDS if status != INVALID else status

    treatment = sections.get("防治方法", "")
    treatment_parts = _subsections(treatment)
    if set(treatment_parts) != set(TREATMENT_HEADINGS):
        issues.append(Issue(INVALID, f"{class_id}/{crop}: treatment must have exact three tiers"))
        status = INVALID
    for heading in TREATMENT_HEADINGS:
        content = treatment_parts.get(heading, "")
        refs = _validate_refs(content, source_records, class_id, crop, f"host:{class_id}:{crop}", issues)
        if not refs:
            if not _has_evidence_marker(content):
                issues.append(Issue(NEEDS, f"{class_id}/{crop}/{heading}: treatment evidence missing"))
            status = NEEDS if status != INVALID else status
        if heading == "化学防治边界" and re.search(r"农药|杀虫剂|药剂|有效成分|乳油|可湿性", content) and "【风险提示】" not in content:
            issues.append(Issue(INVALID, f"{class_id}/{crop}: chemical section lacks risk warning"))
            status = INVALID
    return status, issues


def _validate_document(
    entry: dict[str, Any], source_records: dict[str, dict[str, Any]], root: Path
) -> Result:
    issues: list[Issue] = []
    class_id = int(entry["class_id"])
    path = (root / entry["document"]).resolve()
    try:
        path.relative_to(root.resolve())
        markdown = path.read_text(encoding="utf-8")
    except (OSError, ValueError, KeyError) as exc:
        return Result(INVALID, (Issue(INVALID, f"cannot read document: {entry.get('document')}: {exc}"),))

    sections = _sections(markdown)
    for required in ("推荐寄主", "已审核寄主", "通用害虫防治"):
        if required not in sections:
            issues.append(Issue(INVALID, f"class {class_id}: missing top-level section {required}"))

    recommended = str(entry.get("recommended_host", ""))
    supported = [str(item) for item in entry.get("supported_hosts", [])]
    if recommended not in supported:
        issues.append(Issue(INVALID, f"class {class_id}: recommended host is not supported"))
    recommendation_section = sections.get("推荐寄主", "")
    if "最常见寄主" in recommendation_section or "最常见" in markdown:
        issues.append(Issue(INVALID, f"class {class_id}: recommendation uses absolute-most-common wording"))
    expected_label = f"推荐：常见寄主之一——{recommended}"
    if expected_label not in recommendation_section:
        issues.append(Issue(INVALID, f"class {class_id}: recommendation label must be reviewed common host wording"))
    recommendation_refs = _validate_refs(recommendation_section, source_records, class_id, recommended or None, f"host:{class_id}:{recommended}", issues)
    if not recommendation_refs:
        issues.append(Issue(INVALID, f"class {class_id}: recommended host has no evidence source"))

    host_names = [match.group(1).strip() for match in (HOST_HEADING.match(line) for line in sections.get("已审核寄主", "").splitlines()) if match]
    if len(host_names) != len(set(host_names)):
        issues.append(Issue(INVALID, f"class {class_id}: duplicate host heading"))
    hosts = _host_blocks(sections.get("已审核寄主", ""))
    if set(hosts) != set(supported):
        issues.append(Issue(INVALID, f"class {class_id}: manifest/document host mismatch"))
    host_statuses: list[str] = []
    for crop in supported:
        if crop not in hosts:
            continue
        host_status, host_issues = _validate_host(class_id, crop, hosts[crop], source_records)
        host_statuses.append(host_status)
        issues.extend(host_issues)

    general = sections.get("通用害虫防治", "")
    general_refs = _validate_refs(general, source_records, class_id, None, f"class:{class_id}", issues)
    if not general_refs:
        issues.append(Issue(NEEDS, f"class {class_id}: general IPM has no source"))

    vector = sections.get("可能传播的相关病害", "")
    if vector:
        for disease, block in _vector_blocks(vector).items():
            refs = _validate_refs(block, source_records, class_id, None, f"vector:{class_id}:{disease}", issues)
            if not refs:
                issues.append(Issue(INVALID, f"class {class_id}/{disease}: vector relation has no source"))
        if "确认诊断" in vector or "一定传播" in vector:
            issues.append(Issue(INVALID, f"class {class_id}: vector section uses confirmed-diagnosis language"))

    if any(item.level == INVALID for item in issues) or INVALID in host_statuses:
        return Result(INVALID, tuple(issues))
    if any(item.level == NEEDS for item in issues) or NEEDS in host_statuses or any(_has_evidence_marker(hosts[crop]) for crop in hosts):
        return Result(NEEDS, tuple(issues))
    return Result(COMPLETE, tuple(issues))


def _vector_blocks(section: str) -> dict[str, str]:
    lines = section.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = DISEASE_HEADING.match(line)
        if match:
            starts.append((index, match.group(1).strip()))
    result: dict[str, str] = {}
    for position, (start, disease) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        result[disease] = "\n".join(lines[start + 1 : end]).strip()
    return result


def validate_manifest(manifest_path: Path) -> dict[str, Any]:
    root = manifest_path.parent.resolve()
    try:
        manifest = _read_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": INVALID, "issues": [{"level": INVALID, "message": f"invalid manifest: {exc}"}]}
    if manifest.get("schema_version") != "insect-host-knowledge-v1":
        return {"status": INVALID, "issues": [{"level": INVALID, "message": "unsupported schema_version"}]}

    source_records, source_issues = _validate_sources(manifest)
    document_results: dict[str, Any] = {}
    issues = list(source_issues)
    for entry in manifest.get("documents", []):
        key = str(entry.get("class_id"))
        result = _validate_document(entry, source_records, root)
        document_results[key] = result.as_dict()
        issues.extend(result.issues)

    evidence_summary, evidence_issues = _validate_evidence_registry(manifest, source_records, root)
    issues.extend(evidence_issues)
    evidence_payload: dict[str, Any] = {}
    try:
        evidence_path = _registry_path(manifest, root)
        evidence_payload = _read_json(evidence_path)
        evidence_records = evidence_payload.get("records", []) if isinstance(evidence_payload, dict) else []
    except (OSError, ValueError, json.JSONDecodeError):
        evidence_records = []
    treatment_records = evidence_payload.get("treatment_audit", []) if isinstance(evidence_payload, dict) else []
    capability_summary, capability_issues = _validate_capability_registry(manifest, source_records, root, evidence_records, treatment_records)
    issues.extend(capability_issues)

    statuses = [item["status"] for item in document_results.values()]
    if any(item.level == INVALID for item in issues):
        status = INVALID
    elif any(status == NEEDS for status in statuses) or any(item.level in {NEEDS, REVIEW_REQUIRED} for item in issues):
        status = NEEDS
    else:
        status = COMPLETE
    return {
        "status": status,
        "documents": document_results,
        "evidence_summary": evidence_summary,
        "capability_summary": capability_summary,
        "issues": [item.__dict__ for item in issues],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?", default=Path(__file__).with_name("manifest.json"))
    args = parser.parse_args(argv)
    result = validate_manifest(args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == COMPLETE else 1


if __name__ == "__main__":
    sys.exit(main())
