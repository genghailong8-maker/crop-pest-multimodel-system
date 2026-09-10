from __future__ import annotations

import asyncio
from dataclasses import replace

import httpx

from app import config
from app.catalog import CLASS_CATALOG
from app.search import collect_external_evidence
from app.search.google_custom_search_legacy import LegacyGoogleCustomSearchProvider
from app.search.google_grounding import GeminiGoogleGroundingProvider, parse_grounding_response
from app.search.models import SearchEvidence, SearchSource
from app.search.normalizer import is_obviously_low_quality, low_quality_reason, normalize_search_results, reliability_score
from app.search.provider import DisabledSearchProvider, MockSearchProvider, provider_from_settings
from app.search.tavily import TavilySearchProvider, _query


def source(source_id: str, url: str, *, content: str | None = "原始页面正文") -> SearchSource:
    return SearchSource(id=source_id, title=f"资料 {source_id}", site_name="测试来源", url=url, content=content)


EXPECTED_TAVILY_QUERIES = {
    "玉米叶枯病": {
        "harms": "玉米链格孢菌叶枯病 细交链孢菌 症状 危害 叶片 叶鞘 苞叶 病斑 枯死 农业",
        "possible_causes": "玉米链格孢菌叶枯病 细交链孢菌 发病条件 流行规律 温度 湿度 菌源 病残体 传播 农业",
    },
    "番茄斑枯病": {
        "harms": "番茄斑枯病 番茄壳针孢菌 Septoria lycopersici Tomato Septoria leaf spot 症状 危害 叶片 茎 花萼 斑点 黄化 早期落叶 农业",
        "possible_causes": "番茄斑枯病 发病条件 流行规律 温度 湿度 降雨 菌源 病残体 农业",
    },
    "南瓜白粉病": {
        "harms": "南瓜白粉病 症状 危害 叶片 白粉 黄化 早衰 产量 农技",
        "possible_causes": "南瓜白粉病 发病条件 流行规律 温度 湿度 菌源 孢子 农业",
    },
    "马铃薯早疫病": {
        "harms": "马铃薯早疫病 Potato early blight 症状 危害 叶片 块茎 农技",
        "possible_causes": "马铃薯早疫病 Alternaria solani 发生条件 流行规律 农业",
    },
    "玉米锈病": {
        "harms": "玉米锈病 症状 危害 叶片 锈色 孢子堆 早衰 减产 农技",
        "possible_causes": "玉米锈病 发病条件 流行规律 温度 湿度 降雨 菌源 孢子 农业",
    },
    "番茄细菌性斑点病": {
        "harms": "番茄细菌性斑点病 症状 危害 叶片 果实 斑点 落叶 商品性 农技",
        "possible_causes": "番茄细菌性斑点病 Xanthomonas 发病条件 流行规律 温度 湿度 降雨 传播 农业",
    },
    "番茄晚疫病": {
        "harms": "番茄晚疫病 Phytophthora infestans 症状 危害 叶片 茎 果实 水渍状 白霉 腐烂 农技",
        "possible_causes": "番茄晚疫病 Phytophthora infestans 发病条件 流行规律 低温 高湿 降雨 菌源 农业",
    },
    "马铃薯晚疫病": {
        "harms": "马铃薯晚疫病 Phytophthora infestans 症状 危害 叶片 茎 块茎 水渍状 白霉 腐烂 农技",
        "possible_causes": "马铃薯晚疫病 Phytophthora infestans 发病条件 流行规律 低温 高湿 降雨 菌源 农业",
    },
    "芫菁": {
        "harms": "芫菁 芫菁科 危害 成虫 取食 叶片 花器 嫩梢 受害 农业",
        "possible_causes": "芫菁 芫菁科 发生规律 温度 湿度 寄主 越冬 虫源 农业",
    },
    "蚜虫": {
        "harms": "蚜虫 危害 刺吸 汁液 叶片 卷叶 黄化 生长受阻 传播 农业",
        "possible_causes": "蚜虫 发生规律 温度 湿度 寄主 繁殖 迁飞 越冬 农业",
    },
    "盲蝽科": {
        "harms": "盲蝽 盲蝽科 危害 刺吸 嫩芽 嫩叶 花蕾 果实 畸形 农业",
        "possible_causes": "盲蝽 盲蝽科 发生规律 温度 湿度 寄主 越冬 迁移 虫源 农业",
    },
    "蝼蛄": {
        "harms": "蝼蛄 危害 咬食 根系 幼苗 种子 缺苗 断苗 农业",
        "possible_causes": "蝼蛄 发生规律 土壤 温度 湿度 越冬 虫源 农业",
    },
    "叶蝉科": {
        "harms": "叶蝉 叶蝉科 危害 刺吸 汁液 叶片 黄化 生长受阻 传播 农业",
        "possible_causes": "叶蝉 叶蝉科 发生规律 温度 湿度 寄主 迁飞 越冬 虫源 农业",
    },
    "蝗总科": {
        "harms": "蝗虫 蝗总科 危害 咀嚼 取食 叶片 幼苗 缺刻 减产 农业",
        "possible_causes": "蝗虫 蝗总科 发生规律 温度 降雨 虫卵 孵化 越冬 虫源 农业",
    },
    "蛴螬": {
        "harms": "蛴螬 危害 咬食 取食 根系 叶片 受害 缺苗 减产 农业",
        "possible_causes": "蛴螬 发生条件 发生规律 土壤 温度 湿度 虫源 农业",
    },
    "豆芫菁": {
        "harms": "豆芫菁 Epicauta gorhami 危害 成虫 取食 豆科 叶片 花 嫩荚 农业",
        "possible_causes": "豆芫菁 Epicauta gorhami 发生规律 温度 湿度 寄主 越冬 虫源 农业",
    },
}


def test_disabled_provider_is_explicit_and_does_not_fake_sources():
    result = asyncio.run(DisabledSearchProvider().search_evidence("蛴螬", "harms"))
    assert result.status == "unavailable"
    assert result.sources == []
    assert "未配置" in (result.message or "")


def test_mock_provider_is_only_for_tests():
    result = asyncio.run(MockSearchProvider().search_evidence("蛴螬", "possible_causes"))
    assert result.status == "mock"
    assert "不代表真实" in (result.message or "")


def test_tavily_query_matrix_covers_all_catalog_classes_and_both_query_types():
    catalog_names = {item["name_zh"] for item in CLASS_CATALOG}
    assert len(catalog_names) == 16
    assert set(EXPECTED_TAVILY_QUERIES) == catalog_names
    assert sum(len(queries) for queries in EXPECTED_TAVILY_QUERIES.values()) == 32
    for class_name, queries in EXPECTED_TAVILY_QUERIES.items():
        assert set(queries) == {"harms", "possible_causes"}
        assert _query(class_name, "harms") == queries["harms"]
        assert _query(class_name, "possible_causes") == queries["possible_causes"]
        assert not any(token in queries["possible_causes"] for token in ("防治", "农药", "施肥", "管理措施"))


def test_early_blight_harms_override_is_retrieval_only():
    assert _query("马铃薯早疫病", "harms") == EXPECTED_TAVILY_QUERIES["马铃薯早疫病"]["harms"]
    assert _query("马铃薯早疫病", "possible_causes") == EXPECTED_TAVILY_QUERIES["马铃薯早疫病"]["possible_causes"]
    assert _query("蛴螬", "harms") == EXPECTED_TAVILY_QUERIES["蛴螬"]["harms"]
    assert _query("蛴螬", "possible_causes") == EXPECTED_TAVILY_QUERIES["蛴螬"]["possible_causes"]


def test_tavily_provider_remains_the_selected_external_provider(monkeypatch):
    monkeypatch.setattr(config, "settings", replace(config.settings, search_provider="tavily"))
    assert isinstance(provider_from_settings(), TavilySearchProvider)


def test_tavily_query_keeps_generic_fallback_for_unknown_classes():
    assert _query("未登记病害", "harms") == "未登记病害 危害 为害症状 病斑 叶片 枯死 减产 农业"
    assert _query("未登记病害", "possible_causes") == "未登记病害 发生条件 发病条件 流行规律 温度 湿度 降雨 病原 农业"


def test_provider_settings_recommend_grounding_and_keep_legacy_separate(monkeypatch):
    monkeypatch.setattr(config, "settings", replace(config.settings, search_provider="google_grounding"))
    assert isinstance(provider_from_settings(), GeminiGoogleGroundingProvider)
    monkeypatch.setattr(config, "settings", replace(config.settings, search_provider="google_legacy"))
    assert isinstance(provider_from_settings(), LegacyGoogleCustomSearchProvider)


def test_normalizer_deduplicates_and_preserves_provider_order():
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
    assert [item.url for item in result.sources] == [
        "https://example.com/article",
        "https://agri.gov.cn/article",
    ]
    assert result.sources[0].reliability_level == "普通网页"
    assert result.sources[1].reliability_level == "政府农业部门"


def test_normalizer_reserves_a_source_for_each_query_before_filling_the_cap():
    result = normalize_search_results(
        [
            SearchEvidence(
                class_name="马铃薯早疫病",
                query_type="harms",
                status="available",
                sources=[source(f"harm-{index}", f"https://harm-{index}.gov.cn/article", content="危害资料") for index in range(1, 6)],
            ),
            SearchEvidence(
                class_name="马铃薯早疫病",
                query_type="possible_causes",
                status="available",
                sources=[
                    source("cause", "https://plant.cau.edu.cn/early-blight", content="发生条件资料"),
                    source("cause-duplicate", "https://plant.cau.edu.cn/early-blight?utm_source=test", content="重复资料"),
                    source("low", "https://zhuanlan.zhihu.com/p/early-blight", content="低质量资料"),
                ],
            ),
        ]
    )
    assert len(result.sources) == 5
    assert "https://plant.cau.edu.cn/early-blight" in [item.url for item in result.sources]
    assert len({item.url for item in result.sources}) == len(result.sources)
    assert all(not is_obviously_low_quality(item) for item in result.sources)
    assert [item.id for item in result.sources] == [f"source-{index}" for index in range(1, 6)]


def test_normalizer_rejects_a_title_for_a_competing_catalog_class():
    result = normalize_search_results([
        SearchEvidence(class_name="马铃薯早疫病", query_type="harms", status="available", sources=[
            SearchSource(id="early", title="Potato early blight symptoms", site_name="农业资料", url="https://example.gov/early", content="早疫病资料"),
            SearchSource(id="late", title="Potato late blight symptoms", site_name="农业资料", url="https://example.gov/late", content="晚疫病资料"),
        ])
    ])
    assert [item.url for item in result.sources] == ["https://example.gov/early"]


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


def test_source_selection_preserves_provider_order_across_authority_levels():
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
    assert [item.reliability_level for item in result.sources] == [
        "普通网页",
        "政府农业部门",
        "农业科研院所",
        "农业科研院所",
    ]


def test_authority_score_does_not_crowd_ordinary_sources_out_of_five_slots():
    ordinary = [
        source(f"ordinary-{index}", f"https://ordinary-{index}.example/article")
        for index in range(1, 6)
    ]
    government = source("government", "https://agri.gov.cn/article")

    result = normalize_search_results([
        SearchEvidence(
            class_name="蛴螬",
            query_type="harms",
            status="available",
            sources=ordinary,
        ),
        SearchEvidence(
            class_name="蛴螬",
            query_type="harms",
            status="available",
            sources=[government],
        ),
    ])

    assert [item.url for item in result.sources] == [item.url for item in ordinary]
    assert all(item.reliability_level == "普通网页" for item in result.sources)
    assert len(result.sources) == 5


def test_source_selection_prefers_content_then_keeps_provider_order_deterministic():
    inputs = [
        source("empty", "https://empty.example/article", content=None),
        source("ordinary", "https://ordinary.example/article"),
        source("government", "https://agri.gov.cn/article"),
    ]

    first = normalize_search_results([
        SearchEvidence(class_name="蛴螬", query_type="harms", status="available", sources=inputs)
    ])
    second = normalize_search_results([
        SearchEvidence(class_name="蛴螬", query_type="harms", status="available", sources=inputs)
    ])

    expected = [
        "https://ordinary.example/article",
        "https://agri.gov.cn/article",
        "https://empty.example/article",
    ]
    assert [item.url for item in first.sources] == expected
    assert [item.url for item in second.sources] == expected


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
