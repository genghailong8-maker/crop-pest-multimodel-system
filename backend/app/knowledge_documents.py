from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

from markdown_it import MarkdownIt

from .catalog import CLASS_BY_ID
from .config import settings


MISSING_SECTION = "知识库暂未收录该项"
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$")
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


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


def _section(markdown: str, heading: str) -> str | None:
    lines = markdown.splitlines()
    start: int | None = None
    selected: list[str] = []
    for index, line in enumerate(lines):
        match = SECTION_PATTERN.match(line.strip())
        if match:
            if start is not None:
                break
            if match.group(1).strip() == heading:
                start = index + 1
                continue
        if start is not None:
            selected.append(line)
    content = "\n".join(selected).strip()
    return content or None


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
        render = lambda value: renderer.render(_rewrite_images(value, document_path, version))
        return {
            "schema_version": str(manifest["schema_version"]),
            "version": version,
            "class_id": class_id,
            "class_name": str(catalog_item["name_zh"]),
            "title": markdown.splitlines()[0].removeprefix("# ").strip(),
            "source": manifest["source"],
            "symptoms_html": render(_without_tables(_section(markdown, "为害症状"))),
            "features_html": render(_without_tables(_section(markdown, "特征"))),
            "prevention_html": render(_without_tables(_section(markdown, "防治方法"))),
            "full_html": render(markdown),
        }
    except (FileNotFoundError, OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def clear_knowledge_cache() -> None:
    get_knowledge_document.cache_clear()
