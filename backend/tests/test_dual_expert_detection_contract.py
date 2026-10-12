from __future__ import annotations

from types import SimpleNamespace

import pytest

from app import detector as detector_module
from app.taxonomy import OFFICIAL_TAXONOMY_VERSION


@pytest.fixture(autouse=True)
def official_taxonomy(monkeypatch):
    monkeypatch.setattr(detector_module, "settings", SimpleNamespace(taxonomy_version=OFFICIAL_TAXONOMY_VERSION))


def payload(target_mode: str, class_id: int):
    return {
        "target_mode": target_mode,
        "detections": [{"class_id": class_id, "confidence": 0.82, "bbox": [0.1, 0.2, 0.3, 0.4]}],
    }


def test_mode_scoped_detection_contract_accepts_plant_and_insect_classes():
    plant = detector_module.validate_remote_detections(payload("plant_disease", 0), "plant_disease")
    insect = detector_module.validate_remote_detections(payload("insect_pest", 6), "insect_pest")

    assert plant[0]["class_id"] == 0
    assert plant[0]["canonical_class_name"] == "水稻稻瘟病"
    assert insect[0]["class_id"] == 6
    assert insect[0]["canonical_class_name"] == "蚜虫"


@pytest.mark.parametrize(
    ("target_mode", "class_id"),
    [("plant_disease", 6), ("insect_pest", 0)],
)
def test_mode_scoped_detection_contract_rejects_cross_mode_classes(target_mode, class_id):
    with pytest.raises(ValueError, match="所选识别模式之外"):
        detector_module.validate_remote_detections(payload(target_mode, class_id), target_mode)


def test_mode_scoped_detection_contract_rejects_mode_mismatch_and_missing_mode():
    with pytest.raises(ValueError, match="模式与用户选择不一致"):
        detector_module.validate_remote_detections(payload("plant_disease", 0), "insect_pest")
    with pytest.raises(ValueError, match="必须明确选择"):
        detector_module.validate_remote_detections(payload("plant_disease", 0), "uncertain")
