from __future__ import annotations

import asyncio

from .base import SearchProvider
from .models import SearchEvidence, SearchSource
from .normalizer import build_qwen_context, normalize_search_results
from .provider import provider_from_settings


QUERY_TYPES = ("harms", "possible_causes")


async def collect_external_evidence(class_name: str) -> SearchEvidence:
    provider: SearchProvider = provider_from_settings()
    results = await asyncio.gather(
        *(provider.search_evidence(class_name, query_type) for query_type in QUERY_TYPES),
        return_exceptions=True,
    )
    evidence: list[SearchEvidence] = []
    for query_type, result in zip(QUERY_TYPES, results, strict=True):
        if isinstance(result, SearchEvidence):
            evidence.append(result)
        else:
            evidence.append(
                SearchEvidence(
                    class_name=class_name,
                    query_type=query_type,
                    status="unavailable",
                    message="外部检索暂时不可用",
                )
            )
    return normalize_search_results(evidence)


def public_sources(evidence: SearchEvidence) -> list[dict[str, str | None]]:
    return [source.public_metadata() for source in evidence.sources]


def source_ids(evidence: SearchEvidence) -> set[str]:
    return {source.id for source in evidence.sources if source.content}


__all__ = [
    "SearchEvidence",
    "SearchProvider",
    "SearchSource",
    "build_qwen_context",
    "collect_external_evidence",
    "public_sources",
    "source_ids",
]
