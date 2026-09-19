from __future__ import annotations

import hashlib
import io
import math
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


def first_existing(*paths: Path) -> Path:
    """Choose the production candidate while retaining local backup fallbacks."""
    for path in paths:
        if path.is_file():
            return path
    return paths[0]


DEFAULT_MODEL_PATH = first_existing(
    PROJECT_ROOT / "runs" / "detect" / "official-plus-public-weak-v1-e120-b64" / "weights" / "best.pt",
    PROJECT_ROOT
    / "artifacts"
    / "server"
    / "remote-runs"
    / "official-plus-public-weak-v1-e120-b64"
    / "weights"
    / "best.pt",
    PROJECT_ROOT / "runs" / "detect" / "official-baseline-yolo26n-e120-b64" / "weights" / "best.pt",
    PROJECT_ROOT
    / "artifacts"
    / "server"
    / "official-baseline-yolo26n-e120-b64"
    / "weights"
    / "best.pt",
)
DEFAULT_CLASS10_EXPERT_PATH = first_existing(
    PROJECT_ROOT
    / "runs"
    / "detect"
    / "weak-expert-v2-full-public10-ft-freeze10-lr1e4-e18-b64"
    / "weights"
    / "best.pt",
    PROJECT_ROOT
    / "artifacts"
    / "server"
    / "experiments"
    / "weak-expert-v2-full-public10-ft-freeze10-lr1e4-e18-b64"
    / "best.pt",
)
DEFAULT_CROP_EXPERT_PATH = first_existing(
    PROJECT_ROOT
    / "runs"
    / "detect"
    / "pairwise-crop-cls-10-13-v5-e30-b128"
    / "weights"
    / "best.pt",
    PROJECT_ROOT
    / "artifacts"
    / "server"
    / "experiments"
    / "pairwise-crop-cls-10-13-v5-e30-b128"
    / "best.pt",
)
MAX_IMAGE_BYTES = 15 * 1024 * 1024
ROUTING_TARGETS = {10, 13}
CLASSIFIER_TO_OFFICIAL = {0: 10, 1: 13, 2: 99}
CLASS10_EXPERT_TO_OFFICIAL = {0: 8, 1: 10}


def configured_path(name: str, default: Path | None) -> Path | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def float_env(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return min(max(value, minimum), maximum)


def int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return min(max(value, minimum), maximum)


def text_env(name: str, default: str) -> str:
    value = os.getenv(name, default).strip().lower()
    return value or default


@dataclass(frozen=True)
class Settings:
    model_path: Path
    class10_expert_path: Path | None
    crop_expert_path: Path | None
    device: str
    image_size: int
    classifier_image_size: int
    default_confidence: float
    expert_candidate_confidence: float
    crop_expand: float
    max_candidates: int
    routing_mode: str
    reclassify: bool
    background_threshold: float
    background_margin: float
    target_threshold: float
    target_margin: float
    threshold10: float
    threshold13: float
    score_mode: str
    temperature10: float
    temperature13: float
    class10_expert_threshold: float
    api_key: str | None
    warmup: bool


def load_settings() -> Settings:
    routing_mode = text_env("CROP_INFERENCE_ROUTING_MODE", "shadow")
    if routing_mode not in {"off", "shadow", "active"}:
        routing_mode = "shadow"
    score_mode = text_env("CROP_INFERENCE_SCORE_MODE", "keep")
    if score_mode not in {"keep", "product", "geometric"}:
        score_mode = "keep"
    return Settings(
        model_path=configured_path("CROP_INFERENCE_MODEL_PATH", DEFAULT_MODEL_PATH) or DEFAULT_MODEL_PATH,
        class10_expert_path=configured_path(
            "CROP_INFERENCE_CLASS10_EXPERT_PATH", DEFAULT_CLASS10_EXPERT_PATH
        ),
        crop_expert_path=configured_path("CROP_INFERENCE_CROP_EXPERT_PATH", DEFAULT_CROP_EXPERT_PATH),
        device=os.getenv("CROP_INFERENCE_DEVICE", "0").strip() or "0",
        image_size=int_env("CROP_INFERENCE_IMAGE_SIZE", 640, 32, 4096),
        classifier_image_size=int_env("CROP_INFERENCE_CLASSIFIER_IMAGE_SIZE", 320, 32, 2048),
        default_confidence=float_env("CROP_INFERENCE_CONFIDENCE", 0.25, 0.01, 1.0),
        expert_candidate_confidence=float_env(
            "CROP_INFERENCE_EXPERT_CANDIDATE_CONFIDENCE", 0.05, 0.001, 1.0
        ),
        crop_expand=float_env("CROP_INFERENCE_CROP_EXPAND", 0.5, 0.0, 2.0),
        max_candidates=int_env("CROP_INFERENCE_MAX_CANDIDATES", 64, 1, 300),
        routing_mode=routing_mode,
        reclassify=os.getenv("CROP_INFERENCE_RECLASSIFY", "0").strip().lower() in {"1", "true", "yes"},
        background_threshold=float_env("CROP_INFERENCE_BACKGROUND_THRESHOLD", 0.90, 0.0, 1.0),
        background_margin=float_env("CROP_INFERENCE_BACKGROUND_MARGIN", 0.0, 0.0, 1.0),
        target_threshold=float_env("CROP_INFERENCE_TARGET_THRESHOLD", 0.15, 0.0, 1.0),
        target_margin=float_env("CROP_INFERENCE_TARGET_MARGIN", 0.0, 0.0, 1.0),
        threshold10=float_env("CROP_INFERENCE_THRESHOLD10", 0.15, 0.0, 1.0),
        threshold13=float_env("CROP_INFERENCE_THRESHOLD13", 0.15, 0.0, 1.0),
        score_mode=score_mode,
        temperature10=float_env("CROP_INFERENCE_TEMPERATURE10", 1.25, 0.05, 10.0),
        temperature13=float_env("CROP_INFERENCE_TEMPERATURE13", 0.75, 0.05, 10.0),
        class10_expert_threshold=float_env("CROP_INFERENCE_CLASS10_EXPERT_THRESHOLD", 0.0, 0.0, 1.0),
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


def crop_box(image: Image.Image, bbox: list[float], expand: float) -> Image.Image:
    x, y, width, height = bbox
    left = max(0, math.floor((x - width * expand) * image.width))
    top = max(0, math.floor((y - height * expand) * image.height))
    right = min(image.width, math.ceil((x + width + width * expand) * image.width))
    bottom = min(image.height, math.ceil((y + height + height * expand) * image.height))
    right = max(left + 1, right)
    bottom = max(top + 1, bottom)
    return image.crop((left, top, right, bottom)).convert("RGB")


def probabilities(result: Any) -> dict[int, float]:
    probs = getattr(result, "probs", None)
    if probs is None:
        return {}
    values: Any = getattr(probs, "data", probs)
    if hasattr(values, "detach"):
        values = values.detach().cpu().tolist()
    elif hasattr(values, "tolist"):
        values = values.tolist()
    if not isinstance(values, (list, tuple)):
        return {}
    return {
        CLASSIFIER_TO_OFFICIAL[index]: float(value)
        for index, value in enumerate(values)
        if index in CLASSIFIER_TO_OFFICIAL
    }


def class10_support(result: Any) -> dict[int, float]:
    support = {8: 0.0, 10: 0.0}
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return support
    for confidence, class_id_value in zip(boxes.conf.cpu().tolist(), boxes.cls.cpu().tolist()):
        official_class = CLASS10_EXPERT_TO_OFFICIAL.get(int(class_id_value))
        if official_class is not None:
            support[official_class] = max(support[official_class], float(confidence))
    return support


def logit(value: float) -> float:
    value = min(max(value, 1e-6), 1.0 - 1e-6)
    return math.log(value / (1.0 - value))


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def calibrated_confidence(confidence: float, class_id: int, temperature10: float, temperature13: float) -> float:
    temperature = {10: temperature10, 13: temperature13}.get(class_id)
    if temperature is None:
        return confidence
    return sigmoid(logit(confidence) / temperature)


def apply_active_routing(
    detections: list[dict[str, Any]],
    crop_support: dict[int, dict[int, float]],
    class10_support_by_candidate: dict[int, dict[int, float]],
    *,
    reclassify: bool,
    background_threshold: float,
    background_margin: float,
    target_threshold: float,
    target_margin: float,
    score_mode: str,
    temperature10: float,
    temperature13: float,
    threshold10: float,
    threshold13: float,
    class10_expert_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    routed: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for index, detection in enumerate(detections):
        original_class = int(detection["class_id"])
        support = crop_support.get(index)
        if original_class not in ROUTING_TARGETS or not support:
            routed.append(detection)
            continue
        target_scores = {class_id: support.get(class_id, 0.0) for class_id in ROUTING_TARGETS}
        best_target, best_target_score = max(target_scores.items(), key=lambda item: item[1])
        background_score = support.get(99, 0.0)
        decision: dict[str, Any] = {
            "candidate_index": index,
            "original_class_id": original_class,
            "target_scores": {str(key): round(value, 6) for key, value in target_scores.items()},
            "background_score": round(background_score, 6),
            "action": "keep",
        }
        class10_score = class10_support_by_candidate.get(index, {}).get(10, 0.0)
        if original_class == 10 and class10_expert_threshold > 0 and class10_score < class10_expert_threshold:
            decision.update(action="drop", reason="class10_expert_below_threshold")
            decisions.append(decision)
            continue
        if background_score >= background_threshold and background_score >= best_target_score + background_margin:
            decision.update(action="drop", reason="crop_expert_background")
            decisions.append(decision)
            continue
        final_class = original_class
        if (
            reclassify
            and best_target != original_class
            and best_target_score >= target_threshold
            and best_target_score >= target_scores[original_class] + target_margin
        ):
            final_class = best_target
            decision["action"] = "reclassify"
        confidence = float(detection["confidence"])
        if score_mode == "product":
            confidence *= target_scores.get(final_class, 0.0)
        elif score_mode == "geometric":
            confidence = math.sqrt(confidence * target_scores.get(final_class, 0.0))
        confidence = calibrated_confidence(confidence, final_class, temperature10, temperature13)
        threshold = {10: threshold10, 13: threshold13}.get(final_class, 0.0)
        if confidence < threshold:
            decision.update(action="drop", reason="calibrated_target_below_threshold")
            decisions.append(decision)
            continue
        updated = dict(detection)
        updated["class_id"] = final_class
        updated["confidence"] = round(confidence, 6)
        routed.append(updated)
        decision.update(final_class_id=final_class, confidence=round(confidence, 6))
        decisions.append(decision)
    return routed, decisions


class DetectorRuntime:
    def __init__(self) -> None:
        self.model: Any | None = None
        self.class10_expert: Any | None = None
        self.crop_classifier: Any | None = None
        self.model_hash: str | None = None
        self.class10_expert_hash: str | None = None
        self.crop_expert_hash: str | None = None
        self.class_count = 0
        self.expert_status: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def _load_optional(self, name: str, path: Path | None, task: str) -> Any | None:
        if path is None:
            self.expert_status[name] = {"configured": False, "loaded": False, "reason": "disabled"}
            return None
        if not path.is_file():
            self.expert_status[name] = {
                "configured": True,
                "loaded": False,
                "model": path.name,
                "reason": "weights_missing",
            }
            return None
        try:
            from ultralytics import YOLO

            model = YOLO(str(path), task=task)
            model_hash = sha256(path)
            self.expert_status[name] = {
                "configured": True,
                "loaded": True,
                "model": path.name,
                "sha256": model_hash,
            }
            if name == "class10_detector":
                self.class10_expert_hash = model_hash
            else:
                self.crop_expert_hash = model_hash
            return model
        except Exception as exc:  # expert failure must not take down the main detector
            self.expert_status[name] = {
                "configured": True,
                "loaded": False,
                "model": path.name,
                "reason": f"load_failed: {exc}",
            }
            return None

    def load(self) -> None:
        if self.model is not None:
            return
        if not settings.model_path.is_file():
            raise RuntimeError(f"Model weights do not exist: {settings.model_path}")
        from ultralytics import YOLO

        self.model = YOLO(str(settings.model_path), task="detect")
        self.model_hash = sha256(settings.model_path)
        self.class_count = len(self.model.names)
        self.class10_expert = self._load_optional("class10_detector", settings.class10_expert_path, "detect")
        self.crop_classifier = self._load_optional("crop_classifier", settings.crop_expert_path, "classify")
        if settings.warmup:
            warmup_image = Image.new("RGB", (settings.image_size, settings.image_size), (128, 128, 128))
            self.model.predict(
                source=warmup_image,
                imgsz=settings.image_size,
                conf=settings.default_confidence,
                device=settings.device,
                verbose=False,
            )
            if self.class10_expert is not None:
                self.class10_expert.predict(
                    source=warmup_image,
                    imgsz=settings.image_size,
                    conf=settings.expert_candidate_confidence,
                    device=settings.device,
                    verbose=False,
                )
            if self.crop_classifier is not None:
                self.crop_classifier.predict(
                    source=warmup_image,
                    imgsz=settings.classifier_image_size,
                    device=settings.device,
                    verbose=False,
                )

    def _expert_route(
        self,
        image: Image.Image,
        detections: list[dict[str, Any]],
        requested_confidence: float,
    ) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, float]]:
        route: dict[str, Any] = {
            "mode": settings.routing_mode,
            "configuration": {
                "candidate_confidence": settings.expert_candidate_confidence,
                "crop_expand": settings.crop_expand,
                "background_threshold": settings.background_threshold,
                "background_margin": settings.background_margin,
                "target_threshold": settings.target_threshold,
                "target_margin": settings.target_margin,
                "threshold10": settings.threshold10,
                "threshold13": settings.threshold13,
                "score_mode": settings.score_mode,
                "temperature10": settings.temperature10,
                "temperature13": settings.temperature13,
                "class10_expert_threshold": settings.class10_expert_threshold,
            },
            "candidate_count": 0,
            "routed_candidate_count": 0,
            "decisions": [],
            "errors": [],
        }
        timings: dict[str, float] = {}
        if settings.routing_mode == "off" or (self.crop_classifier is None and self.class10_expert is None):
            route["reason"] = "routing_disabled_or_no_expert"
            return [item for item in detections if item["confidence"] >= requested_confidence], route, timings

        candidate_indexes = [
            index
            for index, detection in enumerate(detections)
            if detection["class_id"] in ROUTING_TARGETS
            and detection["confidence"] >= settings.expert_candidate_confidence
        ]
        candidate_indexes.sort(key=lambda index: detections[index]["confidence"], reverse=True)
        selected_indexes = candidate_indexes[: settings.max_candidates]
        route["candidate_count"] = len(candidate_indexes)
        route["selected_candidate_count"] = len(selected_indexes)
        if not selected_indexes:
            route["reason"] = "no_class10_or_class13_candidates"
            return [item for item in detections if item["confidence"] >= requested_confidence], route, timings

        crops = [crop_box(image, detections[index]["bbox"], settings.crop_expand) for index in selected_indexes]
        crop_support: dict[int, dict[int, float]] = {}
        if self.crop_classifier is not None:
            started = time.perf_counter()
            try:
                results = self.crop_classifier.predict(
                    source=crops,
                    imgsz=settings.classifier_image_size,
                    batch=len(crops),
                    device=settings.device,
                    verbose=False,
                    save=False,
                )
                crop_support = {
                    candidate_index: probabilities(result)
                    for candidate_index, result in zip(selected_indexes, results)
                }
            except Exception as exc:
                route["errors"].append(f"crop_classifier: {exc}")
            timings["crop_classifier_ms"] = round((time.perf_counter() - started) * 1000, 3)

        detector_support: dict[int, dict[int, float]] = {}
        detector_indexes = [
            position for position, candidate_index in enumerate(selected_indexes) if detections[candidate_index]["class_id"] == 10
        ]
        if self.class10_expert is not None and detector_indexes:
            started = time.perf_counter()
            try:
                detector_results = self.class10_expert.predict(
                    source=[crops[position] for position in detector_indexes],
                    imgsz=settings.image_size,
                    batch=len(detector_indexes),
                    device=settings.device,
                    conf=settings.expert_candidate_confidence,
                    iou=0.7,
                    max_det=20,
                    verbose=False,
                    save=False,
                )
                detector_support = {
                    selected_indexes[position]: class10_support(result)
                    for position, result in zip(detector_indexes, detector_results)
                }
            except Exception as exc:
                route["errors"].append(f"class10_detector: {exc}")
            timings["class10_detector_ms"] = round((time.perf_counter() - started) * 1000, 3)

        if settings.routing_mode == "active" and crop_support:
            routed, decisions = apply_active_routing(
                detections,
                crop_support,
                detector_support,
                reclassify=settings.reclassify,
                background_threshold=settings.background_threshold,
                background_margin=settings.background_margin,
                target_threshold=settings.target_threshold,
                target_margin=settings.target_margin,
                score_mode=settings.score_mode,
                temperature10=settings.temperature10,
                temperature13=settings.temperature13,
                threshold10=settings.threshold10,
                threshold13=settings.threshold13,
                class10_expert_threshold=settings.class10_expert_threshold,
            )
            route["routed_candidate_count"] = sum(
                1 for decision in decisions if decision.get("action") in {"keep", "reclassify"}
            )
            route["decisions"] = decisions
            return [item for item in routed if item["confidence"] >= requested_confidence], route, timings

        route["reason"] = "shadow_only" if settings.routing_mode == "shadow" else "expert_support_unavailable"
        route["routed_candidate_count"] = len(selected_indexes)
        route["decisions"] = [
            {
                "candidate_index": index,
                "original_class_id": detections[index]["class_id"],
                "action": "shadow_keep",
                "crop_support": {str(key): round(value, 6) for key, value in crop_support.get(index, {}).items()},
                "class10_support": {
                    str(key): round(value, 6) for key, value in detector_support.get(index, {}).items()
                },
            }
            for index in selected_indexes
        ]
        return [item for item in detections if item["confidence"] >= requested_confidence], route, timings

    def predict(
        self, image: Image.Image, confidence: float
    ) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, Any]]:
        if self.model is None:
            raise RuntimeError("Detector runtime is not loaded")
        started = time.perf_counter()
        with self.lock:
            can_route = settings.routing_mode != "off" and (
                self.crop_classifier is not None or self.class10_expert is not None
            )
            model_confidence = min(confidence, settings.expert_candidate_confidence) if can_route else confidence
            results = self.model.predict(
                source=image,
                imgsz=settings.image_size,
                conf=model_confidence,
                device=settings.device,
                verbose=False,
            )
            result = results[0]
            detections = normalized_detections(result, image.width, image.height)
            route_started = time.perf_counter()
            routed, routing, route_timings = self._expert_route(image, detections, confidence)
        elapsed_ms = (time.perf_counter() - started) * 1000
        speed = {key: round(float(value), 3) for key, value in (result.speed or {}).items()}
        speed["request_model_ms"] = round(elapsed_ms, 3)
        speed["routing_ms"] = round((time.perf_counter() - route_started) * 1000, 3)
        speed.update({f"expert_{key}": value for key, value in route_timings.items()})
        routing["timing_ms"] = {key: value for key, value in route_timings.items()}
        routing["timing_ms"]["total"] = speed["routing_ms"]
        return routed, speed, routing


runtime = DetectorRuntime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime.load()
    yield


app = FastAPI(
    title="农作物病虫害 GPU 推理服务",
    version="0.2.0",
    lifespan=lifespan,
)


def require_api_key(authorization: str | None) -> None:
    if not settings.api_key:
        return
    expected = f"Bearer {settings.api_key}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid inference API key")


def health_model(path: Path | None, loaded: bool, model_hash: str | None) -> dict[str, Any]:
    return {
        "configured": path is not None,
        "loaded": loaded,
        "model": path.name if path is not None else None,
        "sha256": model_hash,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok" if runtime.model is not None else "loading",
        "model": settings.model_path.name,
        "model_sha256": runtime.model_hash,
        "device": settings.device,
        "image_size": settings.image_size,
        "class_count": runtime.class_count,
        "routing": {
            "mode": settings.routing_mode,
            "reclassify": settings.reclassify,
            "score_mode": settings.score_mode,
            "candidate_confidence": settings.expert_candidate_confidence,
            "background_threshold": settings.background_threshold,
            "target_threshold": settings.target_threshold,
            "threshold10": settings.threshold10,
            "threshold13": settings.threshold13,
            "temperature10": settings.temperature10,
            "temperature13": settings.temperature13,
            "class10_expert_threshold": settings.class10_expert_threshold,
            "models": {
                "main": health_model(settings.model_path, runtime.model is not None, runtime.model_hash),
                "class10_detector": runtime.expert_status.get(
                    "class10_detector",
                    health_model(settings.class10_expert_path, runtime.class10_expert is not None, runtime.class10_expert_hash),
                ),
                "crop_classifier": runtime.expert_status.get(
                    "crop_classifier",
                    health_model(settings.crop_expert_path, runtime.crop_classifier is not None, runtime.crop_expert_hash),
                ),
            },
        },
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
    prediction = runtime.predict(decoded, used_confidence)
    if len(prediction) == 2:  # backwards-compatible test doubles and older callers
        detections, speed = prediction  # type: ignore[misc]
        routing = {"mode": "legacy", "decisions": []}
    else:
        detections, speed, routing = prediction
    return {
        "detections": detections,
        "image": {"width": decoded.width, "height": decoded.height},
        "model_sha256": runtime.model_hash,
        "confidence": used_confidence,
        "speed_ms": speed,
        "routing": routing,
    }
