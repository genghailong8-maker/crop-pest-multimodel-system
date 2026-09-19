"""Semantic consistency guard for host severity status in R3.1 Markdown SSOT."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SEVERITIES = ("轻度", "中度", "重度")
STALE_PATTERNS = (
    re.compile(r"(?i)(?:三级分级|host[ -]?specific severity|host severity|severity).{0,24}NEEDS_EVIDENCE"),
    re.compile(r"(?i)NEEDS_EVIDENCE.{0,24}(?:三级分级|host[ -]?specific severity|host severity|severity)"),
    re.compile(r"(?i)(?:三级严重度|三级损失分级|寄主严重度).{0,24}(?:不可用|暂缺|未完成|无法提供)"),
)


def top_section(markdown: str, title: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(title)}\s*$([\s\S]*?)(?=^## |\Z)", markdown)
    return match.group(1) if match else ""


def host_blocks(markdown: str) -> dict[str, str]:
    section = top_section(markdown, "已审核寄主")
    starts = list(re.finditer(r"(?m)^### 寄主：(.+?)\s*$", section))
    result: dict[str, str] = {}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(section)
        result[match.group(1).strip()] = section[match.end() : end]
    return result


def subsection(block: str, title: str) -> str:
    match = re.search(rf"(?ms)^### {re.escape(title)}\s*$([\s\S]*?)(?=^### |\Z)", block)
    return match.group(1) if match else ""


def host_semantic_issues(
    markdown: str,
    capability_record: dict[str, Any],
    evidence_records: list[dict[str, Any]],
) -> list[str]:
    crop = capability_record["crop"]
    block = host_blocks(markdown).get(crop, "")
    issues: list[str] = []
    if not block:
        return [f"{crop}: missing host block"]
    severity_text = subsection(block, "严重程度")
    is_full = capability_record.get("status") == "FULL"
    is_available = capability_record.get("severity_available") is True
    if is_full and is_available:
        for pattern in STALE_PATTERNS:
            if pattern.search(severity_text):
                issues.append(f"{crop}: stale host severity state")
                break
        for label in SEVERITIES:
            tier = re.search(rf"(?ms)^#### {label}\s*$([\s\S]*?)(?=^#### |\Z)", severity_text)
            if tier is None or "COMPLETE" not in tier.group(1):
                issues.append(f"{crop}: {label} Markdown is not COMPLETE")
        by_level = {item.get("severity"): item for item in evidence_records}
        for level in ("mild", "moderate", "severe"):
            if by_level.get(level, {}).get("status") != "COMPLETE":
                issues.append(f"{crop}: {level} evidence is not COMPLETE")
    return issues


def validate() -> dict[str, Any]:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT / "severity-evidence.json").read_text(encoding="utf-8"))
    capability = json.loads((ROOT / "capability-fallback.json").read_text(encoding="utf-8"))
    document_by_class = {int(item["class_id"]): ROOT / item["document"] for item in manifest["documents"]}
    all_issues: list[str] = []
    for record in capability["records"]:
        class_id = int(record["class_id"])
        relevant = [
            item for item in evidence["records"]
            if item.get("object_type") == "insect_host"
            and int(item.get("class_id")) == class_id
            and item.get("crop") == record["crop"]
        ]
        all_issues.extend(
            f"{class_id}:{record['crop']}:{issue}"
            for issue in host_semantic_issues(
                document_by_class[class_id].read_text(encoding="utf-8"), record, relevant
            )
        )
    return {
        "status": "PASS" if not all_issues else "FAIL",
        "FULL_HOST_STALE_NEEDS_EVIDENCE": len(all_issues),
        "issues": all_issues,
    }


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
