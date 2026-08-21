from __future__ import annotations

import base64
import json
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any, Literal, TypeVar

import httpx
from pydantic import BaseModel, Field, ValidationError

from .catalog import CLASS_BY_ID
from .config import settings
from .search import (
    SearchEvidence,
    build_qwen_context,
    collect_external_evidence,
    persisted_evidence_snapshots,
    public_sources,
    source_ids,
)


class MultimodalUnavailable(RuntimeError):
    pass


ANALYSIS_SCHEMA_VERSION = "phase9-multimodal-v4-external-evidence"
ShortText = Annotated[str, Field(min_length=1, max_length=160)]
RiskLevel = Literal["low", "medium", "high", "unknown"]
ModelT = TypeVar("ModelT", bound=BaseModel)
CANONICAL_DIAGNOSES = [item["name_zh"] for item in CLASS_BY_ID.values()]
CANONICAL_DIAGNOSIS_TEXT = "、".join(CANONICAL_DIAGNOSES)
SPREAD_SPEED_LABELS = {
    "unknown": "未知",
    "none": "未扩散",
    "slow": "缓慢",
    "moderate": "中等",
    "rapid": "快速",
}
EvidenceSource = Literal["image", "yolo", "field_input"]
EvidenceReference = Literal[
    "original_image",
    "yolo_primary",
    "field.crop",
    "field.part",
    "field.growth_stage",
    "field.environment",
    "field.affected_ratio_percent",
    "field.spread_speed",
]
SYSTEM_UNDETERMINED = "系统未判断"
OBSERVED_PARTS = {
    "叶片",
    "茎秆",
    "果实",
    "根部",
    "整株",
    "田间环境",
    "虫体",
    SYSTEM_UNDETERMINED,
}
OBSERVED_GROWTH_STAGES = {
    "苗期",
    "营养生长期",
    "开花期",
    "结果期",
    "成熟期",
    SYSTEM_UNDETERMINED,
}


class IndependentImageContent(BaseModel):
    primary_diagnosis: ShortText
    candidate_diagnoses: list[ShortText] = Field(min_length=1, max_length=4)
    symptoms: list[ShortText] = Field(min_length=1, max_length=5)
    possible_causes: list[ShortText] = Field(min_length=1, max_length=5)
    evidence: list[ShortText] = Field(min_length=1, max_length=6)
    uncertainty: list[ShortText] = Field(min_length=1, max_length=5)
    required_additional_photos: list[ShortText] = Field(min_length=1, max_length=4)
    observed_part: str = Field(default=SYSTEM_UNDETERMINED, max_length=160)
    observed_growth_stage: str = Field(default=SYSTEM_UNDETERMINED, max_length=160)


class GroundedEvidence(BaseModel):
    source: EvidenceSource
    reference: EvidenceReference
    observation: ShortText


class GroundedConclusion(BaseModel):
    conclusion: ShortText
    evidence: list[GroundedEvidence] = Field(min_length=1, max_length=4)


class GroundedAssessment(BaseModel):
    harms: list[GroundedConclusion] = Field(min_length=1, max_length=3)
    causes: list[GroundedConclusion] = Field(min_length=1, max_length=3)


class ExternalEvidenceConclusion(BaseModel):
    conclusion: ShortText
    source_ids: list[str] = Field(default_factory=list, max_length=4)


class ExternalEvidenceAnalysis(BaseModel):
    status: Literal["available", "unavailable"] = "unavailable"
    harms: list[ExternalEvidenceConclusion] = Field(default_factory=list, max_length=3)
    possible_causes: list[ExternalEvidenceConclusion] = Field(default_factory=list, max_length=3)


class MultimodalContent(BaseModel):
    primary_diagnosis: ShortText
    candidate_diagnoses: list[ShortText] = Field(min_length=1, max_length=4)
    symptoms: list[ShortText] = Field(min_length=1, max_length=5)
    harm_level: RiskLevel
    grounded_assessment: GroundedAssessment
    uncertainty: list[ShortText] = Field(min_length=1, max_length=5)
    required_additional_photos: list[ShortText] = Field(min_length=1, max_length=4)
    detector_alignment: Literal["agree", "uncertain", "conflict"]
    field_input_consistency: Literal["consistent", "uncertain", "conflict"]
    content_sufficiency: Literal["sufficient", "incomplete"]
    diagnostic_risk: RiskLevel
    field_severity: RiskLevel
    severity_basis: str = Field(min_length=1, max_length=320)
    needs_human_review: bool
    evidence_analysis: ExternalEvidenceAnalysis = Field(default_factory=ExternalEvidenceAnalysis)


def response_schema() -> dict[str, Any]:
    return MultimodalContent.model_json_schema()


def independent_response_schema() -> dict[str, Any]:
    return IndependentImageContent.model_json_schema()


def extract_message_content(payload: Any) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("多模态服务响应缺少 choices[0].message.content") from exc
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
        joined = "".join(text_parts)
        if joined:
            return joined
    raise ValueError("多模态服务返回的 message.content 不是文本")


def parse_model(content: str, model: type[ModelT], stage: str) -> ModelT:
    cleaned = content.strip()
    if cleaned.startswith("```json") and cleaned.endswith("```"):
        cleaned = cleaned[7:-3].strip()
    elif cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
    try:
        return model.model_validate_json(cleaned)
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"多模态{stage}结果不符合 {ANALYSIS_SCHEMA_VERSION}：{exc}") from exc


def parse_content(content: str) -> MultimodalContent:
    return parse_model(content, MultimodalContent, "证据比对")


def normalize_observed_value(value: Any, allowed: set[str]) -> str:
    if not isinstance(value, str):
        return SYSTEM_UNDETERMINED
    normalized = value.strip()
    if normalized in allowed:
        return normalized
    return SYSTEM_UNDETERMINED


def normalize_independent_observations(
    result: IndependentImageContent,
) -> IndependentImageContent:
    return result.model_copy(
        update={
            "observed_part": normalize_observed_value(result.observed_part, OBSERVED_PARTS),
            "observed_growth_stage": normalize_observed_value(
                result.observed_growth_stage, OBSERVED_GROWTH_STAGES
            ),
        }
    )


def validate_grounded_assessment(
    case_record: dict[str, Any],
    result: MultimodalContent,
    independent: IndependentImageContent | None = None,
) -> MultimodalContent:
    field_values: dict[str, tuple[str, ...]] = {
        "field.crop": (str(case_record.get("crop") or ""),),
        "field.part": (str(case_record.get("part") or ""),),
        "field.growth_stage": (str(case_record.get("growth_stage") or ""),),
        "field.environment": tuple(
            str(value) for value in (case_record.get("environment") or {}).values() if value
        ),
        "field.affected_ratio_percent": (
            f"{float(case_record['affected_ratio_percent']):g}",
        )
        if case_record.get("affected_ratio_percent") is not None
        else (),
        "field.spread_speed": (
            str(case_record.get("spread_speed") or ""),
            SPREAD_SPEED_LABELS.get(
                str(case_record.get("spread_speed") or ""),
                str(case_record.get("spread_speed") or ""),
            ),
        ),
    }
    detections = case_record.get("detections") or []
    summary = case_record.get("detector_summary") or {}
    primary = summary.get("primary_candidate") or (detections[0] if detections else {})
    primary_name = str(primary.get("class_name") or "")
    speculative_markers = ("模型认为", "通常", "推测", "可能导致", "可能造成", "会导致", "会造成")
    unsupported_consequence_markers = (
        "导致",
        "造成",
        "影响产量",
        "产量损失",
        "光合作用",
        "传播原因",
        "病原",
        "真菌",
        "细菌",
        "病毒",
    )
    insufficient_markers = ("无法", "不足", "缺少", "未提供", "未显示", "不能判断")
    independent_has_visible_evidence = not independent or any(
        value != "无法判断"
        for value in [*independent.symptoms, *independent.evidence]
    )

    def valid_evidence(evidence: GroundedEvidence) -> bool:
        if any(marker in evidence.observation for marker in speculative_markers):
            return False
        if evidence.source == "image":
            return evidence.reference == "original_image" and (
                independent_has_visible_evidence
                or any(marker in evidence.observation for marker in insufficient_markers)
            )
        if evidence.source == "yolo":
            return (
                evidence.reference == "yolo_primary"
                and bool(primary_name)
                and primary_name in evidence.observation
            )
        if not evidence.reference.startswith("field."):
            return False
        actual_values = tuple(value for value in field_values[evidence.reference] if value)
        return bool(actual_values) and any(
            value in evidence.observation for value in actual_values
        )

    def fallback(section_name: str) -> GroundedConclusion:
        observation = (
            "原图未显示可核验的受害后果或受害范围"
            if section_name == "harms"
            else "原图缺少病原检测、连续田间观察或管理记录"
        )
        return GroundedConclusion(
            conclusion="无法判断",
            evidence=[
                GroundedEvidence(
                    source="image",
                    reference="original_image",
                    observation=observation,
                )
            ],
        )

    def sanitize(
        section_name: Literal["harms", "causes"], claims: list[GroundedConclusion]
    ) -> list[GroundedConclusion]:
        sanitized: list[GroundedConclusion] = []
        for claim in claims:
            evidence = [item for item in claim.evidence if valid_evidence(item)]
            sources = {item.source for item in evidence}
            conclusion_is_insufficient = any(
                marker in claim.conclusion for marker in insufficient_markers
            )
            unsupported = any(
                marker in claim.conclusion for marker in unsupported_consequence_markers
            )
            scene = str((case_record.get("environment") or {}).get("scene") or "")
            context_contradiction = scene == "室内样本" and "田间" in claim.conclusion
            required_sources_present = (
                "image" in sources
                if section_name == "harms"
                else {"image", "yolo"}.issubset(sources)
            )
            if (
                claim.conclusion == "无法判断"
                or conclusion_is_insufficient
                or unsupported
                or context_contradiction
                or not evidence
                or not required_sources_present
            ):
                sanitized.append(fallback(section_name))
            else:
                sanitized.append(claim.model_copy(update={"evidence": evidence}))
        return sanitized

    return result.model_copy(
        update={
            "grounded_assessment": GroundedAssessment(
                harms=sanitize("harms", result.grounded_assessment.harms),
                causes=sanitize("causes", result.grounded_assessment.causes),
            )
        }
    )


def normalize_external_evidence_analysis(
    result: MultimodalContent,
    evidence: SearchEvidence,
) -> ExternalEvidenceAnalysis:
    """Keep only claims that point to content fetched from a real source URL."""
    valid_ids = source_ids(evidence)
    if not valid_ids:
        return ExternalEvidenceAnalysis()

    def claims(items: list[ExternalEvidenceConclusion]) -> list[ExternalEvidenceConclusion]:
        accepted: list[ExternalEvidenceConclusion] = []
        for item in items:
            references = list(
                dict.fromkeys(source_id for source_id in item.source_ids if source_id in valid_ids)
            )
            if not references or item.conclusion.strip() in {"无法判断", ""}:
                continue
            if any(marker in item.conclusion for marker in ("模型认为", "通常会", "一定会", "必然")):
                continue
            accepted.append(item.model_copy(update={"source_ids": references}))
        return accepted

    harms = claims(result.evidence_analysis.harms)
    possible_causes = claims(result.evidence_analysis.possible_causes)
    if not harms and not possible_causes:
        return ExternalEvidenceAnalysis()
    return ExternalEvidenceAnalysis(status="available", harms=harms, possible_causes=possible_causes)


def diagnosis_class_id(value: str | None) -> int | None:
    normalized = "".join(character for character in (value or "").lower() if character.isalnum())
    matches: list[tuple[int, int]] = []
    for class_id, item in CLASS_BY_ID.items():
        for name in (item["name_zh"], item["name_en"]):
            candidate = "".join(character for character in name.lower() if character.isalnum())
            if candidate and candidate in normalized:
                matches.append((len(candidate), class_id))
    return max(matches)[1] if matches else None


def reconcile_detector_alignment(
    case_record: dict[str, Any],
    result: MultimodalContent,
    independent_primary_diagnosis: str | None = None,
) -> MultimodalContent:
    detections = case_record.get("detections") or []
    diagnosis = independent_primary_diagnosis or result.primary_diagnosis
    if not detections or not diagnosis:
        return result.model_copy(update={"detector_alignment": "uncertain"})
    summary = case_record.get("detector_summary") or {}
    candidate = summary.get("primary_candidate") or detections[0]
    detector_class_id = candidate.get("class_id")
    diagnosis_id = diagnosis_class_id(diagnosis)
    if detector_class_id is None or diagnosis_id is None:
        return result.model_copy(update={"detector_alignment": "uncertain"})
    alignment = "agree" if diagnosis_id == int(detector_class_id) else "conflict"
    return result.model_copy(update={"detector_alignment": alignment})


def apply_detector_primary_diagnosis(
    case_record: dict[str, Any],
    result: MultimodalContent,
    independent_primary_diagnosis: str,
) -> tuple[MultimodalContent, str]:
    detections = case_record.get("detections") or []
    if not detections:
        return result, "multimodal_no_detection"
    summary = case_record.get("detector_summary") or {}
    candidate = summary.get("primary_candidate") or detections[0]
    class_id = candidate.get("class_id")
    if class_id is None or int(class_id) not in CLASS_BY_ID:
        return result, "multimodal_invalid_detector_class"
    primary = CLASS_BY_ID[int(class_id)]["name_zh"]
    candidates = [
        value
        for value in dict.fromkeys(
            [primary, independent_primary_diagnosis, *result.candidate_diagnoses]
        )
        if value and value != "无法判断"
    ][:4]
    return (
        result.model_copy(
            update={"primary_diagnosis": primary, "candidate_diagnoses": candidates or [primary]}
        ),
        "detector_primary",
    )


def reconcile_field_input_consistency(
    case_record: dict[str, Any], result: MultimodalContent
) -> MultimodalContent:
    detections = case_record.get("detections") or []
    if not detections:
        return result
    summary = case_record.get("detector_summary") or {}
    candidate = summary.get("primary_candidate") or detections[0]
    class_id = candidate.get("class_id")
    if class_id is None or int(class_id) not in CLASS_BY_ID:
        return result
    selected = str(case_record.get("crop") or "")
    catalog_item = CLASS_BY_ID[int(class_id)]
    compatible = (
        catalog_item["type"] == "害虫"
        if selected == "昆虫"
        else bool(selected) and selected in str(catalog_item["crop"])
    )
    if compatible:
        return result
    return result.model_copy(update={"field_input_consistency": "conflict"})


def build_review_reasons(case_record: dict[str, Any], result: MultimodalContent) -> list[str]:
    summary = case_record.get("detector_summary") or {}
    quality = case_record.get("quality") or {}
    detections = case_record.get("detections") or []
    reasons = list(summary.get("review_reasons") or [])
    reasons.extend(quality.get("flags") or [])
    if not detections:
        reasons.append("视觉模型未定位到明确目标")
    if result.detector_alignment == "conflict":
        reasons.append("独立图像判断与视觉候选冲突")
    elif result.detector_alignment == "uncertain":
        reasons.append("独立图像判断与视觉候选的一致性不确定")
    if result.field_input_consistency == "conflict":
        reasons.append("用户田间信息与图像判断明显矛盾")
    if result.content_sufficiency == "incomplete":
        reasons.append("图片或田间信息不足")
    if result.needs_human_review:
        reasons.append("多模态模型建议人工复核")
    return list(dict.fromkeys(reason for reason in reasons if reason))


def image_data_url(image_path: Path) -> str:
    suffix = image_path.suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def make_payload(
    *,
    schema_name: str,
    schema: dict[str, Any],
    system_prompt: str,
    user_text: str,
    image_url: str | None,
    max_tokens: int = 1200,
) -> dict[str, Any]:
    user_content: str | list[dict[str, Any]] = user_text
    if image_url:
        user_content = [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
    return {
        "model": settings.vlm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "mm_processor_kwargs": {"max_pixels": 501760},
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
        },
    }


async def post_structured(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    payload: dict[str, Any],
    model: type[ModelT],
    stage: str,
) -> tuple[ModelT, float]:
    started = perf_counter()
    response = await client.post(settings.vlm_endpoint, headers=headers, json=payload)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = response.text.strip().replace("\n", " ")[:600]
        raise httpx.HTTPStatusError(
            f"多模态服务返回 {response.status_code}: {detail}",
            request=exc.request,
            response=response,
        ) from exc
    parsed = parse_model(extract_message_content(response.json()), model, stage)
    return parsed, round((perf_counter() - started) * 1000, 3)


def existing_risk_level(case_record: dict[str, Any]) -> RiskLevel:
    quality = case_record.get("quality") or {}
    summary = case_record.get("detector_summary") or {}
    if quality.get("flags") or not (case_record.get("detections") or []):
        return "high"
    if summary.get("needs_review"):
        return "medium"
    return "low"


async def request_multimodal_analysis(
    case_record: dict[str, Any],
    image_path: Path,
) -> dict[str, Any]:
    if not settings.vlm_endpoint:
        raise MultimodalUnavailable("尚未配置多模态分析服务器")
    headers = {"Content-Type": "application/json"}
    if settings.vlm_api_key:
        headers["Authorization"] = f"Bearer {settings.vlm_api_key}"
    image_url = image_data_url(image_path)
    field_context = {
        "crop": case_record["crop"],
        "part": case_record["part"],
        "growth_stage": case_record["growth_stage"],
        "environment": case_record["environment"],
        "affected_ratio_percent": case_record.get("affected_ratio_percent"),
        "spread_speed": case_record.get("spread_speed", "unknown"),
    }
    independent_payload = make_payload(
        schema_name="crop_pest_independent_image_analysis",
        schema=independent_response_schema(),
        system_prompt=(
            "你是农作物病虫害图像分析助手。本阶段只能独立观察原图，"
            "不会收到也不得猜测 YOLO 结论或任何人工填写信息。无法判断时在列表中明确写‘无法判断’而不是留空。"
            f"primary_diagnosis 必须严格使用以下规范名称之一或‘无法判断’：{CANONICAL_DIAGNOSIS_TEXT}。"
            "observed_part 只能填写叶片、茎秆、果实、根部、整株、田间环境、虫体或系统未判断；"
            "observed_growth_stage 只能填写苗期、营养生长期、开花期、结果期、成熟期或系统未判断。"
            "只有图片中存在直接可见证据时才能判断部位和植株阶段，否则必须填写‘系统未判断’。"
            "每个列表只写 1 至 2 条最重要的短句，每条不超过 30 个汉字。"
            "禁止给出农药产品、剂量、混配、施用次数、复入或采收间隔。只返回指定 JSON。"
        ),
        user_text="请只根据这张原图完成独立图像判断。",
        image_url=image_url,
        max_tokens=500,
    )
    comparison_evidence = {
        "independent_image_judgment": None,
        "quality": case_record.get("quality") or {},
        "yolo_detections": case_record.get("detections") or [],
        "detector_review": {
            "needs_review": (case_record.get("detector_summary") or {}).get("needs_review"),
            "review_reasons": (case_record.get("detector_summary") or {}).get("review_reasons") or [],
        },
        "shadow_expert_evidence": (case_record.get("detector_summary") or {}).get("inference", {}).get("routing"),
        "field_context": field_context,
    }
    detector_summary = case_record.get("detector_summary") or {}
    primary_candidate = detector_summary.get("primary_candidate") or (
        (case_record.get("detections") or [None])[0] or {}
    )
    primary_class_name = str(primary_candidate.get("class_name") or "")
    if primary_class_name:
        external_evidence = await collect_external_evidence(primary_class_name)
    else:
        external_evidence = SearchEvidence(
            class_name="未知",
            status="unavailable",
            message="没有可用于外部检索的 YOLO 主候选",
        )
    qwen_evidence_context = build_qwen_context(external_evidence)
    comparison_evidence["external_evidence"] = qwen_evidence_context
    timeout = httpx.Timeout(
        settings.vlm_timeout_seconds,
        connect=min(10.0, settings.vlm_timeout_seconds),
    )
    total_started = perf_counter()
    async with httpx.AsyncClient(timeout=timeout) as client:
        independent, stage1_ms = await post_structured(
            client,
            headers,
            independent_payload,
            IndependentImageContent,
            "独立图像判断",
        )
        independent = normalize_independent_observations(independent)
        comparison_evidence["independent_image_judgment"] = independent.model_dump()
        comparison_payload = make_payload(
            schema_name="crop_pest_evidence_comparison",
            schema=response_schema(),
            system_prompt=(
                "你是农作物病虫害证据比对助手。比较独立看图、YOLO 框和置信度、shadow 专家证据、"
                "图像质量和田间信息；明确一致、冲突或无法判断。严重度依据必须引用受害比例和扩散速度；"
                f"primary_diagnosis 必须严格使用以下规范名称之一或‘无法判断’：{CANONICAL_DIAGNOSIS_TEXT}。"
                "primary_diagnosis 是综合结论，不是独立判断的复制；YOLO 已对目标完成定位，主候选置信度可靠时"
                "应优先采用，只有独立证据给出具体且充分的反证时才改用其他规范类别。"
                "detector_alignment 只描述独立判断与 YOLO 的关系，不要求综合结论跟随独立判断。"
                "grounded_assessment 中每条危害和可能诱因必须绑定 1 至 4 条本次输入依据。"
                "图片依据使用 source=image、reference=original_image；YOLO依据使用 source=yolo、"
                "reference=yolo_primary 且 observation 必须写出实际主候选名称；田间依据使用"
                "source=field_input，并按 field.crop、field.part、field.growth_stage、field.environment、"
                "field.affected_ratio_percent 或 field.spread_speed 引用，observation 必须写出实际字段值。"
                "不得把百度百科、常识、‘模型认为’或‘通常会导致’当作输入依据。若输入不足，"
                "conclusion 必须准确写‘无法判断’，并用图片依据说明缺少的可见证据。"
                "危害的肯定结论必须至少有图片依据，且只能描述原图直接可见的损伤，禁止写产量、"
                "光合作用、传播或未来后果；可能诱因的肯定结论必须同时有图片与YOLO依据，禁止凭类别"
                "补写病原、真菌、细菌或病毒。不能满足这些条件时必须写‘无法判断’。"
                "evidence_analysis 只允许总结 external_evidence.sources 中实际提供的原文；"
                "每条危害和可能诱因必须填写对应 source_ids，且 source_ids 必须来自输入来源。"
                "external_evidence.status 为 unavailable 时，evidence_analysis.status 必须为 unavailable，"
                "harms 和 possible_causes 必须为空，禁止使用模型自身知识补写。"
                "每个列表只写 1 至 2 条最重要的短句，每条不超过 30 个汉字。"
                "缺任一字段时 field_severity 必须为 unknown。已有低质量、低置信度、无目标或冲突风险只能升级，"
                "不得清除。无法判断时写明原因，所有列表不得留空。禁止具体农药产品、剂量、混配、次数和安全间隔。"
                "只返回指定 JSON。"
            ),
            user_text="请完成第二阶段证据比对：\n"
            + json.dumps(comparison_evidence, ensure_ascii=False, separators=(",", ":")),
            image_url=image_url,
            max_tokens=settings.vlm_output_tokens,
        )
        result, stage2_ms = await post_structured(
            client,
            headers,
            comparison_payload,
            MultimodalContent,
            "证据比对",
        )
        result = validate_grounded_assessment(case_record, result, independent)

    raw_alignment = result.detector_alignment
    raw_primary_diagnosis = result.primary_diagnosis
    result = reconcile_detector_alignment(case_record, result, independent.primary_diagnosis)
    result, primary_diagnosis_source = apply_detector_primary_diagnosis(
        case_record, result, independent.primary_diagnosis
    )
    result = reconcile_field_input_consistency(case_record, result)
    if qwen_evidence_context.get("status") != "available":
        external_analysis = ExternalEvidenceAnalysis()
    else:
        external_analysis = normalize_external_evidence_analysis(result, external_evidence)
    updates: dict[str, Any] = {}
    if field_context["affected_ratio_percent"] is None or field_context["spread_speed"] == "unknown":
        updates.update(
            field_severity="unknown",
            severity_basis="缺少受害比例或扩散速度，无法判断田间严重度。",
            needs_human_review=True,
        )
    else:
        ratio = float(field_context["affected_ratio_percent"])
        ratio_text = f"{ratio:g}"
        speed_label = SPREAD_SPEED_LABELS.get(
            str(field_context["spread_speed"]), str(field_context["spread_speed"])
        )
        prefix = f"用户填写受害比例 {ratio_text}%、扩散速度{speed_label}。"
        updates["severity_basis"] = prefix + result.severity_basis[: 320 - len(prefix)]
    risk_rank = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
    existing_risk = existing_risk_level(case_record)
    if risk_rank[result.diagnostic_risk] < risk_rank[existing_risk]:
        updates["diagnostic_risk"] = existing_risk
    if updates:
        result = result.model_copy(update=updates)
    review_reasons = build_review_reasons(case_record, result)
    output = result.model_dump()
    output.update(
        {
            "status": "completed",
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "independent_judgment": independent.model_dump(),
            "needs_human_review": bool(review_reasons),
            "review_reasons": review_reasons,
            "evidence_analysis": external_analysis.model_dump(),
            "sources": public_sources(external_evidence),
            "evidence_snapshots": persisted_evidence_snapshots(external_evidence),
            "provenance": {
                "model": settings.vlm_model,
                "protocol": ANALYSIS_SCHEMA_VERSION,
                "stages": [
                    {"name": "independent_image_judgment", "latency_ms": stage1_ms},
                    {"name": "evidence_comparison", "latency_ms": stage2_ms},
                ],
                "total_latency_ms": round((perf_counter() - total_started) * 1000, 3),
                "raw_detector_alignment": raw_alignment,
                "alignment_reconciled": raw_alignment != result.detector_alignment,
                "raw_primary_diagnosis": raw_primary_diagnosis,
                "primary_diagnosis_source": primary_diagnosis_source,
                "input_metadata": {
                    "crop": {
                        "value": case_record.get("crop", SYSTEM_UNDETERMINED),
                        "source": "user_input",
                    },
                    "part": {
                        "value": case_record.get("part", SYSTEM_UNDETERMINED),
                        "source": "user_input",
                    },
                    "growth_stage": {
                        "value": case_record.get("growth_stage", SYSTEM_UNDETERMINED),
                        "source": "user_input",
                    },
                },
                "independent_observations": {
                    "part": independent.observed_part,
                    "growth_stage": independent.observed_growth_stage,
                },
                "external_search": {
                    "status": external_evidence.status,
                    "queries": external_evidence.queries,
                    "source_ids": sorted(source_ids(external_evidence)),
                    "message": external_evidence.message,
                },
                "qwen_evidence_context": qwen_evidence_context.get("selection", {}),
            },
        }
    )
    return output
