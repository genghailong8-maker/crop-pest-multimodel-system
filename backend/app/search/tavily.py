"""Tavily Search provider for external source retrieval only."""

from __future__ import annotations

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


def _valid_url(value: Any) -> str | None:
    url = str(value or "").strip()
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return url[:2000]


def _site_name(url: str) -> str:
    return (urlsplit(url).hostname or "外部网页").strip()[:160]


class TavilySearchProvider:
    """Call Tavily Search and expose source content, never Tavily's answer."""

    def __init__(self) -> None:
        settings = config.settings
        self.timeout = httpx.Timeout(
            settings.search_timeout_seconds,
            connect=min(5.0, settings.search_timeout_seconds),
        )

    async def search_evidence(self, class_name: str, query_type: QueryType) -> SearchEvidence:
        settings = config.settings
        if not settings.tavily_api_key:
            return SearchEvidence(
                class_name=class_name,
                query_type=query_type,
                status="unavailable",
                message="Tavily 未配置 TAVILY_API_KEY",
            )
        query = QUERY_TEMPLATES[query_type].format(class_name=class_name)
        payload = {
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": min(5, max(1, settings.search_max_sources)),
            "include_answer": False,
            "include_raw_content": "text",
            "include_images": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    settings.tavily_endpoint,
                    headers={
                        "Authorization": f"Bearer {settings.tavily_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
            sources: list[SearchSource] = []
            for item in data.get("results") or []:
                if not isinstance(item, dict):
                    continue
                url = _valid_url(item.get("url"))
                if not url:
                    continue
                title = str(item.get("title") or "").strip()[:240]
                if not title:
                    continue
                raw_content = item.get("raw_content")
                content = raw_content if isinstance(raw_content, str) and raw_content.strip() else item.get("content")
                sources.append(
                    SearchSource(
                        id=f"tavily-{len(sources) + 1}",
                        title=title,
                        site_name=_site_name(url),
                        url=url,
                        snippet=str(item.get("content") or "")[:1200] or None,
                        content=str(content or "")[:12000] or None,
                        retrieved_at=now_iso(),
                    )
                )
            return SearchEvidence(
                class_name=class_name,
                query_type=query_type,
                status="available" if sources else "unavailable",
                queries=[str(data.get("query") or query)[:320]],
                sources=sources,
                message=None if sources else "Tavily 未返回可核验来源正文",
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return SearchEvidence(
                class_name=class_name,
                query_type=query_type,
                status="error",
                queries=[query],
                message=f"Tavily 搜索暂时失败：{type(exc).__name__}",
            )
