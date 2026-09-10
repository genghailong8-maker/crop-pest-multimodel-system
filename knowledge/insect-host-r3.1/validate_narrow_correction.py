"""Deterministic audit for the R3.1 User Knowledge Review narrow correction."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
R31 = ROOT / "knowledge" / "insect-host-r3.1"
DOCS = ROOT / "docs" / "competition" / "r3.1"
GLOBAL = {"R31-GLOBAL-IPM-MOA", "R31-GLOBAL-IPM-FAO"}
LEVELS = {"family", "superfamily", "genus", "species", "source_named_group"}
NEGATIVE_VISUAL_MARKERS = ("\u4ecd\u8fde\u7eed", "\u672a\u666e\u904d", "\u5c1a\u65e0", "\u4ecd\u53ef\u80fd\u8010\u53d7", "\u6765\u6e90 Severe", "\u6765\u6e90 severe")
IOWA_SOY_APHID = "R31-09-IOWA-SOY-APHID-IPM"


def normalize_audit_text(value: str) -> str:
    """Normalize formatting variants before semantic-pattern checks."""
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[‐‑‒–—―﹘﹣－]", "-", value)
    value = re.sub(r"[,，、；;：:。.!！?？/／|｜·•]", "", value)
    return re.sub(r"\s+", "", value).lower()


def soybean_treatment_issues(record: dict[str, Any]) -> list[str]:
    """Return unsupported soybean-aphid treatment concepts after normalization."""
    text = normalize_audit_text(json.dumps(record.get("sections", {}), ensure_ascii=False))
    review = record.get("source_entailment_review", {})
    mappings = {
        item.get("concept"): set(item.get("source_ids", []))
        for item in review.get("clause_source_map", [])
        if isinstance(item, dict)
    }
    record_sources = set(record.get("source_ids", []))

    def mapped(concept: str, required: set[str] | None = None) -> bool:
        source_ids = mappings.get(concept, set())
        if not source_ids or not source_ids.issubset(record_sources):
            return False
        return required is None or bool(source_ids & required)

    issues: list[str] = []
    concepts: list[tuple[str, str, str, set[str] | None]] = [
        (r"(?:至少)?每(?:隔)?7(?:-|至|到)10天(?:巡查|调查|检查)(?:一次)?", "scouting_every_7_10_days", "7–10 day scouting", {IOWA_SOY_APHID}),
        (r"瓢虫", "lady_beetles", "lady beetles", {IOWA_SOY_APHID}),
        (r"草蛉", "lacewings", "lacewings", {IOWA_SOY_APHID}),
        (r"小花蝽", "minute_pirate_bugs", "minute pirate bugs", {IOWA_SOY_APHID}),
        (r"寄生性天敌", "parasitoids_generic", "generic parasitoids", {IOWA_SOY_APHID}),
        (r"(?:抗大豆蚜|抗虫|rag)(?:基因)?品种", "resistant_variety", "resistant variety", {IOWA_SOY_APHID}),
        (r"食蚜蝇", "hoverflies", "hoverflies", None),
        (r"蚜茧蜂", "aphidius_wasps", "aphidius wasps", None),
        (r"(?:合理)?轮作", "crop_rotation", "crop rotation", None),
    ]
    for pattern, concept, label, required in concepts:
        if re.search(pattern, text) and not mapped(concept, required):
            issues.append(f"{label}: missing approved clause-level source mapping")
    return issues


def load(name: str) -> dict[str, Any]:
    return json.loads((R31 / name).read_text(encoding="utf-8"))


def audit() -> dict[str, Any]:
    manifest = load("manifest.json")
    evidence = load("severity-evidence.json")
    capability = load("capability-fallback.json")
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    sources = {item["source_id"]: item for item in manifest["sources"]}
    critical = [item for item in manifest["sources"] if item.get("critical")]
    critical_bad = [
        item["source_id"]
        for item in critical
        if not (
            str(item.get("source_reachability", "")).startswith(("REACHABLE", "LIVE_URL", "STABLE_DOI", "OFFICIAL_ARCHIVE"))
            or item.get("verified_backup_source_ids")
        )
    ]
    check("critical_source_reachability", not critical_bad, f"bad={critical_bad} total={len(critical)}")

    insect_vector = [item for item in evidence["records"] if item["object_type"] in {"insect_host", "vector_disease"}]
    metadata_bad = []
    for item in insect_vector:
        if not isinstance(item.get("evidence_taxon"), list) or not item["evidence_taxon"]:
            metadata_bad.append(f"{item.get('class_id')}:{item.get('crop')} missing taxon")
        if not isinstance(item.get("evidence_taxon_level"), list) or not set(item["evidence_taxon_level"]).issubset(LEVELS):
            metadata_bad.append(f"{item.get('class_id')}:{item.get('crop')} invalid level")
        if not item.get("evidence_taxon_scope"):
            metadata_bad.append(f"{item.get('class_id')}:{item.get('crop')} missing source scope")
    check("taxonomic_scope_metadata", not metadata_bad, f"bad={len(metadata_bad)} total={len(insect_vector)}")

    soybean_beetle = [
        item for item in evidence["records"]
        if item["object_type"] == "insect_host" and item["class_id"] == 15 and item["crop"] == "\u5927\u8c46"
    ]
    exact_ok = all(item["source_ids"] == ["R31-15-ENTOMOLOGY-1956"] and "Epicauta gorhami" in " ".join(item.get("evidence_taxon", [])) for item in soybean_beetle)
    check("epicauta_gorhami_exact_species", exact_ok, f"records={len(soybean_beetle)}")

    soy_vector = [item for item in evidence["records"] if item["object_type"] == "vector_disease" and item.get("class_id") == 9 and item.get("crop") == "\u5927\u8c46" and item.get("disease") == "\u5927\u8c46\u82b1\u53f6\u75c5"]
    check("soy_vector_replacement", bool(soy_vector) and all("R31-09-SOY-VECTOR-APS" in item["source_ids"] for item in soy_vector), "APS source present")
    wheat_vector = [item for item in evidence["records"] if item["object_type"] == "vector_disease" and item.get("class_id") == 9 and item.get("crop") == "\u5c0f\u9ea6" and item.get("disease") == "\u5c0f\u9ea6\u9ec4\u77ee\u75c5"]
    check("wheat_vector_replacement", bool(wheat_vector) and all(item["source_ids"] == ["R31-09-WHEAT-VECTOR"] for item in wheat_vector) and sources["R31-09-WHEAT-VECTOR"]["url"].startswith("https://cropwatch.unl.edu/"), "UNL source present")

    aphid_soy = next(item for item in capability["host_general_treatments"] if item["class_id"] == 9 and item["crop"] == "\u5927\u8c46")
    unsupported = soybean_treatment_issues(aphid_soy)
    check("soybean_aphid_treatment_entailment", not unsupported and aphid_soy.get("host_specific_evidence") is True, f"unsupported={unsupported}")

    treatment_count = len(capability["host_general_treatments"])
    specific_count = sum(bool(item.get("host_specific_evidence")) for item in capability["host_general_treatments"])
    check("host_general_entailment_metadata", treatment_count == 38 and specific_count <= treatment_count, f"host_specific={specific_count}/38 downgraded={treatment_count-specific_count}")

    prompt = (DOCS / "《AI示意图提示词与来源依据》.md").read_text(encoding="utf-8")
    traceable = len(re.findall(r"- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`", prompt))
    bad_visual: list[str] = []
    for block in re.split(r"(?m)^### ", prompt)[1:]:
        if "\u00d7" not in block:
            continue
        visual = block.split("#### Final image-generation prompt", 1)[0]
        if "#### Observable visual features and source mapping" not in visual:
            bad_visual.append("missing mapping")
            continue
        mapping = visual.split("#### Observable visual features and source mapping", 1)[1]
        for marker in NEGATIVE_VISUAL_MARKERS:
            if marker in mapping:
                bad_visual.append(marker)
        if "`R31-" not in mapping:
            bad_visual.append("missing source mapping")
    expected_traceable = sum(
        1 for item in load("severity-evidence.json")["records"]
        if item.get("object_type") == "insect_host" and item.get("status") == "COMPLETE"
    )
    check("prompt_positive_feature_provenance", not bad_visual and traceable == expected_traceable, f"traceable={traceable} expected={expected_traceable} bad={bad_visual[:5]}")

    review_values = {item.get("SOURCE_SEMANTIC_REVIEW") for item in insect_vector}
    treatment_review_values = {item.get("SOURCE_SEMANTIC_REVIEW") for item in capability["host_general_treatments"]}
    active_treatment_review_values = {
        item.get("SOURCE_SEMANTIC_REVIEW") for item in capability["host_general_treatments"] if item.get("available")
    }
    check("source_semantic_review_fields", review_values.issubset({"PASS", "NEEDS_REVIEW"}) and active_treatment_review_values == {"PASS"}, f"evidence={sorted(review_values)} active_treatment={sorted(active_treatment_review_values)}")
    entailment_bad = [
        item.get("source_id", item.get("class_id"))
        for item in insect_vector
        if not isinstance(item.get("source_entailment_review"), dict)
        or item["source_entailment_review"].get("status") != item.get("SOURCE_SEMANTIC_REVIEW")
    ]
    entailment_bad.extend(
        item.get("class_id")
        for item in capability["host_general_treatments"]
        if item.get("available") and (not isinstance(item.get("source_entailment_review"), dict)
        or item["source_entailment_review"].get("status") != item.get("SOURCE_SEMANTIC_REVIEW")
        )
    )
    check("source_entailment_review_flag", not entailment_bad, f"bad={len(entailment_bad)}")

    status = "PASS" if all(item["passed"] for item in checks) else "FAIL"
    return {
        "status": status,
        "checks": checks,
        "counts": {
            "prompt_traceable": traceable,
            "prompt_needs_evidence": sum(1 for item in load("severity-evidence.json")["records"] if item.get("object_type") == "insect_host" and item.get("status") == "NEEDS_EVIDENCE"),
            "host_specific_treatment": specific_count,
            "downgraded_to_insect_general": treatment_count - specific_count,
        },
        "SOURCE_SEMANTIC_REVIEW": "PASS" if active_treatment_review_values == {"PASS"} else "NEEDS_REVIEW",
    }


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
