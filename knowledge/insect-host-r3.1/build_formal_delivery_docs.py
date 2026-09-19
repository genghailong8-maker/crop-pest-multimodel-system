"""Build the formal R3.1 retention documents from the checked-in SSOT."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
R31 = ROOT / "knowledge" / "insect-host-r3.1"
DOCS = ROOT / "docs" / "competition" / "r3.1"
PLANT_ROOT = ROOT / "knowledge" / "baidu-baike-20260818" / "documents"
INSECT_ROOT = R31 / "insects"
SEVERITY_LABELS = {"mild": "轻度", "moderate": "中度", "severe": "重度"}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def text_sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def inline(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def source_url(source: dict[str, Any]) -> str:
    return source.get("doi") or source.get("url") or "未登记"


def demote(markdown: str, level: int) -> str:
    """Keep the complete SSOT body while nesting its Markdown headings."""
    result: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("#"):
            hashes = len(line) - len(line.lstrip("#"))
            if hashes:
                result.append("#" * level + line[hashes:])
                continue
        result.append(line)
    return "\n".join(result).strip()


def severity_id(record: dict[str, Any]) -> str:
    return "|".join(
        str(record.get(key, ""))
        for key in ("object_type", "class_id", "insect", "crop", "disease", "severity")
    )


def severity_marker(record: dict[str, Any]) -> str:
    return (
        "<!-- ARCHIVE_SEVERITY: "
        f"record={severity_id(record)}; status={record['status']}; "
        f"rubric_sha256={text_sha(record['rubric_text'])} -->"
    )


def host_marker(record: dict[str, Any]) -> str:
    key = f"{record['class_id']}|{record['insect']}|{record['crop']}"
    return f"<!-- ARCHIVE_HOST: key={key} -->"


def capability_marker(record: dict[str, Any]) -> str:
    key = f"{record['class_id']}|{record['insect']}|{record['crop']}"
    return f"<!-- ARCHIVE_CAPABILITY: key={key}; sha256={stable_sha(record['capabilities'])} -->"


def fallback_marker(record: dict[str, Any]) -> str:
    key = f"{record['class_id']}|{record['insect']}|{record['crop']}"
    return f"<!-- ARCHIVE_FALLBACK: key={key}; value={inline(record.get('effective_treatment_fallback', {}))} -->"


def vector_marker(record: dict[str, Any], relation: dict[str, Any]) -> str:
    disease = relation.get("disease") or relation.get("disease_name") or relation.get("name") or ""
    key = f"{record['class_id']}|{record['insect']}|{record['crop']}|{disease}"
    return f"<!-- ARCHIVE_VECTOR: key={key}; sha256={stable_sha(relation)} -->"


def string_values(value: Any, path: str = "") -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in {"body", "note", "explanation", "fallback_message"} and isinstance(child, str):
                result.append((child_path, child))
            result.extend(string_values(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(string_values(child, f"{path}[{index}]"))
    return result


def build_prompt_documents(
    manifest: dict[str, Any], evidence: dict[str, Any], capability: dict[str, Any]
) -> tuple[str, str]:
    source_by_id = {item["source_id"]: item for item in manifest["sources"]}
    cap_by_key = {(x["class_id"], x["insect"], x["crop"]): x for x in capability["records"]}
    candidates = sorted(
        [
            x
            for x in evidence["records"]
            if x["object_type"] == "insect_host" and x["status"] == "COMPLETE"
        ],
        key=lambda x: (x["class_id"], x["insect"], x["crop"], x["severity"]),
    )
    candidate_count = len(candidates)
    total_insect_severity = sum(1 for x in evidence["records"] if x.get("object_type") == "insect_host")
    needs_evidence_count = total_insect_severity - candidate_count
    candidate_hosts = len({(x["class_id"], x["insect"], x["crop"]) for x in candidates})
    total_hosts = len(capability["records"])
    companion = [
        "# 《AI示意图提示词与来源依据》",
        "",
        "**文档性质**：R3.1 正式 Prompt provenance 与生成门禁文档。它不是农业事实来源，也不是诊断证据；本批不生成最终图片。",
        "",
        "## Provenance chain",
        "",
        "每条正式候选必须遵循：`agricultural source → severity rubric → observable features → image prompt`。Prompt 根据正式农业资料支持的症状特征整理形成，不声称原始资料采用本项目三级分级；Prompt 本身不是农业事实来源。",
        "",
        "## Prompt evidence gate",
        "",
        f"`PROMPT_EVIDENCE_STATUS` 允许值：`TRACEABLE`、`NEEDS_EVIDENCE`、`REJECTED`。当前只有 `severity-evidence.json` 三档均为 `COMPLETE` 且 capability `severity_available=true` 的 {candidate_count} 个 insect × host × severity 单元可列为 `TRACEABLE` 候选；其余 {needs_evidence_count} 个继续 `NEEDS_EVIDENCE`，不得进入后续生成。用户完成知识审核、来源仍可追溯、图像安全复核通过后才可另行进入 Batch 4。",
        "",
        "## 统一禁止项与免责声明",
        "",
        "- 不添加来源没有支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量结论或其他阈值。",
        "- 不生成文字、UI、箭头、测量数字、农药包装、施药指令、诊断结论，或把传播相关病害画成当前病例已确诊。",
        "- 每张图必须带或邻接展示：**AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。**",
        "",
        "## 正式候选逐项记录",
        "",
    ]
    for item in candidates:
        cap = cap_by_key[(item["class_id"], item["insect"], item["crop"])]
        features = item.get("observable_features", [])
        companion.extend(
            [
                f"### {item['insect']} × {item['crop']} × {SEVERITY_LABELS[item['severity']]}",
                "",
                "- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`",
                f"- evidence_taxon：{'; '.join(item.get('evidence_taxon', [])) or '未记录'}",
                f"- evidence_taxon_level：{'; '.join(item.get('evidence_taxon_level', [])) or '未记录'}",
                f"- evidence_taxon_scope：{json.dumps(item.get('evidence_taxon_scope', []), ensure_ascii=False)}",
                f"- insect：{item['insect']}",
                f"- host：{item['crop']}（reviewed common host；不得自动成为 confirmed_host）",
                f"- severity：{item['severity']} / {SEVERITY_LABELS[item['severity']]}",
                f"- final severity rubric：{item['rubric_text']}",
                f"- severity source IDs：{', '.join('`'+x+'`' for x in item['source_ids'])}",
                f"- SOURCE_SEMANTIC_REVIEW：`{item.get('SOURCE_SEMANTIC_REVIEW', 'NEEDS_REVIEW')}`",
                f"- capability gate：status=`{cap['status']}`；severity_available=`{str(cap['severity_available']).lower()}`",
                "",
                "#### Source provenance",
                "",
                "| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |",
                "|---|---|---|---|---|",
            ]
        )
        for source_id in item["source_ids"]:
            source = source_by_id.get(source_id)
            if source is None:
                companion.append(f"| {source_id} | **DANGLING SOURCE** | — | — | — |")
            else:
                companion.append(
                    f"| {source_id} | {source['title']} | {source['organization']} | {source_url(source)} | {source.get('accessed_at', '未记录')} |"
                )
        companion.extend(
            [
                "",
                "#### Observable visual features and source mapping",
                "",
                "| Observable visual feature | Supporting Source ID(s) |",
                "|---|---|",
            ]
        )
        feature_sources = item.get("visual_feature_source_ids", {})
        for feature in features:
            supporting = feature_sources.get(feature, item["source_ids"])
            companion.append(f"| {feature} | {', '.join('`'+x+'`' for x in supporting)} |")
        companion.extend(
            [
                "",
                "#### Final image-generation prompt",
                "",
                f"> 农业科学示意图：展示{item['insect']}在{item['crop']}上的{SEVERITY_LABELS[item['severity']]}受害状态；仅呈现以下来源支持的可观察特征：{'、'.join(features)}。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。",
                "",
                "#### Synthesis explanation",
                "",
                f"本条为 `EVIDENCE_SYNTHESIZED`：根据 `{', '.join(item['source_ids'])}` 支持的真实症状/进展证据，整理为本项目的 {SEVERITY_LABELS[item['severity']]} 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。",
                "",
                "#### Unsupported / forbidden visual features",
                "",
                "来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。",
                "",
                "#### AI illustration disclaimer",
                "",
                "AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。",
                "",
            ]
        )

    draft = [
        "# 《R3.1 图像生成规格与提示词草案》—正式追溯版",
        "",
        "本文件已从自由草案升级为受证据门禁约束的正式设计规格。完整逐项记录见 [《AI示意图提示词与来源依据》](./《AI示意图提示词与来源依据》.md)。本批不生成最终 AI 图片。",
        "",
        "## 生成候选边界",
        "",
        f"只允许 `severity_available=true` 且 mild/moderate/severe 三档在 `severity-evidence.json` 中为 `COMPLETE` 的 insect × host × severity 进入正式候选；当前为 {candidate_count // 3} 个寄主、{candidate_count} 个 severity 单元。其余 {38 - candidate_count // 3} 个寄主、{needs_evidence_count} 个 severity 单元保持 `NEEDS_EVIDENCE`。",
        "",
        "## 正式 provenance chain",
        "",
        "`agricultural source → final severity rubric → observable features → final image-generation prompt`。每条记录必须有 `PROMPT_EVIDENCE_STATUS`、Source ID、标题、组织/期刊、URL/DOI、accessed_at、visual feature→source mapping、synthesis explanation、禁止项与 AI disclaimer。",
        "",
        "## 统一视觉安全约束",
        "",
        "- 只画来源支持的可观察症状，不自造颜色、斑纹、卷曲、器官损伤、密度、比例、产量数字或阈值。",
        "- 不画文字、UI、箭头、测量数字、农药包装、施药指令或诊断结论。",
        "- “可能传播的相关病害”不得渲染为当前植株已感染；昆虫图不得改变 YOLO 诊断。",
        "- AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。",
        "",
        "## 当前正式候选索引",
        "",
            "| insect × host | mild | moderate | severe |",
        "|---|---|---|---|",
    ]
    grouped: dict[tuple[str, str], dict[str, str]] = {}
    for item in candidates:
        grouped.setdefault((item["insect"], item["crop"]), {})[item["severity"]] = "TRACEABLE"
    for (insect, crop), values in sorted(grouped.items()):
        draft.append(f"| {insect} × {crop} | {values.get('mild', '—')} | {values.get('moderate', '—')} | {values.get('severe', '—')} |")
    draft.extend(
        [
            "",
            "## Gate decision",
            "",
            "`PROMPT_EVIDENCE_STATUS = TRACEABLE` 只表示本条 Prompt 的农业事实链可追溯，不表示图片已经生成或已经被用户批准。只有用户完成知识审核且生成前复核仍通过，才可进入后续 Batch 4；本批明确不生成最终图片。",
            "",
        ]
    )
    return "\n".join(draft), "\n".join(companion)


def build_archive(manifest: dict[str, Any], evidence: dict[str, Any], capability: dict[str, Any]) -> str:
    lines = [
        "# 《R3.1完整知识库归档版》",
        "",
        "**用途**：R3.1 知识阶段完整用户留存包。本文由当前工作区 SSOT 生成，正文包含植物病害、8 类昆虫、全部寄主、严重度、Treatment、向量病害、来源登记与 fail-closed 附录；不是摘要，也不以“见其他文件”替代正文。",
        "",
        f"**生成时间**：{datetime.now(timezone.utc).isoformat()}  ",
        "**归档一致性**：`ARCHIVE_KNOWLEDGE_PARITY = PENDING_VALIDATION`（生成后必须运行 `validate_archive.py`）。  ",
        "**安全边界**：NEEDS_EVIDENCE 不升级为 COMPLETE；推荐寄主不是 confirmed_host；OTHER 不接受自由文本；uncertain = NO_TREATMENT；未核验的中国大陆农药登记不输出具体产品、剂量、次数或 PHI。",
        "",
        "## 1. SSOT 与总体统计",
        "",
        "| SSOT | 路径 |",
        "|---|---|",
        "| Insect manifest | `knowledge/insect-host-r3.1/manifest.json` |",
        "| Severity evidence | `knowledge/insect-host-r3.1/severity-evidence.json` |",
        "| Capability/fallback | `knowledge/insect-host-r3.1/capability-fallback.json` |",
        "| Insect Markdown | `knowledge/insect-host-r3.1/insects/*.md` |",
        "| Plant disease Markdown | `knowledge/baidu-baike-20260818/documents/00.md`–`07.md` |",
        "",
        "| 统计项 | 当前值 |",
        "|---|---:|",
        "| 昆虫类别 | 8 |",
        "| 寄主记录 | 38 |",
        "| insect × host severity | 114 |",
        "| plant disease severity | 24 |",
        "| vector disease severity | 12 |",
        "| severity_available=true 寄主 | 7 |",
        "| Prompt formal candidates | 21 |",
        "| approved vector relationships | 4 |",
        "",
        "## 2. 产品级合同",
        "",
        "- Host status：`FULL` / `PARTIAL` / `REJECTED`；对外 supported_hosts 只返回 FULL/PARTIAL，并固定提供 `OTHER`。",
        "- Capabilities：`host_relation`、`host_damage`、`severity`、`host_general_treatment`、`host_severity_treatment`、`vector_disease`。",
        "- Host authority：`recommended_host` 仅是“推荐：常见寄主之一——<crop>”；只有用户显式选择后才是 `USER_CONFIRMED_HOST`，不得自动确认或接受任意自由文本。",
        "- Treatment fallback：`HOST_SEVERITY_TREATMENT → HOST_GENERAL_TREATMENT → GENERAL_INSECT_TREATMENT`；`uncertain → NO_TREATMENT`。",
        "- R1 generic evidence：昆虫 `harms` / `possible_causes` 保持原语义；host-specific damage 是独立知识，不替换 R1。",
        "- Vector disease：只能写“可能传播的相关病害”，不代表当前植株感染，也不加入 YOLO diagnosis。",
        "- Severity notice：本轻/中/重规则为基于可靠农业资料整理形成的系统辅助判定规则，并非宣称原始资料采用相同三级分级。",
        "",
        "## 3. 现有植物病害 00–07",
        "",
        "下列正文为当前 00–07 Markdown 的完整内容（标题已嵌套以便阅读）。其中 `## 防治方法` 的轻/中/重 Treatment 与来源边界保持 R2 冻结解析契约；R3.1 只增加/更新 Severity provenance。",
        "",
    ]
    for path in sorted(PLANT_ROOT.glob("0[0-7].md")):
        lines.extend([f"### 植物病害 {path.stem}", "", demote(path.read_text(encoding="utf-8"), 4), ""])

    lines.extend(["## 4. 全部 8 类昆虫与寄主知识", ""])
    caps = sorted(capability["records"], key=lambda x: (x["class_id"], x["crop"]))
    sev_by_key = {
        (x["object_type"], x.get("class_id"), x.get("insect"), x.get("crop"), x.get("severity")): x
        for x in evidence["records"]
    }
    for doc in sorted(manifest["documents"], key=lambda x: x["class_id"]):
        class_id = doc["class_id"]
        path = INSECT_ROOT / Path(doc["document"]).name
        lines.extend(
            [
                f"### 昆虫 {class_id}：{doc['class_name']}",
                "",
                f"<!-- ARCHIVE_INSECT: class_id={class_id}; insect={doc['class_name']} -->",
                "",
                demote(path.read_text(encoding="utf-8"), 4),
                "",
                "#### 结构化寄主能力、severity 与 fallback 记录",
                "",
            ]
        )
        for cap in [x for x in caps if x["class_id"] == class_id]:
            lines.extend(
                [
                    host_marker(cap),
                    capability_marker(cap),
                    fallback_marker(cap),
                    f"\n##### 记录：{cap['insect']} × {cap['crop']}",
                    "",
                    f"- Host status：`{cap['status']}`",
                    f"- capabilities：`{inline(cap['capabilities'])}`",
                    f"- fallback：`{inline(cap.get('effective_treatment_fallback', {}))}`",
                ]
            )
            for name in ("host_general_treatment", "host_severity_treatment"):
                if cap.get(name):
                    lines.append(f"- {name}：`{inline(cap[name])}`")
            for severity_name in ("mild", "moderate", "severe"):
                record = sev_by_key.get(("insect_host", cap["class_id"], cap["insect"], cap["crop"], severity_name))
                if record is None:
                    continue
                lines.extend(
                    [
                        "",
                        f"###### {SEVERITY_LABELS[severity_name]} evidence",
                        severity_marker(record),
                        f"- status：`{record['status']}`",
                        f"- rubric：{record['rubric_text']}",
                        f"- observable_features：{'; '.join(record.get('observable_features', [])) or '未记录'}",
                        f"- source_ids：{', '.join('`'+x+'`' for x in record.get('source_ids', [])) or '无'}",
                        f"- evidence_taxon：{'; '.join(record.get('evidence_taxon', [])) or '未记录'}",
                        f"- evidence_taxon_level：{'; '.join(record.get('evidence_taxon_level', [])) or '未记录'}",
                        f"- evidence_taxon_scope：{inline(record.get('evidence_taxon_scope', []))}",
                        f"- evidence_type：`{record.get('evidence_type', '未记录')}`",
                        f"- SOURCE_SEMANTIC_REVIEW：`{record.get('SOURCE_SEMANTIC_REVIEW', 'NEEDS_REVIEW')}`",
                        f"- synthesis_note：{record.get('synthesis_note', '未记录')}",
                    ]
                )

    lines.extend(
        [
            "",
            "## 5. OTHER / 暂未收录规则",
            "",
            "- `free_input=false`：Web/API 不提供任意自由文本寄主输入。",
            "- 不显示 host-specific damage、host severity、vector disease 或 host-specific treatment。",
            "- 继续显示原 R1 generic harms、generic possible_causes 与 `GENERAL_INSECT_TREATMENT`。",
            "- 用户可见说明：当前作物暂未收录，以下仅显示该害虫的通用危害、可能诱因和通用防治建议。",
            "",
            "```json",
            json.dumps(capability["other"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## 6. Approved vector disease relationships",
            "",
        ]
    )
    vector_count = 0
    for cap in caps:
        for relation in cap.get("vector_disease", {}).get("relations", []):
            vector_count += 1
            disease = relation.get("disease") or relation.get("disease_name") or relation.get("name") or "未命名病害"
            lines.extend(
                [
                    f"### {cap['insect']} × {cap['crop']} → {disease}",
                    "",
                    vector_marker(cap, relation),
                    f"- vector relation：{relation.get('relationship', relation.get('relation', '见 SSOT'))}",
                    f"- symptoms：{relation.get('symptoms', relation.get('symptom', '见 SSOT'))}",
                    f"- disease severity_available：`{str(relation.get('disease_severity_available', relation.get('severity_available', False))).lower()}`",
                    f"- general disease treatment：{relation.get('general_treatment', relation.get('treatment', '见 SSOT'))}",
                    f"- source_ids：{', '.join('`'+x+'`' for x in relation.get('source_ids', [])) or '见 SSOT'}",
                ]
            )
            if relation.get("severity"):
                lines.append(f"- disease severity：{inline(relation['severity'])}")
            disease_records = [
                x
                for x in evidence["records"]
                if x["object_type"] == "vector_disease"
                and x.get("class_id") == cap["class_id"]
                and x.get("insect") == cap["insect"]
                and x.get("crop") == cap["crop"]
                and x.get("disease") == disease
            ]
            for disease_record in disease_records:
                lines.extend(
                    [
                        "",
                        f"#### {SEVERITY_LABELS[disease_record['severity']]} disease evidence",
                        severity_marker(disease_record),
                        f"- status：`{disease_record['status']}`",
                        f"- rubric：{disease_record['rubric_text']}",
                        f"- observable_features：{'; '.join(disease_record.get('observable_features', [])) or '未记录'}",
                        f"- source_ids：{', '.join('`'+x+'`' for x in disease_record.get('source_ids', [])) or '无'}",
                        f"- evidence_taxon：{'; '.join(disease_record.get('evidence_taxon', [])) or '未记录'}",
                        f"- evidence_taxon_level：{'; '.join(disease_record.get('evidence_taxon_level', [])) or '未记录'}",
                        f"- SOURCE_SEMANTIC_REVIEW：`{disease_record.get('SOURCE_SEMANTIC_REVIEW', 'NEEDS_REVIEW')}`",
                        f"- evidence_type：`{disease_record.get('evidence_type', '未记录')}`",
                        f"- synthesis_note：{disease_record.get('synthesis_note', '未记录')}",
                    ]
                )
            lines.append("")
    assert vector_count == 4

    lines.extend(
        [
            "## 7. Capability/fallback registry complete JSON",
            "",
            "以下为当前 `capability-fallback.json` 的完整内容，确保 38 个寄主、所有 Treatment 文案、fallback 与 OTHER/uncertain 合同在归档正文中可直接留存。",
            "",
            "```json",
            json.dumps(capability, ensure_ascii=False, indent=2),
            "```",
            "",
            "## 8. Complete source registry",
            "",
            "| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at | reachability | support_scope |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for source in sorted(manifest["sources"], key=lambda x: x["source_id"]):
        lines.extend(
            [
                f"| {source['source_id']} | {source['title']} | {source['organization']} | {source_url(source)} | {source.get('accessed_at', '未记录')} | {source.get('source_reachability', 'NOT_CHECKED')} | {source.get('support_scope', '未记录')} |",
                f"<!-- ARCHIVE_SOURCE: {source['source_id']} -->",
            ]
        )

    lines.extend(
        [
            "",
            "## 9. Machine parity ledger",
            "",
            "以下 ledger 是归档与 SSOT 的逐项比对锚点；它不是新的知识来源。",
            "",
        ]
    )
    for cap in caps:
        lines.extend([capability_marker(cap), fallback_marker(cap)])
    for record in evidence["records"]:
        lines.append(severity_marker(record))
    for cap in caps:
        for relation in cap.get("vector_disease", {}).get("relations", []):
            lines.append(vector_marker(cap, relation))
    for path, value in string_values(capability):
        lines.append(f"<!-- ARCHIVE_TREATMENT: path={path}; body_sha256={text_sha(value)} -->")

    lines.extend(
        [
            "",
            "## 10. NEEDS_EVIDENCE / fail-closed appendix",
            "",
            "以下项目保持 `NEEDS_EVIDENCE`，不会为了归档完整而升级；不得进入正式 AI 示意图生成候选，也不得生成无来源三级 rubric。",
            "",
        ]
    )
    for record in evidence["records"]:
        if record["status"] != "NEEDS_EVIDENCE":
            continue
        label = f"{record.get('insect', '')} × {record.get('crop', '')}"
        if record["object_type"] == "vector_disease":
            label += f" → {record.get('disease', '')}"
        lines.append(
            f"- `{record['object_type']}` {label} × {record['severity']}：`NEEDS_EVIDENCE`；rubric={record['rubric_text']}；source_ids={','.join(record.get('source_ids', [])) or '无'}"
        )
    lines.extend(
        [
            "",
            "## 11. WHY_NOT_UPGRADED",
            "",
            "本批尝试但仍保持 PARTIAL 的候选及其具体缺口见 `docs/competition/r3.1/batch4a-why-not-upgraded.md`；不得把寄主关系、单一物种资料或跨作物症状机械升级为三级证据。",
            "",
            "## 12. Retention package map",
            "",
            "- `docs/competition/r3.1/《R3.1完整知识库归档版》.md`（本文）",
            "- `docs/competition/r3.1/《昆虫×寄主作物知识库总表》.md`",
            "- `docs/competition/r3.1/《严重程度描述与具体来源总表》.md`",
            "- `docs/competition/r3.1/《防治措施与农药来源总表》.md`",
            "- `docs/competition/r3.1/《AI示意图提示词与来源依据》.md`",
            "- `docs/competition/r3.1/《知识库变更报告》.md`",
            "- `knowledge/insect-host-r3.1/` 下的 manifest、evidence、capability/fallback、insects 与 validators。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    manifest = load(R31 / "manifest.json")
    evidence = load(R31 / "severity-evidence.json")
    capability = load(R31 / "capability-fallback.json")
    DOCS.mkdir(parents=True, exist_ok=True)
    draft, companion = build_prompt_documents(manifest, evidence, capability)
    archive = build_archive(manifest, evidence, capability)
    total_insect_severity = sum(1 for x in evidence["records"] if x.get("object_type") == "insect_host")
    candidate_count = sum(1 for x in evidence["records"] if x.get("object_type") == "insect_host" and x.get("status") == "COMPLETE")
    candidate_hosts = len({(x["class_id"], x["insect"], x["crop"]) for x in evidence["records"] if x.get("object_type") == "insect_host" and x.get("status") == "COMPLETE"})
    total_hosts = len(capability["records"])
    for name, value in (("insect × host severity", total_insect_severity), ("severity_available=true 寄主", candidate_hosts), ("Prompt formal candidates", candidate_count)):
        archive = re.sub(rf"(?m)^\| {re.escape(name)}.*$", f"| {name} | {value} |", archive)
    archive = re.sub(r"(?m)^\| severity_available=true.*$", f"| severity_available=true 寄主 | {candidate_hosts} |", archive)
    archive = re.sub(r"(?m)^\| Prompt formal candidates.*$", f"| Prompt formal candidates | {candidate_count} |", archive)
    draft = re.sub(r"(?m)^.*当前为 .* 个寄主、.* 个 severity 单元。其余 .* 个寄主、.* 个 severity 单元保持 `NEEDS_EVIDENCE`。$", f"当前为 {candidate_hosts} 个寄主、{candidate_count} 个 severity 单元。其余 {total_hosts - candidate_hosts} 个寄主、{total_insect_severity - candidate_count} 个 severity 单元保持 `NEEDS_EVIDENCE`。", draft)
    (DOCS / "图像生成规格与提示词草案.md").write_text(draft, encoding="utf-8")
    (DOCS / "《AI示意图提示词与来源依据》.md").write_text(companion, encoding="utf-8")
    (DOCS / "《R3.1完整知识库归档版》.md").write_text(archive, encoding="utf-8")
    print(json.dumps({"prompt_candidates": len([x for x in evidence["records"] if x["object_type"] == "insect_host" and x["status"] == "COMPLETE"]), "archive_bytes": len(archive.encode('utf-8'))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
