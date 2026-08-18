from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"
IMAGE = ROOT / "backend" / "runtime" / "uploads" / "ceb1c0cd242246a480a613a0227fc07b.jpg"


def summary(client: httpx.Client, case_id: str) -> dict[str, object]:
    payload = client.get(f"{BASE}/api/cases/{case_id}").json()
    return {
        "status": payload.get("status"),
        "resolution_status": payload.get("resolution_status"),
        "is_test": payload.get("is_test"),
        "detection_count": len(payload.get("detections") or []),
        "analysis_status": (payload.get("analysis") or {}).get("status"),
    }


def create_case(client: httpx.Client) -> str:
    with IMAGE.open("rb") as image_stream:
        response = client.post(
            f"{BASE}/api/cases",
            files={"image": (IMAGE.name, image_stream, "image/jpeg")},
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


def mark_test(case_id: str) -> None:
    with sqlite3.connect(ROOT / "backend" / "runtime" / "crop-pest.sqlite3") as connection:
        connection.execute("UPDATE diagnosis_cases SET is_test = 1 WHERE id = ?", (case_id,))
        connection.commit()


def run(mode: str, output: Path, fresh: bool) -> None:
    evidence = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    with httpx.Client(timeout=180) as client:
        case_id = create_case(client) if fresh else str(evidence["case_id"])
        evidence["case_id"] = case_id
        evidence[f"before_{mode}"] = summary(client, case_id)
        response = client.post(f"{BASE}/api/cases/{case_id}/analyze")
        payload = response.json()
        evidence[mode] = {
            "http_status": response.status_code,
            "response_status": payload.get("status"),
            "resolution_status": payload.get("resolution_status"),
            "detail": payload.get("detail"),
            "diagnosis": (payload.get("analysis") or {}).get("primary_diagnosis"),
            "schema_version": (payload.get("analysis") or {}).get("schema_version"),
        }
        evidence[f"after_{mode}"] = summary(client, case_id)
    mark_test(case_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["vlm_down", "vlm_up"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    run(args.mode, args.output, args.fresh)
