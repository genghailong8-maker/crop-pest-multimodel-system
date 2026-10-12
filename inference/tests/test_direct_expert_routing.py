from __future__ import annotations

from dataclasses import replace

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
    def __init__(self, class_id: int, confidence: float):
        self.xyxy = FakeTensor([[20.0, 20.0, 80.0, 90.0]])
        self.conf = FakeTensor([confidence])
        self.cls = FakeTensor([class_id])


class FakeResult:
    def __init__(self, class_id: int, confidence: float):
        self.boxes = FakeBoxes(class_id, confidence)
        self.speed = {"inference": 2.0}


class FakeModel:
    def __init__(self, class_id: int, confidence_by_call: list[float]):
        self.class_id = class_id
        self.confidence_by_call = confidence_by_call
        self.calls = 0

    def predict(self, **_kwargs):
        self.calls += 1
        index = min(self.calls - 1, len(self.confidence_by_call) - 1)
        return [FakeResult(self.class_id, self.confidence_by_call[index])]


def runtime_with_models(monkeypatch, plant: FakeModel, insect: FakeModel):
    monkeypatch.setattr(
        service,
        "settings",
        replace(service.settings, direct_experts_enabled=True, device="cpu", image_size=640),
    )
    runtime = service.DetectorRuntime()
    runtime.model = plant
    runtime.class10_expert = insect
    runtime.model_hash = service.E2_MODEL_SHA256
    runtime.class10_expert_hash = service.FROZEN_MODEL_SHA256
    runtime.class_count = 5
    return runtime


def test_plant_mode_calls_only_e2_and_filters_to_plant5(monkeypatch):
    plant = FakeModel(0, [0.82])
    insect = FakeModel(6, [0.91])
    runtime = runtime_with_models(monkeypatch, plant, insect)

    detections, _speed, routing = runtime.predict(Image.new("RGB", (120, 120)), 0.25, "plant_disease")

    assert [item["class_id"] for item in detections] == [0]
    assert plant.calls == 1
    assert insect.calls == 0
    assert routing["model_sha256"] == service.E2_MODEL_SHA256
    assert routing["allowed_class_ids"] == [0, 1, 2, 3, 4]
    assert routing["auto_mode_routing"] is False
    assert routing["dual_expert_final_arbitration"] is False


def test_insect_mode_calls_only_frozen_and_filters_to_official_insects(monkeypatch):
    plant = FakeModel(0, [0.82])
    insect = FakeModel(6, [0.91])
    runtime = runtime_with_models(monkeypatch, plant, insect)

    detections, _speed, routing = runtime.predict(Image.new("RGB", (120, 120)), 0.25, "insect_pest")

    assert [item["class_id"] for item in detections] == [6]
    assert plant.calls == 0
    assert insect.calls == 1
    assert routing["model_sha256"] == service.FROZEN_MODEL_SHA256
    assert routing["allowed_class_ids"] == [5, 6, 7, 8, 9]


def test_low_confidence_recovery_uses_the_selected_expert_for_all_four_variants(monkeypatch):
    plant = FakeModel(0, [0.447964, 0.507695, 0.507695, 0.507695, 0.507695])
    insect = FakeModel(6, [0.91])
    runtime = runtime_with_models(monkeypatch, plant, insect)

    detections, _speed, routing = runtime.predict(Image.new("RGB", (120, 120)), 0.25, "plant_disease")
    recovery = routing["low_quality_fallback"]

    assert recovery["status"] == "success"
    assert recovery["threshold"] == 0.50
    assert recovery["variant_count"] == 4
    assert recovery["support_count"] == 4
    assert recovery["selected_confidence"] == 0.507695
    assert [item["class_id"] for item in detections] == [0]
    assert plant.calls == 5
    assert insect.calls == 0


def test_insect_low_confidence_recovery_uses_frozen_for_all_four_variants(monkeypatch):
    plant = FakeModel(0, [0.91])
    insect = FakeModel(6, [0.447964, 0.507695, 0.507695, 0.507695, 0.507695])
    runtime = runtime_with_models(monkeypatch, plant, insect)

    detections, _speed, routing = runtime.predict(Image.new("RGB", (120, 120)), 0.25, "insect_pest")
    recovery = routing["low_quality_fallback"]

    assert recovery["status"] == "success"
    assert recovery["threshold"] == 0.50
    assert recovery["variant_count"] == 4
    assert recovery["support_count"] == 4
    assert recovery["selected_confidence"] == 0.507695
    assert [item["class_id"] for item in detections] == [6]
    assert plant.calls == 0
    assert insect.calls == 5


def test_failed_recovery_keeps_low_confidence_result_unaccepted(monkeypatch):
    plant = FakeModel(0, [0.447964, 0.48, 0.48, 0.48, 0.48])
    insect = FakeModel(6, [0.91])
    runtime = runtime_with_models(monkeypatch, plant, insect)

    detections, _speed, routing = runtime.predict(Image.new("RGB", (120, 120)), 0.25, "plant_disease")
    recovery = routing["low_quality_fallback"]

    assert recovery["status"] == "rejected"
    assert recovery["reason"] == "below_authoritative_threshold"
    assert max(item["confidence"] for item in detections) == 0.447964
    assert plant.calls == 5
    assert insect.calls == 0


def test_insect_mode_fails_closed_on_plant_class_outputs(monkeypatch):
    plant = FakeModel(0, [0.91])
    insect = FakeModel(0, [0.91])
    runtime = runtime_with_models(monkeypatch, plant, insect)

    detections, _speed, routing = runtime.predict(Image.new("RGB", (120, 120)), 0.25, "insect_pest")

    assert detections == []
    assert routing["low_quality_fallback"]["status"] == "rejected"
    assert routing["low_quality_fallback"]["reason"] == "insufficient_consistency"
    assert plant.calls == 0
    assert insect.calls == 5
