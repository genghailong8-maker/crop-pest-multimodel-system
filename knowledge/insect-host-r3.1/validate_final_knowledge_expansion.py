"""Validate the bounded final R3.1 knowledge expansion and its stop decision."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from validate_archive import validate_archive
from validate_semantic_consistency import validate as validate_semantic


ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parents[1] / "docs" / "competition" / "r3.1"
TEA_SOURCE_IDS = {
    "R31-12-ANKANG-TEA-DAMAGE",
    "R31-12-WEIHAI-TEA-DAMAGE",
    "R31-12-FRONTIERS-ONUKII",
    "R31-12-PLOS-ONUKII-TAXON",
    "R31-12-CAAS-ONUKII-TAXON",
    "R31-12-JTS-ONUKII-TAXON-2026",
}


def load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def validate() -> dict[str, Any]:
    manifest = load("manifest.json")
    evidence = load("severity-evidence.json")
    capability = load("capability-fallback.json")
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    sources = {item["source_id"]: item for item in manifest["sources"]}
    check("new_source_resolution", TEA_SOURCE_IDS <= sources.keys(), f"missing={sorted(TEA_SOURCE_IDS - sources.keys())}")
    bad_reachability = [
        source_id for source_id in TEA_SOURCE_IDS
        if not str(sources.get(source_id, {}).get("source_reachability", "")).startswith(("LIVE_URL", "STABLE_DOI", "OFFICIAL_ARCHIVE"))
    ]
    check("new_source_reachability", not bad_reachability, f"bad={bad_reachability}")

    tea = next(item for item in capability["records"] if item["class_id"] == 12 and item["crop"] == "茶")
    tea_severity = [item for item in evidence["records"] if item.get("object_type") == "insect_host" and item.get("class_id") == 12 and item.get("crop") == "茶"]
    check("leafhopper_tea_full", tea["status"] == "FULL" and tea["severity_available"] is True, f"status={tea['status']} severity={tea['severity_available']}")
    check("leafhopper_tea_three_complete", len(tea_severity) == 3 and all(item["status"] == "COMPLETE" for item in tea_severity), f"statuses={[item['status'] for item in tea_severity]}")
    same_taxon_host = all(
        item.get("SOURCE_SEMANTIC_REVIEW") == "PASS"
        and item.get("evidence_taxon_level") == ["species"]
        and "onukii" in " ".join(item.get("evidence_taxon", [])).lower()
        and item.get("crop") == "茶"
        for item in tea_severity
    )
    check("same_taxon_same_host_progression", same_taxon_host, "tea records are species-scoped and same-host")
    check(
        "current_taxon_name_provenance",
        all("R31-12-JTS-ONUKII-TAXON-2026" in item.get("taxonomic_source_ids", []) for item in tea_severity),
        "current Matsumurasca combination has Journal of Tea Science DOI provenance",
    )
    mapping_ok = all(
        set(item.get("visual_feature_source_ids", {})) == set(item.get("observable_features", []))
        and all(set(ids) <= set(item["source_ids"]) for ids in item.get("visual_feature_source_ids", {}).values())
        for item in tea_severity
    )
    check("prompt_feature_provenance", mapping_ok, "every positive feature has an in-record source mapping")

    remaining_leafhopper = [item for item in capability["records"] if item["class_id"] == 12 and item["crop"] != "茶"]
    check("leafhopper_fail_closed", all(item["status"] == "PARTIAL" and item["severity_available"] is False for item in remaining_leafhopper), f"states={[(x['crop'], x['status']) for x in remaining_leafhopper]}")
    check("tea_treatment_unchanged_host_general", tea["fallback_level"] == "host_general" and tea["host_severity_treatment_available"] is False, f"fallback={tea['fallback_level']}")

    full = [item for item in capability["records"] if item["status"] == "FULL"]
    complete = [item for item in evidence["records"] if item.get("object_type") == "insect_host" and item["status"] == "COMPLETE"]
    needs = [item for item in evidence["records"] if item.get("object_type") == "insect_host" and item["status"] == "NEEDS_EVIDENCE"]
    prompt = (DOCS / "《AI示意图提示词与来源依据》.md").read_text(encoding="utf-8")
    traceable = prompt.count("PROMPT_EVIDENCE_STATUS`: `TRACEABLE")
    check("final_counts", len(full) == 13 and len(complete) == 39 and len(needs) == 75 and traceable == 39, f"full={len(full)} complete={len(complete)} needs={len(needs)} traceable={traceable}")

    expansion = manifest.get("final_knowledge_expansion", {})
    not_upgraded = {item.get("crop"): item.get("reason") for item in expansion.get("not_upgraded", [])}
    check("why_not_upgraded", all(not_upgraded.get(crop) for crop in ("水稻", "芒果")), f"crops={sorted(not_upgraded)}")
    check("formal_expansion_stop", expansion.get("knowledge_expansion_stopped") is True and bool(expansion.get("stop_reason")), f"status={expansion.get('status')}")
    semantic = validate_semantic()
    check("semantic_consistency", semantic["status"] == "PASS" and semantic["FULL_HOST_STALE_NEEDS_EVIDENCE"] == 0, json.dumps(semantic, ensure_ascii=False))
    archive = validate_archive()
    check("archive_parity", archive["status"] == "PASS", f"status={archive['status']}")

    status = "PASS" if all(item["passed"] for item in checks) else "FAIL"
    return {
        "status": status,
        "checks": checks,
        "counts": {
            "new_full_hosts": 1,
            "total_full_hosts": len(full),
            "total_partial_hosts": len(capability["records"]) - len(full),
            "complete_insect_host_severity": len(complete),
            "needs_evidence_insect_host_severity": len(needs),
            "traceable_prompts": traceable,
            "total_ai_images_required": traceable,
        },
        "KNOWLEDGE_EXPANSION_STOPPED": "YES" if expansion.get("knowledge_expansion_stopped") else "NO",
    }


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
