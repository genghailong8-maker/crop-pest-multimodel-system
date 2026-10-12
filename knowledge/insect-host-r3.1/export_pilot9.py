"""Export the fixed v1.17 pilot rows from the hydrated image manifest."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "severity-image-manifest.json"
PILOT_JSON = ROOT / "pilot-9-severity-image-inputs.json"
PILOT_MD = ROOT / "pilot-9-severity-image-inputs.md"
PROMPTS_MD = ROOT / "pilot-9-imagegen-prompts.md"
PAIR_IDS = ("14", "15", "35")
SEVERITIES = ("mild", "moderate", "severe")


def exported(row: dict) -> dict:
    return {
        "pair_id": row["pair_id"],
        "insect": row["insect"],
        "host": row["host"],
        "severity": row["severity"],
        "severity_cn": row["severity_cn"],
        "asset_id": row["asset_id"],
        "knowledge_basis": {
            "manifestation_text": row["knowledge_basis"]["manifestation_text"],
            "source_ids": row["knowledge_basis"]["source_ids"],
        },
        "prompt_basis": row["prompt_basis"],
        "asset": {
            "original_png": row["asset"]["original_png"],
            **({"web_derivative": row["asset"]["web_derivative"]} if row["asset"].get("web_derivative") else {}),
        },
        "display_label": row["display_label"],
    }


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lookup = {(row["pair_id"], row["severity"]): row for row in manifest["entries"]}
    rows = [exported(lookup[(pair_id, severity)]) for pair_id in PAIR_IDS for severity in SEVERITIES]
    if len(rows) != 9:
        raise ValueError(f"expected 9 pilot rows, got {len(rows)}")
    PILOT_JSON.write_text(json.dumps({"source_manifest": MANIFEST.name, "entries": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md: list[str] = ["# v1.17 Pilot-9 Severity Image Inputs", "", "原样导出自 `severity-image-manifest.json`；本文件不生成图片。", ""]
    prompts: list[str] = ["# v1.17 Pilot-9 Image Generation Prompts", "", "以下仅包装现有 `prompt_basis`，不增加 Knowledge 症状或 Treatment。", ""]
    constraints = [
        "realistic agricultural documentary/reference illustration",
        "exact host crop must be visually recognizable",
        "visible damage must correspond only to the frozen manifestation",
        "natural daylight",
        "realistic plant morphology",
        "no embedded text",
        "no watermark",
        "no UI",
        "no humans by default",
        "no unrelated disease symptoms",
        "no treatment tools/products visible",
        "no exaggerated cinematic effects",
        "final UI label remains external: AI示意图 · 非真实照片",
    ]
    for row in rows:
        md.extend([
            f"## {row['asset_id']}", "",
            f"- insect: {row['insect']}", f"- host: {row['host']}", f"- severity: {row['severity']}",
            f"- manifestation_text: {row['knowledge_basis']['manifestation_text']}",
            f"- source_ids: {', '.join(row['knowledge_basis']['source_ids'])}",
            f"- prompt_basis: {row['prompt_basis']}",
            f"- original_png: {row['asset']['original_png']}",
            f"- display_label: {row['display_label']}", "",
        ])
        prompts.extend([
            f"## {row['asset_id']}", "", f"Base prompt: {row['prompt_basis']}", "",
            "Global visual constraints:", *(f"- {item}" for item in constraints), "",
        ])
    PILOT_MD.write_text("\n".join(md), encoding="utf-8")
    PROMPTS_MD.write_text("\n".join(prompts), encoding="utf-8")
    print(f"exported {len(rows)} pilot rows")


if __name__ == "__main__":
    main()
