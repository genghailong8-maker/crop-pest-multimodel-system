"""Run a real, SearchProvider-only Gemini Grounding connectivity check.

The caller must set temporary environment variables before starting Python.
This script never prints the API key and never calls detector services.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any
from urllib.parse import urlsplit

import httpx

from app import config
from app.search.google_grounding import GeminiGoogleGroundingProvider
from app.search.models import SearchEvidence
from app.search.normalizer import normalize_search_results


_REAL_ASYNC_CLIENT = httpx.AsyncClient


class ObservedAsyncClient:
    """Capture only HTTP metadata while delegating all network work to httpx."""

    events: list[dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        self._client = _REAL_ASYNC_CLIENT(**kwargs)

    async def __aenter__(self) -> "ObservedAsyncClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.__aexit__(*args)

    async def post(self, url: str, **kwargs: Any) -> Any:
        response = await self._client.post(url, **kwargs)
        event: dict[str, Any] = {"kind": "gemini", "status": response.status_code, "url": url}
        if response.status_code >= 400:
            try:
                error = response.json().get("error", {})
                if isinstance(error, dict):
                    event["error_code"] = error.get("code")
                    event["error_status"] = error.get("status")
                    event["error_message"] = str(error.get("message") or "")[:300]
            except (ValueError, TypeError):
                event["error_message"] = "Gemini 返回了不可解析的错误响应"
        self.events.append(event)
        return response

    async def get(self, url: str, **kwargs: Any) -> Any:
        response = await self._client.get(url, **kwargs)
        self.events.append(
            {
                "kind": "source_fetch",
                "status": response.status_code,
                "url": url,
                "body_length": len(response.content),
            }
        )
        return response


def _config_failure() -> dict[str, Any] | None:
    endpoint = config.settings.gemini_endpoint
    parsed = urlsplit(endpoint)
    if config.settings.search_provider != "google_grounding":
        return {"category": "provider_config", "message": "CROP_SEARCH_PROVIDER 不是 google_grounding"}
    if not config.settings.gemini_api_key:
        return {"category": "api_key_missing", "message": "GEMINI_API_KEY 未设置"}
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or "[url]" in endpoint:
        return {"category": "endpoint_schema", "message": "CROP_GEMINI_ENDPOINT 不是纯 HTTP(S) URL"}
    return None


def _source_row(source: Any, fetch_events: list[dict[str, Any]]) -> dict[str, Any]:
    matching = [event for event in fetch_events if event["url"] == source.url]
    return {
        "id": source.id,
        "url": source.url,
        "title": source.title,
        "site_name": source.site_name,
        "retrieved_at": source.retrieved_at,
        "raw_page_fetched": bool(source.content),
        "raw_body_length": len(source.content or ""),
        "fetch_http": [{"status": event["status"], "body_length": event["body_length"]} for event in matching],
    }


async def run(class_name: str) -> int:
    failure = _config_failure()
    if failure:
        print(json.dumps({"status": "FAIL", **failure}, ensure_ascii=False, indent=2))
        return 2

    import app.search.google_grounding as grounding_module

    grounding_module.httpx.AsyncClient = ObservedAsyncClient  # type: ignore[assignment]
    ObservedAsyncClient.events = []
    provider = GeminiGoogleGroundingProvider()
    results: list[dict[str, Any]] = []

    for query_type in ("harms", "possible_causes"):
        evidence: SearchEvidence = await provider.search_evidence(class_name, query_type)
        normalized = normalize_search_results([evidence])
        source_rows = [_source_row(source, [event for event in ObservedAsyncClient.events if event["kind"] == "source_fetch"]) for source in normalized.sources]
        source_ids = {source["id"] for source in source_rows}
        invalid_ids = sorted(
            source_id
            for source_id in source_ids
            if not source_id.startswith("source-")
        )
        results.append(
            {
                "query_type": query_type,
                "status": evidence.status,
                "queries": evidence.queries,
                "citation_count": len(evidence.sources),
                "citation_sources": [_source_row(source, [event for event in ObservedAsyncClient.events if event["kind"] == "source_fetch"]) for source in evidence.sources],
                "normalizer_status": normalized.status,
                "normalizer_source_count": len(normalized.sources),
                "normalizer_sources": source_rows,
                "source_ids_are_normalized": not invalid_ids and [source["id"] for source in source_rows] == [f"source-{index}" for index in range(1, len(source_rows) + 1)],
                "fallback_message": normalized.message,
            }
        )

    gemini_events = [event for event in ObservedAsyncClient.events if event["kind"] == "gemini"]
    fetch_events = [event for event in ObservedAsyncClient.events if event["kind"] == "source_fetch"]
    http_success = bool(gemini_events) and all(event["status"] == 200 for event in gemini_events)
    all_sources_valid = all(item["source_ids_are_normalized"] for item in results)
    all_queries_complete = all(item["queries"] for item in results)
    status = "PASS" if http_success and all_queries_complete and all_sources_valid else "FAIL"
    print(
        json.dumps(
            {
                "status": status,
                "provider": config.settings.search_provider,
                "model": config.settings.gemini_model,
                "endpoint": config.settings.gemini_endpoint,
                "class_name": class_name,
                "http": {"gemini_requests": gemini_events, "source_fetches": fetch_events},
                "queries": results,
                "checks": {
                    "http_success": http_success,
                    "grounding_requests": len(gemini_events),
                    "original_page_fetch_only": True,
                    "source_ids_valid": all_sources_valid,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "蛴螬")))
