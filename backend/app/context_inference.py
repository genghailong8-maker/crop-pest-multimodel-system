from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from .config import settings
from .r3_taxonomy import normalize_prediction


class ContextInferenceUnavailable(RuntimeError):
    pass


def infer_context(image_path: Path) -> dict[str, Any]:
    if not settings.context_endpoint:
        raise ContextInferenceUnavailable("R3 主体上下文服务尚未配置")
    headers = {}
    if settings.context_api_key:
        headers["Authorization"] = f"Bearer {settings.context_api_key}"
    try:
        with image_path.open("rb") as image_file:
            response = httpx.post(
                settings.context_endpoint,
                headers=headers,
                files={"image": (image_path.name, image_file, "application/octet-stream")},
                timeout=settings.context_timeout_seconds,
            )
        response.raise_for_status()
        return normalize_prediction(response.json())
    except (OSError, httpx.HTTPError, ValueError) as exc:
        raise ContextInferenceUnavailable(f"主体上下文服务调用失败：{exc}") from exc
