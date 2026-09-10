from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import shutil
import secrets
import threading
import time
import uuid
from copy import deepcopy
from collections import Counter, defaultdict, deque
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
import httpx
from markdown_it import MarkdownIt

from .catalog import CLASS_CATALOG
from .case_context import (
    GROWTH_STAGE_INPUTS,
    GROWTH_STAGE_LABELS,
    build_case_context,
)
from .config import LOW_CONFIDENCE_THRESHOLD, settings
from .control import COOKIE_NAME, ControlStore, issue_session, valid_session, verify_password
from .database import (
    create_case,
    get_case,
    get_edit_token_hash,
    init_database,
    list_cases,
    public_expiry,
    purge_expired_cases,
    stored_image_path,
    update_case,
)
from .detector import DetectorUnavailable, detector, inspect_image_quality, summarize_detections
from .context_inference import ContextInferenceUnavailable, infer_context
from .drafts import create_draft, draft_image_path, draft_response, get_draft, update_draft
from .r3_taxonomy import taxonomy_payload, validate_context_values
from .knowledge import (
    build_explainability,
    get_knowledge_card,
    get_knowledge_sources,
    knowledge_contract,
    prioritized_guidance,
)
from .analysis import request_evidence_analysis
from .knowledge_documents import get_knowledge_document, resolve_knowledge_asset
from .reports import load_latest, save_snapshot
from .r31_host_knowledge import (
    OTHER_HOST,
    confirmable_hosts,
    host_knowledge_payload,
    host_selection_snapshot,
)
from .prelabels import detail as prelabel_detail
from .prelabels import image_path as prelabel_image_path
from .prelabels import queue as prelabel_queue
from .prelabels import save_review as save_prelabel_review
from .severity import SeverityInputError, TierTreatmentError, is_spread_speed_missing, select_tier_treatment, severity_for_record
from .severity_v2 import (
    SEVERITY_V2_LEVELS,
    references_for_canonical,
    rubric_for_canonical,
    severity_pending_payload,
    severity_payload as severity_v2_payload,
)


MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
CROP_OPTIONS = {"玉米", "番茄", "南瓜", "马铃薯", "昆虫"}
PART_OPTIONS = {"叶片", "茎秆", "果实", "根部", "整株"}
GROWTH_STAGE_OPTIONS = set(GROWTH_STAGE_INPUTS) | set(GROWTH_STAGE_LABELS)
ENVIRONMENT_OPTIONS = {"露地", "温室", "大棚", "室内样本", "未知"}
NOT_APPLICABLE = "不适用"
logger = logging.getLogger(__name__)
_TREATMENT_MARKDOWN = MarkdownIt("commonmark")


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int = 3600) -> bool:
        now = time.monotonic()
        with self._lock:
            events = self._events[key]
            while events and now - events[0] >= window_seconds:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True


rate_limiter = SlidingWindowLimiter()


class ReviewRequest(BaseModel):
    decision: Literal["accepted", "needs_more_evidence", "rejected"] = "accepted"
    final_class_id: int | None = Field(default=None, ge=0, le=15)
    final_diagnosis: str | None = Field(default=None, max_length=200)
    severity: str = Field(default="unknown", pattern="^(low|medium|high|unknown)$")
    accepted_detection_indexes: list[int] = Field(default_factory=list)
    reviewer_notes: str = Field(default="", max_length=2000)
    reviewer_id: str = Field(default="local-reviewer", min_length=1, max_length=80)


class SeverityV2Request(BaseModel):
    severity_level: Literal["mild", "moderate", "severe", "uncertain"]


class HostConfirmationRequest(BaseModel):
    confirmed_host: str = Field(min_length=1, max_length=40)


class R3ContextConfirmationRequest(BaseModel):
    subject_type: Literal["plant", "insect"]
    crop_species: str | None = Field(default=None, max_length=40)
    affected_part: str | None = Field(default=None, max_length=40)
    insect_species: str | None = Field(default=None, max_length=40)


class PrelabelReviewRequest(BaseModel):
    decision: str = Field(pattern="^(accepted|needs_rework|skipped)$")
    boxes: list[dict[str, Any]] = Field(default_factory=list, max_length=1000)
    notes: str = Field(default="", max_length=2000)


class AdminLoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=512)


class InstanceSwitchRequest(BaseModel):
    instance_id: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    if settings.public_mode:
        purge_expired_cases()
    yield


app = FastAPI(
    title="农作物病虫害识别与防治系统 API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def control_store() -> ControlStore:
    return ControlStore(settings.control_dir, settings.instance_id)


def instance_for_request(request: Request) -> str:
    supplied = request.headers.get("x-crop-instance")
    allowed = {settings.instance_id, settings.remote_instance_id}
    if supplied:
        return supplied if supplied in allowed else "invalid"
    path = request.url.path
    if path.startswith("/api/cases/"):
        case_id = path.removeprefix("/api/cases/").split("/", 1)[0]
        for candidate in allowed:
            if case_id.startswith(f"{candidate}-"):
                return candidate
    return control_store().active_instance()


def should_route_instance(path: str) -> bool:
    return path == "/api/cases" or path.startswith("/api/cases/") or path == "/api/trends"


@app.middleware("http")
async def route_active_instance(request: Request, call_next):
    if not settings.gateway_mode or not should_route_instance(request.url.path):
        return await call_next(request)
    target = instance_for_request(request)
    if target == "invalid":
        return JSONResponse(status_code=409, content={"detail": "请求中的实例标识无效"})
    if target == settings.instance_id:
        return await call_next(request)
    if target != settings.remote_instance_id or not settings.remote_backend_url:
        return JSONResponse(status_code=503, content={"detail": "目标识别服务器未配置或当前离线"})
    target_url = f"{settings.remote_backend_url.rstrip('/')}{request.url.path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    headers = dict(request.headers)
    headers.pop("host", None)
    try:
        async with httpx.AsyncClient(timeout=settings.remote_backend_timeout_seconds) as client:
            proxied = await client.request(
                request.method,
                target_url,
                headers=headers,
                content=await request.body(),
            )
    except httpx.HTTPError as exc:
        logger.warning("Remote instance proxy failed: %s", exc)
        return JSONResponse(status_code=503, content={"detail": "目标识别服务器暂时不可用"})
    excluded = {"connection", "content-encoding", "content-length", "transfer-encoding"}
    response_headers = {
        key: value for key, value in proxied.headers.items() if key.lower() not in excluded
    }
    response_headers["Cache-Control"] = "no-store"
    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=response_headers,
        media_type=proxied.headers.get("content-type"),
    )


def is_admin_data_request(request: Request) -> bool:
    path = request.url.path
    if path.startswith("/api/prelabels/") or path == "/api/prelabels/queue":
        return True
    if path == "/api/cases/review-queue" or path.endswith("/review-events"):
        return True
    if path.startswith("/api/cases/") and path.endswith("/review") and request.method == "POST":
        return True
    return path == "/api/cases" and request.query_params.get("record_scope", "user") != "user"


@app.middleware("http")
async def protect_admin_data(request: Request, call_next):
    if (
        settings.admin_password_hash
        and not settings.public_mode
        and is_admin_data_request(request)
        and not valid_session(request.cookies.get(COOKIE_NAME), settings.admin_session_secret)
    ):
        return JSONResponse(status_code=401, content={"detail": "请先登录管理端"})
    return await call_next(request)


@app.middleware("http")
async def protect_public_origin(request: Request, call_next):
    if settings.public_mode and request.url.path.startswith("/api/"):
        expected = settings.public_origin_secret
        supplied = request.headers.get("x-crop-origin-secret")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            return JSONResponse(status_code=403, content={"detail": "公网 API 仅允许受信任代理访问"})
    return await call_next(request)


def require_case(case_id: str) -> dict[str, Any]:
    record = get_case(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="识别记录不存在")
    return record


def require_visible_case(case_id: str) -> dict[str, Any]:
    record = require_case(case_id)
    if settings.public_mode:
        expires_at = record.get("expires_at")
        if not record.get("public_consent") or not expires_at or expires_at <= datetime.now(UTC).isoformat():
            raise HTTPException(status_code=404, detail="识别记录不存在")
    return record


def require_local_admin() -> None:
    if settings.public_mode:
        raise HTTPException(status_code=404, detail="页面不存在")


def require_admin_session(request: Request) -> None:
    if not valid_session(request.cookies.get(COOKIE_NAME), settings.admin_session_secret):
        raise HTTPException(status_code=401, detail="请先登录管理端")


def require_edit_token(case_id: str, token: str | None) -> None:
    if not settings.public_mode:
        return
    expected = get_edit_token_hash(case_id)
    supplied = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    if not expected or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=403, detail="缺少有效的病例编辑令牌")


def require_draft(draft_id: str) -> dict[str, Any]:
    draft = get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="分析草稿不存在或已过期")
    expires_at = draft.get("expires_at")
    if isinstance(expires_at, str) and expires_at <= datetime.now(UTC).isoformat():
        raise HTTPException(status_code=410, detail="分析草稿已过期，请重新上传图片")
    return draft


def require_draft_edit_token(draft: dict[str, Any], token: str | None) -> None:
    if not settings.public_mode:
        return
    expected = draft.get("edit_token_hash")
    supplied = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    if not expected or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=403, detail="缺少有效的草稿编辑令牌")


def client_ip(request: Request) -> str:
    if settings.public_mode:
        forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        return forwarded or "unknown"
    return request.client.host if request.client else "local"


def enforce_rate(request: Request, action: str, limit: int) -> None:
    if settings.public_mode and not rate_limiter.allow(f"{action}:{client_ip(request)}", limit):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")


def derive_diagnostic_risk(record: dict[str, Any], analysis: dict[str, Any] | None = None) -> str:
    summary = record.get("detector_summary") or {}
    quality = record.get("quality") or {}
    if quality.get("flags") or not (record.get("detections") or []):
        return "high"
    if analysis and analysis.get("detector_alignment") in {"conflict", "uncertain"}:
        return "high"
    if summary.get("needs_review") or (analysis and analysis.get("needs_human_review")):
        return "medium"
    return "low"


def local_treatment_payload(record: dict[str, Any]) -> dict[str, Any]:
    detections = record.get("detections") or []
    primary = (record.get("detector_summary") or {}).get("primary_candidate") or (
        detections[0] if detections else {}
    )
    class_id = primary.get("class_id") if isinstance(primary, dict) else None
    card = get_knowledge_card(int(class_id)) if isinstance(class_id, int) else None
    document = get_knowledge_document(int(class_id)) if isinstance(class_id, int) else None
    if card is None:
        return {"source": "local_knowledge_base", "content": {}, "source_ids": []}
    severity = record.get("severity")
    if not isinstance(severity, dict):
        severity = (record.get("analysis") or {}).get("severity")
    if not isinstance(severity, dict):
        try:
            severity = severity_for_record(record).as_dict()
        except SeverityInputError:
            return {
                "source": "local_knowledge_base",
                "status": "unavailable",
                "reason": "legacy_severity_input_incomplete",
                "content": {},
                "source_ids": [],
                "sources": [],
            }
    if severity.get("algorithm_version") == "severity-v2":
        if severity.get("status") != "available":
            return _blocked_treatment(severity, "unavailable", "severity_not_selected")
        level = str(severity.get("level") or "")
        canonical = primary.get("class_name") if isinstance(primary, dict) else None
        if not isinstance(canonical, str):
            return _blocked_treatment(severity, "unavailable", "missing_canonical_class")
    if severity.get("status") == "available" and severity.get("level"):
        try:
            selected = select_tier_treatment(str(document["markdown"]) if document else "", str(severity["level"]))
        except TierTreatmentError:
            return {
                "source": "local_knowledge_base",
                "status": "unavailable",
                "severity_level": severity["level"],
                "severity_label": severity.get("label"),
                "content": {},
                "source_ids": [],
                "sources": [],
                "error": "对应严重度的知识库防治内容暂不可用。",
            }
        return {
            "source": "local_knowledge_base",
            "status": "available",
            "severity_level": selected.level,
            "severity_label": selected.label,
            "content": {
                "tier": selected.label,
                "markdown": selected.content,
                "markdown_html": _TREATMENT_MARKDOWN.render(selected.content),
            },
            "source_ids": list(selected.source_ids),
            "sources": [source.as_dict() for source in selected.sources],
            "requires_pesticide_warning": bool(document and document.get("requires_pesticide_warning")),
            "pesticide_warning": document.get("pesticide_warning") if document else None,
        }
    return {
        "source": "local_knowledge_base",
        "status": "available",
        "treatment_mode": "generic",
        "content": {
            "prevention": card.get("prevention", []),
            "first_actions": card.get("first_actions", []),
            "management": card.get("management", {}),
            "prevention_html": document.get("prevention_html") if document else None,
        },
        "source_ids": list(card.get("source_ids", [])),
        "requires_pesticide_warning": bool(document and document.get("requires_pesticide_warning")),
        "pesticide_warning": document.get("pesticide_warning") if document else None,
    }


def _blocked_treatment(severity: dict[str, Any], status: str, reason: str) -> dict[str, Any]:
    """Return a fail-closed V2 treatment result with no content or sources."""
    return {
        "source": "local_knowledge_base",
        "status": status,
        "reason": reason,
        "severity_level": severity.get("level"),
        "severity_label": severity.get("label"),
        "content": {},
        "source_ids": [],
        "sources": [],
    }


def severity_rubric_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Expose only the exact YOLO-selected V2 rubric; never guess a class."""
    summary = record.get("detector_summary") or {}
    detections = record.get("detections") or []
    primary = summary.get("primary_candidate") or (detections[0] if detections else {})
    canonical = primary.get("class_name") if isinstance(primary, dict) else None
    if not isinstance(canonical, str):
        return {"status": "unavailable", "reason": "missing_canonical_class"}
    rubric = rubric_for_canonical(canonical)
    if rubric is None:
        return {"status": "unavailable", "reason": "severity_rubric_unavailable"}
    return {
        "status": "available",
        "canonical_class": canonical,
        "rubric": rubric,
        "references": references_for_canonical(canonical),
    }


def evidence_snapshots_for_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = record.get("analysis") or {}
    snapshots = analysis.get("evidence_snapshots")
    sources = analysis.get("sources") or []
    source_ids = {
        source.get("id")
        for source in sources
        if isinstance(source, dict) and source.get("id")
    }
    if not isinstance(snapshots, list):
        return []
    return [
        snapshot
        for snapshot in snapshots
        if isinstance(snapshot, dict)
        and snapshot.get("source_id") in source_ids
        and isinstance(snapshot.get("content"), str)
        and snapshot.get("content")
    ]


_PUBLIC_EVIDENCE_TRANSLATIONS = {
    "A shortage of nitrogen supply, increased humidity, appropriate temperature, and rainy weather all increase the possibility of an EB outbreak":
        "氮素供应不足、湿度升高、温度适宜以及多雨天气，都会增加早疫病暴发的可能性。",
    # Deterministic public-language contract for the currently accepted
    # Tomato Septoria source sentences. Source IDs/provenance are untouched.
    "Symptoms appear on the leaves as circular, tan-to-gray spots with darker brown margins and dotted with dark, raised pycnidia inside the lesion":
        "叶片上出现圆形、黄褐至灰色的斑点，边缘较深褐色，病斑内部可见深色隆起的分生孢子器。",
    "Lesions can converge and lead to defoliation of lower leaves, and in severe cases the death of an entire plant":
        "病斑可相互汇合，导致下部叶片脱落；严重时可造成整株植株死亡。",
    "Favorable conditions: High humidity, moderate temperatures (68-77ºF), high dew point/wet conditions, poor airflow":
        "有利条件：高湿度、适中温度（68–77°F）、露点较高或叶面湿润，以及通风不良。",
    "Warm temperatures and high humidity are favorable conditions for this disease":
        "温暖和高湿是该病发生的有利条件。",
    "EB affects plants above ground, with symptoms ranging from small brownish to dark lesions to large ones that always begin on old leaves and grow upward (Sherf and MacNab, 1986; Dhaval et al., 2021)":
        "早疫病地上部症状表现为由小型褐色斑点至深色病斑再到大型病斑，且病斑总是先从老叶开始并向上发展。",
}
_PUBLIC_ENGLISH_WORD = re.compile(r"[A-Za-z]{2,}")
_PUBLIC_TRADITIONAL_TO_SIMPLIFIED = str.maketrans({
    "覆": "覆",
    "蓋": "盖",
    "個": "个",
    "葉": "叶",
    "影": "影",
    "響": "响",
    "出": "出",
    "現": "现",
    "粉": "粉",
    "狀": "状",
    "病": "病",
    "徵": "征",
})


def _format_public_evidence_conclusion(value: str) -> str | None:
    formatted = _PUBLIC_EVIDENCE_TRANSLATIONS.get(value, value)
    formatted = formatted.translate(_PUBLIC_TRADITIONAL_TO_SIMPLIFIED)
    formatted = re.sub(r"\s*\|\s*", "；", formatted).strip(" ；")
    # Public Evidence is Chinese-only. Unknown English is withheld rather
    # than translated without source support; raw analysis/provenance stays.
    return None if _PUBLIC_ENGLISH_WORD.search(formatted) else formatted


def _format_public_evidence_analysis(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    formatted = deepcopy(value)
    for section in ("harms", "possible_causes"):
        items = formatted.get(section)
        if not isinstance(items, list):
            continue
        kept: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("conclusion"), str):
                conclusion = _format_public_evidence_conclusion(item["conclusion"])
                if conclusion is None:
                    continue
                item["conclusion"] = conclusion
            kept.append(item)
        formatted[section] = kept
    return formatted


def public_analysis_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _format_public_evidence_analysis(value) if key == "evidence_analysis" else value
        for key, value in analysis.items()
        if key != "evidence_snapshots"
    }


def present_case(
    record: dict[str, Any], *, include_evidence_snapshots: bool = False
) -> dict[str, Any]:
    """Translate technical evidence into one honest user-facing outcome."""
    status = record.get("status")
    if isinstance(record.get("severity"), dict):
        severity = record["severity"]
    else:
        try:
            severity = severity_for_record(record).as_dict()
        except SeverityInputError:
            severity = {
                "status": "not_provided",
                "level": None,
                "label": None,
                "source": "legacy_v1",
                "algorithm_version": "severity_v1",
                "decision_rule": "legacy_inputs_incomplete",
            }
    quality_flags = list((record.get("quality") or {}).get("flags") or [])
    detections = record.get("detections")
    summary = record.get("detector_summary") or {}
    analysis = record.get("analysis") or {}
    public_analysis = public_analysis_payload(analysis)
    primary = summary.get("primary_candidate") or {}
    confidence = primary.get("max_confidence")
    reasons: list[str] = []

    if status in {"model_unavailable", "multimodal_unavailable"}:
        resolution_status = "service_unavailable"
        if status == "model_unavailable":
            user_summary = "图片已经保存，但识别服务暂时不可用。"
            next_action = "服务恢复后重新进行图片识别。"
        else:
            user_summary = "图片识别结果已经保存，但综合分析暂时不可用。"
            next_action = "服务恢复后只需重试综合分析。"
        reasons = list(summary.get("review_reasons") or [])
    elif detections == []:
        resolution_status = "no_supported_target"
        user_summary = "没有发现系统当前支持的病斑或害虫。"
        next_action = "请靠近异常部位重新拍摄，并保证光线充足、画面清晰。"
        reasons = ["视觉模型未定位到支持的目标"]
    elif isinstance(confidence, (int, float)) and confidence < LOW_CONFIDENCE_THRESHOLD:
        resolution_status = "retake_required"
        user_summary = "无法可靠判断当前结果。"
        next_action = "请重新上传图片，或补拍异常部位近照和整株照片。"
        reasons = ["最高视觉置信度低于 50%", *quality_flags]
    else:
        resolution_status = "conclusive"
        user_summary = "现有图片和信息足以给出可参考的辅助判断。"
        next_action = "查看发现位置、判断依据和下一步处理建议。"

    r31_host_knowledge = host_knowledge_payload(record)
    response = {
        **record,
        "analysis": public_analysis,
        "evidence_analysis": public_analysis.get(
            "evidence_analysis",
            {"status": "unavailable", "harms": [], "possible_causes": []},
        ),
        "sources": list(public_analysis.get("sources") or []),
        "severity": severity,
        "severity_rubric": severity_rubric_payload(record),
        "treatment": local_treatment_payload(record),
        "resolution_status": resolution_status,
        "user_summary": user_summary,
        "next_action": next_action,
        "resolution_reasons": reasons,
        "case_context": build_case_context(record, severity=severity),
    }
    if r31_host_knowledge.get("available"):
        response["host_knowledge"] = r31_host_knowledge
    if include_evidence_snapshots:
        response["evidence_snapshots"] = evidence_snapshots_for_record(record)
    return response


@app.get("/health")
def health() -> dict[str, Any]:
    usage = shutil.disk_usage(settings.storage_dir)
    active_instance_id = (
        control_store().active_instance() if settings.gateway_mode else settings.instance_id
    )
    active_is_remote = active_instance_id == settings.remote_instance_id
    return {
        "status": "ok",
        "instance_id": settings.instance_id,
        "instance_label": settings.instance_label,
        "active_instance_id": active_instance_id,
        "active_instance_label": (
            settings.remote_instance_label if active_is_remote else settings.instance_label
        ),
        "active_instance_mode": "gpu" if active_is_remote else "cpu",
        "model_configured": bool(
            settings.detector_endpoint or (settings.model_path and settings.model_path.exists())
        ),
        "detector_mode": (
            "remote"
            if settings.detector_endpoint
            else "local"
            if settings.model_path and settings.model_path.exists()
            else "unconfigured"
        ),
        "evidence_extractor": "deterministic_cpu",
        "public_mode": settings.public_mode,
        "storage_free_bytes": usage.free,
        "case_count": len(list_cases(10_000, record_scope="all")),
    }


async def remote_health() -> dict[str, Any]:
    if not settings.remote_backend_url:
        return {"status": "offline", "detail": "未配置远端后端地址"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.remote_backend_url.rstrip('/')}/health")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {"status": "offline", "detail": str(exc)}
    return {**payload, "status": "online"}


@app.post("/api/admin/login")
def admin_login(payload: AdminLoginRequest) -> JSONResponse:
    if not settings.admin_password_hash or not settings.admin_session_secret:
        raise HTTPException(status_code=503, detail="管理端密码尚未配置")
    if not verify_password(payload.password, settings.admin_password_hash):
        raise HTTPException(status_code=401, detail="管理员密码错误")
    token = issue_session(settings.admin_session_secret, settings.admin_session_ttl_seconds)
    response = JSONResponse({"authenticated": True})
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.admin_session_ttl_seconds,
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite="lax",
        path="/",
    )
    return response


@app.post("/api/admin/logout")
def admin_logout() -> JSONResponse:
    response = JSONResponse({"authenticated": False})
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@app.get("/api/admin/session")
def admin_session(request: Request) -> dict[str, bool]:
    return {
        "authenticated": valid_session(
            request.cookies.get(COOKIE_NAME), settings.admin_session_secret
        )
    }


@app.get("/api/admin/instances")
async def admin_instances(request: Request) -> dict[str, Any]:
    require_admin_session(request)
    local = health()
    remote = await remote_health()
    return {
        "active_instance": control_store().active_instance(),
        "instances": [
            {
                **local,
                "status": "online",
                "instance_id": settings.instance_id,
                "instance_label": settings.instance_label,
                "mode": "cpu",
            },
            {
                **remote,
                "instance_id": settings.remote_instance_id,
                "instance_label": settings.remote_instance_label,
                "mode": "gpu",
            },
        ],
        "audit": control_store().audit(),
        "data_policy": "病例、图片和报告只保存在创建它们的实例，不自动同步。",
    }


@app.post("/api/admin/instances/activate")
async def activate_instance(payload: InstanceSwitchRequest, request: Request) -> dict[str, Any]:
    require_admin_session(request)
    allowed = {settings.instance_id, settings.remote_instance_id}
    if payload.instance_id not in allowed:
        raise HTTPException(status_code=422, detail="未知的识别实例")
    if payload.instance_id == settings.remote_instance_id:
        status = await remote_health()
        if status.get("status") != "online":
            raise HTTPException(status_code=409, detail="GPU 服务器健康检查未通过，未执行切换")
    event = control_store().switch(payload.instance_id)
    return {"active_instance": payload.instance_id, "event": event}


@app.get("/api/catalog/classes")
def classes() -> list[dict[str, Any]]:
    return CLASS_CATALOG


@app.get("/api/catalog/knowledge")
def knowledge() -> dict[str, Any]:
    return knowledge_contract()


@app.get("/api/catalog/classes/{class_id}/knowledge")
def class_knowledge(class_id: int) -> dict[str, Any]:
    card = get_knowledge_card(class_id)
    if card is None:
        raise HTTPException(status_code=404, detail="类别知识卡片不存在")
    return card


@app.get("/api/catalog/classes/{class_id}/knowledge-document")
def class_knowledge_document(class_id: int) -> dict[str, Any]:
    document = get_knowledge_document(class_id)
    if document is None:
        raise HTTPException(status_code=404, detail="类别知识文档不存在")
    return document


@app.get("/api/catalog/knowledge/assets/{version}/{asset_path:path}")
def knowledge_asset(version: str, asset_path: str) -> FileResponse:
    path = resolve_knowledge_asset(version, asset_path)
    if path is None:
        raise HTTPException(status_code=404, detail="知识库图片不存在")
    return FileResponse(path)


@app.get("/api/prelabels/queue")
def prelabel_queue_endpoint(
    priority: Annotated[str | None, Query(pattern="^(all|P0|P1|P2)$")] = "all",
) -> dict[str, Any]:
    require_local_admin()
    return prelabel_queue(settings.prelabel_dir, priority)


@app.get("/api/prelabels/{image_id}")
def prelabel_detail_endpoint(image_id: str) -> dict[str, Any]:
    require_local_admin()
    return prelabel_detail(settings.prelabel_dir, image_id)


@app.get("/api/prelabels/{image_id}/image")
def prelabel_image_endpoint(image_id: str) -> FileResponse:
    require_local_admin()
    path = prelabel_image_path(settings.prelabel_dir, image_id)
    return FileResponse(path, filename=path.name)


@app.post("/api/prelabels/{image_id}/review")
def prelabel_review_endpoint(image_id: str, request: PrelabelReviewRequest) -> dict[str, Any]:
    require_local_admin()
    return save_prelabel_review(
        settings.prelabel_dir,
        image_id,
        request.decision,
        request.boxes,
        request.notes,
    )


@app.get("/api/cases")
def cases(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    crop: str | None = None,
    class_id: Annotated[int | None, Query(ge=0, le=15)] = None,
    severity: Annotated[str | None, Query(pattern="^(low|medium|high|unknown)$")] = None,
    scope: Annotated[Literal["public", "all"] | None, Query()] = None,
    record_scope: Annotated[Literal["user", "test", "all"], Query()] = "user",
) -> list[dict[str, Any]]:
    selected_scope = scope or ("public" if settings.public_mode else "all")
    if settings.public_mode:
        purge_expired_cases()
    if selected_scope == "all":
        require_local_admin()
    if settings.public_mode and record_scope != "user":
        raise HTTPException(status_code=404, detail="页面不存在")
    records = list_cases(
        limit,
        public_only=selected_scope == "public",
        crop=crop,
        class_id=class_id,
        severity=severity,
        record_scope=record_scope,
    )
    return [present_case(record) for record in records]


@app.get("/api/cases/review-queue")
def review_queue(limit: Annotated[int, Query(ge=1, le=200)] = 50) -> dict[str, Any]:
    require_local_admin()
    candidates: list[dict[str, Any]] = []
    for record in list_cases(200, record_scope="all"):
        summary = record.get("detector_summary") or {}
        if record.get("status") not in {"detected", "analyzed", "review_pending"}:
            continue
        if not summary.get("needs_review") and record.get("status") != "review_pending":
            continue
        candidates.append(
            {
                "id": record["id"],
                "created_at": record["created_at"],
                "updated_at": record["updated_at"],
                "crop": record["crop"],
                "part": record["part"],
                "status": record["status"],
                "image_filename": record["image_filename"],
                "quality": record.get("quality"),
                "detector_summary": summary,
                "review_events_count": len(record.get("review_events") or []),
            }
        )
        if len(candidates) >= limit:
            break
    return {"total": len(candidates), "items": candidates}


@app.get("/api/trends")
def trends(days: Annotated[int, Query(ge=7, le=30)] = 30) -> dict[str, Any]:
    if days not in {7, 30}:
        raise HTTPException(status_code=422, detail="days 仅支持 7 或 30")
    if settings.public_mode:
        purge_expired_cases()
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    records = list_cases(
        10_000,
        public_only=settings.public_mode,
        since=since,
        record_scope="user",
    )
    by_date: Counter[str] = Counter()
    crops: Counter[str] = Counter()
    classes: Counter[str] = Counter()
    severities: Counter[str] = Counter()
    reviews: Counter[str] = Counter()
    trace_cases: list[dict[str, Any]] = []
    for record in records:
        by_date[record["created_at"][:10]] += 1
        crops[record.get("crop") or "未填写"] += 1
        severities[record.get("field_severity") or "unknown"] += 1
        outcome = present_case(record)["resolution_status"]
        outcome_label = {
            "conclusive": "已有可参考结论",
            "retake_required": "建议补拍",
            "no_supported_target": "未发现支持目标",
            "service_unavailable": "服务暂不可用",
        }[outcome]
        reviews[outcome_label] += 1
        names = {
            item.get("class_name")
            for item in (record.get("detections") or [])
            if item.get("class_name")
        }
        if not names:
            classes["未识别到目标"] += 1
        for name in names:
            classes[str(name)] += 1
        trace_cases.append(
            {
                "id": record["id"],
                "created_at": record["created_at"],
                "crop": record.get("crop") or "未填写",
                "candidate": sorted(str(name) for name in names)[0]
                if names
                else "未识别到目标",
                "field_severity": record.get("field_severity") or "unknown",
                "review_status": outcome_label,
            }
        )
    return {
        "scope": (
            "系统收到的公开上传记录，不代表真实地区疫情趋势"
            if settings.public_mode
            else "本机保存的诊断记录，不代表真实地区疫情趋势"
        ),
        "days": days,
        "total": len(records),
        "by_date": dict(sorted(by_date.items())),
        "crops": dict(crops.most_common()),
        "candidate_classes": dict(classes.most_common()),
        "field_severity": {
            level: severities.get(level, 0)
            for level in ("low", "medium", "high", "unknown")
        },
        "review_status": dict(reviews),
        "trace_cases": trace_cases,
    }


def build_case_report(record: dict[str, Any]) -> dict[str, Any]:
    detections = record.get("detections") or []
    primary_id = detections[0].get("class_id") if detections else None
    knowledge = get_knowledge_card(primary_id) if isinstance(primary_id, int) else None
    case_payload = present_case(record)
    knowledge_document = (
        get_knowledge_document(primary_id)
        if isinstance(primary_id, int) and case_payload["resolution_status"] == "conclusive"
        else None
    )
    return {
        "report_number": f"TZ-{record['created_at'][:10].replace('-', '')}-{record['id'][:8].upper()}",
        "generated_at": datetime.now(UTC).isoformat(),
        "case": case_payload,
        "knowledge": knowledge,
        "knowledge_document": knowledge_document,
        "sources": get_knowledge_sources(knowledge["source_ids"]) if knowledge else [],
        "evidence_analysis": case_payload["evidence_analysis"],
        "external_sources": case_payload["sources"],
        "evidence_snapshots": evidence_snapshots_for_record(record),
        "treatment": case_payload["treatment"],
        "prioritized_guidance": prioritized_guidance(
            primary_id,
            record.get("diagnostic_risk") or "unknown",
            record.get("field_severity") or "unknown",
        )
        if isinstance(primary_id, int)
        else None,
        "safety_notice": "本报告为基于用户信息和图片的辅助判断，不等同于经济阈值或现场植保结论。",
    }


def snapshot_case_report(record: dict[str, Any]) -> dict[str, Any]:
    return save_snapshot(
        settings.storage_dir / "reports",
        record["id"],
        record.get("instance_id") or settings.instance_id,
        build_case_report(record),
        format_version="crop-report-json-v2",
    )


def _report_snapshot_is_current(existing: dict[str, Any], record: dict[str, Any]) -> bool:
    """Reject pre-V2 report snapshots that cannot render the current case contract."""
    snapshot_case = existing.get("case")
    if not isinstance(snapshot_case, dict):
        return False
    current_case = present_case(record)
    if snapshot_case.get("severity") != current_case.get("severity"):
        return False
    if snapshot_case.get("severity_rubric") != current_case.get("severity_rubric"):
        return False
    if snapshot_case.get("host_knowledge") != current_case.get("host_knowledge"):
        return False

    snapshot_treatment = snapshot_case.get("treatment")
    current_treatment = current_case.get("treatment")
    if not isinstance(snapshot_treatment, dict) or not isinstance(current_treatment, dict):
        return False
    for key in ("status", "reason", "severity_level", "severity_label", "source_ids"):
        if snapshot_treatment.get(key) != current_treatment.get(key):
            return False
    snapshot_content = snapshot_treatment.get("content")
    current_content = current_treatment.get("content")
    if not isinstance(snapshot_content, dict) or not isinstance(current_content, dict):
        return False
    for key in ("tier", "markdown", "markdown_html"):
        if snapshot_content.get(key) != current_content.get(key):
            return False
    return True


@app.get("/api/cases/{case_id}/report")
def case_report(case_id: str) -> dict[str, Any]:
    record = require_visible_case(case_id)
    existing = load_latest(settings.storage_dir / "reports", case_id)
    if (
        existing
        and existing.get("snapshot", {}).get("format") == "crop-report-json-v2"
        and "evidence_analysis" in existing
        and ("evidence_snapshots" in existing or not evidence_snapshots_for_record(record))
        and _report_snapshot_is_current(existing, record)
    ):
        return existing
    if existing and build_case_report(record).get("knowledge_document") is None:
        return existing
    return snapshot_case_report(record)


@app.get("/api/cases/{case_id}")
def case_detail(case_id: str) -> dict[str, Any]:
    return present_case(require_visible_case(case_id), include_evidence_snapshots=True)


@app.get("/api/cases/{case_id}/host-knowledge")
def case_host_knowledge(case_id: str) -> dict[str, Any]:
    record = require_visible_case(case_id)
    payload = host_knowledge_payload(record)
    if not payload.get("available"):
        raise HTTPException(status_code=409, detail="当前病例不是已识别的昆虫类别")
    return payload


@app.post("/api/cases/{case_id}/host-confirmation")
def confirm_case_host(
    case_id: str,
    request: HostConfirmationRequest,
    x_case_edit_token: Annotated[str | None, Header(alias="X-Case-Edit-Token")] = None,
) -> dict[str, Any]:
    record = require_case(case_id)
    require_edit_token(case_id, x_case_edit_token)
    payload = host_knowledge_payload(record)
    if not payload.get("available"):
        raise HTTPException(status_code=409, detail="当前病例不是已识别的昆虫类别")
    confirmed_host = request.confirmed_host.strip()
    if confirmed_host not in confirmable_hosts(record):
        raise HTTPException(status_code=422, detail="confirmed_host 必须是支持寄主或固定 OTHER")
    context = deepcopy(record.get("context") if isinstance(record.get("context"), dict) else {})
    context["host_selection"] = host_selection_snapshot(record, confirmed_host)
    updated = update_case(case_id, context=context)
    snapshot_case_report(updated)
    return present_case(updated)


@app.get("/api/cases/{case_id}/image")
def case_image(case_id: str) -> FileResponse:
    record = require_visible_case(case_id)
    path = stored_image_path(record)
    if not path.exists():
        raise HTTPException(status_code=404, detail="原始图片不存在")
    return FileResponse(path, filename=record["image_filename"])


@app.get("/api/r3/taxonomy")
def r3_taxonomy() -> dict[str, Any]:
    return taxonomy_payload()


@app.post("/api/drafts", status_code=201)
async def upload_r3_draft(
    request: Request,
    image: Annotated[UploadFile, File(...)],
    public_consent: Annotated[bool, Form()] = False,
    notes: Annotated[str, Form(max_length=2000)] = "",
) -> dict[str, Any]:
    enforce_rate(request, "upload", settings.public_uploads_per_hour)
    if settings.public_mode and not public_consent:
        raise HTTPException(status_code=422, detail="公网上传前必须同意病例公开展示 30 天")
    suffix = Path(image.filename or "upload.jpg").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="仅支持 JPG、PNG 或 WebP 图片")
    draft_id = secrets.token_hex(16)
    draft_root = settings.storage_dir / "drafts"
    draft_root.mkdir(parents=True, exist_ok=True)
    destination = draft_root / f"{draft_id}{suffix}"
    total = 0
    with destination.open("wb") as output:
        while chunk := await image.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="图片不能超过 15 MB")
            output.write(chunk)
    try:
        with Image.open(destination) as stored:
            stored.verify()
        with Image.open(destination) as stored:
            width, height = stored.size
    except (UnidentifiedImageError, OSError) as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="上传内容不是有效图片") from exc
    edit_token = secrets.token_urlsafe(32) if settings.public_mode else None
    draft = create_draft(
        id=draft_id,
        image_filename=image.filename or destination.name,
        image_path=str(destination),
        image_width=width,
        image_height=height,
        notes=notes.strip(),
        public_consent=bool(public_consent) if settings.public_mode else False,
        edit_token_hash=hashlib.sha256(edit_token.encode("utf-8")).hexdigest()
        if edit_token
        else None,
    )
    response = draft_response(draft)
    if edit_token:
        response["draft_edit_token"] = edit_token
    return response


@app.get("/api/drafts/{draft_id}")
def read_r3_draft(
    draft_id: str,
    x_draft_edit_token: Annotated[str | None, Header(alias="X-Draft-Edit-Token")] = None,
) -> dict[str, Any]:
    draft = require_draft(draft_id)
    require_draft_edit_token(draft, x_draft_edit_token)
    return draft_response(draft)


@app.get("/api/drafts/{draft_id}/image")
def r3_draft_image(
    draft_id: str,
) -> FileResponse:
    draft = require_draft(draft_id)
    path = draft_image_path(draft)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="分析草稿图片不存在")
    return FileResponse(path, filename=draft.get("image_filename") or path.name)


@app.post("/api/drafts/{draft_id}/analyze")
def analyze_r3_draft(
    draft_id: str,
    request: Request,
    x_draft_edit_token: Annotated[str | None, Header(alias="X-Draft-Edit-Token")] = None,
) -> dict[str, Any]:
    draft = require_draft(draft_id)
    require_draft_edit_token(draft, x_draft_edit_token)
    enforce_rate(request, "analyze", settings.public_analyses_per_hour)
    if draft.get("status") in {"analyzed", "model_unavailable"}:
        return draft_response(draft)
    path = draft_image_path(draft)
    quality = inspect_image_quality(path).as_dict()
    try:
        detections = detector.detect(path)
    except DetectorUnavailable as exc:
        summary = {"target_count": None, "needs_review": True, "review_reasons": [str(exc)]}
        updated = update_draft(
            draft_id,
            status="model_unavailable",
            quality=quality,
            detections=None,
            detector_summary=summary,
            context_prediction={"status": "unavailable", "reason": "detector_unavailable"},
        )
        return draft_response(updated)
    summary = summarize_detections(detections)
    if detector.last_metadata:
        summary["inference"] = detector.last_metadata
    if quality["flags"]:
        summary["needs_review"] = True
        summary["review_reasons"] = [*(summary["review_reasons"]), *quality["flags"]]
    summary["explainability"] = build_explainability(detections, summary, quality, detector.last_metadata)
    confidence = (summary.get("primary_candidate") or {}).get("max_confidence")
    confidence_gate = {
        "status": "allowed",
        "threshold": LOW_CONFIDENCE_THRESHOLD,
        "confidence": confidence,
    }
    if isinstance(confidence, (int, float)) and confidence < LOW_CONFIDENCE_THRESHOLD:
        updated = update_draft(
            draft_id,
            status="low_confidence",
            quality=quality,
            detections=detections,
            detector_summary=summary,
            context_prediction={
                "status": "unavailable",
                "reason": "detector_confidence_below_threshold",
            },
            confidence_gate={
                "status": "blocked",
                "threshold": LOW_CONFIDENCE_THRESHOLD,
                "confidence": confidence,
                "message": "最高视觉置信度低于 50%，无法可靠判断，请重新上传图片。",
            },
        )
        return draft_response(updated)
    try:
        context_prediction = infer_context(path)
    except ContextInferenceUnavailable as exc:
        context_prediction = {"status": "unavailable", "reason": str(exc)}
    updated = update_draft(
        draft_id,
        status="analyzed",
        quality=quality,
        detections=detections,
        detector_summary=summary,
        context_prediction=context_prediction,
        confidence_gate=confidence_gate,
    )
    return draft_response(updated)


@app.post("/api/drafts/{draft_id}/confirm", status_code=201)
def confirm_r3_draft(
    draft_id: str,
    payload: R3ContextConfirmationRequest,
    x_draft_edit_token: Annotated[str | None, Header(alias="X-Draft-Edit-Token")] = None,
) -> dict[str, Any]:
    draft = require_draft(draft_id)
    require_draft_edit_token(draft, x_draft_edit_token)
    if draft.get("final_case_id"):
        existing = get_case(str(draft["final_case_id"]))
        if existing is not None:
            return present_case(existing)
        raise HTTPException(status_code=409, detail="草稿已完成病例创建，但病例记录不可读取")
    if draft.get("status") != "analyzed" or not isinstance(draft.get("detections"), list):
        raise HTTPException(status_code=409, detail="请先完成图片识别")
    try:
        context = validate_context_values(
            subject_type=payload.subject_type,
            crop_species=payload.crop_species,
            affected_part=payload.affected_part,
            insect_species=payload.insect_species,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    path = draft_image_path(draft)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="分析草稿图片不存在")
    case_id = f"{settings.instance_id}-{uuid.uuid4().hex}"
    suffix = path.suffix.lower()
    destination = settings.upload_dir / f"{case_id}{suffix}"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(destination))
    case_token = secrets.token_urlsafe(32) if settings.public_mode else None
    persisted_context = {
        "schema_version": "r3-context-v1",
        "authority": "user_confirmed",
        "source": "user_confirmed",
        **context,
        "model_prediction": draft.get("context_prediction"),
    }
    created = create_case(
        {
            "id": case_id,
            "instance_id": settings.instance_id,
            "crop": context["crop_species"] or NOT_APPLICABLE,
            "part": context["affected_part"] or NOT_APPLICABLE,
            "growth_stage": NOT_APPLICABLE,
            "environment": {},
            "notes": draft.get("notes") or "",
            "image_filename": draft.get("image_filename") or destination.name,
            "image_path": str(destination),
            "image_width": draft["image_width"],
            "image_height": draft["image_height"],
            "status": "detected",
            "quality": draft.get("quality"),
            "detections": draft.get("detections"),
            "detector_summary": draft.get("detector_summary"),
            "context": persisted_context,
            "affected_ratio_percent": None,
            "spread_speed": "unknown",
            "public_consent": draft.get("public_consent", False),
            "expires_at": public_expiry(settings.public_retention_days)
            if draft.get("public_consent")
            else None,
            "diagnostic_risk": derive_diagnostic_risk(draft),
            "field_severity": "unknown",
            "severity": severity_pending_payload(),
            "edit_token_hash": hashlib.sha256(case_token.encode("utf-8")).hexdigest()
            if case_token
            else None,
        }
    )
    update_draft(draft_id, status="finalized", final_case_id=case_id, image_path=str(destination))
    response = present_case(created)
    if case_token:
        response["case_edit_token"] = case_token
    return response


@app.post("/api/cases", status_code=201)
async def upload_case(
    request: Request,
    image: Annotated[UploadFile, File(...)],
    crop: Annotated[str, Form(min_length=1, max_length=100)],
    environment_json: Annotated[str | None, Form(min_length=1)] = None,
    affected_ratio_percent: Annotated[float | None, Form(ge=0, le=100)] = None,
    spread_speed: Annotated[
        str | None, Form(pattern="^(unknown|none|slow|ongoing|moderate|rapid)$")
    ] = None,
    part: Annotated[str, Form(max_length=100)] = "",
    growth_stage: Annotated[str | None, Form(max_length=100)] = None,
    notes: Annotated[str, Form(max_length=2000)] = "",
    public_consent: Annotated[bool, Form()] = False,
) -> dict[str, Any]:
    enforce_rate(request, "upload", settings.public_uploads_per_hour)
    if settings.public_mode and not public_consent:
        raise HTTPException(status_code=422, detail="公网上传前必须同意病例公开展示 30 天")
    suffix = Path(image.filename or "upload.jpg").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="仅支持 JPG、PNG 或 WebP 图片")
    if environment_json is None:
        environment = {}
    else:
        try:
            environment = json.loads(environment_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="环境信息格式错误") from exc
        if not isinstance(environment, dict):
            raise HTTPException(status_code=422, detail="环境信息必须是对象")
    if affected_ratio_percent is None and not is_spread_speed_missing(spread_speed):
        raise HTTPException(status_code=422, detail="提供扩散速度时必须同时提供受害比例")
    if affected_ratio_percent is not None and is_spread_speed_missing(spread_speed):
        raise HTTPException(status_code=422, detail="提供受害比例时必须同时提供扩散速度")
    normalized_crop = crop.strip()
    if normalized_crop not in CROP_OPTIONS:
        raise HTTPException(status_code=422, detail="作物或识别对象选项无效")
    if environment_json is not None:
        scene = environment.get("scene")
        if scene not in ENVIRONMENT_OPTIONS:
            raise HTTPException(status_code=422, detail="必须选择有效的种植环境")
        environment = {"scene": scene}
    normalized_part = part.strip()
    normalized_growth_stage = growth_stage.strip() if growth_stage is not None else ""
    growth_stage_supplied = "growth_stage" in await request.form()
    if normalized_crop == "昆虫":
        normalized_part = NOT_APPLICABLE
        normalized_growth_stage = NOT_APPLICABLE
    elif normalized_part not in PART_OPTIONS or (
        growth_stage_supplied
        and (not normalized_growth_stage or normalized_growth_stage not in GROWTH_STAGE_OPTIONS)
    ):
        raise HTTPException(status_code=422, detail="植物病例必须选择有效的部位和生长阶段")
    case_id = f"{settings.instance_id}-{uuid.uuid4().hex}"
    destination = settings.upload_dir / f"{case_id}{suffix}"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    with destination.open("wb") as output:
        while chunk := await image.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="图片不能超过 15 MB")
            output.write(chunk)
    try:
        with Image.open(destination) as stored:
            stored.verify()
        with Image.open(destination) as stored:
            width, height = stored.size
    except (UnidentifiedImageError, OSError) as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="上传内容不是有效图片") from exc

    edit_token = secrets.token_urlsafe(32) if settings.public_mode else None
    effective_public_consent = public_consent if settings.public_mode else False
    created = create_case(
        {
            "id": case_id,
            "instance_id": settings.instance_id,
            "crop": normalized_crop,
            "part": normalized_part,
            "growth_stage": normalized_growth_stage,
            "environment": environment,
            "notes": notes.strip(),
            "image_filename": image.filename or destination.name,
            "image_path": str(destination),
            "image_width": width,
            "image_height": height,
            "status": "uploaded",
            "affected_ratio_percent": affected_ratio_percent,
            "spread_speed": spread_speed,
            "public_consent": effective_public_consent,
            "expires_at": public_expiry(settings.public_retention_days)
            if effective_public_consent
            else None,
            "diagnostic_risk": "unknown",
            "field_severity": "unknown",
            # Legacy clients that still provide the complete V1 pair retain their
            # historical contract. New form submissions omit the pair and enter
            # the explicit V2 user-selection flow.
            "severity": (
                None
                if affected_ratio_percent is not None and not is_spread_speed_missing(spread_speed)
                else severity_pending_payload()
            ),
            "edit_token_hash": hashlib.sha256(edit_token.encode("utf-8")).hexdigest()
            if edit_token
            else None,
        }
    )
    if edit_token:
        created["case_edit_token"] = edit_token
    return present_case(created)


@app.post("/api/cases/{case_id}/detect")
def detect_case(
    case_id: str,
    x_case_edit_token: Annotated[str | None, Header(alias="X-Case-Edit-Token")] = None,
) -> dict[str, Any]:
    record = require_case(case_id)
    require_edit_token(case_id, x_case_edit_token)
    image_path = stored_image_path(record)
    quality = inspect_image_quality(image_path).as_dict()
    try:
        detections = detector.detect(image_path)
    except DetectorUnavailable as exc:
        unavailable_summary = {
            "target_count": None,
            "needs_review": True,
            "review_reasons": [str(exc)],
        }
        unavailable_summary["explainability"] = build_explainability(
            [], unavailable_summary, quality, None
        )
        return present_case(update_case(
            case_id,
            status="model_unavailable",
            quality=quality,
            detector_summary=unavailable_summary,
            diagnostic_risk="high",
        ))
    summary = summarize_detections(detections)
    if detector.last_metadata:
        summary["inference"] = detector.last_metadata
    if quality["flags"]:
        summary["needs_review"] = True
        summary["review_reasons"] = [
            *summary["review_reasons"],
            *quality["flags"],
        ]
    summary["explainability"] = build_explainability(
        detections,
        summary,
        quality,
        detector.last_metadata,
    )
    risk_record = {
        **record,
        "quality": quality,
        "detections": detections,
        "detector_summary": summary,
    }
    return present_case(update_case(
        case_id,
        status="detected",
        quality=quality,
        detections=detections,
        detector_summary=summary,
        diagnostic_risk=derive_diagnostic_risk(risk_record),
    ))


@app.post("/api/cases/{case_id}/analyze")
async def analyze_case(
    case_id: str,
    request: Request,
    x_case_edit_token: Annotated[str | None, Header(alias="X-Case-Edit-Token")] = None,
) -> dict[str, Any]:
    record = require_case(case_id)
    require_edit_token(case_id, x_case_edit_token)
    enforce_rate(request, "analyze", settings.public_analyses_per_hour)
    if record["detections"] is None:
        raise HTTPException(status_code=409, detail="请先完成视觉识别")
    analysis = await request_evidence_analysis(record)
    field_severity = analysis.get("field_severity", "unknown")
    if isinstance(record.get("severity"), dict) and record["severity"].get("algorithm_version") == "severity-v2":
        field_severity = "unknown"
        analysis["field_severity"] = "unknown"
        analysis["severity_basis"] = "用户依据当前样本可观察症状选择受害程度。"
    elif record.get("affected_ratio_percent") is None or record.get("spread_speed") in {
        None,
        "unknown",
    }:
        field_severity = "unknown"
        analysis["field_severity"] = "unknown"
        analysis["severity_basis"] = "缺少受害比例或扩散速度，无法判断田间严重度。"
        analysis["needs_human_review"] = True
        analysis["review_reasons"] = [
            *(analysis.get("review_reasons") or []),
            "田间严重度信息不完整",
        ]
    risk = derive_diagnostic_risk(record, analysis)
    analysis["diagnostic_risk"] = risk
    updated = update_case(
        case_id,
        status="analyzed",
        analysis=analysis,
        diagnostic_risk=risk,
        field_severity=field_severity,
    )
    snapshot_case_report(updated)
    return present_case(updated)


@app.post("/api/cases/{case_id}/severity")
def set_severity_v2(
    case_id: str,
    request: SeverityV2Request,
    x_case_edit_token: Annotated[str | None, Header(alias="X-Case-Edit-Token")] = None,
) -> dict[str, Any]:
    record = require_case(case_id)
    require_edit_token(case_id, x_case_edit_token)
    rubric = severity_rubric_payload(record)
    if rubric["status"] != "available":
        raise HTTPException(status_code=409, detail="当前识别结果没有可用的受害程度判断标准")
    updated = update_case(case_id, severity=severity_v2_payload(request.severity_level))
    snapshot_case_report(updated)
    return present_case(updated)


@app.post("/api/cases/{case_id}/review")
def review_case(
    case_id: str,
    request: ReviewRequest,
    x_case_edit_token: Annotated[str | None, Header(alias="X-Case-Edit-Token")] = None,
) -> dict[str, Any]:
    record = require_case(case_id)
    require_edit_token(case_id, x_case_edit_token)
    detections = record.get("detections") or []
    invalid_indexes = [
        index
        for index in request.accepted_detection_indexes
        if index < 0 or index >= len(detections)
    ]
    if invalid_indexes:
        raise HTTPException(status_code=422, detail=f"检测框索引不存在：{invalid_indexes}")
    reviewed_at = datetime.now(UTC).isoformat()
    review_payload = request.model_dump()
    review_payload["reviewed_at"] = reviewed_at
    analysis = record.get("analysis")
    evidence_snapshot = {
        "quality": record.get("quality"),
        "detections": detections,
        "detector_summary": record.get("detector_summary"),
        "analysis_status": analysis.get("status") if isinstance(analysis, dict) else None,
    }
    review_payload["evidence_snapshot"] = evidence_snapshot
    event = {
        "event_id": uuid.uuid4().hex,
        "recorded_at": reviewed_at,
        "decision": request.decision,
        "reviewer_id": request.reviewer_id,
        "accepted_detection_indexes": request.accepted_detection_indexes,
        "notes": request.reviewer_notes,
        "evidence_snapshot": evidence_snapshot,
    }
    review_events = [*(record.get("review_events") or []), event]
    next_status = "review_pending" if request.decision == "needs_more_evidence" else "reviewed"
    updated = update_case(
        case_id,
        status=next_status,
        review=review_payload,
        review_events=review_events,
    )
    snapshot_case_report(updated)
    return updated


@app.get("/api/cases/{case_id}/review-events")
def review_events(case_id: str) -> dict[str, Any]:
    require_local_admin()
    record = require_case(case_id)
    return {
        "case_id": case_id,
        "events": record.get("review_events") or [],
    }
