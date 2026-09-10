"""Legacy Google Custom Search JSON API provider.

This is retained only for installations that already have Custom Search JSON
API access. New deployments should use ``google_grounding`` instead.
"""

from __future__ import annotations

import asyncio
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

import httpx

from .. import config
from .base import QueryType
from .models import SearchEvidence, SearchSource, now_iso


QUERY_TEMPLATES = {
    "harms": "{class_name} 危害 危害症状 农业",
    "possible_causes": "{class_name} 发生条件 发病条件 发生原因 农业",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            text = re.sub(r"\s+", " ", data).strip()
            if text:
                self.parts.append(text)


def _text_from_html(raw: bytes, limit: int = 12000) -> str:
    parser = _TextExtractor()
    parser.feed(raw.decode("utf-8", errors="ignore"))
    return " ".join(parser.parts)[:limit]


def _safe_site_name(url: str, display_link: str | None) -> str:
    return (display_link or urlsplit(url).hostname or "外部网页").strip()[:160]


class LegacyGoogleCustomSearchProvider:
    """Compatibility provider for existing Custom Search JSON API accounts."""

    endpoint = "https://www.googleapis.com/customsearch/v1"

    def __init__(self) -> None:
        settings = config.settings
        self.timeout = httpx.Timeout(
            settings.search_timeout_seconds,
            connect=min(5.0, settings.search_timeout_seconds),
        )

    async def _fetch_content(self, client: httpx.AsyncClient, url: str) -> str | None:
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                return None
            response = await client.get(
                url,
                headers={"User-Agent": "crop-pest-evidence/1.0"},
                follow_redirects=True,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if content_type and "html" not in content_type.lower():
                return None
            return _text_from_html(response.content)
        except (httpx.HTTPError, UnicodeError):
            return None

    async def search_evidence(self, class_name: str, query_type: QueryType) -> SearchEvidence:
        settings = config.settings
        if not settings.google_api_key or not settings.google_search_engine_id:
            return SearchEvidence(
                class_name=class_name,
                query_type=query_type,
                status="unavailable",
                message="Legacy Google Custom Search 未配置 API Key 或搜索引擎 ID",
            )
        query = QUERY_TEMPLATES[query_type].format(class_name=class_name)
        params = {
            "key": settings.google_api_key,
            "cx": settings.google_search_engine_id,
            "q": query,
            "num": min(10, max(1, settings.search_max_sources * 2)),
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.endpoint, params=params)
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                items = payload.get("items") or []
                candidates: list[SearchSource] = []
                for item in items:
                    url = str(item.get("link") or "").strip()
                    title = str(item.get("title") or "").strip()
                    if not url or not title:
                        continue
                    candidates.append(
                        SearchSource(
                            id=f"legacy-search-{len(candidates) + 1}",
                            title=title[:240],
                            site_name=_safe_site_name(url, item.get("displayLink")),
                            url=url,
                            snippet=str(item.get("snippet") or "")[:1200] or None,
                            retrieved_at=now_iso(),
                        )
                    )
                contents = await asyncio.gather(
                    *(self._fetch_content(client, source.url) for source in candidates),
                    return_exceptions=True,
                )
                enriched = [
                    source.model_copy(update={"content": content if isinstance(content, str) else None})
                    for source, content in zip(candidates, contents, strict=True)
                ]
            usable = any(source.content for source in enriched)
            return SearchEvidence(
                class_name=class_name,
                query_type=query_type,
                status="available" if usable else "unavailable",
                queries=[query],
                sources=enriched,
                message=None if usable else "Legacy 搜索结果未能核验原始网页内容",
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return SearchEvidence(
                class_name=class_name,
                query_type=query_type,
                status="error",
                queries=[query],
                message=f"Legacy Google 搜索暂时失败：{type(exc).__name__}",
            )
