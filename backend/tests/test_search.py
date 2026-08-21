from __future__ import annotations

import asyncio
from dataclasses import replace

import httpx

from app import config
from app.search import collect_external_evidence
from app.search.google_custom_search_legacy import LegacyGoogleCustomSearchProvider
from app.search.google_grounding import GeminiGoogleGroundingProvider, parse_grounding_response
from app.search.models import SearchEvidence, SearchSource
from app.search.normalizer import build_qwen_context, is_obviously_low_quality, low_quality_reason, normalize_search_results, reliability_score
from app.search.provider import DisabledSearchProvider, MockSearchProvider, provider_from_settings
from app.search.tavily import TavilySearchProvider


def source(source_id: str, url: str, *, content: str | None = "原始页面正文") -> SearchSource:
    return SearchSource(id=source_id, title=f"资料 {source_id}", site_name="测试来源", url=url, content=content)


def test_disabled_provider_is_explicit_and_does_not_fake_sources():
    result = asyncio.run(DisabledSearchProvider().search_evidence("蛴螬", "harms"))
    assert result.status == "unavailable"
    assert result.sources == []
    assert "未配置" in (result.message or "")


def test_mock_provider_is_only_for_tests():
    result = asyncio.run(MockSearchProvider().search_evidence("蛴螬", "possible_causes"))
    assert result.status == "mock"
    assert "不代表真实" in (result.message or "")


def test_provider_settings_recommend_grounding_and_keep_legacy_separate(monkeypatch):
    monkeypatch.setattr(config, "settings", replace(config.settings, search_provider="google_grounding"))
    assert isinstance(provider_from_settings(), GeminiGoogleGroundingProvider)
    monkeypatch.setattr(config, "settings", replace(config.settings, search_provider="google_legacy"))
    assert isinstance(provider_from_settings(), LegacyGoogleCustomSearchProvider)


def test_normalizer_deduplicates_and_prioritizes_reliable_sources():
    result = normalize_search_results(
        [
            SearchEvidence(
                class_name="蛴螬",
                query_type="harms",
                status="available",
                sources=[source("ordinary", "https://example.com/article", content="普通网页"), source("gov", "https://agri.gov.cn/article?utm_source=test", content="政府原文")],
            ),
            SearchEvidence(
                class_name="蛴螬",
                query_type="possible_causes",
                status="available",
                sources=[source("duplicate", "https://agri.gov.cn/article", content="重复政府原文")],
            ),
        ]
    )
    assert result.status == "available"
    assert len(result.sources) == 2
    assert result.sources[0].url == "https://agri.gov.cn/article"
    assert result.sources[0].reliability_level == "政府农业部门"


def test_authoritative_agriculture_library_is_ranked_as_reliable():
    score, level = reliability_score(source("cabi", "https://www.cabidigitallibrary.org/doi/record", content="研究资料"))
    assert score == 60
    assert level == "权威农业数据库"


def test_normalizer_filters_obvious_forum_and_shop_pages():
    result = normalize_search_results(
        [
            SearchEvidence(
                class_name="蛴螬",
                query_type="harms",
                status="available",
                sources=[source("forum", "https://example.com/forum/pest", content="论坛内容"), source("shop", "https://example.com/shop/pest", content="营销内容"), source("valid", "https://agri.gov.cn/pest", content="农业资料")],
            )
        ]
    )
    assert [item.id for item in result.sources] == ["source-1"]
    assert result.sources[0].url == "https://agri.gov.cn/pest"


def test_qwen_context_excludes_grounding_model_excerpt():
    evidence = SearchEvidence(class_name="蛴螬", status="available", sources=[source("source-1", "https://agri.gov.cn/pest", content="网页原文")])
    evidence.sources[0].snippet = "Gemini 的引用文本"
    context = build_qwen_context(evidence)
    assert context["sources"][0]["content"] == "网页原文"
    assert "snippet" not in context["sources"][0]


def test_qwen_context_selects_bounded_subset_without_changing_snapshots():
    evidence = SearchEvidence(
        class_name="蛴螬",
        status="available",
        sources=[
            source(f"source-{index}", f"https://agri-{index}.gov.cn/pest", content="完整正文。" * 1200)
            for index in range(1, 6)
        ],
    )
    original_lengths = [len(item.content or "") for item in evidence.sources]
    context = build_qwen_context(evidence)

    assert len(evidence.sources) == 5
    assert [len(item.content or "") for item in evidence.sources] == original_lengths
    assert 1 <= len(context["sources"]) <= 2
    assert context["selection"]["evidence_sources_total"] == 5
    assert context["selection"]["selected_source_ids"] == [
        item["id"] for item in context["sources"]
    ]
    assert context["selection"]["estimated_tokens"] <= context["selection"]["evidence_budget_tokens"]


def test_qwen_context_uses_normalizer_priority_before_budget(monkeypatch):
    monkeypatch.setattr(
        config,
        "settings",
        replace(
            config.settings,
            vlm_evidence_token_budget=1500,
            vlm_max_evidence_sources=2,
            vlm_evidence_excerpt_max_chars=500,
        ),
    )
    normalized = normalize_search_results(
        [
            SearchEvidence(
                class_name="蛴螬",
                status="available",
                sources=[
                    source("government", "https://nynct.example.gov.cn/pest", content="政府正文。" * 200),
                    source("ordinary", "https://example.com/pest", content="普通正文。" * 200),
                    source("research", "https://www.caas.cn/pest", content="科研正文。" * 200),
                ],
            )
        ]
    )
    context = build_qwen_context(normalized)

    assert [item["id"] for item in context["sources"]] == ["source-1", "source-2"]
    assert normalized.sources[0].reliability_level == "政府农业部门"
    assert normalized.sources[1].reliability_level == "农业科研院所"


def test_qwen_context_preserves_nonconsecutive_source_ids():
    evidence = SearchEvidence(
        class_name="蛴螬",
        status="available",
        sources=[
            source("source-2", "https://a.gov.cn/pest", content="来源二正文"),
            source("source-5", "https://b.gov.cn/pest", content="来源五正文"),
        ],
    )
    context = build_qwen_context(evidence)

    assert context["selection"]["selected_source_ids"] == ["source-2", "source-5"]
    assert [item["id"] for item in context["sources"]] == ["source-2", "source-5"]


def test_qwen_context_truncates_excerpt_but_not_original_content(monkeypatch):
    monkeypatch.setattr(
        config,
        "settings",
        replace(config.settings, vlm_evidence_token_budget=900, vlm_evidence_excerpt_max_chars=900),
    )
    content = "原始网页正文。" * 1500
    evidence = SearchEvidence(
        class_name="蛴螬",
        status="available",
        sources=[source("source-1", "https://a.gov.cn/pest", content=content)],
    )
    context = build_qwen_context(evidence)

    assert len(evidence.sources[0].content or "") == len(content)
    assert len(context["sources"][0]["content"]) < len(content)
    assert context["selection"]["estimated_tokens"] <= 900


def test_qwen_context_returns_unavailable_for_empty_evidence():
    context = build_qwen_context(
        SearchEvidence(class_name="蛴螬", status="unavailable", sources=[])
    )

    assert context["status"] == "unavailable"
    assert context["sources"] == []
    assert context["selection"]["selected_source_ids"] == []


def test_qwen_context_never_exceeds_configured_budget(monkeypatch):
    monkeypatch.setattr(
        config,
        "settings",
        replace(
            config.settings,
            vlm_context_window=8192,
            vlm_output_tokens=700,
            vlm_reserved_input_tokens=5892,
            vlm_evidence_token_budget=1000,
            vlm_max_evidence_sources=5,
        ),
    )
    evidence = SearchEvidence(
        class_name="蛴螬",
        status="available",
        sources=[
            source(f"source-{index}", f"https://{index}.gov.cn/pest", content="长正文" * 2000)
            for index in range(1, 6)
        ],
    )
    context = build_qwen_context(evidence)

    assert context["selection"]["evidence_budget_tokens"] == 1000
    assert context["selection"]["estimated_tokens"] <= 1000


def test_qwen_context_marks_budget_exhaustion_unavailable(monkeypatch):
    monkeypatch.setattr(
        config,
        "settings",
        replace(config.settings, vlm_evidence_token_budget=0),
    )
    evidence = SearchEvidence(
        class_name="蛴螬",
        status="available",
        sources=[source("source-1", "https://a.gov.cn/pest", content="正文")],
    )

    context = build_qwen_context(evidence)

    assert context["status"] == "unavailable"
    assert context["sources"] == []
    assert context["selection"]["selected_source_ids"] == []


def test_collection_with_disabled_settings_returns_unavailable(monkeypatch):
    monkeypatch.setattr(config, "settings", replace(config.settings, search_provider="disabled"))
    result = asyncio.run(collect_external_evidence("蛴螬"))
    assert result.status == "unavailable"
    assert result.sources == []


def interaction_payload() -> dict:
    return {
        "steps": [
            {"type": "google_search_call", "arguments": {"queries": ["蛴螬 危害"]}},
            {
                "type": "model_output",
                "content": [
                    {
                        "type": "text",
                        "text": "模型整合答案：幼虫危害作物根系。",
                        "annotations": [
                            {"type": "url_citation", "url": "https://agri.gov.cn/grub", "title": "农业植保资料", "start_index": 7, "end_index": 15},
                            {"type": "url_citation", "url": "not-a-url", "title": "非法来源"},
                        ],
                    }
                ],
            },
        ]
    }


def test_grounding_citation_is_converted_to_source_without_using_gemini_answer():
    result = parse_grounding_response(interaction_payload(), "蛴螬", "harms")
    assert result.status == "available"
    assert result.queries == ["蛴螬 危害"]
    assert len(result.sources) == 1
    assert result.sources[0].url == "https://agri.gov.cn/grub"
    assert result.sources[0].title == "农业植保资料"
    assert result.sources[0].site_name == "agri.gov.cn"
    assert result.sources[0].snippet == "幼虫危害作物根系"
    assert result.sources[0].content is None


def test_legacy_grounding_metadata_is_supported():
    result = parse_grounding_response(
        {"candidates": [{"groundingMetadata": {"webSearchQueries": ["蛴螬 发生条件"], "groundingChunks": [{"web": {"uri": "https://cau.edu.cn/grub", "title": "高校资料"}}], "groundingSupports": [{"segment": {"text": "高湿条件"}, "groundingChunkIndices": [0]}]}}]},
        "蛴螬",
        "possible_causes",
    )
    assert result.status == "available"
    assert result.sources[0].url == "https://cau.edu.cn/grub"
    assert result.sources[0].snippet == "高湿条件"


def test_grounding_without_citations_is_unavailable():
    result = parse_grounding_response({"steps": [{"type": "model_output", "content": [{"type": "text", "text": "没有引用"}]}]}, "蛴螬", "harms")
    assert result.status == "unavailable"
    assert result.sources == []


class _Response:
    def __init__(self, payload: dict, content: bytes | None = None):
        self.payload = payload
        self.content = content or "<html><body>原始页面正文</body></html>".encode()
        self.headers = {"content-type": "text/html"}

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _GroundingClient:
    payload: dict = {}
    requests: list[dict] = []

    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, **kwargs):
        type(self).requests.append({"url": url, **kwargs})
        return _Response(type(self).payload)

    async def get(self, _url, **_kwargs):
        return _Response({})


def grounding_settings():
    return replace(config.settings, gemini_api_key="test-gemini-key", gemini_model="gemini-3.7-flash", gemini_endpoint="https://generativelanguage.googleapis.com/v1beta/interactions", search_max_sources=3)


def test_grounding_provider_posts_official_request_and_fetches_original_source(monkeypatch):
    monkeypatch.setattr(config, "settings", grounding_settings())
    _GroundingClient.payload = interaction_payload()
    _GroundingClient.requests = []
    monkeypatch.setattr("app.search.google_grounding.httpx.AsyncClient", _GroundingClient)
    result = asyncio.run(GeminiGoogleGroundingProvider().search_evidence("蛴螬", "harms"))
    assert result.status == "available"
    assert result.sources[0].content == "原始页面正文"
    assert _GroundingClient.requests[0]["headers"]["x-goog-api-key"] == "test-gemini-key"
    assert _GroundingClient.requests[0]["json"]["tools"] == [{"type": "google_search"}]


def test_grounding_citation_without_retrievable_page_is_unavailable(monkeypatch):
    monkeypatch.setattr(config, "settings", grounding_settings())
    _GroundingClient.payload = interaction_payload()
    monkeypatch.setattr("app.search.google_grounding.httpx.AsyncClient", _GroundingClient)
    provider = GeminiGoogleGroundingProvider()

    async def no_content(_client, _url):
        return None

    monkeypatch.setattr(provider, "_fetch_content", no_content)
    result = asyncio.run(provider.search_evidence("蛴螬", "possible_causes"))
    assert result.status == "unavailable"
    assert result.sources[0].content is None


def test_grounding_timeout_and_api_failure_degrade(monkeypatch):
    monkeypatch.setattr(config, "settings", grounding_settings())

    class FailingClient(_GroundingClient):
        async def post(self, _url, **_kwargs):
            raise httpx.ReadTimeout("search timeout")

    monkeypatch.setattr("app.search.google_grounding.httpx.AsyncClient", FailingClient)
    timeout = asyncio.run(GeminiGoogleGroundingProvider().search_evidence("蛴螬", "harms"))
    assert timeout.status == "error"
    assert "ReadTimeout" in (timeout.message or "")


def test_legacy_custom_search_provider_still_works_when_explicitly_selected(monkeypatch):
    monkeypatch.setattr(config, "settings", replace(config.settings, google_api_key="test-key", google_search_engine_id="test-cx", search_max_sources=3))

    class LegacyClient(_GroundingClient):
        async def get(self, url, **_kwargs):
            if "googleapis" in url:
                return _Response({"items": [{"title": "农业科研资料", "link": "https://agri.gov.cn/pest", "displayLink": "agri.gov.cn"}]})
            return _Response({})

    monkeypatch.setattr("app.search.google_custom_search_legacy.httpx.AsyncClient", LegacyClient)
    result = asyncio.run(LegacyGoogleCustomSearchProvider().search_evidence("蛴螬", "harms"))
    assert result.status == "available"
    assert result.sources[0].content == "原始页面正文"


def test_tavily_provider_uses_bearer_search_and_raw_content(monkeypatch):
    monkeypatch.setattr(
        config,
        "settings",
        replace(
            config.settings,
            search_provider="tavily",
            tavily_api_key="test-tavily-key",
            tavily_endpoint="https://api.tavily.com/search",
            search_max_sources=3,
        ),
    )
    _GroundingClient.payload = {
        "query": "蛴螬 危害 危害症状 农业",
        "results": [
            {
                "title": "农业植保资料",
                "url": "https://agri.gov.cn/grub",
                "content": "摘要内容",
                "raw_content": "网页原始正文",
            },
            {"title": "非法来源", "url": "not-a-url", "content": "不应保留"},
        ],
        "answer": "不应使用的 Tavily 总结",
    }
    _GroundingClient.requests = []
    monkeypatch.setattr("app.search.tavily.httpx.AsyncClient", _GroundingClient)
    result = asyncio.run(TavilySearchProvider().search_evidence("蛴螬", "harms"))
    assert result.status == "available"
    assert len(result.sources) == 1
    assert result.sources[0].content == "网页原始正文"
    request = _GroundingClient.requests[0]
    assert request["headers"]["Authorization"] == "Bearer test-tavily-key"
    assert request["json"]["include_answer"] is False
    assert request["json"]["include_raw_content"] == "text"


def test_tavily_provider_empty_and_timeout_degrade(monkeypatch):
    test_settings = replace(
        config.settings,
        search_provider="tavily",
        tavily_api_key="test-tavily-key",
        tavily_endpoint="https://api.tavily.com/search",
    )
    monkeypatch.setattr(config, "settings", test_settings)
    _GroundingClient.payload = {"results": []}
    monkeypatch.setattr("app.search.tavily.httpx.AsyncClient", _GroundingClient)
    empty = asyncio.run(TavilySearchProvider().search_evidence("蛴螬", "possible_causes"))
    assert empty.status == "unavailable"

    class FailingClient(_GroundingClient):
        async def post(self, _url, **_kwargs):
            raise httpx.ReadTimeout("tavily timeout")

    monkeypatch.setattr("app.search.tavily.httpx.AsyncClient", FailingClient)
    timeout = asyncio.run(TavilySearchProvider().search_evidence("蛴螬", "harms"))
    assert timeout.status == "error"
    assert "ReadTimeout" in (timeout.message or "")


def test_low_quality_domain_blacklist_matches_subdomains_and_known_commercial_sites():
    urls = [
        "https://zhuanlan.zhihu.com/p/1",
        "https://tieba.baidu.com/p/1",
        "https://zhidao.baidu.com/question/1",
        "https://m.3456.tv/huati/1",
        "https://jin-cang.com/news/1",
    ]
    for url in urls:
        item = source("low", url)
        assert is_obviously_low_quality(item)
        assert low_quality_reason(item)


def test_reliable_sources_are_ranked_before_ordinary_webpages():
    result = normalize_search_results(
        [
            SearchEvidence(
                class_name="蛴螬",
                status="available",
                sources=[
                    source("ordinary", "https://example.com/pest"),
                    source("gov", "https://nynct.shaanxi.gov.cn/pest"),
                    source("research", "https://www.caas.cn/pest"),
                    source("university", "https://plant.cau.edu.cn/pest"),
                ],
            )
        ]
    )
    assert [item.id for item in result.sources] == ["source-1", "source-2", "source-3", "source-4"]
    assert result.sources[0].reliability_level == "政府农业部门"
    assert result.sources[-1].reliability_level == "普通网页"


def test_mixed_results_keep_only_high_quality_sources():
    result = normalize_search_results(
        [
            SearchEvidence(
                class_name="蛴螬",
                status="available",
                sources=[
                    source("gov-1", "https://a.gov.cn/pest"),
                    source("gov-2", "https://b.gov.cn/pest"),
                    source("research", "https://www.caas.cn/pest"),
                    source("zhihu", "https://zhuanlan.zhihu.com/p/1"),
                    source("commercial", "https://m.3456.tv/huati/1"),
                ],
            )
        ]
    )
    assert len(result.sources) == 3
    assert all(not is_obviously_low_quality(item) for item in result.sources)


def test_all_low_quality_results_return_unavailable_without_filling_max_sources():
    result = normalize_search_results(
        [
            SearchEvidence(
                class_name="蛴螬",
                status="available",
                sources=[
                    source("zhihu", "https://zhuanlan.zhihu.com/p/1"),
                    source("commercial", "https://m.3456.tv/huati/1"),
                    source("marketing", "https://jin-cang.com/news/1"),
                ],
            )
        ]
    )
    assert result.status == "unavailable"
    assert result.sources == []


def test_normalizer_caps_sources_and_limits_one_main_domain_to_two():
    sources = [
        source(f"{domain}-{index}", f"https://{domain}.gov.cn/pest-{index}")
        for domain in ("a", "b", "c")
        for index in range(1, 3)
    ]
    result = normalize_search_results(
        [
            SearchEvidence(class_name="蛴螬", status="available", sources=sources[:3]),
            SearchEvidence(class_name="蛴螬", status="available", sources=sources[3:]),
        ]
    )
    assert len(result.sources) == 5
    assert [item.id for item in result.sources] == [f"source-{index}" for index in range(1, 6)]
    counts = {}
    for item in result.sources:
        host = item.url.split("/", 3)[2]
        counts[host] = counts.get(host, 0) + 1
    assert max(counts.values()) <= 2
