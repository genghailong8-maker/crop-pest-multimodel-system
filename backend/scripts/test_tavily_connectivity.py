"""Run a real Tavily SearchProvider-only connectivity check.

The script reads temporary environment variables and never prints the API key.
It does not start or call detector services.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any
from urllib.parse import urlsplit

import httpx

from app import config
from app.search.normalizer import low_quality_reason, normalize_search_results, reliability_score
from app.search.tavily import TavilySearchProvider


_REAL_ASYNC_CLIENT = httpx.AsyncClient


class ObservedAsyncClient:
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
        event: dict[str, Any] = {
            "status": response.status_code,
            "url": url,
            "request": {
                "query": kwargs.get("json", {}).get("query"),
                "search_depth": kwargs.get("json", {}).get("search_depth"),
                "max_results": kwargs.get("json", {}).get("max_results"),
                "include_answer": kwargs.get("json", {}).get("include_answer"),
                "include_raw_content": kwargs.get("json", {}).get("include_raw_content"),
                "authorization_present": bool(kwargs.get("headers", {}).get("Authorization")),
            },
        }
        if response.status_code >= 400:
            try:
                error = response.json()
                event["error"] = {
                    "code": error.get("code") if isinstance(error, dict) else None,
                    "message": str(error.get("detail") or error.get("message") or "")[:300]
                    if isinstance(error, dict)
                    else "",
                }
            except (ValueError, TypeError):
                event["error"] = {"message": "Tavily 返回了不可解析的错误响应"}
        else:
            try:
                data = response.json()
                api_results = data.get("results") or []
                event["result_count"] = len(api_results)
                event["answer_present_in_response"] = bool(data.get("answer"))
                event["api_results"] = [
                    {
                        "title": str(item.get("title") or "")[:240],
                        "url": str(item.get("url") or "")[:2000],
                        "content_length": len(item.get("content") or "") if isinstance(item, dict) else 0,
                        "raw_content_length": len(item.get("raw_content") or "") if isinstance(item, dict) else 0,
                        "raw_content_available": bool(item.get("raw_content")) if isinstance(item, dict) else False,
                    }
                    for item in api_results
                    if isinstance(item, dict)
                ]
            except (ValueError, TypeError):
                event["error"] = {"message": "Tavily 成功响应不是可解析 JSON"}
        self.events.append(event)
        return response


def _config_failure() -> dict[str, Any] | None:
    parsed = urlsplit(config.settings.tavily_endpoint)
    if config.settings.search_provider != "tavily":
        return {"category": "provider_config", "message": "CROP_SEARCH_PROVIDER 不是 tavily"}
    if not config.settings.tavily_api_key:
        return {"category": "api_key_missing", "message": "TAVILY_API_KEY 未设置"}
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {"category": "endpoint", "message": "CROP_TAVILY_ENDPOINT 不是有效 HTTP(S) URL"}
    return None


def _source_row(source: Any) -> dict[str, Any]:
    return {
        "id": source.id,
        "title": source.title,
        "url": source.url,
        "site_name": source.site_name,
        "retrieved_at": source.retrieved_at,
        "content_length": len(source.content or ""),
        "content_available": bool(source.content),
        "filter_reason": low_quality_reason(source),
        "reliability": source.reliability_level or reliability_score(source)[1],
    }


def _low_quality_signal(source: dict[str, Any]) -> bool:
    return source["filter_reason"] is not None


async def run(class_name: str) -> int:
    failure = _config_failure()
    if failure:
        print(json.dumps({"status": "FAIL", **failure}, ensure_ascii=False, indent=2))
        return 2

    import app.search.tavily as tavily_module

    tavily_module.httpx.AsyncClient = ObservedAsyncClient  # type: ignore[assignment]
    ObservedAsyncClient.events = []
    provider = TavilySearchProvider()
    results: list[dict[str, Any]] = []

    for query_type in ("harms", "possible_causes"):
        evidence = await provider.search_evidence(class_name, query_type)
        normalized = normalize_search_results([evidence])
        normalized_sources = [_source_row(source) for source in normalized.sources]
        provider_sources = [_source_row(source) for source in evidence.sources]
        normalized_urls = {source["url"] for source in normalized_sources}
        low_quality_candidates = [source for source in provider_sources if _low_quality_signal(source)]
        low_quality_filtered = [source for source in low_quality_candidates if source["url"] not in normalized_urls]
        expected_ids = [f"source-{index}" for index in range(1, len(normalized_sources) + 1)]
        actual_ids = [source["id"] for source in normalized_sources]
        results.append(
            {
                "query_type": query_type,
                "provider_status": evidence.status,
                "queries": evidence.queries,
                "provider_result_count": len(evidence.sources),
                "provider_sources": provider_sources,
                "normalizer_status": normalized.status,
                "normalizer_source_count": len(normalized.sources),
                "normalizer_sources": normalized_sources,
                "filtered_or_deduplicated_count": max(0, len(evidence.sources) - len(normalized.sources)),
                "low_quality_candidates": low_quality_candidates,
                "low_quality_filtered_count": len(low_quality_filtered),
                "low_quality_filtering_effective": not low_quality_candidates or bool(low_quality_filtered),
                "source_ids_correct": actual_ids == expected_ids,
                "fallback_message": normalized.message,
            }
        )

    successful_requests = [event for event in ObservedAsyncClient.events if event["status"] == 200]
    all_http_success = len(successful_requests) == 2
    all_have_results = all(item["provider_result_count"] > 0 for item in results)
    all_have_content = all(any(source["content_available"] for source in item["provider_sources"]) for item in results)
    all_ids_correct = all(item["source_ids_correct"] for item in results)
    low_quality_filtering_effective = all(item["low_quality_filtering_effective"] for item in results)
    status = "PASS" if all_http_success and all_have_results and all_have_content and all_ids_correct and low_quality_filtering_effective else "FAIL"
    print(
        json.dumps(
            {
                "status": status,
                "provider": config.settings.search_provider,
                "endpoint": config.settings.tavily_endpoint,
                "class_name": class_name,
                "http": ObservedAsyncClient.events,
                "queries": results,
                "checks": {
                    "http_success_for_both_queries": all_http_success,
                    "results_returned_for_both_queries": all_have_results,
                    "content_or_raw_content_available": all_have_content,
                    "source_ids_valid": all_ids_correct,
                    "low_quality_filtering_effective": low_quality_filtering_effective,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "蛴螬")))
