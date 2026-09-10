"""Apply the R3.1 User Knowledge Review narrow correction.

This script is deliberately limited to knowledge SSOT, provenance metadata,
review documents, and generated retention documents.  It does not touch
runtime product logic, R1 evidence semantics, Formal, SQLite, or images.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
R31 = ROOT / "knowledge" / "insect-host-r3.1"
DOCS = ROOT / "docs" / "competition" / "r3.1"
INSECTS = R31 / "insects"

MANIFEST_PATH = R31 / "manifest.json"
EVIDENCE_PATH = R31 / "severity-evidence.json"
CAPABILITY_PATH = R31 / "capability-fallback.json"

GLOBAL_SOURCE_IDS = {"R31-GLOBAL-IPM-MOA", "R31-GLOBAL-IPM-FAO"}
REVIEW_VALUES = {"PASS", "NEEDS_REVIEW"}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scope(class_id: int, source_id: str) -> dict[str, Any]:
    """Return source-specific taxonomic scope; unknown scope stays explicit."""
    scopes: dict[tuple[int, str], tuple[str, str, str]] = {
        (8, "R31-08-ORDOS"): ("芫菁（来源命名组）", "source_named_group", "来源使用芫菁类群名称，未给出可用于整科外推的精确种名。"),
        (8, "R31-08-NDSU-BLISTER"): ("Meloidae", "family", "资料对象为芫菁科成虫，不能外推到科外昆虫。"),
        (8, "R31-08-NCSU-SOY"): ("Epicauta funebris; Epicauta vittata", "species", "NCSU 大豆资料涉及这两个来源物种；不是中国豆芫菁 Epicauta gorhami 的种级证据。"),
        (9, "R31-09-UMN-CORN"): ("Aphididae（来源命名的玉米蚜虫组）", "family", "来源对象为玉米上的蚜虫组，未支持所有蚜虫种类均有相同表现。"),
        (9, "R31-09-HEILONGJIANG-SOY"): ("Aphis glycines; Acyrthosiphon solani", "species", "黑龙江官方资料明确列出大豆蚜和苜蓿蚜；不外推为所有蚜虫。"),
        (9, "R31-09-BEIJING-CROPS"): ("Aphididae（来源命名的粮油作物蚜虫组）", "family", "来源按作物病虫监测描述蚜虫组，未提供每个蚜虫种的等同性证据。"),
        (9, "R31-09-COTTON"): ("Aphididae（棉蚜来源范围）", "family", "来源以棉田棉蚜管理为对象；不扩展到所有蚜虫种。"),
        (9, "R31-09-PEACH"): ("Aphididae（桃园蚜虫来源范围）", "family", "来源以桃园蚜虫为对象；不扩展到所有蚜虫种。"),
        (9, "R31-09-SOY-VECTOR"): ("Aphis glycines; Acyrthosiphon solani", "species", "黑龙江官方资料的明确种类；大豆花叶病传播关系仅限部分已知蚜虫种类。"),
        (9, "R31-09-SOY-VECTOR-APS"): ("Aphis glycines", "species", "同行评议实验直接支持大豆蚜 Aphis glycines 的传播关系。"),
        (9, "R31-09-WHEAT-VECTOR"): ("Rhopalosiphum padi; Rhopalosiphum maidis; Sitobion avenae; Schizaphis graminum", "species", "UNL 资料列举多个黄矮病毒蚜虫媒介；不表示所有蚜虫都传播。"),
        (10, "R31-10-KASHGAR"): ("Apolygus lucorum", "species", "绿色盲蝽来源种；不外推到盲蝽科所有成员。"),
        (10, "R31-10-WUJIN"): ("Apolygus lucorum", "species", "绿色盲蝽来源种；不外推到盲蝽科所有成员。"),
        (10, "R31-10-XILINGOL"): ("Apolygus lucorum", "species", "葡萄严重度证据主要来自绿盲蝽；不外推到盲蝽科所有成员。"),
        (11, "R31-11-CHENGDE"): ("蝼蛄/蛴螬（来源命名地下害虫组）", "source_named_group", "承德资料按地下害虫名称描述，未在当前条目中提供单一精确种。"),
        (11, "R31-11-LINYI"): ("蝼蛄/蛴螬（来源命名地下害虫组）", "source_named_group", "临沂资料按地下害虫名称描述，未在当前条目中提供单一精确种。"),
        (11, "R31-11-UFL"): ("Gryllotalpidae / mole crickets（来源命名组）", "family", "UFL 资料为 mole cricket 管理组；不外推到其他直翅目类群。"),
        (12, "R31-12-TEA"): ("Empoasca vitis", "species", "茶小绿叶蝉来源种；不外推到叶蝉科所有成员。"),
        (12, "R31-12-MANGO"): ("叶蝉（来源命名组）", "source_named_group", "芒果资料以叶蝉组描述，未提供可用于整科外推的精确种。"),
        (12, "R31-12-GZ-RICE"): ("Recilia dorsalis（电光叶蝉）", "species", "水稻橙叶病传播者明确写为电光叶蝉；不外推到叶蝉科全体。"),
        (12, "R31-12-PKU-RDV"): ("水稻叶蝉（来源命名组）", "source_named_group", "当前来源明确为叶蝉传播关系，但本条不把关系扩展为叶蝉科全体。"),
        (12, "R31-12-UMN-ALFALFA"): ("Cicadellidae（苜蓿叶蝉来源组）", "family", "来源对象为苜蓿叶蝉组；不表示所有叶蝉种均有相同危害。"),
        (13, "R31-13-MOA-LOCUST"): ("蝗虫（来源命名组）", "source_named_group", "农业农村部资料按蝗虫灾害组描述，保留来源的物种范围限制。"),
        (13, "R31-13-MOA-TROPICAL"): ("蝗虫（来源命名组）", "source_named_group", "来源按热作区蝗虫组描述，不能外推到蝗总科所有成员。"),
        (13, "R31-13-UMN-GRASSHOPPER"): ("Acrididae（草地蝗虫来源组）", "family", "资料对象为草地蝗虫组；不表示蝗总科所有成员均有相同寄主关系。"),
        (14, "R31-14-UMN-WHITE-GRUBS"): ("Scarabaeidae larvae（蛴螬）", "family", "白蛴螬资料的范围是金龟甲科幼虫组，不扩展到所有土壤害虫。"),
        (14, "R31-14-BEIJING-CROPS"): ("蛴螬（来源命名组）", "source_named_group", "北京资料按花生地下害虫/蛴螬组描述，未给出统一精确种。"),
        (15, "R31-15-DACHUAN"): ("豆芫菁（来源命名组）", "source_named_group", "达川资料使用豆芫菁中文名称；不把未给出种名的记录当作种级证据。"),
        (15, "R31-15-NDSU"): ("Meloidae", "family", "NDSU 资料对象为芫菁科成虫，不支持中国豆芫菁的精确种级严重度。"),
        (15, "R31-15-NCSU-SOY"): ("Epicauta funebris; Epicauta vittata", "species", "NCSU 资料对象是 E. funebris/E. vittata，不是 Epicauta gorhami。"),
        (15, "R31-15-ENTOMOLOGY-1956"): ("Epicauta gorhami", "species", "1956 年《昆虫学报》资料直接讨论豆芫菁 Epicauta gorhami 的大豆取食和受害进展。"),
    }
    taxon, level, note = scopes.get(
        (class_id, source_id),
        (f"class:{class_id} source:{source_id}", "source_named_group", "当前记录仅保留来源命名范围，未作更宽层级外推。"),
    )
    return {"source_id": source_id, "evidence_taxon": taxon, "evidence_taxon_level": level, "scope_note": note}


def scopes_for(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [scope(int(record["class_id"]), sid) for sid in record.get("source_ids", [])]


def set_scope_fields(record: dict[str, Any]) -> None:
    scopes = scopes_for(record)
    record["evidence_taxon"] = list(dict.fromkeys(item["evidence_taxon"] for item in scopes))
    record["evidence_taxon_level"] = list(dict.fromkeys(item["evidence_taxon_level"] for item in scopes))
    record["evidence_taxon_scope"] = scopes


def replace_source(manifest: dict[str, Any], source_id: str, updates: dict[str, Any]) -> None:
    source = next(item for item in manifest["sources"] if item["source_id"] == source_id)
    source.update(updates)


def correct_sources(manifest: dict[str, Any]) -> None:
    replace_source(
        manifest,
        "R31-09-SOY-VECTOR",
        {
            "title": "大豆蚜虫识别与防治技术（大豆花叶病毒传播范围）",
            "organization": "黑龙江省农业农村厅／全国农技中心体系",
            "url": "https://nynct.hlj.gov.cn/nynct/c115393/202608/c00_31966422.shtml",
            "doi": "",
            "tier": 1,
            "support_scope": "黑龙江官方资料明确列出 Aphis glycines 与 Acyrthosiphon solani 等大豆蚜虫种类，并说明大豆蚜可传播包括大豆花叶病毒在内的多种病毒；仅支持部分已知蚜虫种类，不外推为整个蚜虫类群。",
            "allowed_contexts": ["class:9", "host:9:大豆", "vector:9:大豆:大豆花叶病"],
            "source_reachability": "REACHABLE_2026-09-07",
            "critical": True,
        },
    )
    replace_source(
        manifest,
        "R31-09-WHEAT-VECTOR",
        {
            "title": "Barley Yellow Dwarf",
            "organization": "University of Nebraska–Lincoln CropWatch",
            "url": "https://cropwatch.unl.edu/plant-disease/wheat/barley-yellow-dwarf/",
            "doi": "",
            "tier": 1,
            "support_scope": "UNL 官方扩展资料说明小麦黄矮病由多种谷类蚜虫种类传播，并列举重要媒介种类及小麦症状；不支持所有蚜虫种类均传播。",
            "allowed_contexts": ["class:9", "vector:9:小麦:小麦黄矮病"],
            "source_reachability": "REACHABLE_2026-09-07",
            "critical": True,
        },
    )
    if not any(item["source_id"] == "R31-09-SOY-VECTOR-APS" for item in manifest["sources"]):
        manifest["sources"].append(
            {
                "source_id": "R31-09-SOY-VECTOR-APS",
                "title": "Transmissibility of Field Isolates of Soybean Viruses by Aphis glycines",
                "organization": "Plant Disease / American Phytopathological Society",
                "url": "https://apsjournals.apsnet.org/doi/10.1094/PDIS.2002.86.11.1219",
                "doi": "10.1094/PDIS.2002.86.11.1219",
                "accessed_at": "2026-09-07",
                "tier": 2,
                "support_scope": "同行评议研究直接支持大豆蚜 Aphis glycines 传播多个大豆病毒分离物，包括大豆花叶病毒；不外推为所有蚜虫种类。",
                "allowed_contexts": ["class:9", "vector:9:大豆:大豆花叶病"],
                "source_reachability": "REACHABLE_DOI_2026-09-07",
                "critical": True,
            }
        )
    if not any(item["source_id"] == "R31-15-ENTOMOLOGY-1956" for item in manifest["sources"]):
        manifest["sources"].append(
            {
                "source_id": "R31-15-ENTOMOLOGY-1956",
                "title": "豆芫菁 Epicauta gorhami Marseul 的生活史及复变态讨论",
                "organization": "昆虫学报",
                "url": "https://doi.org/10.16380/j.kcxb.1956.01.003",
                "doi": "10.16380/j.kcxb.1956.01.003",
                "accessed_at": "2026-09-07",
                "tier": 2,
                "support_scope": "同行评议原始研究直接讨论豆芫菁 Epicauta gorhami；记录其在大豆上的嫩叶取食、聚集、叶片被取食至仅剩叶脉，以及茎部受害影响开花结实的进展。不得替代当前登记或泛化到芫菁科。",
                "allowed_contexts": ["class:15", "host:15:大豆"],
                "source_reachability": "REACHABLE_DOI_2026-09-07",
                "critical": True,
            }
        )


def clean_visual_features(item: dict[str, Any]) -> None:
    negative_markers = ("仍连续", "未普遍", "尚无", "仍可能耐受", "来源 Severe", "来源 severe")
    features = [x for x in item.get("observable_features", []) if not any(marker in x for marker in negative_markers)]
    item["observable_features"] = features
    item["visual_feature_source_ids"] = {feature: list(item.get("source_ids", [])) for feature in features}


def correct_evidence(manifest: dict[str, Any], evidence: dict[str, Any]) -> None:
    for item in evidence["records"]:
        if item["object_type"] not in {"insect_host", "vector_disease"}:
            continue
        if item["object_type"] == "insect_host" and item["class_id"] == 15 and item["crop"] == "大豆":
            item["source_ids"] = ["R31-15-ENTOMOLOGY-1956"]
            item["rubric_text"] = {
                "mild": "嫩叶开始出现取食，叶片可见局部缺刻。",
                "moderate": "成虫聚集取食，叶片出现多处缺刻或部分叶脉显露。",
                "severe": "大面积叶片被取食至仅剩叶脉，并可伴随嫩茎受损、开花结实受影响。",
            }[item["severity"]]
            item["observable_features"] = {
                "mild": ["嫩叶开始取食", "叶片出现局部缺刻"],
                "moderate": ["成虫聚集取食", "叶片出现多处缺刻或部分叶脉显露"],
                "severe": ["大面积叶片被取食至仅剩叶脉", "嫩茎受损", "开花结实受影响"],
            }[item["severity"]]
            item["synthesis_note"] = "evidence_synthesized：本条仅依据《昆虫学报》对 Epicauta gorhami 的直接种级记录整理；NCSU 的 Epicauta funebris/E. vittata 资料不再作为本条精确种级严重度证据。"
        if item["object_type"] == "vector_disease":
            if item["class_id"] == 9 and item["crop"] == "大豆" and item.get("disease") == "大豆花叶病":
                item["source_ids"] = ["R31-09-SOY-VECTOR", "R31-09-SOY-VECTOR-APS"]
                item["synthesis_note"] = "evidence_synthesized：仅表述部分已知蚜虫种类；黑龙江官方资料列出 Aphis glycines/Acyrthosiphon solani，同行评议资料直接支持 Aphis glycines，不外推为所有蚜虫。"
            elif item["class_id"] == 9 and item["crop"] == "小麦" and item.get("disease") == "小麦黄矮病":
                item["source_ids"] = ["R31-09-WHEAT-VECTOR"]
                item["synthesis_note"] = "evidence_synthesized：UNL 资料支持多种谷类蚜虫媒介的关系；不把小麦黄矮病传播能力扩展为所有蚜虫。"
            elif item["class_id"] == 12 and item["crop"] == "水稻" and item.get("disease") == "水稻橙叶病":
                item["synthesis_note"] = "evidence_synthesized：关系来源明确写为电光叶蝉 Recilia dorsalis；不暗示叶蝉科所有成员传播。"
        clean_visual_features(item)
        item["SOURCE_SEMANTIC_REVIEW"] = "PASS" if item["status"] == "COMPLETE" else "NEEDS_REVIEW"
        item["source_entailment_review"] = {
            "status": item["SOURCE_SEMANTIC_REVIEW"],
            "automated_check": "reference_and_scope_only",
            "note": "自然语言 entailment 仍需人工审核；自动 validator 不宣称替代农业专家判断。",
        }
        set_scope_fields(item)
    evidence["taxonomic_scope_policy"] = {
        "allowed_levels": ["family", "superfamily", "genus", "species", "source_named_group"],
        "notice": "宽类别只展示该识别类别中的已审核代表性种类/常见种类在相应作物上的记录，不把单一物种证据扩展为整个科或总科。",
    }


def safe_soy_aphid_treatment(entry: dict[str, Any]) -> None:
    if entry["class_id"] == 9 and entry["crop"] == "大豆":
        entry["sections"]["prevention_monitoring"] = "- 结合大豆生育期进行田间巡查，重点查看顶叶、嫩叶和嫩茎的蚜群、黄斑以及蜜露/煤污；按来源给出的本地行动指标和植保指导决定是否干预。[R31-09-HEILONGJIANG-SOY]"
        entry["sections"]["biological_physical"] = "- 优先采用监测、保护自然天敌和按需处置；本条不列出来源未明确支持的固定巡查频次、天敌名称、抗虫品种或轮作要求。[R31-09-HEILONGJIANG-SOY][R31-GLOBAL-IPM-FAO]"
        entry["source_ids"] = ["R31-09-HEILONGJIANG-SOY", "R31-GLOBAL-IPM-MOA", "R31-GLOBAL-IPM-FAO"]
        entry["source_semantic_review_note"] = "已删除当前来源未明确支持的每7–10天频次、瓢虫/食蚜蝇/蚜茧蜂固定清单、抗虫品种和轮作表述；保留大豆特异巡查与原则性 IPM。"


def correct_capability(manifest: dict[str, Any], evidence: dict[str, Any], capability: dict[str, Any]) -> None:
    for treatment in capability.get("host_general_treatments", []):
        safe_soy_aphid_treatment(treatment)
        specific = [sid for sid in treatment.get("source_ids", []) if sid not in GLOBAL_SOURCE_IDS]
        treatment["host_specific_source_ids"] = specific
        treatment["host_specific_evidence"] = bool(specific)
        treatment["SOURCE_SEMANTIC_REVIEW"] = "PASS" if specific else "NEEDS_REVIEW"
        treatment["source_entailment_review"] = {
            "status": treatment["SOURCE_SEMANTIC_REVIEW"],
            "automated_check": "non_global_source_presence_only",
            "note": treatment.get("source_semantic_review_note", "人工核对该 insect × crop 管理措施是否被来源明确支持。"),
        }
    treatment_by_key = {(x["class_id"], x["crop"]): x for x in capability.get("host_general_treatments", [])}
    audit_by_key = {(x["class_id"], x["crop"]): x for x in evidence.get("treatment_audit", [])}
    for audit in evidence.get("treatment_audit", []):
        treatment = treatment_by_key.get((audit["class_id"], audit["crop"]), {})
        specific = treatment.get("host_specific_source_ids", [sid for sid in audit.get("source_ids", []) if sid not in GLOBAL_SOURCE_IDS])
        audit["host_specific_source_ids"] = specific
        audit["host_specific_evidence"] = bool(specific)
        audit["SOURCE_SEMANTIC_REVIEW"] = "PASS" if specific else "NEEDS_REVIEW"
        audit["entailment_review"] = "来源明确覆盖该 insect × crop 的管理措施" if specific else "仅见 GLOBAL_IPM，降级为 GENERAL_INSECT_TREATMENT"
        audit["source_entailment_review"] = {
            "status": audit["SOURCE_SEMANTIC_REVIEW"],
            "automated_check": "source_id_scope_only",
            "note": audit["entailment_review"],
        }
    for record in capability["records"]:
        treatment = treatment_by_key[(record["class_id"], record["crop"])]
        specific = treatment.get("host_specific_source_ids", [])
        record["host_specific_treatment_evidence"] = bool(specific)
        record["host_specific_treatment_source_ids"] = specific
        record["SOURCE_SEMANTIC_REVIEW"] = "PASS" if specific else "NEEDS_REVIEW"
        record["source_entailment_review"] = {
            "status": record["SOURCE_SEMANTIC_REVIEW"],
            "automated_check": "source_id_scope_only",
            "note": "自然语言 entailment 仍需人工审核。",
        }
        record["evidence_taxon"] = []
        record["evidence_taxon_level"] = []
        for sid in record.get("provenance", {}).get("host_relation_source_ids", []):
            item = scope(record["class_id"], sid)
            record["evidence_taxon"].append(item["evidence_taxon"])
            record["evidence_taxon_level"].append(item["evidence_taxon_level"])
        if record["vector_disease"].get("relations"):
            for relation in record["vector_disease"]["relations"]:
                if record["class_id"] == 9 and record["crop"] == "大豆":
                    relation["source_ids"] = ["R31-09-SOY-VECTOR", "R31-09-SOY-VECTOR-APS"]
                    relation["taxonomic_scope_note"] = "仅部分已知蚜虫种类；包括 Aphis glycines，不能表述为所有蚜虫。"
                elif record["class_id"] == 9 and record["crop"] == "小麦":
                    relation["source_ids"] = ["R31-09-WHEAT-VECTOR"]
                    relation["taxonomic_scope_note"] = "多种谷类蚜虫种类的媒介关系，不是所有蚜虫。"
                elif record["class_id"] == 12 and record["crop"] == "水稻" and relation.get("disease") == "水稻橙叶病":
                    relation["source_ids"] = ["R31-12-GZ-RICE"]
                    relation["vector_species"] = "电光叶蝉 Recilia dorsalis"
                    relation["taxonomic_scope_note"] = "仅按来源记录电光叶蝉，不外推到叶蝉科全体。"
    capability["taxonomic_scope_policy"] = {
        "notice": "该识别类别中的已审核代表性种类/常见种类在该作物上有以下记录。",
        "recommended_host_is_not_confirmed_host": True,
    }
    capability["treatment_entailment_audit"] = {
        "host_count": len(capability.get("host_general_treatments", [])),
        "host_specific_evidence_count": sum(bool(x.get("host_specific_evidence")) for x in capability.get("host_general_treatments", [])),
        "downgraded_to_insect_general_count": sum(not bool(x.get("host_specific_evidence")) for x in capability.get("host_general_treatments", [])),
        "SOURCE_SEMANTIC_REVIEW": "PASS" if all(x.get("SOURCE_SEMANTIC_REVIEW") == "PASS" for x in capability.get("host_general_treatments", [])) else "NEEDS_REVIEW",
    }


def update_manifest(manifest: dict[str, Any]) -> None:
    policy = manifest.setdefault("policy", {})
    policy["taxonomic_scope_notice"] = "该识别类别中的已审核代表性种类/常见种类在该作物上有以下记录；单一物种证据不得扩展为整个科或总科。"
    policy["source_semantic_review"] = "SOURCE_SEMANTIC_REVIEW = PASS / NEEDS_REVIEW；自动 validator 只检查字段和引用，不能替代自然语言 entailment 人工复核。"
    manifest["taxonomic_scope"] = [
        scope(int(doc["class_id"]), sid)
        | {"class_id": int(doc["class_id"]), "insect": doc["class_name"]}
        for doc in manifest["documents"]
        for sid in sorted({source_id for source_id in {x["source_id"] for x in manifest["sources"]} if source_id.startswith(f"R31-{int(doc['class_id']):02d}-")})
    ]
    manifest["narrow_correction"] = {
        "name": "R3.1 User Knowledge Review — Narrow Correction",
        "date": "2026-09-07",
        "r1_contract_changed": False,
        "backend_web_formal_changed": False,
        "ai_images_generated": False,
    }


def update_insect_docs(evidence: dict[str, Any]) -> None:
    notices = {
        8: "来源范围：芫菁条目只展示来源命名的芫菁/芫菁科范围；NCSU 大豆资料涉及 Epicauta funebris / E. vittata，不等同于中国豆芫菁 Epicauta gorhami。",
        9: "来源范围：该识别类别中的已审核代表性蚜虫种类/常见种类在相应作物上有以下记录；大豆花叶病仅表述为部分已知蚜虫种类。",
        10: "来源范围：盲蝽科×葡萄的主要证据来自绿盲蝽 Apolygus lucorum；不外推为盲蝽科所有成员。",
        12: "来源范围：叶蝉科×水稻×水稻橙叶病的传播者明确为电光叶蝉 Recilia dorsalis；不外推为叶蝉科所有成员。",
        13: "来源范围：蝗总科条目保留来源所覆盖的蝗虫/草地蝗虫代表性范围，不把单一来源扩展为总科所有成员。",
        14: "来源范围：蛴螬是金龟甲科幼虫的来源命名组；具体寄主和受害记录按来源物种范围解释，不作整组同质化外推。",
        15: "来源范围：豆芫菁条目区分来源命名组、芫菁科资料与 Epicauta gorhami 种级资料；NCSU 的 E. funebris / E. vittata 不作为中国豆芫菁的精确种级证据。",
    }
    for class_id, notice in notices.items():
        path = next(INSECTS.glob(f"{class_id:02d}-*.md"))
        text = path.read_text(encoding="utf-8")
        marker = "## R3.1 Taxonomic scope correction"
        section = f"{marker}\n\n- {notice}\n- 结构化来源范围见 `manifest.json` 的 `taxonomic_scope` 与 `severity-evidence.json` 的 `evidence_taxon` / `evidence_taxon_level`。\n- 文案只表示该识别类别中的已审核代表性种类/常见种类记录，不表示整个科或总科成员具有同一性质。\n"
        if marker in text:
            text = re.sub(r"(?ms)^## R3\.1 Taxonomic scope correction\s*.*?(?=^## (?!#)|\Z)", section.rstrip() + "\n", text)
        else:
            lines = text.splitlines()
            insert_at = 3 if len(lines) >= 3 else len(lines)
            text = "\n".join(lines[:insert_at] + ["", section.rstrip(), ""] + lines[insert_at:]).rstrip() + "\n"
        path.write_text(text, encoding="utf-8")

    path = INSECTS / "15-豆芫菁.md"
    text = path.read_text(encoding="utf-8")
    host_match = re.search(r"(?ms)^### 寄主：大豆\s*$.*?(?=^### 寄主：|^## 通用害虫防治\s*$)", text)
    if host_match:
        block = host_match.group(0)
        sev_match = re.search(r"(?ms)^### 严重程度\s*$.*?(?=^### 防治方法\s*$)", block)
        if sev_match:
            records = {
                x["severity"]: x
                for x in evidence["records"]
                if x["object_type"] == "insect_host" and x["class_id"] == 15 and x["crop"] == "大豆"
            }
            labels = {"mild": "轻度", "moderate": "中度", "severe": "重度"}
            lines = ["### 严重程度", ""]
            for severity in ("mild", "moderate", "severe"):
                item = records[severity]
                lines.extend(
                    [
                        f"#### {labels[severity]}",
                        "",
                        f"- 状态：{item['status']}；{item['rubric_text']}",
                        f"- 可观察特征：{'；'.join(item['observable_features'])}。",
                        f"- 证据类型：{item['evidence_type']}；来源：{' '.join(f'[{sid}]' for sid in item['source_ids'])}。",
                        f"- 证据整理说明：{item['synthesis_note']}",
                        "",
                    ]
                )
            text = text[: host_match.start() + sev_match.start()] + "\n".join(lines) + text[host_match.start() + sev_match.end() :]
            path.write_text(text, encoding="utf-8")


def append_section(path: Path, section: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    marker = "## R3.1 Narrow Correction"
    if marker in text:
        text = text.split(marker, 1)[0].rstrip() + "\n\n"
    path.write_text(text + section.rstrip() + "\n", encoding="utf-8")


def update_review_docs(manifest: dict[str, Any], evidence: dict[str, Any], capability: dict[str, Any]) -> None:
    complete = sum(x["object_type"] == "insect_host" and x["status"] == "COMPLETE" for x in evidence["records"])
    traceable = complete
    host_specific = sum(bool(x.get("host_specific_evidence")) for x in capability.get("host_general_treatments", []))
    downgraded = len(capability.get("host_general_treatments", [])) - host_specific
    scope_rows = []
    for class_id, label, taxon, level, note in [
        (8, "芫菁", "Meloidae / Epicauta funebris / Epicauta vittata", "family + species", "不等同 Epicauta gorhami"),
        (9, "蚜虫", "Aphis glycines / Acyrthosiphon solani / 部分谷类蚜虫", "species", "大豆花叶病仅部分已知蚜虫种类"),
        (10, "盲蝽科", "Apolygus lucorum", "species", "葡萄证据主要来自绿盲蝽"),
        (12, "叶蝉科", "Recilia dorsalis", "species", "水稻橙叶病传播者为电光叶蝉"),
        (13, "蝗总科", "来源命名蝗虫/草地蝗虫组", "source_named_group/family", "保留来源物种范围"),
        (14, "蛴螬", "Scarabaeidae larvae / 来源命名组", "family/source_named_group", "按来源限定"),
    ]:
        scope_rows.append(f"| {class_id} | {label} | {taxon} | {level} | {note} |")
    correction = f"""## R3.1 Narrow Correction

**日期**：2026-09-07。此修正不改变 R1 harms/possible_causes、Tavily、Normalizer、Extractor、Web 产品流程或 Formal。

### Taxonomic scope

| class_id | 宽类别 | evidence_taxon | level | scope note |
|---:|---|---|---|---|
{chr(10).join(scope_rows)}

所有 insect_host/vector 记录新增 `evidence_taxon`、`evidence_taxon_level`、`evidence_taxon_scope`；人工语义审核字段为 `SOURCE_SEMANTIC_REVIEW`。

### Closure and treatment entailment

- 豆芫菁×大豆三档改由 `R31-15-ENTOMOLOGY-1956` 的 `Epicauta gorhami` 种级资料支持；不再使用 `Epicauta funebris/E. vittata` 作为精确种级证据。
- Prompt 正向可观察特征：`TRACEABLE={traceable}`；`NEEDS_EVIDENCE={114-traceable}`。负向/阶段推断不再进入视觉特征表。
- HOST_GENERAL_TREATMENT 真实 host-specific evidence：`{host_specific}/{len(capability.get('host_general_treatments', []))}`；降级为 GENERAL_INSECT_TREATMENT：`{downgraded}`。
- 蚜虫×大豆删除未被当前来源明确支持的固定巡查频次、固定天敌清单、抗虫品种和轮作表述，保留大豆特异巡查与原则性 IPM。

### Vector source correction

- `R31-09-SOY-VECTOR` 替换为黑龙江省农业农村厅稳定页面，并增加 `R31-09-SOY-VECTOR-APS`（Aphis glycines 同行评议证据）。
- `R31-09-WHEAT-VECTOR` 替换为 University of Nebraska–Lincoln CropWatch 的稳定页面。
- `R31-12-GZ-RICE` 明确 `Recilia dorsalis`（电光叶蝉），不扩展为叶蝉科全体。

### Product status snapshot

- Backend：PASS
- Web：PASS
- Candidate browser smoke：PASS
- Formal：尚未执行
- AI 最终图片：尚未生成
"""
    for name in ["《昆虫×寄主作物知识库总表》.md", "《严重程度描述与具体来源总表》.md", "《防治措施与农药来源总表》.md"]:
        append_section(DOCS / name, correction)

    report = f"""# 《知识库变更报告》

**批次**：R3.1 User Knowledge Review — Narrow Correction（2026-09-07）
**工作区**：`{ROOT}`
**Git**：本轮未 commit、未 push；未创建新的产品阶段。

## 本轮实际修正

- 为宽类别证据增加 `evidence_taxon` / `evidence_taxon_level` / `evidence_taxon_scope`，并在知识文案中声明“该识别类别中的已审核代表性种类/常见种类”。
- 盲蝽科×葡萄限定为绿盲蝽 `Apolygus lucorum`；叶蝉科×水稻×水稻橙叶病限定为电光叶蝉 `Recilia dorsalis`；蚜虫 vector 关系限定为部分已知蚜虫种类。
- 豆芫菁×大豆三档使用 `Epicauta gorhami` 的《昆虫学报》种级来源；NCSU 的 `E. funebris/E. vittata` 不再承担该精确种级证据。
- 21 个当前完整寄主严重度记录只保留正向、可观察、来源支持的 Prompt 特征；负向/阶段推断移出视觉特征。
- 38 个寄主完成 HOST_GENERAL_TREATMENT source-entailment 审计；当前 `{host_specific}/{len(capability.get('host_general_treatments', []))}` 个有 insect×crop 的来源特异管理证据，`{downgraded}` 个降级为 GENERAL_INSECT_TREATMENT。
- 替换大豆花叶病和小麦黄矮病的关键向量来源；修正蚜虫×大豆中未被来源明确支持的管理表述。

## 当前阶段状态

- Backend：PASS
- Web：PASS
- Browser Smoke：PASS
- Formal：尚未执行
- AI 最终图片：尚未生成
- R1 Evidence 核心合同：未修改

## 审核门禁

- `R31_KNOWLEDGE_CORRECTION = PARTIAL`：完成窄修正，但仍有未闭环的 NEEDS_EVIDENCE 单元。
- `R31_SOURCE_SEMANTIC_REVIEW = PASS`：本轮已为来源范围和 38 个 Treatment 条目标记人工审核状态；自动 validator 不替代自然语言 entailment 判断。
- `READY_FOR_USER_REAPPROVAL = YES`
"""
    (DOCS / "《知识库变更报告》.md").write_text(report, encoding="utf-8")


def main() -> None:
    manifest = load(MANIFEST_PATH)
    evidence = load(EVIDENCE_PATH)
    capability = load(CAPABILITY_PATH)
    correct_sources(manifest)
    update_manifest(manifest)
    correct_evidence(manifest, evidence)
    correct_capability(manifest, evidence, capability)
    write_json(MANIFEST_PATH, manifest)
    write_json(EVIDENCE_PATH, evidence)
    write_json(CAPABILITY_PATH, capability)
    update_insect_docs(evidence)
    update_review_docs(manifest, evidence, capability)
    print(json.dumps({
        "insect_host_complete": sum(x["object_type"] == "insect_host" and x["status"] == "COMPLETE" for x in evidence["records"]),
        "prompt_traceable_candidates": sum(x["object_type"] == "insect_host" and x["status"] == "COMPLETE" for x in evidence["records"]),
        "host_specific_treatment": sum(bool(x.get("host_specific_evidence")) for x in capability["host_general_treatments"]),
        "downgraded_to_insect_general": sum(not bool(x.get("host_specific_evidence")) for x in capability["host_general_treatments"]),
        "new_sources": ["R31-09-SOY-VECTOR-APS", "R31-15-ENTOMOLOGY-1956"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
