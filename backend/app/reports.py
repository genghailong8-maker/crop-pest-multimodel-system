from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load_latest(report_dir: Path, case_id: str) -> dict[str, Any] | None:
    path = report_dir / case_id / "latest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def save_snapshot(
    report_dir: Path,
    case_id: str,
    instance_id: str,
    report: dict[str, Any],
) -> dict[str, Any]:
    if Path(case_id).name != case_id:
        raise ValueError("病例 ID 非法")
    generated_at = report.get("generated_at") or datetime.now(UTC).isoformat()
    body = {**report, "generated_at": generated_at, "instance_id": instance_id}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload = {
        **body,
        "snapshot": {
            "sha256": hashlib.sha256(canonical).hexdigest(),
            "format": "crop-report-json-v1",
        },
    }
    case_dir = report_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    version_path = case_dir / f"{stamp}.json"
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    version_path.write_text(serialized, encoding="utf-8")
    temporary = case_dir / "latest.tmp"
    temporary.write_text(serialized, encoding="utf-8")
    os.replace(temporary, case_dir / "latest.json")
    return payload
