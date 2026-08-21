from __future__ import annotations

import json
import logging
import re
from math import ceil
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .. import config
from .models import SearchEvidence, SearchSource


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
_EVIDENCE_EXCERPT_TOKENS = (
    "危害",
    "为害",
    "症状",
    "发生",
    "原因",
    "条件",
    "幼虫",
    "根部",
    "传播",
    "防治",
)


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


def _reliability_key(source: SearchSource) -> tuple[int, str]:
    score, level = reliability_score(source)
    return (-score, 0 if source.content else 1, level, source.site_name, source.url)


def _is_low_quality(source: SearchSource) -> bool:
    return low_quality_reason(source) is not None


def is_obviously_low_quality(source: SearchSource) -> bool:
    return _is_low_quality(source)


def normalize_search_results(results: list[SearchEvidence]) -> SearchEvidence:
    if not results:
        return SearchEvidence(class_name="未知", status="unavailable", message="没有外部检索结果")
    class_name = results[0].class_name
    all_sources: list[SearchSource] = []
    queries: list[str] = []
    messages: list[str] = []
    for result in results:
        queries.extend(result.queries)
        if result.message:
            messages.append(result.message)
        all_sources.extend(result.sources)

    deduped: dict[str, SearchSource] = {}
    for source in all_sources:
        if is_obviously_low_quality(source):
            continue
        canonical = _canonical_url(source.url)
        if canonical is None:
            continue
        priority, level = reliability_score(source.model_copy(update={"url": canonical}))
        normalized = source.model_copy(
            update={"url": canonical, "reliability_level": source.reliability_level or level}
        )
        previous = deduped.get(canonical)
        if previous is None or (normalized.content and not previous.content):
            deduped[canonical] = normalized

    selected_candidates: list[SearchSource] = []
    domain_counts: dict[str, int] = {}
    for candidate in sorted(deduped.values(), key=_reliability_key):
        domain = _main_domain(urlsplit(candidate.url).hostname or "")
        if domain_counts.get(domain, 0) >= 2:
            continue
        selected_candidates.append(candidate)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        if len(selected_candidates) >= 5:
            break
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


def _conservative_token_estimate(value: str) -> int:
    """Upper-bound estimate for evidence JSON when the Qwen tokenizer is unavailable."""
    return max(1, ceil(len(value)))


def _qwen_evidence_budget() -> int:
    configured_budget = config.settings.vlm_evidence_token_budget
    residual_budget = (
        config.settings.vlm_context_window
        - config.settings.vlm_output_tokens
        - config.settings.vlm_reserved_input_tokens
    )
    return max(0, min(configured_budget, residual_budget))


def _source_excerpt(source: SearchSource, content: str) -> dict:
    return {
        **{
            key: value
            for key, value in source.public_metadata().items()
            if key != "snippet"
        },
        "content": content,
    }


def _bounded_excerpt(content: str, limit: int) -> str:
    """Keep a prefix plus short evidence windows without altering stored content."""
    if len(content) <= limit:
        return content
    prefix_length = max(80, min(limit // 3, 240))
    pieces = [content[:prefix_length]]
    used = prefix_length
    windows: list[str] = []
    for token in _EVIDENCE_EXCERPT_TOKENS:
        start = 0
        while used < limit and (position := content.find(token, start)) >= 0:
            window_start = max(prefix_length, position - 80)
            window_end = min(len(content), position + len(token) + 120)
            window = content[window_start:window_end]
            if window and window not in windows:
                windows.append(window)
            start = position + len(token)
    for window in windows:
        remaining = limit - used
        if remaining <= 0:
            break
        pieces.append(window[:remaining])
        used += min(len(window), remaining)
    return "".join(pieces)[:limit]


def _evidence_payload(
    evidence: SearchEvidence,
    sources: list[dict],
) -> dict:
    return {
        "status": evidence.status,
        "class_name": evidence.class_name,
        "queries": evidence.queries,
        "sources": sources,
        "message": evidence.message,
    }


def build_qwen_context(evidence: SearchEvidence) -> dict:
    """Select bounded excerpts without changing the persisted SearchEvidence."""
    total_sources = len(evidence.sources)
    budget_tokens = _qwen_evidence_budget()
    max_sources = min(config.settings.vlm_max_evidence_sources, total_sources)
    max_chars = config.settings.vlm_evidence_excerpt_max_chars
    selected: list[dict] = []
    selected_ids: list[str] = []

    candidate_sources = [source for source in evidence.sources if source.content][:max_sources]
    minimum_chars = max(120, min(320, max_chars // 4))
    for candidate_count in range(len(candidate_sources), 0, -1):
        candidates = candidate_sources[:candidate_count]
        low, high = minimum_chars, max_chars
        best_sources: list[dict] | None = None
        while low <= high:
            middle = (low + high) // 2
            excerpts = [
                _source_excerpt(source, _bounded_excerpt(source.content or "", middle))
                for source in candidates
            ]
            estimated = _conservative_token_estimate(
                json.dumps(_evidence_payload(evidence, excerpts), ensure_ascii=False)
            )
            if estimated <= budget_tokens:
                best_sources = excerpts
                low = middle + 1
            else:
                high = middle - 1
        if best_sources is not None:
            selected = best_sources
            selected_ids = [source.id for source in candidates]
            break

    context = _evidence_payload(evidence, selected)
    if evidence.status == "available" and not selected:
        context["status"] = "unavailable"
        context["message"] = "证据预算不足，未向 Qwen 发送可安全容纳的来源正文"
    estimated_tokens = _conservative_token_estimate(
        json.dumps(context, ensure_ascii=False)
    )
    selection = {
        "evidence_sources_total": total_sources,
        "evidence_sources_selected": len(selected),
        "evidence_budget_tokens": budget_tokens,
        "estimated_tokens": estimated_tokens,
        "selected_source_ids": selected_ids,
        "max_evidence_sources": max_sources,
        "excerpt_max_chars": max_chars,
        "token_estimator": "conservative_character_upper_bound",
    }
    logger.info(
        "evidence_sources_total=%s evidence_sources_selected=%s evidence_budget_tokens=%s "
        "estimated_tokens=%s selected_source_ids=%s",
        total_sources,
        len(selected),
        budget_tokens,
        estimated_tokens,
        selected_ids,
    )
    return {
        **context,
        "selection": selection,
    }
