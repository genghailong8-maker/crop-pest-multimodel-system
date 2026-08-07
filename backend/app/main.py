from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

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
from .multimodal import MultimodalUnavailable, request_multimodal_analysis
from .prelabels import detail as prelabel_detail
from .prelabels import image_path as prelabel_image_path
from .prelabels import queue as prelabel_queue
from .prelabels import save_review as save_prelabel_review


MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class ReviewRequest(BaseModel):
    final_class_id: int | None = Field(default=None, ge=0, le=15)
    final_diagnosis: str | None = Field(default=None, max_length=200)
    severity: str = Field(default="unknown", pattern="^(low|medium|high|unknown)$")
    accepted_detection_indexes: list[int] = Field(default_factory=list)
    reviewer_notes: str = Field(default="", max_length=2000)


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
        return update_case(
            case_id,
            status="model_unavailable",
            quality=quality,
            detector_summary={
                "target_count": None,
                "needs_review": True,
                "review_reasons": [str(exc)],
            },
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
    require_case(case_id)
    return update_case(
        case_id,
        status="reviewed",
        review=request.model_dump(),
    )
