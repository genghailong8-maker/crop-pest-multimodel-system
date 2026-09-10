"""Tavily Search provider for external source retrieval only."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

import httpx

from .. import config
from ..catalog import CLASS_CATALOG
from .base import QueryType
from .models import SearchEvidence, SearchSource, now_iso


QUERY_VOCABULARY = {
    "病害": {
        "harms": "危害 为害症状 病斑 叶片 枯死 减产",
        "possible_causes": "发生条件 发病条件 流行规律 温度 湿度 降雨 病原",
    },
    "害虫": {
        "harms": "危害 咬食 取食 根系 叶片 受害 缺苗 减产",
        "possible_causes": "发生条件 发生规律 土壤 温度 湿度 虫源",
    },
}

# Retrieval-only disambiguation for this closely named disease. The diagnosed
# label, knowledge lookup, and evidence attribution remain unchanged.
SEARCH_QUERY_OVERRIDES = {
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


def _query(class_name: str, query_type: QueryType) -> str:
    override = SEARCH_QUERY_OVERRIDES.get(class_name, {}).get(query_type)
    if override:
        return override
    class_type = next((str(item["type"]) for item in CLASS_CATALOG if item["name_zh"] == class_name), "病害")
    return f"{class_name} {QUERY_VOCABULARY[class_type][query_type]} 农业"


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
        query = _query(class_name, query_type)
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
