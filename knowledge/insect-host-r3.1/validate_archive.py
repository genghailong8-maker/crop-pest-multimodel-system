"""Parity validator for the R3.1 formal knowledge retention archive."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
R31 = ROOT / "knowledge" / "insect-host-r3.1"
DOCS = ROOT / "docs" / "competition" / "r3.1"


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()[:16]


def text_sha(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def severity_id(record: dict[str, Any]) -> str:
    return "|".join(
        str(record.get(key, ""))
        for key in ("object_type", "class_id", "insect", "crop", "disease", "severity")
    )


def severity_marker(record: dict[str, Any]) -> str:
    return (
        "<!-- ARCHIVE_SEVERITY: "
        f"record={severity_id(record)}; status={record['status']}; "
        f"rubric_sha256={text_sha(record['rubric_text'])} -->"
    )


def capability_marker(record: dict[str, Any]) -> str:
    key = f"{record['class_id']}|{record['insect']}|{record['crop']}"
    return f"<!-- ARCHIVE_CAPABILITY: key={key}; sha256={stable_sha(record['capabilities'])} -->"


def fallback_marker(record: dict[str, Any]) -> str:
    key = f"{record['class_id']}|{record['insect']}|{record['crop']}"
    value = json.dumps(record.get("effective_treatment_fallback", {}), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"<!-- ARCHIVE_FALLBACK: key={key}; value={value} -->"


def vector_marker(record: dict[str, Any], relation: dict[str, Any]) -> str:
    disease = relation.get("disease") or relation.get("disease_name") or relation.get("name") or ""
    key = f"{record['class_id']}|{record['insect']}|{record['crop']}|{disease}"
    return f"<!-- ARCHIVE_VECTOR: key={key}; sha256={stable_sha(relation)} -->"


def string_values(value: Any, path: str = "") -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in {"body", "note", "explanation", "fallback_message"} and isinstance(child, str):
                result.append((child_path, child))
            result.extend(string_values(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(string_values(child, f"{path}[{index}]"))
    return result


def validate_archive(
    archive_path: Path | None = None,
    manifest_path: Path | None = None,
    evidence_path: Path | None = None,
    capability_path: Path | None = None,
) -> dict[str, Any]:
    archive_path = archive_path or DOCS / "《R3.1完整知识库归档版》.md"
    manifest_path = manifest_path or R31 / "manifest.json"
    evidence_path = evidence_path or R31 / "severity-evidence.json"
    capability_path = capability_path or R31 / "capability-fallback.json"
    archive = archive_path.read_text(encoding="utf-8")
    manifest = load(manifest_path)
    evidence = load(evidence_path)
    capability = load(capability_path)
    checks: list[Check] = []

    insect_markers = re.findall(r"<!-- ARCHIVE_INSECT: class_id=([^;]+); insect=(.*?) -->", archive)
    host_markers = re.findall(r"<!-- ARCHIVE_HOST: key=(.*?) -->", archive)
    checks.append(Check("insect_count", len(insect_markers) == len(manifest["documents"]) == 8, f"archive={len(insect_markers)} ssot={len(manifest['documents'])}"))
    checks.append(Check("host_count", len(host_markers) == len(capability["records"]) == 38, f"archive={len(host_markers)} ssot={len(capability['records'])}"))

    missing_severity = [severity_id(item) for item in evidence["records"] if severity_marker(item) not in archive]
    rubric_missing = [severity_id(item) for item in evidence["records"] if item["rubric_text"] not in archive]
    checks.append(Check("severity_texts", not rubric_missing, f"missing={len(rubric_missing)} total={len(evidence['records'])}"))
    checks.append(Check("severity_provenance_markers", not missing_severity, f"missing={len(missing_severity)} total={len(evidence['records'])}"))

    missing_sources = [source["source_id"] for source in manifest["sources"] if f"ARCHIVE_SOURCE: {source['source_id']}" not in archive]
    checks.append(Check("source_registry", not missing_sources, f"missing={missing_sources[:5]} total={len(manifest['sources'])}"))
    critical_unreachable = [
        source["source_id"]
        for source in manifest["sources"]
        if source.get("critical")
        and not (
            str(source.get("source_reachability", "")).startswith(("REACHABLE", "LIVE_URL", "STABLE_DOI", "OFFICIAL_ARCHIVE"))
            or source.get("verified_backup_source_ids")
        )
    ]
    checks.append(Check("critical_source_reachability", not critical_unreachable, f"bad={critical_unreachable}"))

    taxon_records = [item for item in evidence["records"] if item.get("object_type") in {"insect_host", "vector_disease"}]
    taxon_count = archive.count("evidence_taxon")
    level_count = archive.count("evidence_taxon_level")
    checks.append(Check("taxonomic_scope_metadata", taxon_count >= len(taxon_records) and level_count >= len(taxon_records), f"archive_taxon={taxon_count} archive_level={level_count} ssot={len(taxon_records)}"))

    missing_capability = [f"{x['class_id']}|{x['insect']}|{x['crop']}" for x in capability["records"] if capability_marker(x) not in archive]
    missing_fallback = [f"{x['class_id']}|{x['insect']}|{x['crop']}" for x in capability["records"] if fallback_marker(x) not in archive]
    checks.append(Check("capabilities", not missing_capability, f"missing={len(missing_capability)} total={len(capability['records'])}"))
    checks.append(Check("fallback_levels", not missing_fallback, f"missing={len(missing_fallback)} total={len(capability['records'])}"))

    vector_expected = [vector_marker(record, relation) for record in capability["records"] for relation in record.get("vector_disease", {}).get("relations", [])]
    missing_vectors = [marker for marker in vector_expected if marker not in archive]
    checks.append(Check("vector_relations", not missing_vectors and len(vector_expected) == 4, f"missing={len(missing_vectors)} total={len(vector_expected)}"))

    treatment_values = string_values(capability)
    missing_treatments = [path for path, body in treatment_values if body and body not in archive]
    checks.append(Check("treatment_texts", not missing_treatments, f"missing={len(missing_treatments)} total={len(treatment_values)}"))

    prompt_path = DOCS / "《AI示意图提示词与来源依据》.md"
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    traceable_count = prompt.count("PROMPT_EVIDENCE_STATUS`: `TRACEABLE")
    expected_traceable = sum(1 for item in evidence["records"] if item.get("object_type") == "insect_host" and item.get("status") == "COMPLETE")
    checks.append(Check("prompt_positive_feature_gate", traceable_count == expected_traceable and "evidence-taxon" not in prompt, f"traceable={traceable_count} expected={expected_traceable}"))
    checks.append(Check("archive_parity_marker", "ARCHIVE_KNOWLEDGE_PARITY = PASS" in archive, "marker must be promoted only after parity validation"))

    required_contract = (
        "FULL", "PARTIAL", "REJECTED", "host_relation", "host_damage", "severity", "host_general_treatment",
        "host_severity_treatment", "vector_disease", "HOST_SEVERITY_TREATMENT", "HOST_GENERAL_TREATMENT",
        "GENERAL_INSECT_TREATMENT", "NO_TREATMENT", "OTHER", "recommended_host", "confirmed_host",
    )
    missing_contract = [item for item in required_contract if item not in archive]
    checks.append(Check("contract_terms", not missing_contract, f"missing={missing_contract}"))

    status = "PASS" if all(check.passed for check in checks) else "FAIL"
    return {"status": status, "checks": [check.as_dict() for check in checks]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    result = validate_archive(archive_path=args.archive)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
