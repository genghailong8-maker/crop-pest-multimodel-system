from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
import httpx

from .catalog import CLASS_CATALOG
from .config import settings
from .database import create_case, get_case, init_database, list_cases, stored_image_path, update_case
from .detector import DetectorUnavailable, detector, inspect_image_quality, summarize_detections
from .knowledge import build_explainability, get_knowledge_card, knowledge_contract
from .multimodal import MultimodalUnavailable, request_multimodal_analysis
from .prelabels import detail as prelabel_detail
from .prelabels import image_path as prelabel_image_path
from .prelabels import queue as prelabel_queue
from .prelabels import save_review as save_prelabel_review


MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class ReviewRequest(BaseModel):
    decision: Literal["accepted", "needs_more_evidence", "rejected"] = "accepted"
    final_class_id: int | None = Field(default=None, ge=0, le=15)
    final_diagnosis: str | None = Field(default=None, max_length=200)
    severity: str = Field(default="unknown", pattern="^(low|medium|high|unknown)$")
    accepted_detection_indexes: list[int] = Field(default_factory=list)
    reviewer_notes: str = Field(default="", max_length=2000)
    reviewer_id: str = Field(default="local-reviewer", min_length=1, max_length=80)


class PrelabelReviewRequest(BaseModel):
    decision: str = Field(pattern="^(accepted|needs_rework|skipped)$")
    boxes: list[dict[str, Any]] = Field(default_factory=list, max_length=1000)
    notes: str = Field(default="", max_length=2000)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
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


def require_case(case_id: str) -> dict[str, Any]:
    record = get_case(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="识别记录不存在")
    return record


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
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
        "multimodal_configured": bool(settings.vlm_endpoint),
    }


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


@app.get("/api/prelabels/queue")
def prelabel_queue_endpoint(
    priority: Annotated[str | None, Query(pattern="^(all|P0|P1|P2)$")] = "all",
) -> dict[str, Any]:
    return prelabel_queue(settings.prelabel_dir, priority)


@app.get("/api/prelabels/{image_id}")
def prelabel_detail_endpoint(image_id: str) -> dict[str, Any]:
    return prelabel_detail(settings.prelabel_dir, image_id)


@app.get("/api/prelabels/{image_id}/image")
def prelabel_image_endpoint(image_id: str) -> FileResponse:
    path = prelabel_image_path(settings.prelabel_dir, image_id)
    return FileResponse(path, filename=path.name)


@app.post("/api/prelabels/{image_id}/review")
def prelabel_review_endpoint(image_id: str, request: PrelabelReviewRequest) -> dict[str, Any]:
    return save_prelabel_review(
        settings.prelabel_dir,
        image_id,
        request.decision,
        request.boxes,
        request.notes,
    )


@app.get("/api/cases")
def cases(limit: Annotated[int, Query(ge=1, le=200)] = 50) -> list[dict[str, Any]]:
    return list_cases(limit)


@app.get("/api/cases/review-queue")
def review_queue(limit: Annotated[int, Query(ge=1, le=200)] = 50) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for record in list_cases(200):
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


@app.get("/api/cases/{case_id}")
def case_detail(case_id: str) -> dict[str, Any]:
    return require_case(case_id)


@app.get("/api/cases/{case_id}/image")
def case_image(case_id: str) -> FileResponse:
    record = require_case(case_id)
    path = stored_image_path(record)
    if not path.exists():
        raise HTTPException(status_code=404, detail="原始图片不存在")
    return FileResponse(path, filename=record["image_filename"])


@app.post("/api/cases", status_code=201)
async def upload_case(
    image: Annotated[UploadFile, File(...)],
    crop: Annotated[str, Form(min_length=1, max_length=100)],
    part: Annotated[str, Form(min_length=1, max_length=100)],
    growth_stage: Annotated[str, Form(min_length=1, max_length=100)],
    environment_json: Annotated[str, Form()] = "{}",
    notes: Annotated[str, Form(max_length=2000)] = "",
) -> dict[str, Any]:
    suffix = Path(image.filename or "upload.jpg").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="仅支持 JPG、PNG 或 WebP 图片")
    try:
        environment = json.loads(environment_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="环境信息格式错误") from exc
    if not isinstance(environment, dict):
        raise HTTPException(status_code=422, detail="环境信息必须是对象")

    case_id = uuid.uuid4().hex
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

    return create_case(
        {
            "id": case_id,
            "crop": crop.strip(),
            "part": part.strip(),
            "growth_stage": growth_stage.strip(),
            "environment": environment,
            "notes": notes.strip(),
            "image_filename": image.filename or destination.name,
            "image_path": str(destination),
            "image_width": width,
            "image_height": height,
            "status": "uploaded",
        }
    )


@app.post("/api/cases/{case_id}/detect")
def detect_case(case_id: str) -> dict[str, Any]:
    record = require_case(case_id)
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
        return update_case(
            case_id,
            status="model_unavailable",
            quality=quality,
            detector_summary=unavailable_summary,
        )
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
    return update_case(
        case_id,
        status="detected",
        quality=quality,
        detections=detections,
        detector_summary=summary,
    )


@app.post("/api/cases/{case_id}/analyze")
async def analyze_case(case_id: str) -> dict[str, Any]:
    record = require_case(case_id)
    if record["detections"] is None:
        raise HTTPException(status_code=409, detail="请先完成视觉识别")
    try:
        analysis = await request_multimodal_analysis(record, stored_image_path(record))
    except MultimodalUnavailable as exc:
        return update_case(
            case_id,
            status="multimodal_unavailable",
            analysis={
                "status": "not_configured",
                "message": str(exc),
                "needs_human_review": True,
            },
        )
    except (httpx.HTTPError, ValueError) as exc:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail=f"多模态服务调用失败：{exc}") from exc
    return update_case(case_id, status="analyzed", analysis=analysis)


@app.post("/api/cases/{case_id}/review")
def review_case(case_id: str, request: ReviewRequest) -> dict[str, Any]:
    record = require_case(case_id)
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
    return update_case(
        case_id,
        status=next_status,
        review=review_payload,
        review_events=review_events,
    )


@app.get("/api/cases/{case_id}/review-events")
def review_events(case_id: str) -> dict[str, Any]:
    record = require_case(case_id)
    return {
        "case_id": case_id,
        "events": record.get("review_events") or [],
    }
