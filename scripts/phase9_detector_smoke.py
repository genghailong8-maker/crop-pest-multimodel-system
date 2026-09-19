from __future__ import annotations

import json
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "http://127.0.0.1:8870/v1/detect"
OUTPUT = ROOT / "artifacts" / "server" / "phase9-detector-smoke-20260813.json"
SAMPLES = {
    "class8_class10_existing_sample": ROOT / "backend" / "runtime" / "uploads" / "b0e72284d5de449cbcad6cb1c2c465be.jpg",
    "class10_existing_sample": ROOT / "backend" / "runtime" / "uploads" / "ceb1c0cd242246a480a613a0227fc07b.jpg",
    "class13_existing_sample": ROOT / "backend" / "runtime" / "uploads" / "5879b10c19ba4da28e05efe42f5b1172.jpg",
    "class15_existing_sample": ROOT / "backend" / "runtime" / "uploads" / "0bedbf7b405b46a49bac3db15d1d9475.jpg",
}


def main() -> None:
    evidence: dict[str, object] = {"endpoint": ENDPOINT, "confidence": 0.25, "samples": []}
    with httpx.Client(timeout=120) as client:
        for purpose, path in SAMPLES.items():
            with path.open("rb") as image_stream:
                response = client.post(
                    ENDPOINT,
                    files={"image": (path.name, image_stream, "image/jpeg")},
                    data={"confidence": "0.25"},
                )
            response.raise_for_status()
            payload = response.json()
            routing = payload.get("routing") or {}
            evidence["samples"].append(
                {
                    "purpose": purpose,
                    "path": str(path),
                    "detection_count": len(payload.get("detections") or []),
                    "detections": payload.get("detections") or [],
                    "model_sha256": payload.get("model_sha256"),
                    "routing_mode": routing.get("mode"),
                    "reclassify": routing.get("configuration", {}).get("reclassify"),
                    "expert_decisions": routing.get("decisions") or [],
                    "request_model_ms": (payload.get("speed_ms") or {}).get("request_model_ms"),
                }
            )
    OUTPUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
