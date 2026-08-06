from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageFilter, ImageStat

from .catalog import CLASS_BY_ID
from .config import settings


class DetectorUnavailable(RuntimeError):
    pass


@dataclass
class ImageQuality:
    width: int
    height: int
    brightness: float
    contrast: float
    edge_energy: float
    flags: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "brightness": round(self.brightness, 2),
            "contrast": round(self.contrast, 2),
            "edge_energy": round(self.edge_energy, 2),
            "flags": self.flags,
            "acceptable": not self.flags,
        }


def inspect_image_quality(image_path: Path) -> ImageQuality:
    with Image.open(image_path) as source:
        image = source.convert("RGB")
        width, height = image.size
        sample = image.copy()
    sample.thumbnail((768, 768), Image.Resampling.LANCZOS)
    grayscale = sample.convert("L")
    stats = ImageStat.Stat(grayscale)
    brightness = float(stats.mean[0])
    contrast = float(stats.stddev[0])
    edges = grayscale.filter(ImageFilter.FIND_EDGES)
    edge_energy = float(ImageStat.Stat(edges).stddev[0])
    flags: list[str] = []
    if min(width, height) < 320:
        flags.append("分辨率偏低")
    if brightness < 42:
        flags.append("画面过暗")
    elif brightness > 220:
        flags.append("画面过亮")
    if contrast < 18:
        flags.append("对比度偏低")
    if edge_energy < 12:
        flags.append("可能模糊")
    return ImageQuality(width, height, brightness, contrast, edge_energy, flags)


class UltralyticsDetector:
    def __init__(self) -> None:
        self._model: Any | None = None

    def _load(self) -> Any:
        if settings.model_path is None:
            raise DetectorUnavailable("尚未配置视觉模型权重")
        if not settings.model_path.exists():
            raise DetectorUnavailable(f"视觉模型权重不存在：{settings.model_path}")
        if self._model is None:
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise DetectorUnavailable("视觉模型运行环境尚未安装") from exc
            self._model = YOLO(str(settings.model_path))
        return self._model

    def detect(self, image_path: Path) -> list[dict[str, Any]]:
        model = self._load()
        with Image.open(image_path) as image:
            width, height = image.size
        results = model.predict(
            source=str(image_path),
            conf=settings.model_confidence,
            device=settings.model_device,
            verbose=False,
        )
        detections: list[dict[str, Any]] = []
        if not results:
            return detections
        boxes = results[0].boxes
        if boxes is None:
            return detections
        for xyxy, confidence, class_id_value in zip(
            boxes.xyxy.cpu().tolist(),
            boxes.conf.cpu().tolist(),
            boxes.cls.cpu().tolist(),
        ):
            left, top, right, bottom = map(float, xyxy)
            class_id = int(class_id_value)
            catalog_item = CLASS_BY_ID.get(class_id, {})
            left_normalized = min(1.0, max(0.0, left / width))
            top_normalized = min(1.0, max(0.0, top / height))
            right_normalized = min(1.0, max(0.0, right / width))
            bottom_normalized = min(1.0, max(0.0, bottom / height))
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": catalog_item.get("name_zh", str(class_id)),
                    "class_name_en": catalog_item.get("name_en", str(class_id)),
                    "category_type": catalog_item.get("type", "未知"),
                    "confidence": round(float(confidence), 6),
                    "bbox": [
                        left_normalized,
                        top_normalized,
                        max(0.0, right_normalized - left_normalized),
                        max(0.0, bottom_normalized - top_normalized),
                    ],
                }
            )
        return detections


def validate_remote_detections(payload: Any) -> list[dict[str, Any]]:
    raw_detections = payload.get("detections") if isinstance(payload, dict) else payload
    if not isinstance(raw_detections, list):
        raise ValueError("视觉服务响应缺少 detections 数组")

    detections: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_detections):
        if not isinstance(raw, dict):
            raise ValueError(f"第 {index + 1} 个检测结果格式错误")
        try:
            class_id = int(raw["class_id"])
            confidence = float(raw["confidence"])
            bbox = [float(value) for value in raw["bbox"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"第 {index + 1} 个检测结果字段错误") from exc
        if class_id not in CLASS_BY_ID:
            raise ValueError(f"视觉服务返回未知类别：{class_id}")
        if not 0 <= confidence <= 1:
            raise ValueError(f"视觉服务返回非法置信度：{confidence}")
        if len(bbox) != 4 or any(value < 0 or value > 1 for value in bbox):
            raise ValueError("视觉服务必须返回归一化 [x, y, width, height] 框")
        if bbox[0] + bbox[2] > 1.001 or bbox[1] + bbox[3] > 1.001:
            raise ValueError("视觉服务返回的检测框超出图片范围")
        catalog_item = CLASS_BY_ID[class_id]
        detections.append(
            {
                "class_id": class_id,
                "class_name": catalog_item["name_zh"],
                "class_name_en": catalog_item["name_en"],
                "category_type": catalog_item["type"],
                "confidence": round(confidence, 6),
                "bbox": bbox,
            }
        )
    return detections


class RemoteDetector:
    def detect(self, image_path: Path) -> list[dict[str, Any]]:
        if not settings.detector_endpoint:
            raise DetectorUnavailable("尚未配置服务器视觉识别地址")
        headers = {}
        if settings.detector_api_key:
            headers["Authorization"] = f"Bearer {settings.detector_api_key}"
        try:
            with image_path.open("rb") as image_file:
                response = httpx.post(
                    settings.detector_endpoint,
                    headers=headers,
                    files={"image": (image_path.name, image_file, "application/octet-stream")},
                    data={"confidence": str(settings.model_confidence)},
                    timeout=settings.detector_timeout_seconds,
                )
            response.raise_for_status()
            return validate_remote_detections(response.json())
        except (OSError, httpx.HTTPError, ValueError) as exc:
            raise DetectorUnavailable(f"服务器视觉识别调用失败：{exc}") from exc


class ConfiguredDetector:
    def __init__(self) -> None:
        self.remote = RemoteDetector()
        self.local = UltralyticsDetector()

    def detect(self, image_path: Path) -> list[dict[str, Any]]:
        if settings.detector_endpoint:
            return self.remote.detect(image_path)
        return self.local.detect(image_path)


def summarize_detections(detections: list[dict[str, Any]]) -> dict[str, Any]:
    if not detections:
        return {
            "target_count": 0,
            "primary_candidate": None,
            "candidate_classes": [],
            "needs_review": True,
            "review_reasons": ["未检测到目标，请检查图片质量、拍摄部位或补充图片"],
        }
    by_class: dict[int, list[float]] = {}
    for item in detections:
        by_class.setdefault(item["class_id"], []).append(item["confidence"])
    candidates = []
    for class_id, confidences in by_class.items():
        catalog_item = CLASS_BY_ID.get(class_id, {})
        candidates.append(
            {
                "class_id": class_id,
                "class_name": catalog_item.get("name_zh", str(class_id)),
                "max_confidence": max(confidences),
                "mean_confidence": sum(confidences) / len(confidences),
                "target_count": len(confidences),
            }
        )
    candidates.sort(key=lambda item: item["max_confidence"], reverse=True)
    review_reasons: list[str] = []
    if candidates[0]["max_confidence"] < 0.45:
        review_reasons.append("最高视觉置信度较低")
    if len(candidates) > 1 and candidates[0]["max_confidence"] - candidates[1]["max_confidence"] < 0.12:
        review_reasons.append("候选类别接近，需进行差异诊断")
    return {
        "target_count": len(detections),
        "primary_candidate": candidates[0],
        "candidate_classes": candidates,
        "needs_review": bool(review_reasons),
        "review_reasons": review_reasons,
    }


detector = ConfiguredDetector()
