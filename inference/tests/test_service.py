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
