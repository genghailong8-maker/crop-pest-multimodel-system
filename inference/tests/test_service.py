from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image

from inference import service


class FakeTensor:
    def __init__(self, values):
        self.values = values

    def cpu(self):
        return self

    def tolist(self):
        return self.values


class FakeBoxes:
    xyxy = FakeTensor([[64.0, 48.0, 320.0, 240.0]])
    conf = FakeTensor([0.91234567])
    cls = FakeTensor([3.0])


class FakeResult:
    boxes = FakeBoxes()


def image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (68, 122, 61)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_normalized_detection_contract():
    detections = service.normalized_detections(FakeResult(), 640, 480)
    assert detections == [
        {
            "class_id": 3,
            "confidence": 0.912346,
            "bbox": [0.1, 0.1, 0.4, 0.4],
        }
    ]


def test_active_routing_uses_per_class_thresholds_and_keeps_class10_support():
    detections = [
        {"class_id": 10, "confidence": 0.55, "bbox": [0.1, 0.1, 0.2, 0.2]},
        {"class_id": 13, "confidence": 0.55, "bbox": [0.5, 0.1, 0.2, 0.2]},
    ]
    routed, decisions = service.apply_active_routing(
        detections,
        {
            0: {10: 0.80, 13: 0.05, 99: 0.02},
            1: {10: 0.05, 13: 0.80, 99: 0.02},
        },
        {0: {8: 0.10, 10: 0.90}},
        reclassify=False,
        background_threshold=0.90,
        background_margin=0.0,
        target_threshold=0.50,
        target_margin=0.0,
        score_mode="keep",
        temperature10=1.0,
        temperature13=1.0,
        threshold10=0.50,
        threshold13=0.70,
        class10_expert_threshold=0.50,
    )
    assert [row["class_id"] for row in routed] == [10]
    assert decisions[0]["action"] == "keep"
    assert decisions[1]["action"] == "drop"
    assert decisions[1]["reason"] == "calibrated_target_below_threshold"
    assert routed[0]["confidence"] == 0.55


def test_active_routing_drops_background_candidate():
    routed, decisions = service.apply_active_routing(
        [{"class_id": 13, "confidence": 0.90, "bbox": [0.1, 0.1, 0.2, 0.2]}],
        {0: {10: 0.10, 13: 0.20, 99: 0.95}},
        {},
        reclassify=False,
        background_threshold=0.90,
        background_margin=0.0,
        target_threshold=0.15,
        target_margin=0.0,
        score_mode="keep",
        temperature10=1.25,
        temperature13=0.75,
        threshold10=0.15,
        threshold13=0.15,
        class10_expert_threshold=0.0,
    )
    assert routed == []
    assert decisions[0]["reason"] == "crop_expert_background"


def test_detect_endpoint_contract(monkeypatch):
    monkeypatch.setattr(service.runtime, "load", lambda: None)
    monkeypatch.setattr(service.runtime, "model", object())
    monkeypatch.setattr(service.runtime, "model_hash", "test-sha256")
    monkeypatch.setattr(service.runtime, "class_count", 16)
    monkeypatch.setattr(
        service.runtime,
        "predict",
        lambda image, confidence: (
            [{"class_id": 3, "confidence": 0.91, "bbox": [0.1, 0.1, 0.4, 0.4]}],
            {"inference": 5.2},
        ),
    )
    with TestClient(service.app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["class_count"] == 16
        response = client.post(
            "/v1/detect",
            files={"image": ("leaf.jpg", image_bytes(), "image/jpeg")},
            data={"confidence": "0.35"},
        )
    assert response.status_code == 200
    assert response.json()["detections"][0]["class_id"] == 3
    assert response.json()["image"] == {"width": 640, "height": 480}
