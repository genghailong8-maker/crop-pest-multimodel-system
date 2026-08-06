from __future__ import annotations

import hashlib
import io
import os
import secrets
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS_DIR = (
    PROJECT_ROOT
    / "runs"
    / "detect"
    / "official-baseline-yolo26n-e120-b64"
    / "weights"
)
DEFAULT_ONNX_PATH = DEFAULT_WEIGHTS_DIR / "best.onnx"
DEFAULT_PT_PATH = DEFAULT_WEIGHTS_DIR / "best.pt"
DEFAULT_MODEL_PATH = DEFAULT_ONNX_PATH if DEFAULT_ONNX_PATH.is_file() else DEFAULT_PT_PATH
MAX_IMAGE_BYTES = 15 * 1024 * 1024


@dataclass(frozen=True)
class Settings:
    model_path: Path
    device: str
    image_size: int
    default_confidence: float
    api_key: str | None
    warmup: bool


def load_settings() -> Settings:
    configured_path = Path(os.getenv("CROP_INFERENCE_MODEL_PATH", str(DEFAULT_MODEL_PATH)))
    if not configured_path.is_absolute():
        configured_path = (PROJECT_ROOT / configured_path).resolve()
    return Settings(
        model_path=configured_path,
        device=os.getenv("CROP_INFERENCE_DEVICE", "0").strip() or "0",
        image_size=int(os.getenv("CROP_INFERENCE_IMAGE_SIZE", "640")),
        default_confidence=float(os.getenv("CROP_INFERENCE_CONFIDENCE", "0.25")),
        api_key=os.getenv("CROP_INFERENCE_API_KEY") or None,
        warmup=os.getenv("CROP_INFERENCE_WARMUP", "1").strip().lower() not in {"0", "false", "no"},
    )


settings = load_settings()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_detections(result: Any, width: int, height: int) -> list[dict[str, Any]]:
    boxes = result.boxes
    if boxes is None:
        return []
    detections: list[dict[str, Any]] = []
    for xyxy, confidence, class_id_value in zip(
        boxes.xyxy.cpu().tolist(),
        boxes.conf.cpu().tolist(),
        boxes.cls.cpu().tolist(),
    ):
        left, top, right, bottom = map(float, xyxy)
        x = min(1.0, max(0.0, left / width))
        y = min(1.0, max(0.0, top / height))
        normalized_right = min(1.0, max(0.0, right / width))
        normalized_bottom = min(1.0, max(0.0, bottom / height))
        detections.append(
            {
                "class_id": int(class_id_value),
                "confidence": round(float(confidence), 6),
                "bbox": [
                    round(x, 7),
                    round(y, 7),
                    round(max(0.0, normalized_right - x), 7),
                    round(max(0.0, normalized_bottom - y), 7),
                ],
            }
        )
    return detections


class DetectorRuntime:
    def __init__(self) -> None:
        self.model: Any | None = None
        self.model_hash: str | None = None
        self.class_count = 0
        self.lock = threading.Lock()

    def load(self) -> None:
        if not settings.model_path.is_file():
            raise RuntimeError(f"Model weights do not exist: {settings.model_path}")
        from ultralytics import YOLO

        self.model = YOLO(str(settings.model_path))
        self.model_hash = sha256(settings.model_path)
        self.class_count = len(self.model.names)
        if settings.warmup:
            warmup_image = Image.new("RGB", (settings.image_size, settings.image_size), (128, 128, 128))
            self.model.predict(
                source=warmup_image,
                imgsz=settings.image_size,
                conf=settings.default_confidence,
                device=settings.device,
                verbose=False,
            )

    def predict(self, image: Image.Image, confidence: float) -> tuple[list[dict[str, Any]], dict[str, float]]:
        if self.model is None:
            raise RuntimeError("Detector runtime is not loaded")
        started = time.perf_counter()
        with self.lock:
            results = self.model.predict(
                source=image,
                imgsz=settings.image_size,
                conf=confidence,
                device=settings.device,
                verbose=False,
            )
        elapsed_ms = (time.perf_counter() - started) * 1000
        result = results[0]
        speed = {key: round(float(value), 3) for key, value in (result.speed or {}).items()}
        speed["request_model_ms"] = round(elapsed_ms, 3)
        return normalized_detections(result, image.width, image.height), speed


runtime = DetectorRuntime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime.load()
    yield


app = FastAPI(
    title="农作物病虫害 GPU 推理服务",
    version="0.1.0",
    lifespan=lifespan,
)


def require_api_key(authorization: str | None) -> None:
    if not settings.api_key:
        return
    expected = f"Bearer {settings.api_key}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid inference API key")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok" if runtime.model is not None else "loading",
        "model": settings.model_path.name,
        "model_sha256": runtime.model_hash,
        "device": settings.device,
        "image_size": settings.image_size,
        "class_count": runtime.class_count,
    }


@app.post("/v1/detect")
async def detect(
    image: Annotated[UploadFile, File(...)],
    confidence: Annotated[float | None, Form(ge=0.01, le=1.0)] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    require_api_key(authorization)
    payload = bytearray()
    while chunk := await image.read(1024 * 1024):
        payload.extend(chunk)
        if len(payload) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Image exceeds the 15 MiB limit")
    try:
        with Image.open(io.BytesIO(payload)) as source:
            source.verify()
        with Image.open(io.BytesIO(payload)) as source:
            decoded = source.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=422, detail="Uploaded content is not a valid image") from exc

    used_confidence = confidence if confidence is not None else settings.default_confidence
    detections, speed = runtime.predict(decoded, used_confidence)
    return {
        "detections": detections,
        "image": {"width": decoded.width, "height": decoded.height},
        "model_sha256": runtime.model_hash,
        "confidence": used_confidence,
        "speed_ms": speed,
    }
