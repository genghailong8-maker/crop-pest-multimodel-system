"""Hydrate the R3.1 severity-image foundation from frozen Knowledge only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "severity-image-manifest.json"
SEVERITIES = ("mild", "moderate", "severe")
SEVERITY_CN = {"mild": "轻度", "moderate": "中度", "severe": "重度"}
LABEL = "AI示意图 · 非真实照片"


def load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def hydrate() -> dict[str, Any]:
    evidence = load("severity-evidence.json")
    capabilities = load("capability-fallback.json")["records"]
    source_records = {
        item["source_id"]: item for item in load("manifest.json")["sources"]
    }
    source_by_key = {
        (item.get("class_id"), item.get("crop"), item.get("severity")): item
        for item in evidence["records"]
        if item.get("object_type") == "insect_host"
    }

    entries: list[dict[str, Any]] = []
    for pair_number, capability in enumerate(capabilities, start=1):
        pair_id = f"{pair_number:02d}"
        key = (capability["class_id"], capability["crop"])
        for severity in SEVERITIES:
            record = source_by_key.get((*key, severity))
            if not record or record.get("status") != "COMPLETE":
                raise ValueError(f"missing frozen COMPLETE manifestation: {key}/{severity}")
            source_ids = record.get("source_ids") or []
            if not source_ids or any(source_id not in source_records for source_id in source_ids):
                raise ValueError(f"invalid manifestation source IDs: {key}/{severity}")
            features = record.get("observable_features") or []
            if not features:
                raise ValueError(f"missing observable features: {key}/{severity}")
            feature_text = "、".join(str(feature) for feature in features)
            prompt_basis = (
                f"农业田间示意：{capability['crop']}植株上可见{feature_text}，"
                f"呈现{SEVERITY_CN[severity]}程度；仅表现冻结知识中的受害特征。"
            )
            entries.append(
                {
                    "pair_id": pair_id,
                    "class_id": capability["class_id"],
                    "insect": capability["insect"],
                    "host": capability["crop"],
                    "severity": severity,
                    "severity_cn": SEVERITY_CN[severity],
                    "asset_id": f"r31-{pair_id}-{severity}",
                    "knowledge_basis": {
                        "source": "FROZEN_R31_KNOWLEDGE",
                        "manifestation_text": record["rubric_text"],
                        "observable_features": features,
                        "source_ids": source_ids,
                    },
                    "prompt_basis": prompt_basis,
                    "asset": {
                        "original_png": f"web/public/assets/severity/r31/{pair_id}/{severity}.png",
                        "web_derivative": f"web/public/assets/severity/r31/{pair_id}/{severity}.webp",
                        "status": "PENDING",
                    },
                    "display_label": LABEL,
                    "qa": {
                        "host_identity": "PENDING",
                        "insect_identity": "PENDING",
                        "severity_match": "PENDING",
                        "manifestation_match": "PENDING",
                        "no_text_in_image": "PENDING",
                        "no_watermark": "PENDING",
                        "no_wrong_host_reuse": "PENDING",
                        "no_cross_severity_reuse": "PENDING",
                        "approved": False,
                    },
                }
            )
    if len(capabilities) != 38 or len(entries) != 114:
        raise ValueError(f"unexpected hydrated dimensions: pairs={len(capabilities)} assets={len(entries)}")
    return {
        "schema_version": "1.0",
        "project": "crop-pest-multimodel-system",
        "scope": "R3.1 insect × host severity AI illustrations",
        "knowledge_status": "PASS/CLOSED/FROZEN",
        "expected_pair_count": 38,
        "expected_severity_count": 3,
        "expected_asset_count": 114,
        "global_label": LABEL,
        "rules": {
            "knowledge_authority": "frozen local Knowledge only",
            "generation_must_not_modify_knowledge": True,
            "treatment_must_not_influence_visuals": True,
            "unique_asset_per_pair_and_severity": True,
            "cross_host_reuse_forbidden": True,
            "cross_severity_reuse_forbidden": True,
            "text_inside_image_forbidden": True,
            "watermark_forbidden": True,
            "uncertain_has_image": False,
        },
        "entries": entries,
    }


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(hydrate(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(json.loads(OUTPUT.read_text(encoding='utf-8'))['entries'])} entries)")
