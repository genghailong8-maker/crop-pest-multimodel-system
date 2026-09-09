"""Finalize the R3.1 adaptive host capability and treatment-fallback registry.

This is a knowledge-layer generator only.  It consumes the Batch 1B manifest,
severity registry and Markdown SSOT; it does not alter product runtime code.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.json"
EVIDENCE_PATH = ROOT / "severity-evidence.json"
CAPABILITY_PATH = ROOT / "capability-fallback.json"
REPORTS_ROOT = ROOT.parents[1] / "docs" / "competition" / "r3.1"
SEVERITIES = ("mild", "moderate", "severe")
LABELS = {"mild": "轻度", "moderate": "中度", "severe": "重度"}
SOURCE_REF = re.compile(r"\[(R31-[A-Z0-9-]+)\]")
SEVERITY_SPECIFIC_HOSTS = {(8, "大豆"), (9, "大豆"), (13, "大豆")}
FALLBACK_ORDER = ["host_severity", "host_general", "insect_general"]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _refs(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(1) for match in SOURCE_REF.finditer(text)))


def _top_sections(markdown: str) -> dict[str, str]:
    lines = markdown.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^## (.+?)\s*$", line)
        if match:
            starts.append((index, match.group(1)))
    result: dict[str, str] = {}
    for position, (start, title) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        result[title] = "\n".join(lines[start + 1 : end]).strip()
    return result


def _host_blocks(section: str) -> dict[str, str]:
    lines = section.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^### 寄主：(.+?)\s*$", line)
        if match:
            starts.append((index, match.group(1).strip()))
    result: dict[str, str] = {}
    for position, (start, crop) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        result[crop] = "\n".join(lines[start + 1 : end]).strip()
    return result


def _section(block: str, title: str) -> str:
    match = re.search(rf"(?ms)^### {re.escape(title)}\s*$([\s\S]*?)(?=^### |\Z)", block)
    return match.group(1).strip() if match else ""


def _treatment_parts(text: str) -> dict[str, str]:
    headings = {"预防与监测": "prevention_monitoring", "生物与物理": "biological_physical", "化学防治边界": "chemical_boundary"}
    result: dict[str, str] = {}
    starts = list(re.finditer(r"(?m)^#### (预防与监测|生物与物理|化学防治边界)\s*$", text))
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        result[headings[match.group(1)]] = text[match.end() : end].strip()
    return result


def _insect_general(class_id: int, insect: str) -> dict[str, Any]:
    source_ids = ["R31-GLOBAL-IPM-MOA", "R31-GLOBAL-IPM-FAO"]
    return {
        "object_type": "GENERAL_INSECT_TREATMENT",
        "class_id": class_id,
        "insect": insect,
        "treatment_level": "insect_general",
        "available": True,
        "source_ids": source_ids,
        "measures": {
            "monitoring": "按虫态、发生位置、寄主生育期和天敌情况开展田间巡查，记录变化后再决定是否干预。",
            "agricultural": "结合清洁田园、合理轮作或错期、去除明显虫源和改善田间管理，按当地植保意见执行。",
            "physical_biological": "优先采用人工或物理措施，并保护、利用自然天敌和其他绿色防控资源。",
            "chemical_boundary": "不固化特定作物产品、有效成分、剂型、剂量、次数或 PHI；只有中国当前登记明确覆盖当前作物与目标害虫且当地指导支持时，才按标签执行。",
        },
        "pesticide_policy": "principle_only; exact current China crop+target registration required",
        "provenance_note": "仅包含可合理跨寄主使用的监测、农业、物理、生物和原则性化学边界；不携带特定作物登记数字。",
    }


def _effective_fallback(capabilities: dict[str, bool], severity: str) -> str:
    if severity == "uncertain":
        return "none"
    if capabilities["host_severity_treatment"]:
        return "host_severity"
    if capabilities["host_general_treatment"]:
        return "host_general"
    return "insect_general"


def _host_status(capabilities: dict[str, bool]) -> str:
    if not capabilities["host_relation"]:
        return "REJECTED"
    if (
        capabilities["host_relation"]
        and capabilities["host_damage"]
        and capabilities["severity"]
        and (capabilities["host_general_treatment"] or capabilities["host_severity_treatment"])
    ):
        return "FULL"
    return "PARTIAL"


def build_registry(manifest: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    evidence_records = evidence["records"]
    severity_by_host = {
        (item["class_id"], item["crop"], item["severity"]): item
        for item in evidence_records
        if item.get("object_type") == "insect_host"
    }
    treatment_by_host = {
        (item["class_id"], item["crop"]): item
        for item in evidence.get("treatment_audit", [])
    }
    host_general: list[dict[str, Any]] = []
    capability_records: list[dict[str, Any]] = []
    general_treatments = [_insect_general(int(entry["class_id"]), entry["class_name"]) for entry in manifest["documents"]]
    vector_hosts: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for item in evidence_records:
        if item.get("object_type") == "vector_disease":
            vector_hosts.setdefault((item["class_id"], item["crop"]), []).append(item)

    for entry in manifest["documents"]:
        class_id = int(entry["class_id"])
        document_path = ROOT / entry["document"]
        markdown = document_path.read_text(encoding="utf-8")
        sections = _top_sections(markdown)
        hosts = _host_blocks(sections.get("已审核寄主", ""))
        for crop in entry["supported_hosts"]:
            block = hosts[crop]
            relation_text = block.split("### 当前作物受害表现", 1)[0]
            damage_text = _section(block, "当前作物受害表现")
            treatment_text = _section(block, "防治方法")
            treatment_parts = _treatment_parts(treatment_text)
            relation_source_ids = _refs(relation_text)
            damage_source_ids = _refs(damage_text)
            treatment_source_ids = _refs(treatment_text)
            severity_records = [severity_by_host[(class_id, crop, severity)] for severity in SEVERITIES]
            severity_available = all(
                item.get("status") == "COMPLETE"
                and bool(item.get("source_ids"))
                and (item.get("evidence_type") != "EVIDENCE_SYNTHESIZED" or bool(str(item.get("synthesis_note", "")).strip()))
                for item in severity_records
            )
            treatment_audit = treatment_by_host[(class_id, crop)]
            host_severity_available = treatment_audit.get("status") == "SEVERITY_SPECIFIC_SUPPORTED"
            host_general_available = bool(
                treatment_text
                and treatment_source_ids
                and treatment_audit.get("host_specific_evidence") is True
                and treatment_audit.get("SOURCE_SEMANTIC_REVIEW") == "PASS"
                and treatment_audit.get("host_specific_source_ids")
            )
            host_capabilities = {
                "host_relation": bool(relation_source_ids),
                "host_damage": bool(damage_text and damage_source_ids),
                "severity": severity_available,
                "host_general_treatment": host_general_available,
                "host_severity_treatment": host_severity_available,
                "vector_disease": bool(vector_hosts.get((class_id, crop))),
            }
            status = _host_status(host_capabilities)
            host_general.append(
                {
                    "object_type": "HOST_GENERAL_TREATMENT",
                    "class_id": class_id,
                    "insect": entry["class_name"],
                    "crop": crop,
                    "treatment_level": "host_general",
                    "available": host_capabilities["host_general_treatment"],
                    "source_ids": treatment_source_ids,
                    "sections": treatment_parts,
                    "host_specific_source_ids": list(treatment_audit.get("host_specific_source_ids", [])),
                    "host_specific_evidence": bool(treatment_audit.get("host_specific_evidence")),
                    "SOURCE_SEMANTIC_REVIEW": treatment_audit.get("SOURCE_SEMANTIC_REVIEW", "NEEDS_REVIEW"),
                    "source_entailment_review": treatment_audit.get("source_entailment_review", {}),
                    "pesticide_policy": "principle_only; exact current China crop+target registration required",
                    "explanation": "当前审核资料支持该寄主的严重程度判断，但未支持按轻/中/重进一步区分防治措施，因此显示该害虫在当前作物上的通用防治方案。",
                    "provenance_note": "作物特异防治资料可用，但来源未可靠区分轻/中/重时，作为 HOST_GENERAL_TREATMENT 使用。",
                }
            )
            severity_treatment = {
                "object_type": "HOST_SEVERITY_TREATMENT",
                "class_id": class_id,
                "insect": entry["class_name"],
                "crop": crop,
                "treatment_level": "host_severity",
                "available": host_severity_available,
                "supported_severities": list(SEVERITIES) if host_severity_available else [],
                "source_ids": list(treatment_audit.get("source_ids", [])),
                "note": treatment_audit.get("note", ""),
                "explanation": "当前资料支持按受害阶段或行动级别调整管理强度，并不代表来源采用本项目三级 Severity 分级。",
            }
            provenance = {
                "host_relation_source_ids": relation_source_ids,
                "host_damage_source_ids": damage_source_ids,
                "host_general_treatment_source_ids": treatment_source_ids,
                "host_severity_treatment_source_ids": severity_treatment["source_ids"],
                "vector_disease_source_ids": list(dict.fromkeys(source_id for item in vector_hosts.get((class_id, crop), []) for source_id in item.get("source_ids", []))),
                "complete": bool(relation_source_ids and damage_source_ids and treatment_source_ids),
            }
            capability_records.append(
                {
                    "object_type": "insect_host_capability",
                    "class_id": class_id,
                    "insect": entry["class_name"],
                    "crop": crop,
                    "status": status,
                    "capabilities": host_capabilities,
                    "host_relation_available": host_capabilities["host_relation"],
                    "host_damage_available": host_capabilities["host_damage"],
                    "severity_available": severity_available,
                    "host_general_treatment_available": host_capabilities["host_general_treatment"],
                    "host_severity_treatment_available": host_capabilities["host_severity_treatment"],
                    "vector_disease_available": host_capabilities["vector_disease"],
                    "host_general_treatment": {
                        "available": host_capabilities["host_general_treatment"],
                        "treatment_level": "host_general",
                        "source_ids": treatment_source_ids,
                    },
                    "host_severity_treatment": severity_treatment,
                    "vector_disease": {
                        "available": host_capabilities["vector_disease"],
                        "relations": [
                            {"disease": item.get("disease"), "source_ids": item.get("source_ids", [])}
                            for item in vector_hosts.get((class_id, crop), [])
                            if item.get("severity") == "mild"
                        ],
                    },
                    "provenance": provenance,
                    "fallback_level": _effective_fallback(host_capabilities, "mild"),
                    "effective_treatment_fallback": {
                        "mild": _effective_fallback(host_capabilities, "mild"),
                        "moderate": _effective_fallback(host_capabilities, "moderate"),
                        "severe": _effective_fallback(host_capabilities, "severe"),
                        "uncertain": "none",
                    },
                }
            )

    return {
        "schema_version": "r31-adaptive-capability-v1",
        "batch": manifest["batch"],
        "closure": manifest.get("closure", "Batch 1C — Adaptive Host Capability & Treatment Fallback Finalization"),
        "treatment_fallback_order": FALLBACK_ORDER,
        "treatment_explanations": {
            "host_severity": "当前资料支持按受害阶段或行动级别调整管理强度，并不代表来源采用本项目三级 Severity 分级。",
            "host_general": "当前审核资料支持该寄主的严重程度判断，但未支持按轻/中/重进一步区分防治措施，因此显示该害虫在当前作物上的通用防治方案。",
            "insect_general": "当前寄主暂无完整的作物特异防治资料，以下显示该害虫的通用防治建议。",
            "none": "当前受害程度无法判断，因此不提供防治措施。",
        },
        "uncertain": {
            "treatment_level": "none",
            "treatment": None,
            "explanation": "当前受害程度无法判断，因此不提供防治措施。",
        },
        "other": {
            "free_input": False,
            "host_damage": False,
            "severity": False,
            "vector_disease": False,
            "host_specific_treatment": False,
            "treatment_level": "insect_general",
            "explanation": "当前寄主为其他/暂未收录时，仅显示该昆虫通用危害、通用 possible_causes 和 GENERAL_INSECT_TREATMENT。",
        },
        "records": capability_records,
        "host_general_treatments": host_general,
        "general_insect_treatments": general_treatments,
    }


def _update_manifest(manifest: dict[str, Any], registry: dict[str, Any]) -> None:
    manifest.setdefault("closure", "Batch 1C — Adaptive Host Capability & Treatment Fallback Finalization")
    manifest["capability_registry"] = "capability-fallback.json"
    manifest["treatment_fallback_order"] = FALLBACK_ORDER
    manifest["uncertain_treatment_level"] = "none"
    manifest.setdefault("policy", {}).update(
        {
            "severity_treatment_decoupled": True,
            "treatment_fallback_order": FALLBACK_ORDER,
            "uncertain_treatment": "NO_TREATMENT",
            "other_policy": "no free input, no host-specific damage/severity/vector/treatment; insect_general only",
        }
    )
    manifest["host_capabilities"] = registry["records"]
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_capability_section(path: Path, class_id: int, records: list[dict[str, Any]]) -> None:
    text = path.read_text(encoding="utf-8")
    marker = "## R3.1 自适应能力与防治 fallback"
    if marker in text:
        text = text.split(marker, 1)[0].rstrip()
    lines = ["", marker, "", "Severity 与 Treatment 完全解耦；`severity_available` 只由 mild/moderate/severe 三档完整证据决定。Treatment 按 `HOST_SEVERITY_TREATMENT` → `HOST_GENERAL_TREATMENT` → `GENERAL_INSECT_TREATMENT` 解析。"]
    for record in records:
        capabilities = record["capabilities"]
        lines.append(
            f"- {record['crop']}：`{record['status']}`；capabilities={json.dumps(capabilities, ensure_ascii=False, separators=(',', ':'))}；severity_available=`{str(record['severity_available']).lower()}`；fallback={json.dumps(record['effective_treatment_fallback'], ensure_ascii=False, separators=(',', ':'))}。"
        )
    lines.extend([
        "- `severity=uncertain` 时固定为 `treatment_level=none`，不显示任何防治措施。",
        "- `其他/暂未收录` 不允许自由输入，不显示寄主特异 damage、severity、vector disease 或 treatment，仅使用 GENERAL_INSECT_TREATMENT。",
    ])
    path.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def _update_other_policy(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    updated = text.replace("未知寄主不等于未知严重度", "OTHER 不提供 host-specific severity；它与 severity=uncertain 是两个独立状态")
    if updated != text:
        path.write_text(updated, encoding="utf-8")


def _md_sources(source_ids: list[str], sources: dict[str, dict[str, Any]]) -> str:
    return "; ".join(f"{source_id} — {sources[source_id]['title']} — {sources[source_id]['url']}" for source_id in source_ids if source_id in sources)


def build_reports(manifest: dict[str, Any], evidence: dict[str, Any], registry: dict[str, Any]) -> None:
    sources = {item["source_id"]: item for item in manifest["sources"]}
    records = registry["records"]
    status_counts = {status: sum(item["status"] == status for item in records) for status in ("FULL", "PARTIAL", "REJECTED")}
    severity_hosts = sum(item["severity_available"] for item in records)
    host_general_count = sum(item["capabilities"]["host_general_treatment"] for item in records)
    matrix = [
        "# 《昆虫×寄主作物知识库总表》",
        "",
        "**批次**：R3.1 Batch 1 — Batch 1C Adaptive Host Capability & Treatment Fallback",
        "",
        "Severity 与 Treatment 完全解耦。推荐寄主仍为“推荐：常见寄主之一——<crop>”，仅表示 reviewed common host，不是 confirmed_host。",
        "",
        "| 类别 | 昆虫 | 作物 | Host status | severity_available | host_general_treatment | host_severity_treatment | fallback level | vector disease |",
        "|---:|---|---|---|---|---|---|---|---|",
    ]
    for item in records:
        matrix.append(
            f"| {item['class_id']} | {item['insect']} | {item['crop']} | {item['status']} | {str(item['severity_available']).lower()} | {str(item['capabilities']['host_general_treatment']).lower()} | {str(item['capabilities']['host_severity_treatment']).lower()} | {item['fallback_level']} | {str(item['capabilities']['vector_disease']).lower()} |"
        )
    matrix.extend([
        "",
        f"推荐寄主：{len(manifest['documents'])} 个昆虫文档均保持 reviewed common-host 语义；产品未来仍必须由用户手动确认。",
        f"统计：FULL={status_counts['FULL']}，PARTIAL={status_counts['PARTIAL']}，REJECTED={status_counts['REJECTED']}；severity_available={severity_hosts}/38。",
        "",
        "能力字段：`host_relation`、`host_damage`、`severity`、`host_general_treatment`、`host_severity_treatment`、`vector_disease`。",
        "",
        "`severity=uncertain` 固定 `NO_TREATMENT`；OTHER 只使用 GENERAL_INSECT_TREATMENT。",
    ])
    (REPORTS_ROOT / "《昆虫×寄主作物知识库总表》.md").write_text("\n".join(matrix) + "\n", encoding="utf-8")

    severity_lines = [
        "# 《严重程度描述与具体来源总表》",
        "",
        "**Batch 1C 口径**：Severity 是否可用只取决于同一 insect×host 的 mild、moderate、severe 三档证据是否全部 COMPLETE；Treatment 是否三级不影响 Severity 选择。",
        "",
        "| 昆虫 | 作物 | Host status | mild | moderate | severe | severity_available |",
        "|---|---|---|---|---|---|---|",
    ]
    evidence_by_host = {}
    for item in evidence["records"]:
        if item.get("object_type") == "insect_host":
            evidence_by_host.setdefault((item["class_id"], item["crop"]), {})[item["severity"]] = item
    for item in records:
        values = [evidence_by_host[(item["class_id"], item["crop"])][severity]["status"] for severity in SEVERITIES]
        severity_lines.append(f"| {item['insect']} | {item['crop']} | {item['status']} | {values[0]} | {values[1]} | {values[2]} | {str(item['severity_available']).lower()} |")
    severity_lines.extend([
        "",
        f"`severity_available=true`：{severity_hosts}/38 个寄主。三档完整时仍允许用户选择 uncertain；uncertain 不显示 Treatment。",
        "",
        "## 证据登记位置",
        "",
        "逐项 `rubric_text`、`observable_features`、`source_ids`、`evidence_type`、`synthesis_note` 和状态继续见 `knowledge/insect-host-r3.1/severity-evidence.json`。本轻/中/重规则为基于可靠农业资料整理形成的系统辅助判定规则，并非宣称原始资料本身采用相同三级分级。",
        "",
        "## Vector disease",
        "",
        "Vector relationship 与 disease severity 完全解耦；关系可用不代表病害三级 Severity 可用。",
    ])
    for item in evidence["records"]:
        if item.get("object_type") == "vector_disease":
            severity_lines.append(f"- {item['insect']}×{item['crop']}×{item['disease']}×{item['severity']}：{item['status']}；source_ids={','.join(item.get('source_ids', []))}。")
    (REPORTS_ROOT / "《严重程度描述与具体来源总表》.md").write_text("\n".join(severity_lines) + "\n", encoding="utf-8")

    treatment_lines = [
        "# 《防治措施与农药来源总表》",
        "",
        "**Batch 1C 新合同**：`HOST_SEVERITY_TREATMENT` → `HOST_GENERAL_TREATMENT` → `GENERAL_INSECT_TREATMENT`。Treatment 不再要求三级内容完全不同，也不决定 Severity 是否可用。",
        "",
        "`severity=uncertain` 固定 `NO_TREATMENT`；OTHER 不使用任何 host-specific Treatment。具体农药参数仍须有中国大陆当前精确登记依据。",
        "",
        "## 页面解释语义（仅定义合同，不实现 Web）",
        "",
        "- `host_general`：当前审核资料支持该寄主的严重程度判断，但未支持按轻/中/重进一步区分防治措施，因此显示该害虫在当前作物上的通用防治方案。",
        "- `insect_general`：当前寄主暂无完整的作物特异防治资料，以下显示该害虫的通用防治建议。",
        "- `none`：当前受害程度无法判断，因此不提供防治措施。",
        "",
        "## HOST_SEVERITY_TREATMENT",
        "",
        "| 昆虫 | 作物 | 覆盖 severity | Source ID | 说明 |",
        "|---|---|---|---|---|",
    ]
    for item in records:
        hs = item["host_severity_treatment"]
        if hs["available"]:
            treatment_lines.append(f"| {item['insect']} | {item['crop']} | {','.join(hs['supported_severities'])} | {_md_sources(hs['source_ids'], sources)} | {hs['note']} |")
    treatment_lines.extend([
        "",
        f"## HOST_GENERAL_TREATMENT（{host_general_count}/38）",
        "",
        "只有经人工语义审核、来源直接支持当前 insect×host 管理措施的条目才作为 host-general 使用；其余 fail closed 到 insect-general。",
        "",
        "| 昆虫 | 作物 | Source ID | 最终 fallback |",
        "|---|---|---|---|",
    ])
    for item in records:
        host_general = next(record for record in registry["host_general_treatments"] if record["class_id"] == item["class_id"] and record["crop"] == item["crop"])
        if host_general["available"]:
            treatment_lines.append(f"| {item['insect']} | {item['crop']} | {_md_sources(host_general['host_specific_source_ids'], sources)} | {item['fallback_level']} |")
    treatment_lines.extend([
        "",
        "## GENERAL_INSECT_TREATMENT（8/8）",
        "",
        "仅包含跨寄主合理的监测、农业、物理、生物和原则性化学边界；来源为通用 IPM 原则，不携带特定作物剂量或 PHI。",
        "",
        "| 昆虫 | Source ID | treatment_level |",
        "|---|---|---|",
    ])
    for item in registry["general_insect_treatments"]:
        treatment_lines.append(f"| {item['insect']} | {_md_sources(item['source_ids'], sources)} | {item['treatment_level']} |")
    treatment_lines.extend(["", "## Effective treatment fallback", "", "| 昆虫 | 作物 | mild | moderate | severe | uncertain |", "|---|---|---|---|---|---|"])
    for item in records:
        fallback = item["effective_treatment_fallback"]
        treatment_lines.append(f"| {item['insect']} | {item['crop']} | {fallback['mild']} | {fallback['moderate']} | {fallback['severe']} | {fallback['uncertain']} |")
    (REPORTS_ROOT / "《防治措施与农药来源总表》.md").write_text("\n".join(treatment_lines) + "\n", encoding="utf-8")

    change_report = f"""# 《知识库变更报告》

**批次**：R3.1 — Final Documentation Consistency + Final Controlled Knowledge Expansion

## 旧规则

- Host 是否可用容易被“Treatment 是否三级完整”混淆。
- Severity 和 Treatment 的能力边界没有结构化表达。
- Treatment 缺少明确的 host-specific → insect-general fallback。

## 新规则

- Severity 与 Treatment 完全解耦；`severity_available=true` 仅要求同一寄主的 mild、moderate、severe 三档证据完整、有 Source ID、provenance 完整且无 unsupported quantitative threshold。
- Host status 自适应为 FULL/PARTIAL/REJECTED。当前结果为 FULL={status_counts['FULL']}、PARTIAL={status_counts['PARTIAL']}、REJECTED={status_counts['REJECTED']}；PARTIAL 仍可作为寄主选项，但按 capability fail closed。
- Treatment 解析顺序固定为 `HOST_SEVERITY_TREATMENT` → `HOST_GENERAL_TREATMENT` → `GENERAL_INSECT_TREATMENT`。
- `severity=uncertain` 固定 `NO_TREATMENT`；OTHER 只显示通用危害、通用 possible_causes 和 GENERAL_INSECT_TREATMENT。
- 8/8 昆虫具备 source-backed GENERAL_INSECT_TREATMENT；{host_general_count}/38 寄主通过 HOST_GENERAL_TREATMENT 语义审核，其余回退 GENERAL_INSECT_TREATMENT。

## 当前状态

- R31_KNOWLEDGE_CORRECTION = PASS
- R31_FINAL_EVIDENCE_SPRINT = PASS
- R31_FINAL_EVIDENCE_CORRECTION = PASS
- R31_KNOWLEDGE_EXPANSION = PASS
- R31_EVIDENCE_COVERAGE = PARTIAL
- 最终知识计数：FULL={status_counts['FULL']}，PARTIAL={status_counts['PARTIAL']}，insect-host Severity COMPLETE={severity_hosts * 3}/114，NEEDS_EVIDENCE={114 - severity_hosts * 3}/114，TRACEABLE Prompt={severity_hosts * 3}。
- KNOWLEDGE_EXPANSION_STOPPED = YES；剩余 PARTIAL 转为未来 enhancement backlog，不再阻塞后续图像批次。
- Backend = PASS；Web = PASS；Candidate Browser Smoke = PASS（均为既有已完成状态，本次未修改产品逻辑）。
- Formal = NOT RUN；AI final illustrations = NOT GENERATED。

## 未做

- 本次未修改 Backend/Web/Formal/SQLite，也未修改 R1 frozen Evidence、Normalizer、Extractor、Guard、YOLO、CLIP。
- 未添加未经当前中国精确登记核验的农药有效成分、剂型、剂量、次数或 PHI。
- 未 commit/push，未生成最终 AI 图片。
"""
    (REPORTS_ROOT / "《知识库变更报告》.md").write_text(change_report, encoding="utf-8")


def main() -> None:
    manifest = _read_json(MANIFEST_PATH)
    evidence = _read_json(EVIDENCE_PATH)
    registry = build_registry(manifest, evidence)
    CAPABILITY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _update_manifest(manifest, registry)
    for entry in manifest["documents"]:
        path = ROOT / entry["document"]
        records = [item for item in registry["records"] if item["class_id"] == int(entry["class_id"])]
        _update_other_policy(path)
        _append_capability_section(path, int(entry["class_id"]), records)
    build_reports(manifest, evidence, registry)


if __name__ == "__main__":
    main()
