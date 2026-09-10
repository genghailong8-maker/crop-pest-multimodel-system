from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

QueryType = Literal["harms", "possible_causes"]
SearchStatus = Literal["available", "unavailable", "error", "mock"]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SearchSource(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=240)
    site_name: str = Field(min_length=1, max_length=160)
    url: str = Field(min_length=1, max_length=2000)
    snippet: str | None = Field(default=None, max_length=1200)
    content: str | None = Field(default=None, max_length=12000)
    retrieved_at: str = Field(default_factory=now_iso, max_length=80)
    reliability_level: str | None = Field(default=None, max_length=80)

    def public_metadata(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "title": self.title,
            "site_name": self.site_name,
            "url": self.url,
            "snippet": self.snippet,
            "retrieved_at": self.retrieved_at,
            "reliability_level": self.reliability_level,
        }


class SearchEvidence(BaseModel):
    class_name: str = Field(min_length=1, max_length=160)
    query_type: QueryType = "harms"
    status: SearchStatus = "unavailable"
    queries: list[str] = Field(default_factory=list, max_length=6)
    sources: list[SearchSource] = Field(default_factory=list, max_length=5)
    message: str | None = Field(default=None, max_length=240)
