from __future__ import annotations

import base64
import json
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from .catalog import CLASS_BY_ID
from .config import settings


class MultimodalUnavailable(RuntimeError):
    pass


ANALYSIS_SCHEMA_VERSION = "phase8-multimodal-v1"
ShortText = Annotated[str, Field(max_length=120)]


class MultimodalContent(BaseModel):
    primary_diagnosis: str | None = Field(max_length=200)
    candidate_diagnoses: list[ShortText] = Field(max_length=4)
    symptoms: list[ShortText] = Field(max_length=5)
    harm_level: Literal["low", "medium", "high", "unknown"]
    possible_causes: list[ShortText] = Field(max_length=5)
    evidence: list[ShortText] = Field(max_length=6)
    uncertainty: list[ShortText] = Field(max_length=5)
    detector_alignment: Literal["agree", "uncertain", "conflict"]
    needs_human_review: bool


def response_schema() -> dict[str, Any]:
    return MultimodalContent.model_json_schema()


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


def parse_content(content: str) -> MultimodalContent:
    cleaned = content.strip()
    if cleaned.startswith("```json") and cleaned.endswith("```"):
        cleaned = cleaned[7:-3].strip()
    elif cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
    try:
        return MultimodalContent.model_validate_json(cleaned)
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"多模态分析结果不符合 {ANALYSIS_SCHEMA_VERSION}：{exc}") from exc


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
    case_record: dict[str, Any], result: MultimodalContent
) -> MultimodalContent:
    detections = case_record.get("detections") or []
    if not detections or not result.primary_diagnosis:
        return result.model_copy(update={"detector_alignment": "uncertain"})
    summary = case_record.get("detector_summary") or {}
    candidate = summary.get("primary_candidate") or detections[0]
    detector_class_id = candidate.get("class_id")
    diagnosis_id = diagnosis_class_id(result.primary_diagnosis)
    if detector_class_id is None or diagnosis_id is None:
        return result.model_copy(update={"detector_alignment": "uncertain"})
    if diagnosis_id == int(detector_class_id):
        return result.model_copy(update={"detector_alignment": "agree"})
    return result.model_copy(update={"detector_alignment": "conflict"})


def build_review_reasons(case_record: dict[str, Any], result: MultimodalContent) -> list[str]:
    summary = case_record.get("detector_summary") or {}
    quality = case_record.get("quality") or {}
    detections = case_record.get("detections") or []
    reasons = list(summary.get("review_reasons") or [])
    reasons.extend(quality.get("flags") or [])
    if not detections:
        reasons.append("视觉模型未定位到明确目标")
    if result.detector_alignment == "conflict":
        reasons.append("多模态判断与视觉候选冲突")
    elif result.detector_alignment == "uncertain":
        reasons.append("多模态判断与视觉候选的一致性不确定")
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


async def request_multimodal_analysis(
    case_record: dict[str, Any],
    image_path: Path,
) -> dict[str, Any]:
    if not settings.vlm_endpoint:
        raise MultimodalUnavailable("尚未配置多模态分析服务器")
    headers = {"Content-Type": "application/json"}
    if settings.vlm_api_key:
        headers["Authorization"] = f"Bearer {settings.vlm_api_key}"
    evidence = {
        "case_id": case_record["id"],
        "crop": case_record["crop"],
        "part": case_record["part"],
        "growth_stage": case_record["growth_stage"],
        "environment": case_record["environment"],
        "notes": case_record.get("notes", ""),
        "quality": case_record["quality"],
        "detections": case_record["detections"] or [],
        "detector_summary": case_record["detector_summary"],
    }
    system_prompt = (
        "你是农作物病虫害多模态分析助手。只能依据原图和给定视觉证据形成候选结论；"
        "不得把不确定判断写成确定事实。视觉模型无目标、低置信度、图像质量异常或模型冲突时必须建议人工复核。"
        "禁止给出农药产品、剂量、混配、复入间隔或采收安全间隔。每个列表最多写3条，每条保持简短；只返回指定 JSON schema。"
    )
    payload = {
        "model": settings.vlm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请结合原图分析以下结构化证据：\n"
                        + json.dumps(evidence, ensure_ascii=False, separators=(",", ":")),
                    },
                    {"type": "image_url", "image_url": {"url": image_data_url(image_path)}},
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": 1200,
        "mm_processor_kwargs": {"max_pixels": 1003520},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "crop_pest_analysis",
                "strict": True,
                "schema": response_schema(),
            },
        },
    }
    started = perf_counter()
    timeout = httpx.Timeout(settings.vlm_timeout_seconds, connect=min(10.0, settings.vlm_timeout_seconds))
    async with httpx.AsyncClient(timeout=timeout) as client:
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
        response_payload = response.json()
    result = parse_content(extract_message_content(response_payload))
    raw_alignment = result.detector_alignment
    result = reconcile_detector_alignment(case_record, result)
    review_reasons = build_review_reasons(case_record, result)
    output = result.model_dump()
    output.update(
        {
            "status": "completed",
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "needs_human_review": bool(review_reasons),
            "review_reasons": review_reasons,
            "provenance": {
                "model": settings.vlm_model,
                "protocol": "openai_chat_completions",
                "latency_ms": round((perf_counter() - started) * 1000, 3),
                "raw_detector_alignment": raw_alignment,
                "alignment_reconciled": raw_alignment != result.detector_alignment,
            },
        }
    )
    return output
