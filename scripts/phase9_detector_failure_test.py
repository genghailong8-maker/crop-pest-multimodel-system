from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"
IMAGE = ROOT / "artifacts" / "incoming" / "phase5-e2e-class10.jpg"
OUTPUT = ROOT / "artifacts" / "server" / "phase9-detector-failure-20260813.json"


def main() -> None:
    with httpx.Client(timeout=60) as client:
        with IMAGE.open("rb") as image_stream:
            created = client.post(
                f"{BASE}/api/cases",
                files={"image": (IMAGE.name, image_stream, "image/jpeg")},
                data={
                    "crop": "玉米",
                    "part": "叶片",
                    "growth_stage": "苗期",
                    "environment_json": json.dumps({"scene": "露地"}, ensure_ascii=False),
                    "notes": "检测器故障提示测试",
                    "affected_ratio_percent": "10",
                    "spread_speed": "slow",
                },
            )
        created.raise_for_status()
        case_id = created.json()["id"]
        response = client.post(f"{BASE}/api/cases/{case_id}/detect")
        payload = response.json()

    with sqlite3.connect(ROOT / "backend" / "runtime" / "crop-pest.sqlite3") as connection:
        connection.execute("UPDATE diagnosis_cases SET is_test = 1 WHERE id = ?", (case_id,))
        connection.commit()

    evidence = {
        "case_id": case_id,
        "http_status": response.status_code,
        "status": payload.get("status"),
        "resolution_status": payload.get("resolution_status"),
        "diagnostic_risk": payload.get("diagnostic_risk"),
        "detection_count": len(payload.get("detections") or []),
        "user_summary": payload.get("user_summary"),
        "next_action": payload.get("next_action"),
    }
    OUTPUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
