from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx

from .config import settings


class MultimodalUnavailable(RuntimeError):
    pass


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
    payload = {
        "case_id": case_record["id"],
        "image": image_data_url(image_path),
        "crop": case_record["crop"],
        "part": case_record["part"],
        "growth_stage": case_record["growth_stage"],
        "environment": case_record["environment"],
        "quality": case_record["quality"],
        "detections": case_record["detections"] or [],
        "detector_summary": case_record["detector_summary"],
        "required_schema": {
            "primary_diagnosis": "string|null",
            "candidate_diagnoses": "array",
            "symptoms": "array",
            "harm_level": "low|medium|high|unknown",
            "possible_causes": "array",
            "evidence": "array",
            "uncertainty": "array",
            "needs_human_review": "boolean",
        },
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        response = await client.post(settings.vlm_endpoint, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
    if not isinstance(result, dict):
        raise ValueError("多模态服务必须返回 JSON 对象")
    return result

