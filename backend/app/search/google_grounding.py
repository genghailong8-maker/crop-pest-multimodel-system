"""Gemini API + Grounding with Google Search provider.

Gemini is used only as a live search/citation broker here. Its synthesized
answer is intentionally discarded. The cited URLs are fetched as source
material and normalized before Qwen3-VL receives them.
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


def _valid_url(value: Any) -> str | None:
    url = str(value or "").strip()
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return url[:2000]


def _site_name(url: str, title: Any) -> str:
    return str(urlsplit(url).hostname or title or "外部网页").strip()[:160]


def _citation_source(url: Any, title: Any, snippet: Any, index: int) -> SearchSource | None:
    safe_url = _valid_url(url)
    if not safe_url:
        return None
    clean_title = str(title or "").strip()[:240] or (urlsplit(safe_url).hostname or "外部网页")
    clean_snippet = str(snippet or "").strip()[:1200] or None
    return SearchSource(
        id=f"grounding-{index}",
        title=clean_title,
        site_name=_site_name(safe_url, title),
        url=safe_url,
        snippet=clean_snippet,
        retrieved_at=now_iso(),
    )


def _interaction_citations(payload: dict[str, Any]) -> tuple[list[str], list[SearchSource]]:
    queries: list[str] = []
    sources: list[SearchSource] = []
    for step in payload.get("steps") or []:
        if not isinstance(step, dict):
            continue
        if step.get("type") == "google_search_call":
            arguments = step.get("arguments") or {}
            if isinstance(arguments, dict):
                queries.extend(str(query).strip() for query in arguments.get("queries", []) if str(query).strip())
        if step.get("type") != "model_output":
            continue
        for block in step.get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            text = str(block.get("text") or "")
            for annotation in block.get("annotations") or []:
                if not isinstance(annotation, dict) or annotation.get("type") != "url_citation":
                    continue
                start = annotation.get("start_index")
                end = annotation.get("end_index")
                snippet = (
                    text[start:end]
                    if isinstance(start, int)
                    and isinstance(end, int)
                    and 0 <= start <= end <= len(text)
                    else None
                )
                source = _citation_source(
                    annotation.get("url"),
                    annotation.get("title"),
                    snippet,
                    len(sources) + 1,
                )
                if source:
                    sources.append(source)
    return queries, sources


def _legacy_grounding_citations(payload: dict[str, Any]) -> tuple[list[str], list[SearchSource]]:
    candidates = payload.get("candidates") or []
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        return [], []
    metadata = candidates[0].get("groundingMetadata") or candidates[0].get("grounding_metadata") or {}
    if not isinstance(metadata, dict):
        return [], []
    queries = [
        str(query).strip()
        for query in metadata.get("webSearchQueries", metadata.get("web_search_queries", []))
        if str(query).strip()
    ]
    chunks = metadata.get("groundingChunks", metadata.get("grounding_chunks", [])) or []
    supports = metadata.get("groundingSupports", metadata.get("grounding_supports", [])) or []
    snippets: dict[int, str] = {}
    for support in supports:
        if not isinstance(support, dict):
            continue
        segment = support.get("segment") or {}
        text = str(segment.get("text") or "").strip()
        for index in support.get("groundingChunkIndices", support.get("grounding_chunk_indices", [])) or []:
            if isinstance(index, int) and text:
                snippets[index] = text[:1200]
    sources: list[SearchSource] = []
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            continue
        web = chunk.get("web") or {}
        if not isinstance(web, dict):
            continue
        source = _citation_source(
            web.get("uri"),
            web.get("title"),
            snippets.get(index),
            len(sources) + 1,
        )
        if source:
            sources.append(source)
    return queries, sources


def parse_grounding_response(
    payload: dict[str, Any],
    class_name: str,
    query_type: QueryType,
) -> SearchEvidence:
    """Extract only citation metadata; never expose Gemini text as content."""
    queries, sources = _interaction_citations(payload)
    if not sources:
        legacy_queries, legacy_sources = _legacy_grounding_citations(payload)
        queries.extend(legacy_queries)
        sources.extend(legacy_sources)
    return SearchEvidence(
        class_name=class_name,
        query_type=query_type,
        status="available" if sources else "unavailable",
        queries=list(dict.fromkeys(queries))[:6],
        sources=sources[:5],
        message=None if sources else "Google Grounding 未返回可用引用",
    )


class GeminiGoogleGroundingProvider:
    """Use Gemini's official Google Search grounding tool as a citation broker."""

    def __init__(self) -> None:
        settings = config.settings
        self.timeout = httpx.Timeout(
            settings.search_timeout_seconds,
            connect=min(5.0, settings.search_timeout_seconds),
        )

    async def _fetch_content(self, client: httpx.AsyncClient, url: str) -> str | None:
        try:
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
        if not settings.gemini_api_key:
            return SearchEvidence(
                class_name=class_name,
                query_type=query_type,
                status="unavailable",
                message="Gemini Grounding 未配置 GEMINI_API_KEY",
            )
        query = QUERY_TEMPLATES[query_type].format(class_name=class_name)
        request = {
            "model": settings.gemini_model,
            "input": query,
            "tools": [{"type": "google_search"}],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    settings.gemini_endpoint,
                    headers={
                        "x-goog-api-key": settings.gemini_api_key,
                        "Content-Type": "application/json",
                    },
                    json=request,
                )
                response.raise_for_status()
                parsed = parse_grounding_response(response.json(), class_name, query_type)
                contents = await asyncio.gather(
                    *(self._fetch_content(client, source.url) for source in parsed.sources),
                    return_exceptions=True,
                )
                enriched = [
                    source.model_copy(update={"content": content if isinstance(content, str) else None})
                    for source, content in zip(parsed.sources, contents, strict=True)
                ]
            usable = any(source.content for source in enriched)
            return parsed.model_copy(
                update={
                    "status": "available" if usable else "unavailable",
                    "sources": enriched,
                    "message": None if usable else "Google Grounding 引用未能核验原始网页内容",
                }
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return SearchEvidence(
                class_name=class_name,
                query_type=query_type,
                status="error",
                queries=[query],
                message=f"Gemini Grounding 暂时失败：{type(exc).__name__}",
            )
