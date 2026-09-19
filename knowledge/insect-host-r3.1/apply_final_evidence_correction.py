"""Apply the approved R3.1 Batch 4A final-evidence narrow correction.

This script is intentionally narrow and idempotent.  It updates only the two
reviewed severity pairs, three reviewed treatment records, the Ordos backup
chain, and the corresponding insect Markdown.  It does not touch runtime code.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.json"
EVIDENCE_PATH = ROOT / "severity-evidence.json"
APHID_MD = ROOT / "insects" / "09-蚜虫.md"
MOLE_MD = ROOT / "insects" / "11-蝼蛄.md"
BLISTER_MD = ROOT / "insects" / "08-芫菁.md"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def upsert_source(manifest: dict[str, Any], source: dict[str, Any]) -> None:
    matches = [item for item in manifest["sources"] if item["source_id"] == source["source_id"]]
    if len(matches) > 1:
        raise ValueError(f"duplicate source before update: {source['source_id']}")
    if matches:
        matches[0].clear()
        matches[0].update(source)
    else:
        manifest["sources"].append(source)


def evidence_record(evidence: dict[str, Any], class_id: int, crop: str, severity: str) -> dict[str, Any]:
    matches = [
        item
        for item in evidence["records"]
        if item.get("object_type") == "insect_host"
        and item.get("class_id") == class_id
        and item.get("crop") == crop
        and item.get("severity") == severity
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one evidence record: {class_id}/{crop}/{severity}; got {len(matches)}")
    return matches[0]


def treatment_record(evidence: dict[str, Any], class_id: int, crop: str) -> dict[str, Any]:
    matches = [
        item
        for item in evidence["treatment_audit"]
        if item.get("class_id") == class_id and item.get("crop") == crop
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one treatment audit: {class_id}/{crop}; got {len(matches)}")
    return matches[0]


def replace_host_subsection(text: str, crop: str, heading: str, body: str) -> str:
    host_match = re.search(rf"(?m)^### 寄主：{re.escape(crop)}\s*$", text)
    if not host_match:
        raise ValueError(f"host section not found: {crop}")
    next_host = re.search(r"(?m)^### 寄主：", text[host_match.end() :])
    host_end = host_match.end() + next_host.start() if next_host else len(text)
    block = text[host_match.start() : host_end]
    section_match = re.search(rf"(?m)^### {re.escape(heading)}\s*$", block)
    if not section_match:
        raise ValueError(f"subsection not found: {crop}/{heading}")
    next_section = re.search(r"(?m)^### (?!寄主：)", block[section_match.end() :])
    section_end = section_match.end() + next_section.start() if next_section else len(block)
    replacement = f"### {heading}\n\n{body.strip()}\n\n"
    new_block = block[: section_match.start()] + replacement + block[section_end:]
    return text[: host_match.start()] + new_block + text[host_end:]


def replace_refs(values: list[str], old: str, replacements: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        for candidate in replacements if value == old else [value]:
            if candidate not in result:
                result.append(candidate)
    return result


def replace_ref_in_host_block(text: str, crop: str, old: str, replacement: str) -> str:
    """Replace one citation only inside a named host block."""
    host_match = re.search(rf"(?m)^### 寄主：{re.escape(crop)}\s*$", text)
    if not host_match:
        raise ValueError(f"host section not found: {crop}")
    next_host = re.search(r"(?m)^### 寄主：", text[host_match.end() :])
    host_end = host_match.end() + next_host.start() if next_host else len(text)
    block = text[host_match.start() : host_end]
    if old not in block:
        return text
    block = block.replace(old, replacement)
    return text[: host_match.start()] + block + text[host_end:]


def apply_sources(manifest: dict[str, Any]) -> None:
    new_sources = [
        {
            "source_id": "R31-09-KSTATE-GREENBUG-WHEAT",
            "title": "Greenbug — wheat crop protection",
            "organization": "Kansas State University Research and Extension",
            "url": "https://entomology.k-state.edu/extension/crop-protection/wheat/greenbug.html",
            "doi": "",
            "accessed_at": "2026-09-07",
            "tier": 3,
            "support_scope": "Schizaphis graminum on wheat: tiny reddish lesions coalesce; leaves become yellow then reddish brown and die; yellow/red-brown field patches can expand.",
            "allowed_contexts": ["host:9:小麦"],
            "critical": True,
            "source_reachability": "REACHABLE_2026-09-07",
            "geographic_scope": "United States, Kansas/High Plains",
            "taxonomic_scope": "Schizaphis graminum",
            "crop_scope": "wheat",
            "reachability_note": "Official K-State Extension page opened successfully on 2026-09-07.",
        },
        {
            "source_id": "R31-09-OSU-GREENBUG-WHEAT",
            "title": "Check Your Wheat: Greenbugs Reported in Central Oklahoma",
            "organization": "Oklahoma State University Extension",
            "url": "https://extension.okstate.edu/e-pest-alerts/2026/check-your-wheat-greenbugs-reported-in-central-oklahoma",
            "doi": "",
            "accessed_at": "2026-09-07",
            "tier": 3,
            "support_scope": "Schizaphis graminum in winter wheat: early reddish/copper feeding spots; advanced yellow/orange leaves, dead tissue, stunting and expanding dead-wheat patches; heavy infestations may kill seedlings and reduce tillering.",
            "allowed_contexts": ["host:9:小麦"],
            "critical": True,
            "source_reachability": "REACHABLE_2026-09-07",
            "geographic_scope": "United States, Oklahoma/southern Great Plains",
            "taxonomic_scope": "Schizaphis graminum",
            "crop_scope": "winter wheat",
            "reachability_note": "Official Oklahoma State Extension page opened successfully on 2026-09-07.",
        },
        {
            "source_id": "R31-09-IOWA-SOY-APHID-IPM",
            "title": "Soybean Aphid",
            "organization": "Iowa State University Extension and Outreach",
            "url": "https://crops.extension.iastate.edu/encyclopedia/soybean-aphid",
            "doi": "",
            "accessed_at": "2026-09-07",
            "tier": 3,
            "support_scope": "Aphis glycines on soybean: scout every 7–10 days; lady beetles, lacewings, minute pirate bugs and parasitoids are natural enemies; preserve them by treating only when needed; Rag-gene resistant varieties may be effective with stated limitations.",
            "allowed_contexts": ["host:9:大豆"],
            "critical": True,
            "source_reachability": "REACHABLE_2026-09-07",
            "geographic_scope": "United States, Iowa/Midwest",
            "taxonomic_scope": "Aphis glycines",
            "crop_scope": "soybean",
            "reachability_note": "Official Iowa State Extension page opened successfully on 2026-09-07.",
        },
        {
            "source_id": "R31-11-HAMI-PEANUT-IPM",
            "title": "DB 6505/T 188—2024 花生病虫害绿色防控技术规程",
            "organization": "哈密市市场监督管理局；哈密市农业农村局归口；哈密市农业农机技术推广服务中心起草",
            "url": "https://www.hami.gov.cn/hami/c120122/202409/5d5342f355d34946be8dec33305b177a/files/e5e166dd845846fc9200caa1deadfe99.pdf",
            "doi": "",
            "accessed_at": "2026-09-07",
            "tier": 1,
            "support_scope": "哈密市花生绿色防控标准明确将蝼蛄列为花生主要地下害虫，并给出农业、物理、生物和化学防控框架；本知识库仅采用原则性管理语义，不转录产品、剂量或阈值。",
            "allowed_contexts": ["host:11:花生"],
            "critical": True,
            "source_reachability": "REACHABLE_2026-09-07",
            "geographic_scope": "中国新疆哈密市",
            "taxonomic_scope": "蝼蛄（标准命名地下害虫组）",
            "crop_scope": "花生",
            "reachability_note": "Official Hami government PDF opened successfully on 2026-09-07.",
        },
        {
            "source_id": "R31-08-DAZHOU-PEANUT-BACKUP",
            "title": "植保情报[2024]第14期：警惕食叶性害虫豆芫菁局部暴发危害",
            "organization": "达州市达川区人民政府／达川区农业农村局",
            "url": "https://www.dachuan.gov.cn/xxgk-show-146920.html",
            "doi": "",
            "accessed_at": "2026-09-07",
            "tier": 1,
            "support_scope": "官方植保情报记录豆芫菁成虫群聚取食嫩叶和花、重发可吃光叶片仅留叶脉，并明确要求检查花生等作物地块；用于替代 R31-08-ORDOS 的花生当前使用语义。",
            "allowed_contexts": ["class:8", "host:8:花生", "class:15"],
            "critical": True,
            "source_reachability": "REACHABLE_2026-09-07",
            "geographic_scope": "中国四川省达州市达川区",
            "taxonomic_scope": "豆芫菁（来源命名组，未提供拉丁种名）",
            "crop_scope": "花生等来源明确列出的巡查作物",
            "reachability_note": "Official Dachuan District government page opened successfully on 2026-09-07.",
        },
    ]
    for source in new_sources:
        upsert_source(manifest, source)

    ordos = next(item for item in manifest["sources"] if item["source_id"] == "R31-08-ORDOS")
    ordos["source_status"] = "DEAD_LINK_HISTORICAL_PROVENANCE_ONLY"
    ordos["archived"] = True
    ordos["current_capability_use"] = False
    ordos["verified_backup_source_ids"] = [
        "R31-08-CAU-BACKUP",
        "R31-08-BEIJING-STANDARD",
        "R31-08-NCSU-SOY",
        "R31-08-NDSU-BLISTER",
        "R31-08-DAZHOU-PEANUT-BACKUP",
    ]
    ordos["reachability_note"] = (
        "Direct URL resolves to the official 404 page. Historical indexed metadata is retained only for audit; "
        "no current capability, COMPLETE severity, TRACEABLE prompt or effective host-general treatment may cite it."
    )

    pku_rdv = next(item for item in manifest["sources"] if item["source_id"] == "R31-12-PKU-RDV")
    pku_rdv["doi"] = "https://doi.org/10.1371/journal.ppat.1009118"
    pku_rdv["source_reachability"] = "LIVE_URL_AND_STABLE_DOI_2026-09-07"
    pku_rdv["reachability_note"] = (
        "Official Peking University page opened successfully on 2026-09-07 and links the underlying PLOS Pathogens DOI."
    )


def apply_wheat_severity(evidence: dict[str, Any]) -> None:
    source_ids = ["R31-09-KSTATE-GREENBUG-WHEAT", "R31-09-OSU-GREENBUG-WHEAT"]
    scope = [
        {
            "source_id": "R31-09-KSTATE-GREENBUG-WHEAT",
            "evidence_taxon": "Schizaphis graminum",
            "evidence_taxon_level": "species",
            "geographic_scope": "United States, Kansas/High Plains",
            "crop_scope": "wheat",
            "scope_note": "同一物种绿虫蚜在小麦上的斑点合并、黄化、红褐化、叶片死亡和田间斑块扩展；不外推为所有蚜虫。",
        },
        {
            "source_id": "R31-09-OSU-GREENBUG-WHEAT",
            "evidence_taxon": "Schizaphis graminum",
            "evidence_taxon_level": "species",
            "geographic_scope": "United States, Oklahoma/southern Great Plains",
            "crop_scope": "winter wheat",
            "scope_note": "同一物种绿虫蚜在冬小麦上的早期斑点与重发坏死、矮化、死苗、分蘖减少和死株斑块；不外推为所有蚜虫。",
        },
    ]
    values = {
        "mild": (
            "小麦叶片先出现细小的红色或铜色斑点，取食点周围可见黄化。",
            ["细小红色或铜色斑点", "取食点周围黄化"],
        ),
        "moderate": (
            "斑点逐渐合并，受害叶片转黄，田间出现并扩展的黄色或红褐色受害斑块。",
            ["斑点逐渐合并", "受害叶片转黄", "黄色或红褐色田间斑块扩展"],
        ),
        "severe": (
            "叶片组织变为红褐色并死亡，植株可明显矮化；重发生时出现死苗、分蘖减少和扩展的死株斑块。",
            ["红褐色坏死叶片", "植株矮化", "死苗", "分蘖减少", "死株斑块扩展"],
        ),
    }
    for severity, (rubric, features) in values.items():
        item = evidence_record(evidence, 9, "小麦", severity)
        item.update(
            {
                "status": "COMPLETE",
                "rubric_text": rubric,
                "observable_features": features,
                "source_ids": source_ids,
                "evidence_type": "EVIDENCE_SYNTHESIZED",
                "synthesis_note": (
                    "evidence_synthesized：仅使用同一物种 Schizaphis graminum 在小麦上的来源进展；"
                    f"本档按来源明确描述的{severity}阶段可观察损伤整理，不拼接其他 cereal aphid species，"
                    "不加入虫口密度、处理阈值或产量数字。"
                ),
                "visual_feature_source_ids": {feature: source_ids for feature in features},
                "SOURCE_SEMANTIC_REVIEW": "PASS",
                "evidence_taxon": ["Schizaphis graminum"],
                "evidence_taxon_level": ["species"],
                "evidence_taxon_scope": scope,
                "source_entailment_review": {
                    "status": "PASS",
                    "automated_check": "same_species_same_host_progression_and_manual_review",
                    "note": "K-State 与 OSU 均明确指向 Schizaphis graminum × wheat；三级只整理该物种同一寄主的症状进展。",
                },
            }
        )


def fail_close_peanut_severity(evidence: dict[str, Any]) -> None:
    reasons = {
        "mild": "现有资料确认花生属于可受蝼蛄危害的作物，但未给出花生专属轻度损伤边界。",
        "moderate": "现有资料未提供花生上从局部根区受害扩展到中度植株后果的专属进展。",
        "severe": "现有资料中的少根、死斑或植株死亡是蝼蛄一般损伤描述，不能直接作为花生专属重度结论。",
    }
    scope = [
        {
            "source_id": "R31-11-UFL",
            "evidence_taxon": "mole cricket source-named group",
            "evidence_taxon_level": "source_named_group",
            "geographic_scope": "United States, Florida",
            "crop_scope": "peanut is listed among affected plants; damage progression is described generally",
            "scope_note": "来源确认花生寄主关系，但损伤进展未逐句限定为花生，因此不足以形成花生三级严重度。",
        },
        {
            "source_id": "R31-11-HAMI-PEANUT-IPM",
            "evidence_taxon": "蝼蛄（标准命名地下害虫组）",
            "evidence_taxon_level": "source_named_group",
            "geographic_scope": "中国新疆哈密市",
            "crop_scope": "花生",
            "scope_note": "标准直接支持花生×蝼蛄关系和防治框架，但没有花生专属三级症状进展。",
        },
    ]
    for severity in ("mild", "moderate", "severe"):
        item = evidence_record(evidence, 11, "花生", severity)
        item.update(
            {
                "status": "NEEDS_EVIDENCE",
                "rubric_text": reasons[severity],
                "observable_features": [],
                "source_ids": ["R31-11-UFL", "R31-11-HAMI-PEANUT-IPM"],
                "evidence_type": "EVIDENCE_SYNTHESIZED",
                "synthesis_note": (
                    f"evidence_synthesized：{reasons[severity]}经限定范围检索后仍缺少 same-host damage progression；"
                    "严格 fail closed，不将一般蝼蛄损伤转写为花生三级。"
                ),
                "visual_feature_source_ids": {},
                "SOURCE_SEMANTIC_REVIEW": "NEEDS_REVIEW",
                "evidence_taxon": ["mole cricket source-named group", "蝼蛄（标准命名地下害虫组）"],
                "evidence_taxon_level": ["source_named_group"],
                "evidence_taxon_scope": scope,
                "source_entailment_review": {
                    "status": "NEEDS_REVIEW",
                    "automated_check": "host_relation_present_but_same_host_progression_missing",
                    "note": "来源支持寄主关系/管理，不足以支持花生专属 mild→moderate→severe。",
                },
            }
        )


def remove_ordos_from_current_evidence(evidence: dict[str, Any]) -> None:
    replacements = {
        "大豆": ["R31-08-NCSU-SOY"],
        "马铃薯": ["R31-08-NDSU-BLISTER"],
        "花生": ["R31-08-DAZHOU-PEANUT-BACKUP"],
        "甜菜": ["R31-08-NDSU-BLISTER"],
        "苜蓿": ["R31-08-NDSU-BLISTER"],
    }
    for item in evidence["records"]:
        if item.get("object_type") != "insect_host" or item.get("class_id") != 8:
            continue
        if "R31-08-ORDOS" not in item.get("source_ids", []):
            continue
        replacement = replacements[item["crop"]]
        item["source_ids"] = replace_refs(item["source_ids"], "R31-08-ORDOS", replacement)
        for feature, ids in list(item.get("visual_feature_source_ids", {}).items()):
            item["visual_feature_source_ids"][feature] = replace_refs(ids, "R31-08-ORDOS", replacement)
        item["evidence_taxon_scope"] = [
            scope for scope in item.get("evidence_taxon_scope", []) if scope.get("source_id") != "R31-08-ORDOS"
        ]
        if item["crop"] == "花生":
            item["evidence_taxon"] = ["豆芫菁（达川区来源命名组）"]
            item["evidence_taxon_level"] = ["source_named_group"]
            item["evidence_taxon_scope"].append(
                {
                    "source_id": "R31-08-DAZHOU-PEANUT-BACKUP",
                    "evidence_taxon": "豆芫菁（达川区来源命名组）",
                    "evidence_taxon_level": "source_named_group",
                    "scope_note": "达川区官方植保情报明确要求检查花生地块，但未提供可用于三级分级的花生专属进展。",
                }
            )
        elif not item["evidence_taxon_scope"]:
            source_id = replacement[0]
            taxon = "Epicauta funebris; Epicauta vittata" if item["crop"] == "大豆" else "Meloidae"
            level = "species" if item["crop"] == "大豆" else "family"
            item["evidence_taxon"] = [taxon]
            item["evidence_taxon_level"] = [level]
            item["evidence_taxon_scope"].append(
                {
                    "source_id": source_id,
                    "evidence_taxon": taxon,
                    "evidence_taxon_level": level,
                    "scope_note": "当前记录仅采用可访问替代来源明确支持的分类与寄主范围。",
                }
            )

    for item in evidence["treatment_audit"]:
        if item.get("class_id") != 8 or "R31-08-ORDOS" not in item.get("host_specific_source_ids", []):
            continue
        replacement = replacements[item["crop"]]
        item["host_specific_source_ids"] = replace_refs(item["host_specific_source_ids"], "R31-08-ORDOS", replacement)
        item["host_specific_evidence"] = True
        item["SOURCE_SEMANTIC_REVIEW"] = "PASS"
        item["entailment_review"] = "当前作物级管理语义由可访问替代来源直接支持；R31-08-ORDOS 仅保留历史审计元数据。"
        item["source_entailment_review"] = {
            "status": "PASS",
            "automated_check": "live_host_specific_source_required",
            "note": item["entailment_review"],
            "clause_source_map": [
                {"concept": "host_specific_monitoring_or_management", "source_ids": replacement}
            ],
        }


def apply_treatment_audits(evidence: dict[str, Any]) -> None:
    soy = treatment_record(evidence, 9, "大豆")
    soy["host_specific_source_ids"] = ["R31-09-HEILONGJIANG-SOY", "R31-09-IOWA-SOY-APHID-IPM"]
    soy["host_specific_evidence"] = True
    soy["SOURCE_SEMANTIC_REVIEW"] = "PASS"
    soy["entailment_review"] = "大豆蚜 host-specific 条款已逐句映射；合理轮作、食蚜蝇和蚜茧蜂的旧表述已删除。"
    soy["source_entailment_review"] = {
        "status": "PASS",
        "automated_check": "normalized_concept_pattern_and_clause_source_map",
        "note": soy["entailment_review"],
        "clause_source_map": [
            {"concept": "scouting_every_7_10_days", "source_ids": ["R31-09-IOWA-SOY-APHID-IPM"]},
            {"concept": "lady_beetles", "source_ids": ["R31-09-IOWA-SOY-APHID-IPM"]},
            {"concept": "lacewings", "source_ids": ["R31-09-IOWA-SOY-APHID-IPM"]},
            {"concept": "minute_pirate_bugs", "source_ids": ["R31-09-IOWA-SOY-APHID-IPM"]},
            {"concept": "parasitoids_generic", "source_ids": ["R31-09-IOWA-SOY-APHID-IPM"]},
            {"concept": "resistant_variety", "source_ids": ["R31-09-IOWA-SOY-APHID-IPM"]},
        ],
        "removed_clauses": ["合理轮作", "食蚜蝇", "蚜茧蜂"],
    }

    potato = treatment_record(evidence, 11, "马铃薯")
    potato["host_specific_source_ids"] = ["R31-11-NCSU-POTATO-MOLECRICKET"]
    potato["host_specific_evidence"] = True
    potato["SOURCE_SEMANTIC_REVIEW"] = "PASS"
    potato["entailment_review"] = "NCSU 直接覆盖 Neoscapteriscus borellii × potato 的掘道/根块茎受害与播前处理方向。"
    potato["source_entailment_review"] = {
        "status": "PASS",
        "automated_check": "direct_crop_taxon_source_required",
        "note": potato["entailment_review"],
        "clause_source_map": [
            {"concept": "potato_damage_monitoring", "source_ids": ["R31-11-NCSU-POTATO-MOLECRICKET"]},
            {"concept": "preplant_management_direction", "source_ids": ["R31-11-NCSU-POTATO-MOLECRICKET"]},
        ],
    }

    peanut = treatment_record(evidence, 11, "花生")
    peanut["host_specific_source_ids"] = ["R31-11-HAMI-PEANUT-IPM"]
    peanut["host_specific_evidence"] = True
    peanut["SOURCE_SEMANTIC_REVIEW"] = "PASS"
    peanut["entailment_review"] = "哈密市花生绿色防控标准直接将蝼蛄列为花生主要地下害虫并提供作物级综合防控框架。"
    peanut["source_entailment_review"] = {
        "status": "PASS",
        "automated_check": "direct_crop_pest_standard_required",
        "note": peanut["entailment_review"],
        "clause_source_map": [
            {"concept": "peanut_mole_cricket_monitoring", "source_ids": ["R31-11-HAMI-PEANUT-IPM"]},
            {"concept": "peanut_integrated_management", "source_ids": ["R31-11-HAMI-PEANUT-IPM"]},
        ],
    }


def apply_markdown() -> None:
    aphid = APHID_MD.read_text(encoding="utf-8")
    aphid = replace_host_subsection(
        aphid,
        "大豆",
        "防治方法",
        """#### 预防与监测

- 生育期建议每 7–10 天系统巡查，早期重点看新生长部位，随后扩展到全田；仅依据当前行动条件决定是否处理。[R31-09-IOWA-SOY-APHID-IPM][R31-09-HEILONGJIANG-SOY]

#### 生物与物理

- 保护瓢虫、草蛉、小花蝽等捕食性天敌以及寄生性天敌；频繁发生地块可评估抗大豆蚜 Rag 品种的当地适用性。[R31-09-IOWA-SOY-APHID-IPM]

#### 化学防治边界

- 不提供大豆蚜产品、剂量或抗性方案；按照中国当前登记和当地指导进行标签化决策。
- 【风险提示】必须核对登记作物和靶标、剂量、次数、安全间隔、PPE、抗性轮换及对天敌/授粉昆虫的影响；不得用其他作物登记信息替代。[R31-GLOBAL-IPM-MOA]""",
    )
    aphid = replace_host_subsection(
        aphid,
        "小麦",
        "当前作物受害表现",
        "- 本三级只描述绿虫蚜 `Schizaphis graminum` 在小麦上的已审核记录：先出现红色/铜色小斑，随后斑点合并并黄化或红褐化，重发生可见坏死、矮化、死苗、分蘖减少及死株斑块扩展；不外推为所有蚜虫。[R31-09-KSTATE-GREENBUG-WHEAT][R31-09-OSU-GREENBUG-WHEAT]",
    )
    wheat_severity = """#### 轻度

- 状态：COMPLETE
- 最终 rubric：小麦叶片先出现细小的红色或铜色斑点，取食点周围可见黄化。
- 可观察特征：细小红色或铜色斑点；取食点周围黄化
- 证据类型：EVIDENCE_SYNTHESIZED
- evidence_taxon：Schizaphis graminum
- evidence_taxon_level：species
- evidence_taxon_scope：K-State 与 OSU 均明确指向绿虫蚜 `Schizaphis graminum` × wheat；地理范围为美国大平原小麦生产资料，不外推为所有蚜虫。
- SOURCE_SEMANTIC_REVIEW：PASS
- synthesis_note：evidence_synthesized：只采用同一物种、同一寄主的早期取食斑点记录，不拼接其他 cereal aphid species。
- 来源：[R31-09-KSTATE-GREENBUG-WHEAT][R31-09-OSU-GREENBUG-WHEAT]

#### 中度

- 状态：COMPLETE
- 最终 rubric：斑点逐渐合并，受害叶片转黄，田间出现并扩展的黄色或红褐色受害斑块。
- 可观察特征：斑点逐渐合并；受害叶片转黄；黄色或红褐色田间斑块扩展
- 证据类型：EVIDENCE_SYNTHESIZED
- evidence_taxon：Schizaphis graminum
- evidence_taxon_level：species
- evidence_taxon_scope：K-State 与 OSU 均明确指向绿虫蚜 `Schizaphis graminum` × wheat；地理范围为美国大平原小麦生产资料，不外推为所有蚜虫。
- SOURCE_SEMANTIC_REVIEW：PASS
- synthesis_note：evidence_synthesized：只采用同一物种、同一寄主的斑点合并、黄化/红褐化和田间斑块扩展记录。
- 来源：[R31-09-KSTATE-GREENBUG-WHEAT][R31-09-OSU-GREENBUG-WHEAT]

#### 重度

- 状态：COMPLETE
- 最终 rubric：叶片组织变为红褐色并死亡，植株可明显矮化；重发生时出现死苗、分蘖减少和扩展的死株斑块。
- 可观察特征：红褐色坏死叶片；植株矮化；死苗；分蘖减少；死株斑块扩展
- 证据类型：EVIDENCE_SYNTHESIZED
- evidence_taxon：Schizaphis graminum
- evidence_taxon_level：species
- evidence_taxon_scope：K-State 与 OSU 均明确指向绿虫蚜 `Schizaphis graminum` × wheat；地理范围为美国大平原小麦生产资料，不外推为所有蚜虫。
- SOURCE_SEMANTIC_REVIEW：PASS
- synthesis_note：evidence_synthesized：只采用同一物种、同一寄主的坏死、矮化、死苗、分蘖减少和死株斑块记录；不加入来源阈值数字。
- 来源：[R31-09-KSTATE-GREENBUG-WHEAT][R31-09-OSU-GREENBUG-WHEAT]"""
    aphid = replace_host_subsection(aphid, "小麦", "严重程度", wheat_severity)
    APHID_MD.write_text(aphid, encoding="utf-8")

    mole = MOLE_MD.read_text(encoding="utf-8")
    mole = replace_host_subsection(
        mole,
        "花生",
        "当前作物受害表现",
        "- UF/IFAS 明确列出花生可受蝼蛄危害；哈密市花生标准也把蝼蛄列为主要地下害虫。但现有来源未提供花生专属 mild→moderate→severe 损伤进展，因此严重度保持 NEEDS_EVIDENCE。[R31-11-UFL][R31-11-HAMI-PEANUT-IPM]",
    )
    peanut_severity = """#### 轻度

- 状态：NEEDS_EVIDENCE
- 当前结论：现有资料确认花生属于可受蝼蛄危害的作物，但未给出花生专属轻度损伤边界。
- evidence_taxon：mole cricket source-named group；蝼蛄（标准命名地下害虫组）
- evidence_taxon_level：source_named_group
- SOURCE_SEMANTIC_REVIEW：NEEDS_REVIEW
- synthesis_note：evidence_synthesized：寄主关系和防治资料不能替代 same-host damage progression；不生成轻度 Prompt。
- 来源：[R31-11-UFL][R31-11-HAMI-PEANUT-IPM]

#### 中度

- 状态：NEEDS_EVIDENCE
- 当前结论：现有资料未提供花生上从局部根区受害扩展到中度植株后果的专属进展。
- evidence_taxon：mole cricket source-named group；蝼蛄（标准命名地下害虫组）
- evidence_taxon_level：source_named_group
- SOURCE_SEMANTIC_REVIEW：NEEDS_REVIEW
- synthesis_note：evidence_synthesized：一般蝼蛄损伤不能直接改写为花生中度；不生成中度 Prompt。
- 来源：[R31-11-UFL][R31-11-HAMI-PEANUT-IPM]

#### 重度

- 状态：NEEDS_EVIDENCE
- 当前结论：现有资料中的少根、死斑或植株死亡是蝼蛄一般损伤描述，不能直接作为花生专属重度结论。
- evidence_taxon：mole cricket source-named group；蝼蛄（标准命名地下害虫组）
- evidence_taxon_level：source_named_group
- SOURCE_SEMANTIC_REVIEW：NEEDS_REVIEW
- synthesis_note：evidence_synthesized：花生专属重度进展未闭环；不生成重度 Prompt。
- 来源：[R31-11-UFL][R31-11-HAMI-PEANUT-IPM]"""
    mole = replace_host_subsection(mole, "花生", "严重程度", peanut_severity)
    mole = replace_host_subsection(
        mole,
        "花生",
        "防治方法",
        """#### 预防与监测

- 将蝼蛄作为花生主要地下害虫之一开展播前和苗期调查，结合土壤、缺苗点和虫体鉴定决定是否干预。[R31-11-HAMI-PEANUT-IPM]

#### 生物与物理

- 按花生绿色防控标准优先采用农业、物理和生物措施的综合组合；不把标准中的用药数字固化到本知识库。[R31-11-HAMI-PEANUT-IPM]

#### 化学防治边界

- 来源支持花生地下害虫的作物级管理方向，但本库不转录具体产品、剂量或施用方法；必须核对中国当前登记。
- 【风险提示】核对标签、剂量、次数、安全间隔、PPE、抗性轮换、授粉昆虫和水生环境，不得跨作物换算。[R31-GLOBAL-IPM-MOA]""",
    )
    mole = replace_host_subsection(
        mole,
        "马铃薯",
        "防治方法",
        """#### 预防与监测

- 播前和苗期检查土壤、根区和块茎附近掘道、幼苗拔起及根/块茎受害，并先确认来源物种 `Neoscapteriscus borellii` 的适用范围。[R31-11-NCSU-POTATO-MOLECRICKET]

#### 生物与物理

- NCSU 资料支持播前管理方向；本库仅结合虫体鉴定和原则性综合防控，不扩写来源未提供的马铃薯专属措施。[R31-11-NCSU-POTATO-MOLECRICKET][R31-GLOBAL-IPM-FAO]

#### 化学防治边界

- NCSU 指向播前处理，但不得把美国化学建议直接迁移到中国；仅在中国当前登记明确覆盖马铃薯×蝼蛄时按标签执行。
- 【风险提示】不得以其他根部害虫药剂或剂型换算；严格执行标签剂量、次数、安全间隔、PPE、抗性轮换和环境要求。[R31-GLOBAL-IPM-MOA]""",
    )
    MOLE_MD.write_text(mole, encoding="utf-8")

    blister = BLISTER_MD.read_text(encoding="utf-8")
    blister = re.sub(
        r"(?ms)(## 推荐寄主\s+).*?(?=\n## 已审核寄主)",
        r"\1\n- 推荐：常见寄主之一——大豆。已审核资料记录代表性芫菁种类在大豆上取食叶片；该推荐不代表自动确认，也不外推为整个芫菁科。[R31-08-NCSU-SOY][R31-08-CAU-BACKUP]\n",
        blister,
        count=1,
    )
    for crop, replacement in {
        "大豆": "R31-08-NCSU-SOY",
        "马铃薯": "R31-08-NDSU-BLISTER",
        "花生": "R31-08-DAZHOU-PEANUT-BACKUP",
        "甜菜": "R31-08-NDSU-BLISTER",
        "苜蓿": "R31-08-NDSU-BLISTER",
    }.items():
        blister = replace_ref_in_host_block(blister, crop, "R31-08-ORDOS", replacement)
    # The historical source may remain only in registry/archive audit prose, never
    # in a current insect Markdown capability or treatment citation.
    if "R31-08-ORDOS" in blister:
        raise ValueError("active R31-08-ORDOS citation remains in 08-芫菁.md")
    BLISTER_MD.write_text(blister, encoding="utf-8")


def main() -> None:
    manifest = read_json(MANIFEST_PATH)
    evidence = read_json(EVIDENCE_PATH)
    apply_sources(manifest)
    apply_wheat_severity(evidence)
    fail_close_peanut_severity(evidence)
    remove_ordos_from_current_evidence(evidence)
    apply_treatment_audits(evidence)
    apply_markdown()

    manifest["closure"] = "Batch 4A — Final Evidence Review Narrow Correction"
    manifest["final_evidence_sprint"]["status"] = "PASS"
    manifest["final_evidence_correction"] = {
        "status": "PASS",
        "date": "2026-09-07",
        "scope": [
            "aphid:wheat:severity",
            "mole_cricket:peanut:severity_and_treatment",
            "aphid:soybean:treatment",
            "mole_cricket:potato:treatment",
            "R31-08-ORDOS:resilience",
            "validator:false_negative",
        ],
        "ai_images_generated": False,
        "runtime_product_logic_changed": False,
    }
    evidence["closure"] = "Batch 4A — Final Evidence Review Narrow Correction"
    evidence["sprint"]["status"] = "PASS"
    evidence["sprint"]["upgraded_hosts"] = [
        item
        for item in evidence["sprint"].get("upgraded_hosts", [])
        if not (item.get("class_id") == 11 and item.get("crop") == "花生")
    ]
    evidence["final_evidence_correction"] = {
        "status": "PASS",
        "aphid_wheat": "SAME_SPECIES_CHAIN_REBUILT",
        "mole_cricket_peanut_severity": "FAIL_CLOSED",
        "soybean_aphid_treatment": "CLAUSE_LEVEL_PROVENANCE_REBUILT",
        "mole_cricket_potato_treatment": "DIRECT_SOURCE_ADDED",
        "ordos_current_dependency": False,
    }

    write_json(MANIFEST_PATH, manifest)
    write_json(EVIDENCE_PATH, evidence)
    print(
        json.dumps(
            {
                "status": "APPLIED",
                "sources": len(manifest["sources"]),
                "wheat_complete": sum(
                    item.get("class_id") == 9 and item.get("crop") == "小麦" and item.get("status") == "COMPLETE"
                    for item in evidence["records"]
                ),
                "peanut_needs_evidence": sum(
                    item.get("class_id") == 11 and item.get("crop") == "花生" and item.get("status") == "NEEDS_EVIDENCE"
                    for item in evidence["records"]
                ),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
