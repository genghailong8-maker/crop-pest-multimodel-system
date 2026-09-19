"""Deterministic gates for R3.1 Batch 4A Final Evidence Review correction."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from validate_final_evidence_sprint import QUANTITATIVE, reachable
from validate_narrow_correction import soybean_treatment_issues


ROOT = Path(__file__).resolve().parents[2]
R31 = ROOT / "knowledge" / "insect-host-r3.1"
DOCS = ROOT / "docs" / "competition" / "r3.1"
ORDOS = "R31-08-ORDOS"


def load(name: str) -> dict[str, Any]:
    return json.loads((R31 / name).read_text(encoding="utf-8"))


def main() -> int:
    manifest = load("manifest.json")
    evidence = load("severity-evidence.json")
    capability = load("capability-fallback.json")
    sources = {item["source_id"]: item for item in manifest["sources"]}
    insect_records = [item for item in evidence["records"] if item.get("object_type") == "insect_host"]
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    wheat = [item for item in insect_records if item.get("class_id") == 9 and item.get("crop") == "小麦"]
    wheat_sources = {"R31-09-KSTATE-GREENBUG-WHEAT", "R31-09-OSU-GREENBUG-WHEAT"}
    wheat_ok = len(wheat) == 3 and all(
        item.get("status") == "COMPLETE"
        and set(item.get("source_ids", [])) == wheat_sources
        and item.get("evidence_taxon") == ["Schizaphis graminum"]
        and item.get("evidence_taxon_level") == ["species"]
        and item.get("SOURCE_SEMANTIC_REVIEW") == "PASS"
        and "R31-09-UIDAHO-CEREAL" not in item.get("source_ids", [])
        for item in wheat
    )
    check("aphid_wheat_same_species_progression", wheat_ok, f"records={len(wheat)} sources={sorted({sid for item in wheat for sid in item.get('source_ids', [])})}")

    peanut = [item for item in insect_records if item.get("class_id") == 11 and item.get("crop") == "花生"]
    peanut_cap = next(item for item in capability["records"] if item["class_id"] == 11 and item["crop"] == "花生")
    peanut_ok = len(peanut) == 3 and all(
        item.get("status") == "NEEDS_EVIDENCE"
        and item.get("observable_features") == []
        and item.get("SOURCE_SEMANTIC_REVIEW") == "NEEDS_REVIEW"
        for item in peanut
    )
    peanut_ok = peanut_ok and peanut_cap["status"] == "PARTIAL" and peanut_cap["severity_available"] is False
    check("mole_cricket_peanut_severity_fail_closed", peanut_ok, f"status={peanut_cap['status']} severity={peanut_cap['severity_available']}")

    soy_treatment = next(item for item in capability["host_general_treatments"] if item["class_id"] == 9 and item["crop"] == "大豆")
    soy_issues = soybean_treatment_issues(soy_treatment)
    soy_text = json.dumps(soy_treatment.get("sections", {}), ensure_ascii=False)
    removed = [term for term in ("食蚜蝇", "蚜茧蜂", "合理轮作", "桥梁寄主") if term in soy_text]
    check(
        "soybean_aphid_clause_entailment",
        not soy_issues and not removed and "R31-09-IOWA-SOY-APHID-IPM" in soy_treatment.get("host_specific_source_ids", []),
        f"issues={soy_issues} removed_terms_still_present={removed}",
    )

    potato_treatment = next(item for item in capability["host_general_treatments"] if item["class_id"] == 11 and item["crop"] == "马铃薯")
    peanut_treatment = next(item for item in capability["host_general_treatments"] if item["class_id"] == 11 and item["crop"] == "花生")
    check(
        "mole_cricket_potato_direct_treatment",
        potato_treatment.get("available") is True and "R31-11-NCSU-POTATO-MOLECRICKET" in potato_treatment.get("host_specific_source_ids", []),
        f"source_ids={potato_treatment.get('host_specific_source_ids')}",
    )
    check(
        "mole_cricket_peanut_host_general_treatment",
        peanut_treatment.get("available") is True
        and "R31-11-HAMI-PEANUT-IPM" in peanut_treatment.get("host_specific_source_ids", [])
        and peanut_cap["fallback_level"] == "host_general",
        f"source_ids={peanut_treatment.get('host_specific_source_ids')} fallback={peanut_cap['fallback_level']}",
    )

    active_ordos: list[str] = []
    for item in evidence["records"]:
        if ORDOS in item.get("source_ids", []):
            active_ordos.append(f"evidence:{item.get('class_id')}:{item.get('crop')}:{item.get('severity')}")
        for ids in item.get("visual_feature_source_ids", {}).values():
            if ORDOS in ids:
                active_ordos.append(f"feature:{item.get('class_id')}:{item.get('crop')}:{item.get('severity')}")
    for item in evidence.get("treatment_audit", []):
        if ORDOS in item.get("host_specific_source_ids", []):
            active_ordos.append(f"treatment:{item.get('class_id')}:{item.get('crop')}")
    for path in sorted((R31 / "insects").glob("*.md")):
        if ORDOS in path.read_text(encoding="utf-8"):
            active_ordos.append(f"markdown:{path.name}")
    ordos = sources[ORDOS]
    ordos_ok = (
        ordos.get("source_status") == "DEAD_LINK_HISTORICAL_PROVENANCE_ONLY"
        and ordos.get("current_capability_use") is False
        and bool(ordos.get("verified_backup_source_ids"))
        and not active_ordos
    )
    check("R31_08_ORDOS_not_active", ordos_ok, f"active={active_ordos} backups={ordos.get('verified_backup_source_ids')}")

    referenced: set[str] = set()
    for item in evidence["records"]:
        referenced.update(item.get("source_ids", []))
    for item in evidence.get("treatment_audit", []):
        referenced.update(item.get("source_ids", []))
        referenced.update(item.get("host_specific_source_ids", []))
    dangling = sorted(referenced - set(sources))
    unreachable = sorted(sid for sid in referenced if sid in sources and not reachable(sources[sid], sources))
    check("source_resolution_and_reachability", not dangling and not unreachable, f"dangling={dangling} unreachable={unreachable}")

    complete = [item for item in insect_records if item.get("status") == "COMPLETE"]
    full = [item for item in capability["records"] if item.get("status") == "FULL"]
    partial = [item for item in capability["records"] if item.get("status") == "PARTIAL"]
    check(
        "final_counts",
        len(full) >= 12 and len(partial) == 38 - len(full) and len(complete) == len(full) * 3 and len(insect_records) - len(complete) == 114 - len(complete),
        f"full={len(full)} partial={len(partial)} complete={len(complete)} needs={len(insect_records)-len(complete)}; correction baseline>=12 with later evidence expansion allowed",
    )

    quantitative_bad: list[str] = []
    rubric_groups: dict[str, set[tuple[int, str]]] = defaultdict(set)
    for item in complete:
        text = " ".join([str(item.get("rubric_text", "")), *map(str, item.get("observable_features", []))])
        if QUANTITATIVE.search(text):
            quantitative_bad.append(f"{item['class_id']}:{item['crop']}:{item['severity']}")
        normalized = re.sub(r"\s+", " ", str(item.get("rubric_text", "")).strip())
        rubric_groups[normalized].add((item["class_id"], item["crop"]))
    duplicates = [rubric for rubric, hosts in rubric_groups.items() if rubric and len(hosts) > 1]
    check("unsupported_quantitative_guard", not quantitative_bad, f"bad={quantitative_bad}")
    check("duplicate_rubric_guard", not duplicates, f"duplicate_groups={len(duplicates)}")

    prompt_path = DOCS / "《AI示意图提示词与来源依据》.md"
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    traceable = prompt.count("PROMPT_EVIDENCE_STATUS`: `TRACEABLE")
    peanut_prompt = re.search(r"(?m)^### 蝼蛄 × 花生 ×", prompt) is not None
    check("prompt_provenance_count", traceable == len(complete) and not peanut_prompt, f"traceable={traceable} expected={len(complete)} peanut_prompt={peanut_prompt}")

    result = {
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "checks": checks,
        "counts": {
            "total_full_hosts": len(full),
            "total_partial_hosts": len(partial),
            "complete_insect_host_severity": len(complete),
            "needs_evidence_insect_host_severity": len(insect_records) - len(complete),
            "traceable_prompts": traceable,
            "total_ai_images_required": len(full) * 3,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
