from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


TAXONOMY_PATH = Path(__file__).resolve().parents[2] / "config" / "r3-taxonomy.json"


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    payload = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "r3-taxonomy-v1":
        raise ValueError("R3 taxonomy schema is invalid")
    return payload


def taxonomy_payload() -> dict[str, Any]:
    return json.loads(json.dumps(load_taxonomy(), ensure_ascii=False))


def taxonomy_values(section: str) -> set[str]:
    return {str(item["value"]) for item in load_taxonomy()[section]}


def validate_context_values(
    *, subject_type: str, crop_species: str | None, affected_part: str | None, insect_species: str | None
) -> dict[str, Any]:
    if subject_type not in {"plant", "insect"}:
        raise ValueError("subject_type must be plant or insect")
    if subject_type == "plant":
        if crop_species not in taxonomy_values("crops"):
            raise ValueError("plant context requires a valid crop_species")
        if affected_part not in taxonomy_values("affected_parts"):
            raise ValueError("plant context requires a valid affected_part")
        return {
            "subject_type": "plant",
            "crop_species": crop_species,
            "affected_part": affected_part,
            "insect_species": None,
        }
    if insect_species not in taxonomy_values("insects"):
        raise ValueError("insect context requires a valid insect_species")
    return {
        "subject_type": "insect",
        "crop_species": None,
        "affected_part": None,
        "insect_species": insect_species,
    }


def normalize_prediction(payload: Any) -> dict[str, Any]:
    """Keep only deterministic taxonomy candidates returned by the context service."""
    if not isinstance(payload, dict):
        return {"status": "unavailable", "reason": "invalid_context_response"}
    if payload.get("status") != "available":
        return {"status": "unavailable", "reason": str(payload.get("reason") or "context_service_unavailable")}
    result: dict[str, Any] = {"status": "available", "model": payload.get("model"), "revision": payload.get("revision")}
    for key, section in (("subject_type", "subject_types"), ("crop_species", "crops"), ("affected_part", "affected_parts"), ("insect_species", "insects")):
        allowed = taxonomy_values(section)
        raw = payload.get(key)
        if not isinstance(raw, dict):
            result[key] = None
            continue
        candidates = []
        for candidate in raw.get("candidates", []):
            if not isinstance(candidate, dict) or candidate.get("value") not in allowed:
                continue
            candidates.append({"value": candidate["value"], "score": float(candidate.get("score", 0.0)), "rank": len(candidates) + 1})
            if len(candidates) == 3:
                break
        result[key] = {
            "top1": candidates[0]["value"] if candidates else None,
            "candidates": candidates,
            "margin": float(raw["margin"]) if raw.get("margin") is not None else None,
        }
    return result
