"""Validate the repository-side R3.1 severity image foundation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "severity-image-manifest.json"
LABEL = "AI示意图 · 非真实照片"
SEVERITIES = {"mild", "moderate", "severe"}
PAIR_PATTERN = re.compile(r"^(0[1-9]|[12][0-9]|3[0-8])$")
PATH_PATTERN = re.compile(r"^web/public/assets/severity/r31/(0[1-9]|[12][0-9]|3[0-8])/(mild|moderate|severe)\.(png|webp)$")


def load() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def validate(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    data = manifest or load()
    entries = data.get("entries", [])
    errors: list[str] = []
    pairs = {(item.get("pair_id"), item.get("insect"), item.get("host")) for item in entries}
    asset_ids = [item.get("asset_id") for item in entries]
    paths = [item.get("asset", {}).get("original_png") for item in entries]
    by_pair: dict[str, set[str]] = {}
    for item in entries:
        pair_id = item.get("pair_id")
        severity = item.get("severity")
        by_pair.setdefault(pair_id, set()).add(severity)
        if not PAIR_PATTERN.fullmatch(str(pair_id)):
            errors.append(f"invalid_pair_id:{pair_id}")
        if severity not in SEVERITIES:
            errors.append(f"invalid_severity:{pair_id}:{severity}")
        if not item.get("knowledge_basis", {}).get("manifestation_text"):
            errors.append(f"empty_manifestation:{pair_id}:{severity}")
        if not item.get("knowledge_basis", {}).get("source_ids"):
            errors.append(f"empty_source_ids:{pair_id}:{severity}")
        if not item.get("prompt_basis"):
            errors.append(f"empty_prompt_basis:{pair_id}:{severity}")
        if item.get("display_label") != LABEL:
            errors.append(f"invalid_display_label:{pair_id}:{severity}")
        asset = item.get("asset", {})
        for field in ("original_png", "web_derivative"):
            if not PATH_PATTERN.fullmatch(str(asset.get(field))):
                errors.append(f"invalid_asset_path:{pair_id}:{severity}:{field}")
        if "treatment" in str(item.get("prompt_basis", "")).lower():
            errors.append(f"treatment_in_prompt:{pair_id}:{severity}")
    for pair_id, severities in by_pair.items():
        if severities != SEVERITIES:
            errors.append(f"missing_tier:{pair_id}:{sorted(SEVERITIES - severities)}")
    result = {
        "PAIR_COUNT": len(pairs),
        "ASSET_COUNT": len(entries),
        "MISSING_TIERS": sum(1 for value in by_pair.values() if value != SEVERITIES),
        "DUPLICATE_ASSET_IDS": len(asset_ids) - len(set(asset_ids)),
        "DUPLICATE_ASSET_PATHS": len(paths) - len(set(paths)),
        "EMPTY_MANIFESTATIONS": sum(not item.get("knowledge_basis", {}).get("manifestation_text") for item in entries),
        "EMPTY_SOURCE_IDS": sum(not item.get("knowledge_basis", {}).get("source_ids") for item in entries),
        "EMPTY_PROMPT_BASIS": sum(not item.get("prompt_basis") for item in entries),
        "UNCERTAIN_IMAGE_ENTRIES": sum(item.get("severity") == "uncertain" for item in entries),
        "ERRORS": errors,
    }
    result["status"] = "PASS" if (
        result["PAIR_COUNT"] == 38
        and result["ASSET_COUNT"] == 114
        and not errors
        and result["DUPLICATE_ASSET_IDS"] == 0
        and result["DUPLICATE_ASSET_PATHS"] == 0
        and result["UNCERTAIN_IMAGE_ENTRIES"] == 0
    ) else "FAIL"
    return result


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
