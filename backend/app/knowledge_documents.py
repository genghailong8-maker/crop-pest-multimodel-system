from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from markdown_it import MarkdownIt

from .catalog import CLASS_BY_ID
from .config import settings


MISSING_SECTION = "知识库暂未收录该项"
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
PESTICIDE_WARNING = "【风险提示】化学防治涉及农药使用。实际使用前请核对产品登记标签及当地最新禁限用规定，严格遵守适用作物、使用剂量、施用次数、安全间隔期、个人防护和环境保护要求。不得依据本系统自行增加剂量、扩大适用范围或进行未经确认的药剂混配。"
HEADING_LINE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CHEMICAL_HEADING = re.compile(r"化学|药剂|药物")
CHEMICAL_KEYWORDS = re.compile(r"农药|杀虫剂|杀菌剂|药剂|可湿性粉剂|乳油|喷雾|施用")


def _manifest() -> dict[str, Any]:
    return json.loads((settings.knowledge_dir / "manifest.json").read_text(encoding="utf-8"))


def _document_entry(class_id: int) -> dict[str, Any] | None:
    return next(
        (item for item in _manifest().get("documents", []) if item.get("class_id") == class_id),
        None,
    )


def _safe_relative_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    candidate.relative_to(root.resolve())
    return candidate


def resolve_knowledge_asset(version: str, asset_path: str) -> Path | None:
    try:
        manifest = _manifest()
        if version != manifest.get("version"):
            return None
        candidate = _safe_relative_path(settings.knowledge_dir / "assets", asset_path)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
        return None
    if not candidate.is_file() or candidate.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
        return None
    return candidate


def _section(markdown: str, heading: str, *, include_heading: bool = False) -> str | None:
    lines = markdown.splitlines()
    start: int | None = None
    level: int | None = None
    end = len(lines)
    for index, line in enumerate(lines):
        match = HEADING_LINE.match(line.strip())
        if match:
            current_level = len(match.group(1))
            title = _heading_text(match.group(2))
            if start is not None and level is not None and current_level <= level:
                end = index
                break
            if title == heading:
                start = index if include_heading else index + 1
                level = current_level
    content = "\n".join(lines[start:end] if start is not None else []).strip()
    return content or None


_CURATED_SOURCE_FIELD = re.compile(r"^(title|site|url):\s*(.+?)\s*$")
_CURATED_EVIDENCE_HEADINGS = ("危害", "可能诱因")


def _parse_curated_sources(value: str) -> list[dict[str, str]] | None:
    """Parse the deliberately small title/site/url contract in curated sections."""
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in value.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _CURATED_SOURCE_FIELD.match(stripped)
        if match is None:
            return None
        field, field_value = match.groups()
        if field == "title" and current:
            if set(current) != {"title", "site", "url"}:
                return None
            records.append(current)
            current = {}
        if field in current:
            return None
        current[field] = field_value
    if current:
        if set(current) != {"title", "site", "url"}:
            return None
        records.append(current)
    if not records:
        return None
    for record in records:
        parsed = urlsplit(record["url"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
    return records


def get_curated_evidence_sections(
    class_id: int, *, expected_class_name: str | None = None
) -> dict[str, Any] | None:
    """Return exact class-mapped curated evidence without touching treatment data."""
    catalog_item = CLASS_BY_ID.get(class_id)
    document = get_knowledge_document(class_id)
    catalog_name = str(catalog_item["name_zh"]) if catalog_item is not None else None
    expected_names = {name for name in (catalog_name, expected_class_name) if name}
    if catalog_item is None or document is None or document["class_name"] not in expected_names:
        return None
    sections: dict[str, dict[str, Any]] = {}
    for heading in _CURATED_EVIDENCE_HEADINGS:
        section = _section(str(document["markdown"]), heading)
        content = _section(section, "内容") if section else None
        source_text = (
            _section(section, "内容来源：") or _section(section, "内容来源")
            if section
            else None
        )
        if not content or not source_text:
            return None
        content = re.sub(r"^\*\*(.*)\*\*$", r"\1", content.strip(), flags=re.DOTALL).strip()
        sources = _parse_curated_sources(source_text)
        if not content or sources is None:
            return None
        sections[heading] = {"content": content, "sources": sources}
    return {"class_id": class_id, "class_name": str(catalog_item["name_zh"]), "sections": sections}


def _heading_blocks(markdown: str) -> list[dict[str, str | bool]]:
    lines = markdown.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if (match := HEADING_LINE.match(line.strip())) and len(match.group(1)) == 2
    ]
    blocks: list[dict[str, str | bool]] = []
    if starts:
        intro = "\n".join(lines[: starts[0]]).strip()
        if intro:
            title_match = HEADING_LINE.match(lines[0].strip())
            blocks.append({
                "title": _heading_text(title_match.group(2)) if title_match else "知识参考",
                "markdown": intro,
                "full_width": "|" in intro or "![" in intro,
            })
    elif markdown.strip():
        blocks.append({
            "title": "知识参考",
            "markdown": markdown.strip(),
            "full_width": "|" in markdown or "![" in markdown,
        })
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        block = "\n".join(lines[start:end]).strip()
        if not block:
            continue
        title_match = HEADING_LINE.match(lines[start].strip())
        blocks.append({
            "title": _heading_text(title_match.group(2)) if title_match else "知识参考",
            "markdown": block,
            "full_width": "|" in block or "![" in block,
        })
    return blocks


def _without_tables(markdown: str | None) -> str:
    if not markdown:
        return MISSING_SECTION
    return "\n".join(line for line in markdown.splitlines() if not line.lstrip().startswith("|")).strip() or MISSING_SECTION


def _rewrite_images(markdown: str, document_path: Path, version: str) -> str:
    root = settings.knowledge_dir.resolve()

    def replace(match: re.Match[str]) -> str:
        relative = match.group(2).strip()
        asset = (document_path.parent / relative).resolve()
        asset.relative_to(root)
        asset_relative = asset.relative_to(root / "assets").as_posix()
        if not asset.is_file() or asset.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
            raise ValueError(f"知识库图片不存在或格式不受支持：{relative}")
        url = f"/api/catalog/knowledge/assets/{quote(version, safe='')}/{quote(asset_relative, safe='/')}"
        return f"![{match.group(1)}]({url})"

    return IMAGE_PATTERN.sub(replace, markdown)


def _heading_text(value: str) -> str:
    return re.sub(r"[*_`\[\]]", "", value).strip()


def pesticide_warning_metadata(markdown: str) -> dict[str, str | bool]:
    """Identify chemical content under the prevention hierarchy before keyword fallback."""
    lines = markdown.splitlines()
    prevention_level: int | None = None
    for index, line in enumerate(lines):
        match = HEADING_LINE.match(line.strip())
        if not match:
            continue
        level = len(match.group(1))
        title = _heading_text(match.group(2))
        if "防治方法" in title:
            prevention_level = level
            continue
        if prevention_level is not None and level <= prevention_level:
            prevention_level = None
        if prevention_level is not None and level > prevention_level and CHEMICAL_HEADING.search(title):
            return {"requires_pesticide_warning": True, "chemical_detection": "prevention_hierarchy"}
    return {
        "requires_pesticide_warning": bool(CHEMICAL_KEYWORDS.search(markdown)),
        "chemical_detection": "keyword_fallback" if CHEMICAL_KEYWORDS.search(markdown) else "none",
    }


def _with_pesticide_warning(markdown: str, metadata: dict[str, str | bool]) -> str:
    if not metadata["requires_pesticide_warning"]:
        return markdown
    lines = markdown.splitlines()
    insertion: int | None = None
    prevention_level: int | None = None
    for index, line in enumerate(lines):
        match = HEADING_LINE.match(line.strip())
        if match:
            level = len(match.group(1))
            title = _heading_text(match.group(2))
            if "防治方法" in title:
                prevention_level = level
            elif prevention_level is not None and level <= prevention_level:
                prevention_level = None
            elif prevention_level is not None and level > prevention_level and CHEMICAL_HEADING.search(title):
                insertion = index + 1
                break
        if insertion is None and prevention_level is not None and CHEMICAL_KEYWORDS.search(line):
            insertion = index
            break
    if insertion is None:
        insertion = len(lines)
    lines[insertion:insertion] = ["", f"> {PESTICIDE_WARNING}", ""]
    return "\n".join(lines)


def _renderer() -> MarkdownIt:
    renderer = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
    renderer.enable("table")
    default_link_open = renderer.renderer.rules.get("link_open", renderer.renderer.renderToken)

    def link_open(tokens, index, options, env):
        href = tokens[index].attrGet("href") or ""
        if href.startswith("https://"):
            tokens[index].attrSet("target", "_blank")
            tokens[index].attrSet("rel", "noreferrer")
        return default_link_open(tokens, index, options, env)

    renderer.renderer.rules["link_open"] = link_open
    return renderer


@lru_cache(maxsize=32)
def get_knowledge_document(class_id: int) -> dict[str, Any] | None:
    catalog_item = CLASS_BY_ID.get(class_id)
    if catalog_item is None:
        return None
    try:
        manifest = _manifest()
        entry = _document_entry(class_id)
        if entry is None or entry.get("class_name") != catalog_item["name_zh"]:
            return None
        document_path = _safe_relative_path(settings.knowledge_dir, str(entry["document"]))
        markdown = document_path.read_text(encoding="utf-8")
        version = str(manifest["version"])
        renderer = _renderer()
        metadata = pesticide_warning_metadata(markdown)
        render = lambda value: renderer.render(_rewrite_images(value, document_path, version))
        full_markdown = _with_pesticide_warning(markdown, metadata)
        prevention_markdown = _section(markdown, "防治方法", include_heading=True) or MISSING_SECTION
        return {
            "schema_version": str(manifest["schema_version"]),
            "version": version,
            "class_id": class_id,
            "class_name": str(catalog_item["name_zh"]),
            "title": markdown.splitlines()[0].removeprefix("# ").strip(),
            "source": manifest["source"],
            "markdown": markdown,
            "requires_pesticide_warning": metadata["requires_pesticide_warning"],
            "pesticide_warning": PESTICIDE_WARNING if metadata["requires_pesticide_warning"] else None,
            "chemical_detection": metadata["chemical_detection"],
            "symptoms_html": render(_without_tables(_section(markdown, "为害症状"))),
            "features_html": render(_without_tables(_section(markdown, "特征"))),
            "prevention_html": render(_with_pesticide_warning(prevention_markdown, metadata)),
            "full_html": render(full_markdown),
            "sections": [
                {
                    "title": block["title"],
                    "html": render(str(block["markdown"])),
                    "full_width": block["full_width"],
                }
                for block in _heading_blocks(full_markdown)
            ],
        }
    except (FileNotFoundError, OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def clear_knowledge_cache() -> None:
    get_knowledge_document.cache_clear()
