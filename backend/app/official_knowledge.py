"""Read-only adapter for the accepted official five-disease candidate bundle."""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

from .config import settings
from .taxonomy import OFFICIAL_TAXONOMY_VERSION, official_item_for_key


_TIER_LABELS = {"mild": "轻度", "moderate": "中度", "severe": "重度"}
_IMAGE_DIRS = {
    "rice_blast": "rice_blast",
    "rice_brown_spot": "rice_brown_spot",
    "northern_corn_leaf_blight": "northern_corn_leaf_blight",
    "rice_tungro": "rice_tungro",
    "corn_gray_leaf_spot": "corn_gray_leaf_spot",
}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_key(value: str) -> str:
    return value.split("::", 1)[-1]


@lru_cache(maxsize=1)
def _bundle() -> dict[str, Any]:
    root = settings.official_knowledge_dir
    candidate = _read(root / "knowledge_candidate.json")
    treatment = _read(root / "treatment_v4.json")
    registry = _read(root / "source_registry.json")
    manifest = _read(root / "severity_image_manifest.json")
    aliases = {
        **{str(key): str(value) for key, value in (registry.get("source_id_aliases") or {}).items()},
        **{str(key): str(value) for key, value in (treatment.get("source_id_aliases") or {}).items()},
    }
    sources: dict[str, dict[str, Any]] = {}
    for source in registry.get("sources", []):
        if isinstance(source, dict) and source.get("source_id"):
            sources[str(source["source_id"])] = dict(source)
    for key, source in (treatment.get("sources") or {}).items():
        if isinstance(source, dict):
            sources[str(aliases.get(key, key))] = {"source_id": aliases.get(key, key), **source}
    return {"candidate": candidate, "treatment": treatment, "registry": registry, "manifest": manifest, "aliases": aliases, "sources": sources}


def clear_cache() -> None:
    _bundle.cache_clear()


def _source_id(source_id: Any) -> str:
    return str(_bundle()["aliases"].get(str(source_id), source_id))


def _source_ids(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(_source_id(value) for value in values if value))


def _source_payload(source_id: str) -> dict[str, Any]:
    source = _bundle()["sources"].get(source_id, {})
    return {
        "id": source_id,
        "title": source.get("title", source_id),
        "site_name": source.get("organization", source.get("site", "")),
        "url": source.get("verified_url") or source.get("url", ""),
        "publisher": source.get("organization", source.get("site", "")),
        "retrieved_at": _bundle()["registry"].get("accessed_at", ""),
        "reliability_level": source.get("tier") or source.get("evidence_level"),
    }


def _find_disease(class_id: int | None = None, canonical_key: str | None = None) -> dict[str, Any] | None:
    wanted = _canonical_key(canonical_key) if canonical_key else None
    for disease in _bundle()["candidate"].get("diseases", []):
        key = _canonical_key(str(disease.get("stable_key", "")))
        if class_id is not None and int(disease.get("class_id", -1)) == int(class_id):
            return disease
        if wanted and key in {wanted, "gray_leaf_spot" if wanted == "corn_gray_leaf_spot" else wanted}:
            return disease
    return None


def _render() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})


def _rows_table(rows: list[dict[str, Any]]) -> str:
    lines = ["| 项目 | 内容 |", "| --- | --- |"]
    for row in rows:
        if isinstance(row, dict):
            lines.append(f"| {row.get('field', '')} | {row.get('value', '')} |" )
    return "\n".join(lines)


def _disease_source_ids(disease: dict[str, Any]) -> list[str]:
    full = disease.get("full_knowledge") or {}
    ids: list[str] = []
    for section in ("basic_info", "features", "harm_symptoms"):
        ids.extend(_source_ids((full.get(section) or {}).get("source_ids")))
    return list(dict.fromkeys(ids))


def _item_identity(disease: dict[str, Any]) -> dict[str, Any]:
    name = str(disease.get("canonical_class_name"))
    key = _canonical_key(str(disease.get("stable_key", "")))
    if key == "gray_leaf_spot":
        key = "corn_gray_leaf_spot"
    item = official_item_for_key(key) or {"class_id": int(disease["class_id"]), "canonical_key": key, "name_zh": name}
    return {
        "taxonomy_version": OFFICIAL_TAXONOMY_VERSION,
        "class_id": int(disease["class_id"]),
        "canonical_key": key,
        "canonical_class_name": name,
        "class_name": name,
        "name_zh": name,
        "name_en": item.get("name_en", key),
        "type": "病害",
    }


def knowledge_card(class_id: int | None = None, canonical_key: str | None = None) -> dict[str, Any] | None:
    disease = _find_disease(class_id, canonical_key)
    if disease is None:
        return None
    identity = _item_identity(disease)
    full = disease.get("full_knowledge") or {}
    source_ids = _disease_source_ids(disease)
    return {
        **identity,
        "source_ids": source_ids,
        "basic_info": deepcopy(full.get("basic_info") or {}),
        "features": deepcopy(full.get("features") or {}),
        "harm_symptoms": deepcopy(full.get("harm_symptoms") or {}),
        "prevention": [],
        "first_actions": [],
        "management": {},
        "chemical_safety": None,
        "source": [_source_payload(source_id) for source_id in source_ids],
    }


def knowledge_document(class_id: int | None = None, canonical_key: str | None = None) -> dict[str, Any] | None:
    card = knowledge_card(class_id, canonical_key)
    if card is None:
        return None
    disease = _find_disease(class_id, canonical_key)
    assert disease is not None
    full = disease.get("full_knowledge") or {}
    renderer = _render()
    basic = _rows_table((full.get("basic_info") or {}).get("rows") or [])
    features = "\n\n".join((full.get("features") or {}).get("paragraphs") or [])
    harms = "\n\n".join((full.get("harm_symptoms") or {}).get("paragraphs") or [])
    blocks = [("基础信息", basic), ("特征", features), ("为害症状", harms)]
    sections = [{"title": title, "html": renderer.render(text), "full_width": title == "基础信息"} for title, text in blocks]
    source_id = card["source_ids"][0] if card["source_ids"] else ""
    source = _source_payload(source_id)
    return {
        "schema_version": "official-10class-knowledge-v1",
        "version": OFFICIAL_TAXONOMY_VERSION,
        **{key: card[key] for key in ("class_id", "canonical_key", "canonical_class_name", "class_name")},
        "taxonomy_version": OFFICIAL_TAXONOMY_VERSION,
        "title": card["class_name"],
        "source": {"title": source.get("title", "官方农业资料"), "url": source.get("url", ""), "attribution": source.get("publisher", "官方农业资料")},
        "markdown": "\n\n".join(f"## {title}\n{text}" for title, text in blocks),
        "requires_pesticide_warning": False,
        "pesticide_warning": None,
        "chemical_detection": "none",
        "symptoms_html": renderer.render(harms),
        "features_html": renderer.render(features),
        "prevention_html": "",
        "full_html": renderer.render("\n\n".join(f"## {title}\n{text}" for title, text in blocks)),
        "sections": sections,
    }


def _treatment_record(disease: dict[str, Any], level: str) -> dict[str, Any] | None:
    key = _canonical_key(str(disease.get("stable_key", "")))
    if key == "gray_leaf_spot":
        key = "corn_gray_leaf_spot"
    record = next((item for item in _bundle()["treatment"].get("diseases", []) if item.get("disease_key") == key), None)
    if record is None:
        return None
    return (record.get("tiers") or {}).get(level)


def treatment_payload(class_id: int, level: str | None) -> dict[str, Any]:
    disease = _find_disease(class_id)
    if disease is None:
        return {"source": "local_knowledge_base", "status": "unavailable", "reason": "knowledge_unavailable", "content": {}, "source_ids": [], "sources": []}
    if level not in _TIER_LABELS:
        return {"source": "local_knowledge_base", "status": "unavailable", "reason": "severity_uncertain", "content": {}, "source_ids": [], "sources": []}
    tier = _treatment_record(disease, level)
    if tier is None:
        return {"source": "local_knowledge_base", "status": "unavailable", "reason": "treatment_unavailable", "content": {}, "source_ids": [], "sources": []}
    sections = tier.get("sections") or {
        section_key: tier.get(section_key) or []
        for section_key in ("agricultural_physical", "biological", "chemical")
    }
    lines = [f"### {_TIER_LABELS[level]}"]
    section_labels = {"agricultural_physical": "农业/物理防治", "biological": "生物防治", "chemical": "化学防治"}
    source_ids: list[str] = []
    for section_key, label in section_labels.items():
        lines.append(f"\n#### {label}")
        entries = sections.get(section_key) or []
        if not entries:
            lines.append("\n暂无足够成熟来源支持。")
        for entry in entries:
            if isinstance(entry, dict):
                lines.append(f"\n- {entry.get('text', '')}")
                source_ids.extend(_source_ids(entry.get("source_ids")))
    safety = tier.get("safety_notice") or _bundle()["treatment"].get("global_safety_notice")
    lines.append(f"\n#### 安全提醒\n\n{safety}")
    source_ids = list(dict.fromkeys(source_ids))
    markdown = "\n".join(lines)
    return {
        "source": "local_knowledge_base",
        "status": "available",
        "severity_level": level,
        "severity_label": _TIER_LABELS[level],
        "content": {"tier": _TIER_LABELS[level], "markdown": markdown, "markdown_html": _render().render(markdown)},
        "source_ids": source_ids,
        "sources": [_source_payload(source_id) for source_id in source_ids],
        "requires_pesticide_warning": bool(tier.get("chemical")),
        "pesticide_warning": safety,
    }


def severity_payload(class_id: int, canonical_key: str | None = None) -> dict[str, Any]:
    disease = _find_disease(class_id, canonical_key)
    if disease is None:
        return {"status": "unavailable", "reason": "severity_rubric_unavailable"}
    identity = _item_identity(disease)
    references: dict[str, Any] = {}
    levels: dict[str, str] = {}
    image_key = _IMAGE_DIRS[identity["canonical_key"]]
    manifest_entries = _bundle()["manifest"].get("entries", [])
    for level in _TIER_LABELS:
        manifestation = ((disease.get("severity") or {}).get(level) or {}).get("manifestation") or {}
        levels[level] = str(manifestation.get("text") or "")
        entry = next((item for item in manifest_entries if _canonical_key(str(item.get("disease_key", ""))) in {identity["canonical_key"], "gray_leaf_spot" if identity["canonical_key"] == "corn_gray_leaf_spot" else identity["canonical_key"]} and item.get("severity") == level), {})
        source_ids = _source_ids(manifestation.get("source_ids"))
        references[level] = {
            "class_id": identity["class_id"],
            "canonical_class": identity["canonical_class_name"],
            "canonical_key": identity["canonical_key"],
            "severity": level,
            "rubric_reference": manifestation.get("source_scale_mapping") or manifestation.get("support_type"),
            "image_asset": f"/assets/severity/official_10class_20260917/{image_key}/{level}.png",
            "image_type": "AI_ILLUSTRATION",
            "source": _source_payload(source_ids[0]) if source_ids else None,
            "source_ids": source_ids,
            "license": "candidate_asset",
            "fallback_label": "AI示意图 · 非真实照片",
            "manifest_sha256": entry.get("sha256"),
        }
    return {
        "status": "available",
        "taxonomy_version": OFFICIAL_TAXONOMY_VERSION,
        "canonical_key": identity["canonical_key"],
        "canonical_class": identity["canonical_class_name"],
        "rubric": {
            "assessment_template": "source_backed_manifestation",
            "assessment_unit": "当前图片中可见的病害表现",
            "observable_features": "仅依据已审核来源的症状表现选择受害程度。",
            **levels,
            "uncertain": "无法判断",
        },
        "references": references,
    }


def source_registry() -> dict[str, Any]:
    return deepcopy(_bundle()["registry"])


def validate_bundle() -> dict[str, int]:
    diseases = _bundle()["candidate"].get("diseases", [])
    tiers = sum(1 for disease in diseases for level in _TIER_LABELS if ((disease.get("severity") or {}).get(level) or {}).get("manifestation"))
    treatment_tiers = sum(1 for disease in _bundle()["treatment"].get("diseases", []) for level in _TIER_LABELS if (disease.get("tiers") or {}).get(level))
    images = len(_bundle()["manifest"].get("entries", []))
    return {"diseases": len(diseases), "severity_tiers": tiers, "treatment_tiers": treatment_tiers, "images": images}
