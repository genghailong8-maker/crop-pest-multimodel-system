from __future__ import annotations

from copy import deepcopy
from typing import Any

from .catalog import CLASS_CATALOG


KNOWLEDGE_SCHEMA_VERSION = "phase9-knowledge-v2"
KNOWLEDGE_REVIEW_DATE = "2026-08-11"

# These are principle-level sources. They are deliberately not product labels.
KNOWLEDGE_SOURCES: tuple[dict[str, Any], ...] = (
    {
        "id": "fao-ipm-principles",
        "title": "Principles and practices",
        "publisher": "Food and Agriculture Organization of the United Nations",
        "url": "https://www.fao.org/pest-and-pesticide-management/ipm/principles-and-practices/en/",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "ecosystem approach, sanitation, rotation and risk-based IPM",
        "evidence_level": "principle",
    },
    {
        "id": "fao-ipm-definition",
        "title": "Integrated Pest Management (IPM)",
        "publisher": "Food and Agriculture Organization of the United Nations",
        "url": "https://www.fao.org/pest-and-pesticide-management/ipm/integrated-pest-management/en/",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "combining biological, physical, cultural and chemical measures while reducing risk",
        "evidence_level": "principle",
    },
    {
        "id": "cn-crop-pest-regulation",
        "title": "农作物病虫害防治条例",
        "publisher": "中华人民共和国农业农村部",
        "url": "https://fgs.moa.gov.cn/flfg/202004/t20200403_6340771.htm",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "prevention-first, integrated and green control; healthy cultivation",
        "evidence_level": "regulation",
    },
    {
        "id": "cn-green-control",
        "title": "2013年全国农作物病虫害绿色防控示范区建设方案",
        "publisher": "中华人民共和国农业农村部",
        "url": "https://zzys.moa.gov.cn/gzdt/201304/t20130411_6309844.htm",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "ecological, biological, physical and supervised control categories",
        "evidence_level": "guidance",
    },
    {
        "id": "class-0-umn-corn-leaf-blight",
        "title": "Northern corn leaf blight",
        "publisher": "University of Minnesota Extension",
        "url": "https://extension.umn.edu/corn-pest-management/northern-corn-leaf-blight",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "玉米叶枯病症状、适生条件、抗病品种、轮作和残体管理",
        "evidence_level": "class_specific_extension",
    },
    {
        "id": "class-1-umn-tomato-leaf-spots",
        "title": "Spotty tomato leaves - what is it and what to do",
        "publisher": "University of Minnesota Extension",
        "url": "https://blog-fruit-vegetable-ipm.extension.umn.edu/2022/07/as-fruit-sets-leaf-spots-follow-tomato.html",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "番茄斑枯病鉴别、通风、清除病叶、轮作和滴灌",
        "evidence_level": "class_specific_extension",
    },
    {
        "id": "class-2-umn-cucurbit-powdery-mildew",
        "title": "Powdery mildew of cucurbits",
        "publisher": "University of Minnesota Extension",
        "url": "https://extension.umn.edu/disease-management/powdery-mildew-cucurbits",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "葫芦科白粉病识别、抗性品种、通风和巡查",
        "evidence_level": "class_specific_extension",
    },
    {
        "id": "class-3-moa-potato-control",
        "title": "2023年马铃薯重大病虫害防控技术方案",
        "publisher": "中华人民共和国农业农村部",
        "url": "https://www.moa.gov.cn/ztzl/2023cg/jszd_29356/202302/P020230228395603536186.pdf",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "马铃薯早疫病等主要病虫的监测、健康栽培与综合防控",
        "evidence_level": "class_specific_government_guidance",
    },
    {
        "id": "class-4-umn-corn-rust",
        "title": "Common rust on corn",
        "publisher": "University of Minnesota Extension",
        "url": "https://extension.umn.edu/corn-pest-management/common-rust-corn",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "玉米锈病症状、气象条件和抗病品种管理",
        "evidence_level": "class_specific_extension",
    },
    {
        "id": "class-5-umn-tomato-bacterial-spot",
        "title": "Bacterial spot of tomato and pepper",
        "publisher": "University of Minnesota Extension",
        "url": "https://extension.umn.edu/disease-management/bacterial-spot-tomato-and-pepper",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "番茄细菌性斑点识别、健康种苗、工具清洁、轮作和控湿",
        "evidence_level": "class_specific_extension",
    },
    {
        "id": "class-6-cornell-late-blight",
        "title": "Late Blight",
        "publisher": "Cornell University Cooperative Extension",
        "url": "https://www.vegetables.cornell.edu/crops/tomatoes/late-blight/",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "番茄/马铃薯晚疫病识别、抗病品种、卫生处理、轮作和巡查",
        "evidence_level": "class_specific_extension",
    },
    {
        "id": "class-7-cn-potato-late-blight-standard",
        "title": "马铃薯晚疫病防治技术规范（NY/T 1783-2009）",
        "publisher": "全国标准信息公共服务平台（主管部门：农业农村部）",
        "url": "https://std.samr.gov.cn/hb/search/stdHBDetailed?id=B07EFC3E467D9E67E05397BE0A0A1A5C",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "马铃薯晚疫病现行行业技术规范及适用范围",
        "evidence_level": "class_specific_standard",
    },
    {
        "id": "class-8-umn-blister-beetle",
        "title": "Blister beetles in alfalfa hay",
        "publisher": "University of Minnesota Extension",
        "url": "https://extension.umn.edu/horse-nutrition/blister-beetles-alfalfa-hay",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "苜蓿芫菁识别、巡查、收获避险和斑蝥素安全风险",
        "evidence_level": "class_specific_extension",
    },
    {
        "id": "class-9-umn-corn-aphids",
        "title": "Aphids in corn (post-pollination)",
        "publisher": "University of Minnesota Extension",
        "url": "https://extension.umn.edu/corn-pest-management/aphids-corn-post-pollination",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "玉米蚜虫群体位置、蜜露危害和田间取样",
        "evidence_level": "class_specific_extension",
    },
    {
        "id": "class-10-shaanxi-grape-mirid",
        "title": "临渭：葡萄绿盲蝽防治技术意见",
        "publisher": "陕西省农业农村厅",
        "url": "https://nynct.shaanxi.gov.cn/zt/snzbxx/zbjs/202504/t20250415_3493113.html",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "葡萄绿盲蝽识别、清园、防虫网、诱捕和天敌保护",
        "evidence_level": "class_specific_government_guidance",
    },
    {
        "id": "class-11-chengde-mole-cricket",
        "title": "2020年承德市主要玉米虫害防控技术指导意见",
        "publisher": "承德市农业农村局",
        "url": "https://www.chengde.gov.cn/art/2020/4/22/art_9944_538515.html",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "玉米蝼蛄和蛴螬识别、地下活动痕迹及苗期危害",
        "evidence_level": "class_specific_government_guidance",
    },
    {
        "id": "class-12-moa-mango-leafhopper",
        "title": "2025年全国芒果重大病虫害发生趋势预报",
        "publisher": "农业农村部农垦局",
        "url": "https://nkj.moa.gov.cn/rzny/202503/t20250310_6471444.htm",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "芒果叶蝉发生风险、监测和绿色防控技术方向",
        "evidence_level": "class_specific_government_guidance",
    },
    {
        "id": "class-13-umn-grasshopper",
        "title": "Grasshopper management in Minnesota crops",
        "publisher": "University of Minnesota Extension",
        "url": "https://extension.umn.edu/corn-pest-management/grasshopper-management-minnesota-crops",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "蝗虫/蚱蜢气象风险、早期巡查、种群密度和作物边缘管理",
        "evidence_level": "class_specific_extension",
    },
    {
        "id": "class-14-umn-white-grubs",
        "title": "White grubs",
        "publisher": "University of Minnesota Extension",
        "url": "https://extension.umn.edu/corn-pest-management/white-grubs",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "玉米蛴螬识别、生活史、根系危害、取样和风险田块",
        "evidence_level": "class_specific_extension",
    },
    {
        "id": "class-15-moa-potato-blister-beetle",
        "title": "2023年马铃薯重大病虫害防控技术方案",
        "publisher": "中华人民共和国农业农村部",
        "url": "https://www.moa.gov.cn/ztzl/2023cg/jszd_29356/202302/P020230228395603536186.pdf",
        "retrieved_at": KNOWLEDGE_REVIEW_DATE,
        "scope": "豆芫菁等马铃薯重大病虫的监测与综合防控",
        "evidence_level": "class_specific_government_guidance",
    },
)


CLASS_SOURCE_IDS: dict[int, str] = {
    class_id: f"class-{class_id}-{suffix}"
    for class_id, suffix in {
        0: "umn-corn-leaf-blight",
        1: "umn-tomato-leaf-spots",
        2: "umn-cucurbit-powdery-mildew",
        3: "moa-potato-control",
        4: "umn-corn-rust",
        5: "umn-tomato-bacterial-spot",
        6: "cornell-late-blight",
        7: "cn-potato-late-blight-standard",
        8: "umn-blister-beetle",
        9: "umn-corn-aphids",
        10: "shaanxi-grape-mirid",
        11: "chengde-mole-cricket",
        12: "moa-mango-leafhopper",
        13: "umn-grasshopper",
        14: "umn-white-grubs",
        15: "moa-potato-blister-beetle",
    }.items()
}


SAFE_BOUNDARY: dict[str, Any] = {
    "scope": "general_ipm_orientation_only",
    "diagnosis_limit": "图像结果是候选线索，不替代植保人员现场诊断、实验室检测或当地病虫情报。",
    "chemical_limit": "未登记具体产品、剂量、混配、施用次数、再入田间间隔或安全间隔；这些信息必须来自当地现行标签和植保部门。",
    "first_line_actions": ["补拍清晰的整株、近景和叶背/茎基部", "隔离疑似植株并标记观察", "清洁工具和鞋具，避免从疑似区域向健康区域传播", "记录时间、作物、生育期、天气和扩展速度"],
    "human_review_triggers": ["最高置信度低于 0.75", "候选类别置信度接近", "图像质量异常"],
    "escalation": "症状快速扩展、成片发生、整株萎蔫、根部受害或涉及生产安全时，暂停自行施药并联系当地植保部门/农技人员。",
}


_CLASS_FOCUS: dict[int, str] = {
    0: "玉米叶片疑似枯斑/条斑的形态、分布和扩展速度",
    1: "番茄叶片疑似斑点的近景、叶背和由下向上的分布",
    2: "南瓜叶面疑似白色粉状覆盖、叶片卷曲和通风湿度背景",
    3: "马铃薯叶片疑似早期斑和轮纹样变化的近景与扩展范围",
    4: "玉米叶片疑似锈色斑点/孢子状区域及其在叶片上的分布",
    5: "番茄叶片疑似细菌性斑点的水渍样变化、叶背和天气背景",
    6: "番茄叶片疑似晚疫病样水渍状病斑及快速扩展迹象",
    7: "马铃薯叶片和茎秆疑似晚疫病样暗色病斑及湿度背景",
    8: "芫菁疑似成虫/取食痕迹、群体位置和受害叶片分布",
    9: "蚜虫疑似群体、叶背聚集、卷叶/蜜露迹象和扩散范围",
    10: "葡萄嫩梢和叶片疑似盲蝽取食痕迹、虫体近景及群体位置",
    11: "蝼蛄疑似活动孔道、土表痕迹、根际和幼苗受害位置",
    12: "叶蝉科疑似小型跳动昆虫、叶背位置和叶片失绿/卷曲迹象",
    13: "蝗总科疑似成虫/若虫、咀嚼缺刻和田间群体分布",
    14: "蛴螬疑似根际幼虫、根部受害和土壤剖面证据",
    15: "豆芫菁疑似成虫、豆科/苜蓿叶片缺刻和群体分布",
}


def _guidance_for_type(target_type: str) -> dict[str, list[str]]:
    if target_type == "病害":
        return {
            "prevention": [
                "优先使用健康种苗，按当地技术意见进行轮作或选用抗性品种。",
                "及时清除并妥善处理病残体，清洁工具，避免把疑似病组织带到健康区域。",
                "改善通风和排水，尽量避免叶面长时间潮湿；把天气和扩展速度纳入巡查记录。",
            ],
            "first_actions": [
                "隔离并标记疑似植株，补拍整株、病斑近景、叶背和茎基部。",
                "暂停从疑似区域向健康区域搬运植株、工具和残体。",
                "记录首次发现时间、受害比例和最近的降雨/灌溉情况。",
            ],
        }
    return {
        "prevention": [
            "按固定路线巡田并记录虫口、受害叶片和扩展位置，优先保护天敌和授粉昆虫。",
            "结合防虫网、粘捕/诱捕、人工清除和田间卫生等物理或栽培措施，先降低传播机会。",
            "清除严重受害组织并密封转移；不要把疑似害虫带到健康地块或育苗区。",
        ],
        "first_actions": [
            "补拍虫体近景、叶背/茎基部、受害部位和周边植株，记录虫体数量与分布。",
            "隔离疑似发生点并标记巡查范围，保留一张带尺度的现场照片。",
            "观察 24–48 小时变化；快速扩展或成片发生时联系当地植保人员。",
        ],
    }


def _management_for_class(item: dict[str, Any]) -> dict[str, list[str]]:
    class_id = int(item["id"])
    if item["type"] == "病害":
        management = {
            "agronomic": [
                "优先选择适合当地的抗（耐）性品种和健康种苗，避免把疑似带病材料带入田块。",
                "清理病残体并结合当地轮作条件减少连续寄主；改善通风、排水和植株长势。",
            ],
            "physical": [
                "补拍病斑近景、叶背、整株和周边植株；标记疑似点并单独处理工具。",
                "避免叶面长时间潮湿，不在植株湿润时修剪或从疑似区转向健康区作业。",
            ],
            "biological": [
                "本系统不依据单张图片自动推荐生物制剂；是否适用须查询该作物、病害和当地现行登记标签。"
            ],
            "monitoring_and_escalation": [
                "按固定路线记录病斑数量、受害比例、扩散速度及降雨/灌溉变化。",
                "快速扩展、成片发生或无法区分相近病害时，提交人工复核并联系当地植保人员。",
            ],
        }
        if class_id in {6, 7}:
            management["monitoring_and_escalation"].insert(
                0, "晚疫病可快速扩展；重点巡查低洼、阴湿和通风不良处，发现疑似中心株应立即升级处置。"
            )
        return management
    management = {
        "agronomic": [
            "清理田边杂草、残株和适生寄主，结合当地栽培制度减少虫源和迁入通道。",
            "保护田间生态和天敌，避免在尚未达到当地处置阈值时进行无差别处理。",
        ],
        "physical": [
            "补拍虫体、受害部位和周边植株，使用带尺度照片；小范围可人工清除或隔离。",
            "依据害虫习性评估防虫网、诱虫板、诱捕器或灯诱；使用时减少对天敌和授粉昆虫的影响。",
        ],
        "biological": [
            "优先保护捕食性和寄生性天敌；释放天敌或使用生物防控措施前应由当地植保人员确认对象与适期。"
        ],
        "monitoring_and_escalation": [
            "按固定样点记录虫体数量、受害株比例、虫态和扩散边界，不用单张近照推断田间虫口密度。",
            "快速扩散、根部/苗期受害或成片发生时，联系当地植保人员核定发生程度和处置阈值。",
        ],
    }
    if class_id in {8, 15}:
        management["physical"].insert(
            0, "芫菁可能含斑蝥素；苜蓿收获时发现群集应暂停收割并让虫群逸散，污染干草不得饲喂牲畜。"
        )
    if class_id in {11, 14}:
        management["monitoring_and_escalation"].insert(
            0, "检查缺苗断垄处的根际、土表隧道和幼虫；地上照片不足以确认地下害虫。"
        )
    return management


def _build_card(item: dict[str, Any]) -> dict[str, Any]:
    guidance = _guidance_for_type(str(item["type"]))
    management = _management_for_class(item)
    return {
        "class_id": item["id"],
        "name_zh": item["name_zh"],
        "name_en": item["name_en"],
        "crop": item["crop"],
        "type": item["type"],
        "knowledge_scope": "general_ipm_orientation_only",
        "claim_status": "candidate_guidance_not_a_confirmed_diagnosis",
        "observation_focus": _CLASS_FOCUS[item["id"]],
        "prevention": guidance["prevention"],
        "first_actions": guidance["first_actions"],
        "management": management,
        "chemical_safety": "仅提示查询当地现行登记标签并联系植保人员；本系统不提供具体产品、剂量、混配、次数或安全间隔。",
        "escalate_when": [
            "图像补充后仍无法区分相近类别或病因时，提交人工复核。",
            "症状快速扩展、成片发生、整株萎蔫或根部受害时，联系当地植保部门/农技人员。",
        ],
        "prohibited_inference": [
            "不得仅凭模型类别直接确认病原、虫龄、发生程度或经济阈值。",
            "不得从本卡片推导具体农药产品、剂量、混配、施用次数或安全间隔。",
        ],
        "source_ids": [
            CLASS_SOURCE_IDS[int(item["id"])],
            "fao-ipm-principles",
            "fao-ipm-definition",
            "cn-crop-pest-regulation",
            "cn-green-control",
        ],
        "reviewed_at": KNOWLEDGE_REVIEW_DATE,
    }


KNOWLEDGE_CARDS: tuple[dict[str, Any], ...] = tuple(_build_card(item) for item in CLASS_CATALOG)
_CARD_BY_ID = {card["class_id"]: card for card in KNOWLEDGE_CARDS}
_SOURCE_BY_ID = {source["id"]: source for source in KNOWLEDGE_SOURCES}


def get_knowledge_card(class_id: int) -> dict[str, Any] | None:
    card = _CARD_BY_ID.get(int(class_id))
    return deepcopy(card) if card is not None else None


def get_knowledge_sources(source_ids: list[str] | None = None) -> list[dict[str, Any]]:
    selected = source_ids if source_ids is not None else list(_SOURCE_BY_ID)
    return [deepcopy(_SOURCE_BY_ID[source_id]) for source_id in selected if source_id in _SOURCE_BY_ID]


def knowledge_contract() -> dict[str, Any]:
    return {
        "schema_version": KNOWLEDGE_SCHEMA_VERSION,
        "reviewed_at": KNOWLEDGE_REVIEW_DATE,
        "safety_boundary": deepcopy(SAFE_BOUNDARY),
        "sources": get_knowledge_sources(),
        "classes": [deepcopy(card) for card in KNOWLEDGE_CARDS],
    }


def prioritized_guidance(
    class_id: int,
    diagnostic_risk: str = "unknown",
    field_severity: str = "unknown",
) -> dict[str, Any] | None:
    card = get_knowledge_card(class_id)
    if card is None:
        return None
    management = card["management"]
    immediate = list(management["monitoring_and_escalation"])
    if diagnostic_risk in {"high", "unknown"}:
        immediate.insert(0, "先补充证据并等待人工复核，不把候选类别当成已确诊结果。")
    if field_severity == "high":
        immediate.insert(0, "受害信息提示较高田间严重度，应尽快联系当地植保人员现场核验。")
    elif field_severity == "unknown":
        immediate.insert(0, "田间严重度无法判断，请先补充受害比例和扩散速度。")
    return {
        "diagnostic_risk": diagnostic_risk,
        "field_severity": field_severity,
        "immediate": list(dict.fromkeys(immediate)),
        "agronomic": management["agronomic"],
        "physical": management["physical"],
        "biological": management["biological"],
        "chemical_safety": card["chemical_safety"],
        "source_ids": card["source_ids"],
    }


def _confidence_band(confidence: float | None) -> str:
    if confidence is None:
        return "none"
    if confidence < 0.50:
        return "low"
    if confidence < 0.75:
        return "medium"
    return "high"


def build_explainability(
    detections: list[dict[str, Any]],
    summary: dict[str, Any],
    quality: dict[str, Any] | None,
    inference: dict[str, Any] | None,
) -> dict[str, Any]:
    primary = summary.get("primary_candidate") if isinstance(summary, dict) else None
    primary_class_id = primary.get("class_id") if isinstance(primary, dict) else None
    primary_confidence = primary.get("max_confidence") if isinstance(primary, dict) else None
    card = get_knowledge_card(int(primary_class_id)) if primary_class_id is not None else None
    reasons = list(summary.get("review_reasons") or []) if isinstance(summary, dict) else []
    quality_flags = list((quality or {}).get("flags") or [])
    for flag in quality_flags:
        if flag not in reasons:
            reasons.append(flag)
    if not detections and "未检测到目标，请检查图片质量、拍摄部位或补充图片" not in reasons:
        reasons.append("未检测到目标，请检查图片质量、拍摄部位或补充图片")

    routing = inference.get("routing") if isinstance(inference, dict) else None
    route_mode = routing.get("mode") if isinstance(routing, dict) else None
    model_evidence = {
        "mode": inference.get("mode") if isinstance(inference, dict) else None,
        "model_sha256": inference.get("model_sha256") if isinstance(inference, dict) else None,
        "speed_ms": deepcopy(inference.get("speed_ms")) if isinstance(inference, dict) else None,
        "routing": deepcopy(routing) if isinstance(routing, dict) else None,
        "routing_is_shadow": route_mode == "shadow",
    }
    candidate_evidence = [
        {
            "detection_index": index,
            "class_id": item.get("class_id"),
            "class_name": item.get("class_name"),
            "confidence": item.get("confidence"),
            "confidence_band": _confidence_band(item.get("confidence")),
            "bbox": item.get("bbox"),
        }
        for index, item in enumerate(detections)
    ]
    return {
        "schema_version": KNOWLEDGE_SCHEMA_VERSION,
        "decision_scope": "orientation_only",
        "primary_class_id": primary_class_id,
        "primary_class_name": primary.get("class_name") if isinstance(primary, dict) else None,
        "primary_confidence": primary_confidence,
        "primary_confidence_band": _confidence_band(primary_confidence),
        "candidate_evidence": candidate_evidence,
        "model_evidence": model_evidence,
        "knowledge_card": card,
        "source_ids": list(card["source_ids"]) if card else [],
        "human_review": {
            "required": bool(summary.get("needs_review") if isinstance(summary, dict) else True) or bool(quality_flags),
            "reasons": reasons,
            "review_endpoint": "POST /api/cases/{case_id}/review",
        },
        "safety": {
            "chemical_recommendations": "not_provided",
            "requires_local_label_and_agronomist": True,
            "boundary_version": KNOWLEDGE_SCHEMA_VERSION,
        },
    }
