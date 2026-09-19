from __future__ import annotations

from .. import config
from .base import QueryType, SearchProvider
from .models import SearchEvidence, SearchSource
from .google_custom_search_legacy import LegacyGoogleCustomSearchProvider
from .google_grounding import GeminiGoogleGroundingProvider
from .tavily import TavilySearchProvider


class DisabledSearchProvider:
    async def search_evidence(self, class_name: str, query_type: QueryType) -> SearchEvidence:
        return SearchEvidence(
            class_name=class_name,
            query_type=query_type,
            status="unavailable",
            message="外部检索未配置",
        )


class MockSearchProvider:
    def __init__(self, sources: list[SearchSource] | None = None) -> None:
        self.sources = sources or [
            SearchSource(
                id="mock-source-1",
                title="示例农业资料",
                site_name="测试资料源",
                url="https://example.invalid/agriculture/evidence",
                snippet="仅用于自动化测试，不代表真实检索结果。",
                content="仅用于自动化测试的外部资料片段。",
                reliability_level="测试资料源",
            )
        ]

    async def search_evidence(self, class_name: str, query_type: QueryType) -> SearchEvidence:
        return SearchEvidence(
            class_name=class_name,
            query_type=query_type,
            status="mock",
            queries=[f"{class_name} {query_type}"],
            sources=self.sources,
            message="仅用于自动化测试，不代表真实 Web Search 已接入",
        )


def provider_from_settings() -> SearchProvider:
    provider = (config.settings.search_provider or "disabled").lower()
    if provider == "google_grounding":
        return GeminiGoogleGroundingProvider()
    if provider == "tavily":
        return TavilySearchProvider()
    if provider in {"google_legacy", "google_custom_search_legacy", "google"}:
        return LegacyGoogleCustomSearchProvider()
    if provider == "mock":
        return MockSearchProvider()
    return DisabledSearchProvider()
