from __future__ import annotations

import json
from dataclasses import replace

from fastapi.testclient import TestClient
from PIL import Image

from app import config, database, main


def write_fixture(tmp_path):
    source_root = tmp_path / "source"
    source_path = source_root / "test_images" / "57.Myzus persicae Sulzer" / "000.jpg"
    source_path.parent.mkdir(parents=True)
    Image.new("RGB", (100, 80), (120, 160, 90)).save(source_path, format="JPEG")

    prelabel_dir = tmp_path / "prelabels"
    (prelabel_dir / "raw").mkdir(parents=True)
    (prelabel_dir / "labels").mkdir()
    image_id = "fixture_000"
    item = {
        "image_id": image_id,
        "source_relative_path": "test_images/57.Myzus persicae Sulzer/000.jpg",
        "label_relative_path": f"labels/{image_id}.txt",
        "review_priority": "P1",
        "target_box_count": 1,
        "native_box_count": 1,
        "remapped_box_count": 0,
        "other_box_count": 0,
        "minimum_target_confidence": 0.8,
        "maximum_target_confidence": 0.8,
        "flags": [],
    }
    (prelabel_dir.parent / "manifest.json").write_text(
        json.dumps({"summary": {"source_root": str(source_root)}}), encoding="utf-8"
    )
    (prelabel_dir / "review-manifest.json").write_text(
        json.dumps({"summary": {"target_box_count": 1}, "images": [item]}), encoding="utf-8"
    )
    (prelabel_dir / "raw" / f"{image_id}.json").write_text(
        json.dumps(
            {
                "image_id": image_id,
                "source_size": {"width": 100, "height": 80},
                "working_size": {"width": 100, "height": 80},
                "model_sha256": "fixture-model",
                "detections": [
                    {"class_id": 9, "confidence": 0.8, "bbox": [0.1, 0.2, 0.3, 0.4]}
                ],
                "target_detections": [
                    {"class_id": 9, "confidence": 0.8, "bbox": [0.1, 0.2, 0.3, 0.4]}
                ],
            }
        ),
        encoding="utf-8",
    )
    return prelabel_dir, image_id


def test_prelabel_queue_detail_image_and_review(tmp_path, monkeypatch):
    prelabel_dir, image_id = write_fixture(tmp_path)
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path / "runtime",
        database_path=tmp_path / "runtime" / "test.sqlite3",
        upload_dir=tmp_path / "runtime" / "uploads",
        prelabel_dir=prelabel_dir,
        detector_endpoint=None,
        vlm_endpoint=None,
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    with TestClient(main.app) as client:
        queue = client.get("/api/prelabels/queue")
        assert queue.status_code == 200
        assert queue.json()["remaining"] == 1
        assert queue.json()["items"][0]["review_status"] == "pending"

        detail = client.get(f"/api/prelabels/{image_id}")
        assert detail.status_code == 200
        assert detail.json()["target_detections"][0]["class_id"] == 9

        image = client.get(f"/api/prelabels/{image_id}/image")
        assert image.status_code == 200
        assert image.headers["content-type"].startswith("image/jpeg")

        review = client.post(
            f"/api/prelabels/{image_id}/review",
            json={
                "decision": "accepted",
                "boxes": [{"bbox": [0.1, 0.2, 0.3, 0.4], "confidence": 0.9}],
                "notes": "fixture review",
            },
        )
        assert review.status_code == 200
        assert review.json()["review"]["decision"] == "accepted"
        assert (prelabel_dir / "reviewed-labels" / f"{image_id}.txt").read_text() == (
            "9 0.2500000 0.4000000 0.3000000 0.4000000\n"
        )

        updated_queue = client.get("/api/prelabels/queue").json()
        assert updated_queue["remaining"] == 0
        assert updated_queue["items"][0]["review_status"] == "accepted"


def test_needs_rework_remains_in_active_queue(tmp_path, monkeypatch):
    prelabel_dir, image_id = write_fixture(tmp_path)
    test_settings = replace(
        config.settings,
        storage_dir=tmp_path / "runtime",
        database_path=tmp_path / "runtime" / "test.sqlite3",
        upload_dir=tmp_path / "runtime" / "uploads",
        prelabel_dir=prelabel_dir,
        detector_endpoint=None,
        vlm_endpoint=None,
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(main, "settings", test_settings)

    with TestClient(main.app) as client:
        response = client.post(
            f"/api/prelabels/{image_id}/review",
            json={"decision": "needs_rework", "boxes": [], "notes": "check again"},
        )
        assert response.status_code == 200
        queue = client.get("/api/prelabels/queue").json()
        assert queue["reviewed"] == 0
        assert queue["remaining"] == 1
        assert queue["items"][0]["review_status"] == "needs_rework"
