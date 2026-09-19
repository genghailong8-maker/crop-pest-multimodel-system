from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import httpx


BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "server" / "phase9-real-test-20260813.json"


def main() -> None:
    image_path = ROOT / "backend" / "runtime" / "uploads" / "ceb1c0cd242246a480a613a0227fc07b.jpg"
    payload = {
        "crop": "玉米",
        "part": "叶片",
        "growth_stage": "苗期",
        "environment_json": json.dumps({"scene": "露地"}, ensure_ascii=False),
        "notes": "服务器恢复后的有目标完整链路测试",
        "affected_ratio_percent": "20",
        "spread_speed": "slow",
    }
    result: dict[str, object] = {"sample": str(image_path)}
    with httpx.Client(timeout=180) as client:
        with image_path.open("rb") as image_stream:
            upload = client.post(
                f"{BASE}/api/cases",
                files={"image": (image_path.name, image_stream, "image/jpeg")},
                data=payload,
            )
        upload.raise_for_status()
        created = upload.json()
        case_id = created["id"]
        result["created"] = {
            "id": case_id,
            "status": created["status"],
            "is_test": created["is_test"],
        }

        detected = client.post(f"{BASE}/api/cases/{case_id}/detect")
        detected.raise_for_status()
        detected_json = detected.json()
        routing = (detected_json.get("detector_summary") or {}).get("inference", {}).get("routing", {})
        result["detected"] = {
            "status": detected_json["status"],
            "resolution_status": detected_json["resolution_status"],
            "detections": detected_json.get("detections"),
            "diagnostic_risk": detected_json.get("diagnostic_risk"),
            "routing_mode": routing.get("mode"),
            "reclassify": routing.get("configuration", {}).get("reclassify"),
        }

        analyzed = client.post(f"{BASE}/api/cases/{case_id}/analyze")
        analyzed.raise_for_status()
        analyzed_json = analyzed.json()
        analysis = analyzed_json.get("analysis") or {}
        result["analyzed"] = {
            "status": analyzed_json["status"],
            "resolution_status": analyzed_json["resolution_status"],
            "primary_diagnosis": analysis.get("primary_diagnosis"),
            "detector_alignment": analysis.get("detector_alignment"),
            "diagnostic_risk": analyzed_json.get("diagnostic_risk"),
            "field_severity": analyzed_json.get("field_severity"),
            "latency_ms": analysis.get("provenance", {}).get("total_latency_ms"),
            "schema_version": analysis.get("schema_version"),
        }

        report = client.get(f"{BASE}/api/cases/{case_id}/report")
        report.raise_for_status()
        report_json = report.json()
        result["report"] = {
            "report_number": report_json.get("report_number"),
            "source_count": len(report_json.get("sources") or []),
            "has_safety_notice": bool(report_json.get("safety_notice")),
        }

        database_path = ROOT / "backend" / "runtime" / "crop-pest.sqlite3"
        with sqlite3.connect(database_path) as connection:
            connection.execute("UPDATE diagnosis_cases SET is_test = 1 WHERE id = ?", (case_id,))
            connection.commit()

        history = client.get(f"{BASE}/api/cases?limit=100")
        history.raise_for_status()
        trend = client.get(f"{BASE}/api/trends?days=30")
        trend.raise_for_status()
        result["after_marking_test"] = {
            "history_contains_case": case_id in {item["id"] for item in history.json()},
            "trend_total": trend.json().get("total"),
            "trend_scope": trend.json().get("scope"),
        }

    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
