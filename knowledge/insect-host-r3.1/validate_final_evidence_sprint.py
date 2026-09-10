"""Narrow deterministic gates for R3.1 Batch 4A Final Evidence Sprint."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
R31 = ROOT / "knowledge" / "insect-host-r3.1"
DOCS = ROOT / "docs" / "competition" / "r3.1"
REACHABLE_PREFIXES = ("REACHABLE", "LIVE_URL", "STABLE_DOI", "OFFICIAL_ARCHIVE")
NEGATIVE_FEATURES = ("尚未", "未普遍", "无明显", "没有", "未出现", "仍连续", "仍可耐受")
QUANTITATIVE = re.compile(r"(?:%|％|百分比|每株|每叶|虫口|株率|面积比例|产量(?:下降|损失)?\s*\d|\d+(?:\.\d+)?\s*(?:头|只|株|叶|亩|克|毫升|倍液|天|次))")


def load(name: str) -> dict[str, Any]:
    return json.loads((R31 / name).read_text(encoding="utf-8"))


def reachable(source: dict[str, Any], sources: dict[str, dict[str, Any]], seen: set[str] | None = None) -> bool:
    seen = seen or set()
    source_id = str(source.get("source_id", ""))
    if source_id in seen:
        return False
    seen.add(source_id)
    if source.get("doi") or str(source.get("source_reachability", "")).startswith(REACHABLE_PREFIXES):
        return True
    for backup_id in source.get("verified_backup_source_ids", []):
        backup = sources.get(backup_id)
        if backup and reachable(backup, sources, seen):
            return True
    return False


def main() -> int:
    manifest = load("manifest.json")
    evidence = load("severity-evidence.json")
    capability = load("capability-fallback.json")
    sources = {item["source_id"]: item for item in manifest.get("sources", [])}
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    # A. Critical source reachability, including the explicit Ordos dead-link backup chain.
    critical = [item for item in manifest.get("sources", []) if item.get("critical")]
    bad_critical = [item["source_id"] for item in critical if not reachable(item, sources)]
    ordos = sources.get("R31-08-ORDOS", {})
    check("source_reachability", not bad_critical, f"critical={len(critical)} bad={bad_critical}")
    check(
        "R31-08-ORDOS_resilience",
        "UNREACHABLE" in str(ordos.get("source_reachability", "")) and all(
            backup_id in sources and reachable(sources[backup_id], sources)
            for backup_id in ordos.get("verified_backup_source_ids", [])
        ),
        f"historical={ordos.get('source_reachability')} backups={ordos.get('verified_backup_source_ids', [])}",
    )

    # B. Evidence/capability counts must be data-derived and agree.
    insect = [item for item in evidence["records"] if item.get("object_type") == "insect_host"]
    complete_insect = [item for item in insect if item.get("status") == "COMPLETE"]
    complete_hosts = {(item.get("class_id"), item.get("crop")) for item in complete_insect}
    full_hosts = [item for item in capability["records"] if item.get("status") == "FULL"]
    check("evidence_count", len(insect) == 114, f"insect_host_records={len(insect)}")
    check("full_capability_parity", len(full_hosts) == len(complete_hosts) and len(complete_insect) == len(full_hosts) * 3, f"full={len(full_hosts)} complete_cells={len(complete_insect)}")

    # C. Taxon/scope and semantic review are required for every newly complete cell.
    taxon_bad: list[str] = []
    for item in complete_insect:
        key = f"{item.get('class_id')}|{item.get('crop')}|{item.get('severity')}"
        if not item.get("evidence_taxon") or not item.get("evidence_taxon_level") or not item.get("evidence_taxon_scope"):
            taxon_bad.append(key)
        if item.get("SOURCE_SEMANTIC_REVIEW") != "PASS":
            taxon_bad.append(key + " semantic")
        if item.get("source_entailment_review", {}).get("status") != "PASS":
            taxon_bad.append(key + " entailment")
    check("taxonomy_scope_and_semantic_review", not taxon_bad, f"bad={taxon_bad[:10]} total_complete={len(complete_insect)}")

    # D. Resolve all evidence and treatment source IDs.
    referenced: set[str] = set()
    for item in evidence["records"]:
        referenced.update(item.get("source_ids", []))
    for item in evidence.get("treatment_audit", []):
        referenced.update(item.get("source_ids", []))
        referenced.update(item.get("host_specific_source_ids", []))
    dangling = sorted(referenced - set(sources))
    check("source_id_resolution", not dangling, f"referenced={len(referenced)} dangling={dangling}")

    # E. New completed rubrics remain qualitative and host-specific.
    quantitative_bad = []
    rubric_groups: dict[str, set[tuple[Any, Any]]] = defaultdict(set)
    for item in complete_insect:
        text = " ".join([str(item.get("rubric_text", "")), *[str(x) for x in item.get("observable_features", [])], str(item.get("synthesis_note", ""))])
        unsupported = False
        for match in QUANTITATIVE.finditer(text):
            prefix = text[max(0, match.start() - 16) : match.start()]
            if re.search(r"(?:不|未|无|禁止|不得|不应|不将|不加入).{0,10}$", prefix):
                continue
            unsupported = True
            break
        if unsupported:
            quantitative_bad.append(f"{item.get('class_id')}|{item.get('crop')}|{item.get('severity')}")
        rubric_groups[re.sub(r"\s+", " ", str(item.get("rubric_text", "")).strip())].add((item.get("class_id"), item.get("crop")))
    duplicate_bad = [text for text, hosts in rubric_groups.items() if text and len(hosts) > 1]
    check("unsupported_quantitative_guard", not quantitative_bad, f"bad={quantitative_bad}")
    check("duplicate_rubric_guard", not duplicate_bad, f"duplicate_groups={len(duplicate_bad)}")

    # F. Prompt provenance: one traceable record per completed insect-host severity.
    prompt_paths = list(DOCS.glob("*AI*来源依据*.md"))
    prompt = prompt_paths[0].read_text(encoding="utf-8") if prompt_paths else ""
    traceable = prompt.count("PROMPT_EVIDENCE_STATUS`: `TRACEABLE")
    prompt_bad: list[str] = []
    for item in complete_insect:
        if item.get("source_ids") and not all(f"`{sid}`" in prompt for sid in item["source_ids"]):
            prompt_bad.append(f"missing source {item.get('class_id')}|{item.get('crop')}|{item.get('severity')}")
        for feature in item.get("observable_features", []):
            if feature not in prompt:
                prompt_bad.append(f"missing feature {item.get('class_id')}|{item.get('crop')}|{feature}")
    mapping_blocks = re.findall(r"#### Observable visual features and source mapping(.*?)(?=#### Final image-generation prompt)", prompt, re.S)
    negative_mapping = [marker for block in mapping_blocks for marker in NEGATIVE_FEATURES if marker in block]
    check("prompt_provenance_gate", bool(prompt_paths) and traceable == len(complete_insect) and not prompt_bad, f"traceable={traceable} expected={len(complete_insect)} bad={prompt_bad[:10]}")
    check("prompt_positive_visual_features", not negative_mapping, f"negative_mapping={negative_mapping}")

    # G. An explicit fast-fail record is required for attempted but unupgraded hosts.
    why_paths = list(DOCS.glob("*why-not-upgraded*.md"))
    why = why_paths[0].read_text(encoding="utf-8") if why_paths else ""
    check("WHY_NOT_UPGRADED_register", bool(why_paths) and "WHY_NOT_UPGRADED" in why and "PARTIAL" in why, f"path={why_paths[0] if why_paths else None}")

    # H. Archive parity is checked by validate_archive.py; this validator only reports its presence.
    archive_paths = list(DOCS.glob("*R3.1*完整知识库归档版*.md"))
    check("archive_present", bool(archive_paths), f"path={archive_paths[0] if archive_paths else None}")

    result = {
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "checks": checks,
        "counts": {
            "insect_host_complete_cells": len(complete_insect),
            "insect_host_needs_evidence_cells": len(insect) - len(complete_insect),
            "full_hosts": len(full_hosts),
            "traceable_prompts": traceable,
            "critical_sources": len(critical),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
