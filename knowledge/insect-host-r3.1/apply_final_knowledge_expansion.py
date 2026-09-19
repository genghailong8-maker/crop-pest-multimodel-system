"""Apply the bounded 2026-09-08 final R3.1 knowledge expansion.

This migration upgrades only leafhopper x tea.  It is intentionally
idempotent and does not touch runtime product logic.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.json"
EVIDENCE_PATH = ROOT / "severity-evidence.json"
LEAFHOPPER_PATH = ROOT / "insects" / "12-叶蝉科.md"
TAXON = "Matsumurasca (Matsumurasca) onukii (Matsuda, 1952)"
SOURCE_TAXON = "Empoasca (Matsumurasca) onukii Matsuda"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source(
    source_id: str,
    title: str,
    organization: str,
    url: str,
    *,
    doi: str = "",
    tier: int,
    support_scope: str,
    reachability: str,
    geographic_scope: str,
    taxonomic_scope: str,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "title": title,
        "organization": organization,
        "url": url,
        "doi": doi,
        "accessed_at": "2026-09-08",
        "tier": tier,
        "support_scope": support_scope,
        "allowed_contexts": ["host:12:茶"],
        "source_reachability": reachability,
        "critical": True,
        "reachability_note": "Live official URL or stable DOI verified during the bounded final knowledge expansion on 2026-09-08.",
        "geographic_scope": geographic_scope,
        "taxonomic_scope": taxonomic_scope,
        "crop_scope": "Camellia sinensis (茶)",
    }


NEW_SOURCES = [
    source(
        "R31-12-ANKANG-TEA-DAMAGE",
        "茶小绿叶蝉防治技术",
        "安康市农业技术推广中心／安康市农业农村局",
        "https://nyj.ankang.gov.cn/Content-2290998.html",
        tier=1,
        support_scope="茶小绿叶蝉在茶树上的轻度与严重田间受害表现：芽小、节间缩短或生长停止，以及大面积叶缘焦枯和茶园黄色火烧状。",
        reachability="LIVE_URL_2026-09-08",
        geographic_scope="中国大陆（陕西茶区）",
        taxonomic_scope="茶小绿叶蝉（来源命名种组）",
    ),
    source(
        "R31-12-FRONTIERS-ONUKII",
        "Fumigant activity and transcriptomic analysis of two plant essential oils against the tea green leafhopper, Empoasca onukii Matsuda",
        "Frontiers in Physiology",
        "https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2023.1217608/full",
        doi="10.3389/fphys.2023.1217608",
        tier=2,
        support_scope="Empoasca (Matsumurasca) onukii 在茶树幼嫩芽叶取食和产卵，可阻断营养运输并使芽叶生长停止；严重时叶缘与叶尖红褐并萎缩。",
        reachability="STABLE_DOI_2026-09-08",
        geographic_scope="中国茶树研究语境",
        taxonomic_scope=SOURCE_TAXON,
    ),
    source(
        "R31-12-WEIHAI-TEA-DAMAGE",
        "山东早春茶树主要病虫害绿色防控技术",
        "威海市农业局／山东省现代农业产业技术体系茶叶创新团队",
        "https://nyj.weihai.gov.cn/art/2018/4/12/art_24524_1327014.html",
        tier=1,
        support_scope="小贯小绿叶蝉危害茶树嫩梢的连续可见表现：凋萎、叶脉变红、叶尖叶缘变红以至枯焦，以及节间短缩和质地变脆。",
        reachability="LIVE_URL_2026-09-08",
        geographic_scope="中国大陆（山东茶区）",
        taxonomic_scope="茶小绿叶蝉（来源命名种组）",
    ),
    source(
        "R31-12-PLOS-ONUKII-TAXON",
        "Clarification of the Identity of the Tea Green Leafhopper Based on Morphological Comparison between Chinese and Japanese Specimens",
        "PLOS ONE",
        "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0139202",
        doi="10.1371/journal.pone.0139202",
        tier=2,
        support_scope="中国茶园茶小绿叶蝉的种级鉴定与 Empoasca (Matsumurasca) onukii 名称范围。",
        reachability="STABLE_DOI_2026-09-08",
        geographic_scope="中国大陆茶园",
        taxonomic_scope=SOURCE_TAXON,
    ),
    source(
        "R31-12-CAAS-ONUKII-TAXON",
        "我国茶小绿叶蝉种名历史问题研究取得重要进展",
        "中国农业科学院",
        "https://www.caas.cn/xwzx/kyhd/f9e8fa57997145a4977e2fa60b614094.htm",
        tier=1,
        support_scope="中国茶小绿叶蝉应使用 Empoasca (Matsumurasca) onukii 的分类学范围说明。",
        reachability="LIVE_URL_2026-09-08",
        geographic_scope="中国大陆",
        taxonomic_scope=SOURCE_TAXON,
    ),
    source(
        "R31-12-JTS-ONUKII-TAXON-2026",
        "陕西茶区叶蝉及蜡蝉类害虫学名厘定及中国茶树小绿叶蝉学名更正",
        "《茶叶科学》／西北农林科技大学",
        "https://www.tea-science.com/CN/Y2026/V46/I1/101",
        doi="10.13305/j.cnki.jts.2026.01.007",
        tier=2,
        support_scope="建议将中国茶树小绿叶蝉学名统一更正为 Matsumurasca (Matsumurasca) onukii (Matsuda, 1952)，并明确其与 Empoasca (Matsumurasca) onukii Matsuda, 1952 的名称关系。",
        reachability="STABLE_DOI_2026-09-08",
        geographic_scope="中国大陆茶区",
        taxonomic_scope=TAXON,
    ),
]


SEVERITY_DATA = {
    "mild": {
        "rubric_text": "叶脉开始变红，叶尖和叶缘出现变红的可见受害表现。",
        "observable_features": ["叶脉变红", "叶尖和叶缘变红"],
        "source_ids": ["R31-12-WEIHAI-TEA-DAMAGE"],
        "visual_feature_source_ids": {
            "叶脉变红": ["R31-12-WEIHAI-TEA-DAMAGE"],
            "叶尖和叶缘变红": ["R31-12-WEIHAI-TEA-DAMAGE"],
        },
        "synthesis_note": "evidence_synthesized：中国官方茶树技术资料记录叶脉、叶尖和叶缘由变红发展至枯焦；本档只将变红作为起始可见阶段，不引入虫口或比例阈值。",
    },
    "moderate": {
        "rubric_text": "芽叶出现凋萎，节间短缩，受害芽叶质地变脆，表明嫩梢生长已受阻。",
        "observable_features": ["芽叶凋萎", "节间短缩", "受害芽叶质地变脆"],
        "source_ids": ["R31-12-WEIHAI-TEA-DAMAGE"],
        "visual_feature_source_ids": {
            "芽叶凋萎": ["R31-12-WEIHAI-TEA-DAMAGE"],
            "节间短缩": ["R31-12-WEIHAI-TEA-DAMAGE"],
            "受害芽叶质地变脆": ["R31-12-WEIHAI-TEA-DAMAGE"],
        },
        "synthesis_note": "evidence_synthesized：中国官方茶树技术资料同时记录茶树生长受阻、芽叶凋萎、节间短缩和质地变脆；据此整理生长受抑阶段，不创造阈值。",
    },
    "severe": {
        "rubric_text": "叶尖和叶缘转为红褐并焦枯、萎缩，茶园可出现大面积发黄或火烧状受害景象。",
        "observable_features": ["叶尖和叶缘红褐焦枯", "受害芽叶萎缩", "茶园大面积发黄或火烧状"],
        "source_ids": ["R31-12-FRONTIERS-ONUKII", "R31-12-WEIHAI-TEA-DAMAGE", "R31-12-ANKANG-TEA-DAMAGE"],
        "visual_feature_source_ids": {
            "叶尖和叶缘红褐焦枯": ["R31-12-FRONTIERS-ONUKII", "R31-12-WEIHAI-TEA-DAMAGE", "R31-12-ANKANG-TEA-DAMAGE"],
            "受害芽叶萎缩": ["R31-12-FRONTIERS-ONUKII"],
            "茶园大面积发黄或火烧状": ["R31-12-ANKANG-TEA-DAMAGE"],
        },
        "synthesis_note": "evidence_synthesized：同一种级 taxon×茶树论文记录叶尖/叶缘红褐和萎缩，官方农技资料直接描述严重时大面积叶缘焦枯及茶园黄色火烧状；据此整理明显组织损伤阶段。",
    },
}


OLD_TEA = """### 寄主：茶

- 寄主关系：茶小绿叶蝉在茶树嫩梢和叶片上刺吸危害，属于中国农业技术资料直接支持的关系。[R31-12-TEA]

### 当前作物受害表现

- 重点观察嫩梢、嫩叶失绿、叶片卷曲或生长受抑，结合虫体跳动、叶背位置和田间监测结果识别；不得将所有叶蝉物种等同。[R31-12-TEA]

### 严重程度

#### 轻度

- 状态：NEEDS_EVIDENCE（来源支持对象和监测，但未提供本项目茶树三级严重度）。可记录少量嫩梢叶背虫体和局部失绿。[R31-12-TEA]

#### 中度

- 状态：NEEDS_EVIDENCE。可记录多个嫩梢/叶片出现失绿、卷曲或生长受抑；需按当地茶园指标复核。[R31-12-TEA]

#### 重度

- 状态：NEEDS_EVIDENCE。可记录虫群扩大、嫩梢持续受害和明显生长受抑；不得从图片直接推断茶叶产量损失。[R31-12-TEA]
"""


NEW_TEA = """### 寄主：茶

- 寄主关系：本组合只表达叶蝉科识别类别中已审核代表性种类——茶小绿叶蝉在茶树上的记录，不外推为所有叶蝉科成员。[R31-12-TEA][R31-12-PLOS-ONUKII-TAXON][R31-12-CAAS-ONUKII-TAXON]
- 证据 taxon：`Matsumurasca (Matsumurasca) onukii (Matsuda, 1952)`；来源使用同物异名 `Empoasca (Matsumurasca) onukii Matsuda`。

### 当前作物受害表现

- 可观察叶脉、叶尖和叶缘变红；随受害加重，芽叶可凋萎、节间短缩、质地变脆，并发展为叶尖/叶缘红褐焦枯和萎缩。[R31-12-WEIHAI-TEA-DAMAGE][R31-12-FRONTIERS-ONUKII][R31-12-ANKANG-TEA-DAMAGE]

### 严重程度

> 本轻/中/重规则为基于可靠农业资料整理形成的系统辅助判定规则，并非宣称原始资料本身采用相同三级分级。

#### 轻度

- 状态：COMPLETE（EVIDENCE_SYNTHESIZED）。叶脉开始变红，叶尖和叶缘出现变红的可见受害表现。[R31-12-WEIHAI-TEA-DAMAGE]

#### 中度

- 状态：COMPLETE（EVIDENCE_SYNTHESIZED）。芽叶出现凋萎，节间短缩，受害芽叶质地变脆，表明嫩梢生长已受阻。[R31-12-WEIHAI-TEA-DAMAGE]

#### 重度

- 状态：COMPLETE（EVIDENCE_SYNTHESIZED）。叶尖和叶缘转为红褐并焦枯、萎缩，茶园可出现大面积发黄或火烧状受害景象。[R31-12-FRONTIERS-ONUKII][R31-12-WEIHAI-TEA-DAMAGE][R31-12-ANKANG-TEA-DAMAGE]

### 防治方法

#### 预防与监测

- 结合灯诱、田间巡查和嫩梢叶背调查，记录虫口、天敌、茶园生育期与气象条件，按当地技术方案决定干预。[R31-12-TEA][R31-GLOBAL-IPM-MOA]

#### 生物与物理

- 保护天敌、清除桥梁寄主、采用物理诱控和合理修剪/田间管理，减少无阈值用药。[R31-12-TEA][R31-GLOBAL-IPM-FAO]

#### 化学防治边界

- 不提供茶小绿叶蝉产品、剂量、剂型、次数或安全间隔；必须核对中国当前茶树+目标叶蝉登记和当地指导。
- 【风险提示】严格执行标签的作物/靶标、剂量、次数、安全间隔、PPE、抗性轮换、授粉昆虫和环境保护要求，不得跨作物换算。[R31-GLOBAL-IPM-MOA]
"""


def main() -> None:
    manifest = load(MANIFEST_PATH)
    evidence = load(EVIDENCE_PATH)
    source_by_id = {item["source_id"]: item for item in manifest["sources"]}
    source_by_id.pop("R31-12-FORESTRY-TEA-DAMAGE", None)
    source_by_id.pop("R31-12-FASE-ONUKII", None)
    for item in NEW_SOURCES:
        source_by_id[item["source_id"]] = item
    manifest["sources"] = list(source_by_id.values())

    taxon_by_source = {item["source_id"]: item for item in manifest.get("taxonomic_scope", [])}
    taxon_by_source.pop("R31-12-FORESTRY-TEA-DAMAGE", None)
    taxon_by_source.pop("R31-12-FASE-ONUKII", None)
    for item in NEW_SOURCES:
        taxon_by_source[item["source_id"]] = {
            "source_id": item["source_id"],
            "evidence_taxon": item["taxonomic_scope"],
            "evidence_taxon_level": "species",
            "scope_note": "仅支持茶树上已审核的茶小绿叶蝉物种范围；不外推为叶蝉科所有成员。",
            "class_id": 12,
            "insect": "叶蝉科",
        }
    taxon_by_source["R31-12-TEA"].update(
        evidence_taxon="茶小绿叶蝉（来源命名种组）",
        evidence_taxon_level="source_named_group",
        scope_note="全国农技中心资料以茶小绿叶蝉命名；精确种级范围由 PLOS 与中国农科院分类学来源补充限定。",
    )
    manifest["taxonomic_scope"] = list(taxon_by_source.values())
    manifest["closure"] = "Final Documentation Consistency + Final Controlled Knowledge Expansion"
    manifest["final_knowledge_expansion"] = {
        "status": "COMPLETE",
        "date": "2026-09-08",
        "leafhopper_candidates_researched": ["茶", "水稻", "芒果"],
        "new_full_hosts": [{"class_id": 12, "insect": "叶蝉科", "crop": "茶"}],
        "not_upgraded": [
            {"class_id": 12, "crop": "水稻", "reason": "高质量结果主要支持电光叶蝉传播水稻病害，未形成同一 taxon×水稻的直接取食三档进程；传毒症状不与害虫直接受害混合。"},
            {"class_id": 12, "crop": "芒果", "reason": "官方标准与论文可支持叶蝉在嫩梢、花序和幼果取食及落花/落果后果，但未提供同一 taxon×芒果的三档损伤进程。"},
        ],
        "knowledge_expansion_stopped": True,
        "stop_reason": "茶小绿叶蝉已以同一种级 taxon×茶树证据闭环；后续高价值叶蝉候选开始缺少可分离的直接取食三档进程，继续扩充边际收益低且会引入跨病害/跨 taxon 推断风险。",
    }

    for record in evidence["records"]:
        if record.get("object_type") != "insect_host" or record.get("class_id") != 12 or record.get("crop") != "茶":
            continue
        data = SEVERITY_DATA[record["severity"]]
        record.update(
            status="COMPLETE",
            rubric_text=data["rubric_text"],
            observable_features=data["observable_features"],
            source_ids=data["source_ids"],
            evidence_type="EVIDENCE_SYNTHESIZED",
            synthesis_note=data["synthesis_note"],
            visual_feature_source_ids=data["visual_feature_source_ids"],
            SOURCE_SEMANTIC_REVIEW="PASS",
            evidence_taxon=[TAXON, SOURCE_TAXON],
            evidence_taxon_level=["species"],
            taxonomic_source_ids=["R31-12-JTS-ONUKII-TAXON-2026", "R31-12-PLOS-ONUKII-TAXON", "R31-12-CAAS-ONUKII-TAXON"],
            evidence_taxon_scope=[
                {
                    "source_id": source_id,
                    "evidence_taxon": SOURCE_TAXON if source_id not in {"R31-12-ANKANG-TEA-DAMAGE", "R31-12-WEIHAI-TEA-DAMAGE"} else "茶小绿叶蝉（来源命名种组）",
                    "evidence_taxon_level": "species" if source_id not in {"R31-12-ANKANG-TEA-DAMAGE", "R31-12-WEIHAI-TEA-DAMAGE"} else "source_named_group",
                    "scope_note": "仅用于茶树上已审核的茶小绿叶蝉范围；不外推为叶蝉科全体。",
                }
                for source_id in data["source_ids"]
            ],
            source_entailment_review={
                "status": "PASS",
                "automated_check": "reference_and_scope_only",
                "note": "2026-09-08 人工核对同一 taxon×茶树的症状进展及逐项可视特征；自动 validator 不替代农业专家判断。",
            },
        )
    evidence["closure"] = manifest["closure"]
    evidence["final_knowledge_expansion"] = manifest["final_knowledge_expansion"]

    markdown = LEAFHOPPER_PATH.read_text(encoding="utf-8")
    tea_block = re.compile(r"(?ms)^### 寄主：茶\s*$.*?(?=^### 寄主：芒果\s*$)")
    if not tea_block.search(markdown):
        raise RuntimeError("leafhopper tea block did not match expected SSOT")
    markdown = tea_block.sub(NEW_TEA + "\n", markdown, count=1)
    markdown = markdown.replace(
        "- 本批尚未完成可安全闭环的寄主三级严重度；全部保持 `NEEDS_EVIDENCE`。",
        "- 茶小绿叶蝉×茶的三档严重度已完成同一种级 taxon×同一寄主的证据闭环；芒果、水稻、苜蓿继续 `NEEDS_EVIDENCE`。",
    )
    LEAFHOPPER_PATH.write_text(markdown, encoding="utf-8")
    dump(MANIFEST_PATH, manifest)
    dump(EVIDENCE_PATH, evidence)


if __name__ == "__main__":
    main()
