from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import httpx


BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "2fcd4b59d2bf442aa13b5bbb59b76950"
DEFAULT_OUTPUT = Path("artifacts/server/phase9-failure-recovery-20260813.json")
DEFAULT_IMAGE = Path("backend/runtime/uploads/ceb1c0cd242246a480a613a0227fc07b.jpg")


def case_summary(client: httpx.Client, case_id: str) -> dict[str, object]:
    response = client.get(f"{BASE}/api/cases/{case_id}")
    response.raise_for_status()
    payload = response.json()
    return {
        "status": payload.get("status"),
        "resolution_status": payload.get("resolution_status"),
        "is_test": payload.get("is_test"),
        "detection_count": len(payload.get("detections") or []),
        "analysis_status": (payload.get("analysis") or {}).get("status"),
    }


def create_detected_case(client: httpx.Client) -> str:
    with DEFAULT_IMAGE.open("rb") as image_stream:
        response = client.post(
            f"{BASE}/api/cases",
            files={"image": (DEFAULT_IMAGE.name, image_stream, "image/jpeg")},
            data={
                "crop": "玉米",
                "part": "叶片",
                "growth_stage": "苗期",
                "environment_json": json.dumps({"scene": "露地"}, ensure_ascii=False),
                "notes": "多模态服务故障恢复测试",
                "affected_ratio_percent": "10",
                "spread_speed": "slow",
            },
        )
    response.raise_for_status()
    case_id = response.json()["id"]
    detected = client.post(f"{BASE}/api/cases/{case_id}/detect")
    detected.raise_for_status()
    return case_id


def run(mode: str, output: Path, fresh: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    case_id = CASE_ID
    with httpx.Client(timeout=180) as client:
        if fresh:
            case_id = create_detected_case(client)
        evidence = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
        if not fresh:
            case_id = str(evidence.get("case_id") or CASE_ID)
        evidence["case_id"] = case_id
        evidence[f"before_{mode}"] = case_summary(client, case_id)
        endpoint = f"{BASE}/api/cases/{case_id}/analyze" if mode.startswith("vlm") else f"{BASE}/api/cases/{case_id}/detect"
        try:
            response = client.post(endpoint)
            payload = response.json()
            evidence[mode] = {
                "http_status": response.status_code,
                "response_status": payload.get("status"),
                "resolution_status": payload.get("resolution_status"),
                "detail": payload.get("detail"),
                "diagnosis": (payload.get("analysis") or {}).get("primary_diagnosis"),
                "schema_version": (payload.get("analysis") or {}).get("schema_version"),
                "detection_count": len(payload.get("detections") or []),
            }
        except (httpx.HTTPError, ValueError) as exc:
            evidence[mode] = {"client_error": str(exc)}
        evidence[f"after_{mode}"] = case_summary(client, case_id)
        connection = sqlite3.connect(ROOT / "backend" / "runtime" / "crop-pest.sqlite3")
        connection.execute("UPDATE diagnosis_cases SET is_test = 1 WHERE id = ?", (case_id,))
        connection.commit()
        connection.close()
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["vlm_down", "vlm_up", "detector_down", "detector_up"])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    run(args.mode, args.output, args.fresh)
