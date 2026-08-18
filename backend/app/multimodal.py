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


class MultimodalUnavailable(RuntimeError):
    pass


ANALYSIS_SCHEMA_VERSION = "phase9-multimodal-v2"
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


class IndependentImageContent(BaseModel):
    primary_diagnosis: ShortText
    candidate_diagnoses: list[ShortText] = Field(min_length=1, max_length=4)
    symptoms: list[ShortText] = Field(min_length=1, max_length=5)
    possible_causes: list[ShortText] = Field(min_length=1, max_length=5)
    evidence: list[ShortText] = Field(min_length=1, max_length=6)
    uncertainty: list[ShortText] = Field(min_length=1, max_length=5)
    required_additional_photos: list[ShortText] = Field(min_length=1, max_length=4)


class MultimodalContent(BaseModel):
    primary_diagnosis: ShortText
    candidate_diagnoses: list[ShortText] = Field(min_length=1, max_length=4)
    symptoms: list[ShortText] = Field(min_length=1, max_length=5)
    harm: list[ShortText] = Field(min_length=1, max_length=4)
    harm_level: RiskLevel
    possible_causes: list[ShortText] = Field(min_length=1, max_length=5)
    evidence: list[ShortText] = Field(min_length=1, max_length=6)
    uncertainty: list[ShortText] = Field(min_length=1, max_length=5)
    required_additional_photos: list[ShortText] = Field(min_length=1, max_length=4)
    detector_alignment: Literal["agree", "uncertain", "conflict"]
    field_input_consistency: Literal["consistent", "uncertain", "conflict"]
    content_sufficiency: Literal["sufficient", "incomplete"]
    diagnostic_risk: RiskLevel
    field_severity: RiskLevel
    severity_basis: str = Field(min_length=1, max_length=320)
    needs_human_review: bool


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
        "mm_processor_kwargs": {"max_pixels": 1003520},
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
        "case_id": case_record["id"],
        "crop": case_record["crop"],
        "part": case_record["part"],
        "growth_stage": case_record["growth_stage"],
        "environment": case_record["environment"],
        "notes": case_record.get("notes", ""),
        "affected_ratio_percent": case_record.get("affected_ratio_percent"),
        "spread_speed": case_record.get("spread_speed", "unknown"),
    }
    independent_payload = make_payload(
        schema_name="crop_pest_independent_image_analysis",
        schema=independent_response_schema(),
        system_prompt=(
            "你是农作物病虫害图像分析助手。本阶段必须独立观察原图和田间信息，"
            "不会收到也不得猜测 YOLO 结论。无法判断时在列表中明确写‘无法判断’而不是留空。"
            f"primary_diagnosis 必须严格使用以下规范名称之一或‘无法判断’：{CANONICAL_DIAGNOSIS_TEXT}。"
            "每个列表只写 1 至 2 条最重要的短句，每条不超过 30 个汉字。"
            "禁止给出农药产品、剂量、混配、施用次数、复入或采收间隔。只返回指定 JSON。"
        ),
        user_text="请独立分析原图与田间信息：\n"
        + json.dumps(field_context, ensure_ascii=False, separators=(",", ":")),
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
                "每个列表只写 1 至 2 条最重要的短句，每条不超过 30 个汉字。"
                "缺任一字段时 field_severity 必须为 unknown。已有低质量、低置信度、无目标或冲突风险只能升级，"
                "不得清除。无法判断时写明原因，所有列表不得留空。禁止具体农药产品、剂量、混配、次数和安全间隔。"
                "只返回指定 JSON。"
            ),
            user_text="请完成第二阶段证据比对：\n"
            + json.dumps(comparison_evidence, ensure_ascii=False, separators=(",", ":")),
            image_url=None,
            max_tokens=700,
        )
        result, stage2_ms = await post_structured(
            client,
            headers,
            comparison_payload,
            MultimodalContent,
            "证据比对",
        )

    raw_alignment = result.detector_alignment
    raw_primary_diagnosis = result.primary_diagnosis
    result = reconcile_detector_alignment(case_record, result, independent.primary_diagnosis)
    result, primary_diagnosis_source = apply_detector_primary_diagnosis(
        case_record, result, independent.primary_diagnosis
    )
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
            },
        }
    )
    return output
