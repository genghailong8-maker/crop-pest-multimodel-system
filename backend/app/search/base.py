from __future__ import annotations

from typing import Literal, Protocol

from .models import SearchEvidence

QueryType = Literal["harms", "possible_causes"]


class SearchProvider(Protocol):
    async def search_evidence(self, class_name: str, query_type: QueryType) -> SearchEvidence:
        """Return source-backed material for one diagnosis question."""
