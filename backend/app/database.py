from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import settings


JSON_COLUMNS = {
    "environment_json": "environment",
    "quality_json": "quality",
    "detections_json": "detections",
    "detector_summary_json": "detector_summary",
    "analysis_json": "analysis",
    "review_json": "review",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS diagnosis_cases (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                crop TEXT NOT NULL,
                part TEXT NOT NULL,
                growth_stage TEXT NOT NULL,
                environment_json TEXT NOT NULL,
                notes TEXT NOT NULL,
                image_filename TEXT NOT NULL,
                image_path TEXT NOT NULL,
                image_width INTEGER NOT NULL,
                image_height INTEGER NOT NULL,
                status TEXT NOT NULL,
                quality_json TEXT,
                detections_json TEXT,
                detector_summary_json TEXT,
                analysis_json TEXT,
                review_json TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_diagnosis_cases_created_at
            ON diagnosis_cases(created_at DESC)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_diagnosis_cases_crop_status
            ON diagnosis_cases(crop, status)
            """
        )
        connection.execute("PRAGMA optimize")


def decode_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    for database_name, public_name in JSON_COLUMNS.items():
        raw_value = item.pop(database_name, None)
        item[public_name] = json.loads(raw_value) if raw_value else None
    item["image_url"] = f"/api/cases/{item['id']}/image"
    return item


def create_case(record: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    values = {
        **record,
        "created_at": now,
        "updated_at": now,
        "environment_json": json.dumps(record.get("environment") or {}, ensure_ascii=False),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO diagnosis_cases (
                id, created_at, updated_at, crop, part, growth_stage,
                environment_json, notes, image_filename, image_path,
                image_width, image_height, status
            ) VALUES (
                :id, :created_at, :updated_at, :crop, :part, :growth_stage,
                :environment_json, :notes, :image_filename, :image_path,
                :image_width, :image_height, :status
            )
            """,
            values,
        )
    result = get_case(record["id"])
    assert result is not None
    return result


def get_case(case_id: str) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM diagnosis_cases WHERE id = ?",
            (case_id,),
        ).fetchone()
    return decode_row(row)


def list_cases(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM diagnosis_cases ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [item for row in rows if (item := decode_row(row)) is not None]


def update_case(case_id: str, **fields: Any) -> dict[str, Any]:
    if not fields:
        result = get_case(case_id)
        if result is None:
            raise KeyError(case_id)
        return result
    prepared: dict[str, Any] = {"id": case_id, "updated_at": utc_now()}
    assignments = ["updated_at = :updated_at"]
    for name, value in fields.items():
        database_name = next((key for key, public in JSON_COLUMNS.items() if public == name), name)
        if database_name in JSON_COLUMNS:
            value = json.dumps(value, ensure_ascii=False) if value is not None else None
        prepared[database_name] = value
        assignments.append(f"{database_name} = :{database_name}")
    with connect() as connection:
        cursor = connection.execute(
            f"UPDATE diagnosis_cases SET {', '.join(assignments)} WHERE id = :id",
            prepared,
        )
        if cursor.rowcount == 0:
            raise KeyError(case_id)
    result = get_case(case_id)
    assert result is not None
    return result


def stored_image_path(case_record: dict[str, Any]) -> Path:
    return Path(case_record["image_path"])

