"""Exact class-scoped evidence sourced from the curated knowledge documents."""

from __future__ import annotations

from typing import Any

from ..catalog import CLASS_BY_ID
from ..knowledge_documents import get_curated_evidence_sections
from .evidence_extractor import ExternalEvidenceAnalysis, ExternalEvidenceConclusion
from .models import SearchEvidence, SearchSource


CURATED_CLASS_IDS = frozenset({0, 8, 15})
CURATED_KNOWLEDGE_CLASS_ALIASES = {
    "玉米叶枯病": "玉米链格孢菌叶枯病",
}
_SECTION_BY_QUERY_TYPE = {"harms": "危害", "possible_causes": "可能诱因"}
_CURATED_RETRIEVED_AT = "2026-08-28"


def curated_evidence_for_class(
    class_id: int, class_name: str | None = None
) -> tuple[SearchEvidence, SearchEvidence] | None:
    """Build the existing SearchEvidence contract for the three exact classes."""
    catalog_item = CLASS_BY_ID.get(class_id)
    if class_id not in CURATED_CLASS_IDS or catalog_item is None:
        return None
    canonical_name = str(catalog_item["name_zh"])
    if class_name is not None and class_name != canonical_name:
        return None
    knowledge_class_name = CURATED_KNOWLEDGE_CLASS_ALIASES.get(
        canonical_name, canonical_name
    )
    curated = get_curated_evidence_sections(
        class_id, expected_class_name=knowledge_class_name
    )
    if curated is None or curated["class_name"] != canonical_name:
        return None

    evidence: list[SearchEvidence] = []
    for query_type, heading in _SECTION_BY_QUERY_TYPE.items():
        section = curated["sections"].get(heading)
        if not isinstance(section, dict):
            return None
        content = section.get("content")
        records = section.get("sources")
        if not isinstance(content, str) or not content or not isinstance(records, list) or not records:
            return None
        sources: list[SearchSource] = []
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                return None
            title, site, url = (record.get(key) for key in ("title", "site", "url"))
            if not all(isinstance(value, str) and value for value in (title, site, url)):
                return None
            sources.append(
                SearchSource(
                    id=f"curated-{class_id}-{query_type}-{index}",
                    title=title,
                    site_name=site,
                    url=url,
                    content=content if index == 1 else None,
                    retrieved_at=_CURATED_RETRIEVED_AT,
                    reliability_level="curated_knowledge_base",
                )
            )
        evidence.append(
            SearchEvidence(
                class_name=canonical_name,
                query_type=query_type,
                status="available",
                sources=sources,
                message="本地精选知识库证据",
            )
        )
    return evidence[0], evidence[1]


def curated_analysis(
    evidence: tuple[SearchEvidence, SearchEvidence],
) -> ExternalEvidenceAnalysis:
    """Expose curated text directly while retaining the existing source-id contract."""
    conclusions: dict[str, list[ExternalEvidenceConclusion]] = {}
    for item in evidence:
        content = item.sources[0].content if item.sources else None
        if not content or not item.sources:
            continue
        conclusions[item.query_type] = [
            ExternalEvidenceConclusion(conclusion=content, source_ids=[item.sources[0].id])
        ]
    return ExternalEvidenceAnalysis(
        status="available" if conclusions else "unavailable",
        harms=conclusions.get("harms", []),
        possible_causes=conclusions.get("possible_causes", []),
    )


def curated_public_sources(
    evidence: tuple[SearchEvidence, SearchEvidence],
) -> list[dict[str, Any]]:
    return [source.public_metadata() for item in evidence for source in item.sources]
