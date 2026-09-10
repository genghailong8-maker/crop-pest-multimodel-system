from __future__ import annotations

import logging
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ..catalog import CLASS_CATALOG
from .models import QueryType, SearchEvidence, SearchSource


logger = logging.getLogger(__name__)


_LOW_QUALITY_DOMAINS = {
    "zhihu.com": "community_content",
    "tieba.baidu.com": "community_content",
    "zhidao.baidu.com": "community_content",
    "3456.tv": "commercial_agriculture",
    "jin-cang.com": "low_quality_or_marketing",
}
_LOW_QUALITY_TOKENS = {
    "forum": "forum_content",
    "bbs": "forum_content",
    "tieba": "community_content",
    "zhidao": "community_content",
    "问答": "community_content",
    "问答社区": "community_content",
    "自媒体": "self_media",
    "内容农场": "content_farm",
    "聚合转载": "aggregator_repost",
    "营销软文": "marketing_content",
    "软文": "marketing_content",
    "seo": "seo_content",
    "shop": "commercial_page",
    "mall": "commercial_page",
    "taobao": "ecommerce_page",
    "1688": "ecommerce_page",
    "商城": "commercial_page",
    "农资招商": "commercial_agriculture",
    "农资销售": "commercial_agriculture",
    "农药销售": "commercial_agriculture",
    "农药厂家": "commercial_agriculture",
    "农药价格": "commercial_agriculture",
    "农药购买": "commercial_agriculture",
    "种子销售": "commercial_agriculture",
    "种子价格": "commercial_agriculture",
    "招商网": "commercial_agriculture",
    "批发": "commercial_agriculture",
    "零售": "commercial_agriculture",
    "price": "commercial_agriculture",
}
_RESEARCH_DOMAIN_TOKENS = ("cas.cn", "caas.cn", "agri.cn", "cau.edu.cn")
_AGRICULTURE_DATABASE_DOMAINS = ("chinapesticide.org", "baike.baidu.com", "cabidigitallibrary.org")
_AGRICULTURE_TITLE_TOKENS = (
    "农业农村",
    "农业科学",
    "农业科学院",
    "农业大学",
    "农学院",
    "植物保护",
    "植保",
    "农技推广",
    "推广中心",
    "植保站",
    "农业技术",
)
_AGRICULTURE_SITE_TOKENS = ("agri", "agriculture", "nongye", "nongji", "nync", "plant", "crop", "pest")


def _canonical_url(url: str) -> str | None:
    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    query = urlencode([
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(("utm_", "gclid", "fbclid"))
    ])
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", query, ""))


def _domain_matches(hostname: str, domain: str) -> bool:
    return hostname == domain or hostname.endswith(f".{domain}")


def _main_domain(hostname: str) -> str:
    labels = [label for label in hostname.lower().rstrip(".").split(".") if label]
    if len(labels) <= 2:
        return ".".join(labels)
    if labels[-2:] == ["gov", "cn"]:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def low_quality_reason(source: SearchSource) -> str | None:
    parsed = urlsplit(source.url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    for domain, reason in _LOW_QUALITY_DOMAINS.items():
        if _domain_matches(hostname, domain):
            return reason
    haystack = " ".join((hostname, parsed.path, source.title, source.site_name)).lower()
    for token, reason in _LOW_QUALITY_TOKENS.items():
        if token in haystack:
            return reason
    return None


def _source_text(source: SearchSource) -> str:
    return " ".join((urlsplit(source.url).hostname or "", source.site_name, source.title)).lower()


def _normalized_class_text(value: str) -> str:
    return re.sub(r"[\W_]+", "", value).lower()


def _title_names_a_competing_class(source: SearchSource, class_name: str) -> bool:
    title = _normalized_class_text(source.title)
    target = next((item for item in CLASS_CATALOG if item["name_zh"] == class_name), None)
    target_aliases = {
        _normalized_class_text(str(value))
        for value in ((target or {}).get("name_zh"), (target or {}).get("name_en"))
        if value
    }
    for item in CLASS_CATALOG:
        aliases = {
            _normalized_class_text(str(value))
            for value in (item.get("name_zh"), item.get("name_en"))
            if value
        }
        if aliases & target_aliases:
            continue
        if any(alias and alias in title for alias in aliases):
            return True
    return False


def _is_narrow_subclass_title_match(source: SearchSource, class_name: str) -> bool:
    """Keep proven bean-blister-beetle child pages despite parent-name overlap."""
    if class_name != "豆芫菁":
        return False
    title = _normalized_class_text(source.title)
    return "豆芫菁" in title or "epicaugorhami" in title


def reliability_score(source: SearchSource) -> tuple[int, str]:
    hostname = (urlsplit(source.url).hostname or "").lower().rstrip(".")
    text = _source_text(source)
    if hostname.endswith(".gov.cn") or hostname.endswith(".gov"):
        return (100, "政府农业部门")
    if any(_domain_matches(hostname, token) for token in _RESEARCH_DOMAIN_TOKENS):
        return (80, "农业科研院所")
    if hostname.endswith(".edu.cn") or hostname.endswith(".edu"):
        return (70, "高校农学院/植保学院")
    if any(token in text for token in _AGRICULTURE_TITLE_TOKENS):
        return (70, "农技推广/植保机构")
    if any(token in text for token in _AGRICULTURE_SITE_TOKENS):
        return (60, "其他可信农业专业站点")
    if any(_domain_matches(hostname, domain) for domain in _AGRICULTURE_DATABASE_DOMAINS):
        return (60, "权威农业数据库")
    return (0, "普通网页")


def reliability_level(url: str) -> tuple[int, str]:
    """Backward-compatible URL-only ranking helper."""
    return reliability_score(
        SearchSource(id="ranking", title="", site_name="", url=url)
    )

def _reliability_key(source: SearchSource) -> tuple[int]:
    """Prefer usable content while stable sorting preserves provider order."""
    return (0 if source.content else 1,)


def _is_low_quality(source: SearchSource) -> bool:
    return low_quality_reason(source) is not None


def is_obviously_low_quality(source: SearchSource) -> bool:
    return _is_low_quality(source)


def normalize_search_results(results: list[SearchEvidence]) -> SearchEvidence:
    if not results:
        return SearchEvidence(class_name="未知", status="unavailable", message="没有外部检索结果")
    class_name = results[0].class_name
    sources_by_query: dict[QueryType, list[SearchSource]] = {
        "harms": [],
        "possible_causes": [],
    }
    queries: list[str] = []
    messages: list[str] = []
    for result in results:
        queries.extend(result.queries)
        if result.message:
            messages.append(result.message)
        sources_by_query[result.query_type].extend(result.sources)

    deduped: dict[str, SearchSource] = {}
    query_urls: dict[QueryType, list[str]] = {"harms": [], "possible_causes": []}
    for query_type, sources in sources_by_query.items():
        for source in sources:
            if is_obviously_low_quality(source) or (
                _title_names_a_competing_class(source, class_name)
                and not _is_narrow_subclass_title_match(source, class_name)
            ):
                continue
            canonical = _canonical_url(source.url)
            if canonical is None:
                continue
            _, level = reliability_score(source.model_copy(update={"url": canonical}))
            normalized = source.model_copy(
                update={"url": canonical, "reliability_level": source.reliability_level or level}
            )
            if canonical not in query_urls[query_type]:
                query_urls[query_type].append(canonical)
            previous = deduped.get(canonical)
            if previous is None or (normalized.content and not previous.content):
                deduped[canonical] = normalized

    selected_candidates: list[SearchSource] = []
    selected_urls: set[str] = set()
    domain_counts: dict[str, int] = {}

    def select(candidate: SearchSource) -> bool:
        if candidate.url in selected_urls:
            return True
        domain = _main_domain(urlsplit(candidate.url).hostname or "")
        if domain_counts.get(domain, 0) >= 2:
            return False
        selected_candidates.append(candidate)
        selected_urls.add(candidate.url)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        return True

    # Reserve one accepted source per query before provider-order selection
    # fills the remaining slots. A URL returned by both queries is still only
    # selected once globally. Stable sorting preserves the provider's order
    # among sources with the same content availability.
    for query_type in ("harms", "possible_causes"):
        for url in sorted(query_urls[query_type], key=lambda item: _reliability_key(deduped[item])):
            if select(deduped[url]):
                break

    for candidate in sorted(deduped.values(), key=_reliability_key):
        if len(selected_candidates) >= 5:
            break
        select(candidate)
    selected = selected_candidates
    selected = [
        source.model_copy(update={"id": f"source-{index}"})
        for index, source in enumerate(selected, start=1)
    ]
    usable = [source for source in selected if source.content]
    return SearchEvidence(
        class_name=class_name,
        status="available" if usable else "unavailable",
        queries=list(dict.fromkeys(queries))[:6],
        sources=selected,
        message=None if usable else (messages[0] if messages else "暂未检索到可核验的原文资料"),
    )
