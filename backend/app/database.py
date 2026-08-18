from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
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
    "review_events_json": "review_events",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.database_path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def init_database() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    with connect() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
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
                review_json TEXT,
                review_events_json TEXT,
                affected_ratio_percent REAL,
                spread_speed TEXT NOT NULL DEFAULT 'unknown',
                public_consent INTEGER NOT NULL DEFAULT 0,
                expires_at TEXT,
                diagnostic_risk TEXT NOT NULL DEFAULT 'unknown',
                field_severity TEXT NOT NULL DEFAULT 'unknown',
                edit_token_hash TEXT,
                is_test INTEGER NOT NULL DEFAULT 0,
                instance_id TEXT
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(diagnosis_cases)").fetchall()
        }
        migrations = {
            "review_events_json": "TEXT",
            "affected_ratio_percent": "REAL",
            "spread_speed": "TEXT NOT NULL DEFAULT 'unknown'",
            "public_consent": "INTEGER NOT NULL DEFAULT 0",
            "expires_at": "TEXT",
            "diagnostic_risk": "TEXT NOT NULL DEFAULT 'unknown'",
            "field_severity": "TEXT NOT NULL DEFAULT 'unknown'",
            "edit_token_hash": "TEXT",
            "is_test": "INTEGER NOT NULL DEFAULT 0",
            "instance_id": "TEXT",
        }
        for column, definition in migrations.items():
            if column not in columns:
                connection.execute(
                    f"ALTER TABLE diagnosis_cases ADD COLUMN {column} {definition}"
                )
        connection.execute(
            "UPDATE diagnosis_cases SET instance_id = ? WHERE instance_id IS NULL OR instance_id = ''",
            (settings.instance_id,),
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
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_diagnosis_cases_public_expiry
            ON diagnosis_cases(public_consent, expires_at, created_at DESC)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_diagnosis_cases_test_created
            ON diagnosis_cases(is_test, created_at DESC)
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
    if item.get("review_events") is None:
        item["review_events"] = []
    item["public_consent"] = bool(item.get("public_consent"))
    item["is_test"] = bool(item.get("is_test"))
    item["instance_id"] = item.get("instance_id") or settings.instance_id
    item.pop("edit_token_hash", None)
    item["image_url"] = f"/api/cases/{item['id']}/image"
    return item


def create_case(record: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    values = {
        **record,
        "created_at": now,
        "updated_at": now,
        "environment_json": json.dumps(record.get("environment") or {}, ensure_ascii=False),
        "spread_speed": record.get("spread_speed") or "unknown",
        "public_consent": int(bool(record.get("public_consent"))),
        "affected_ratio_percent": record.get("affected_ratio_percent"),
        "expires_at": record.get("expires_at"),
        "diagnostic_risk": record.get("diagnostic_risk") or "unknown",
        "field_severity": record.get("field_severity") or "unknown",
        "edit_token_hash": record.get("edit_token_hash"),
        "is_test": int(bool(record.get("is_test", False))),
        "instance_id": record.get("instance_id") or settings.instance_id,
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO diagnosis_cases (
                id, created_at, updated_at, crop, part, growth_stage,
                environment_json, notes, image_filename, image_path,
                image_width, image_height, status, affected_ratio_percent,
                spread_speed, public_consent, expires_at, diagnostic_risk,
                field_severity, edit_token_hash, is_test, instance_id
            ) VALUES (
                :id, :created_at, :updated_at, :crop, :part, :growth_stage,
                :environment_json, :notes, :image_filename, :image_path,
                :image_width, :image_height, :status, :affected_ratio_percent,
                :spread_speed, :public_consent, :expires_at, :diagnostic_risk,
                :field_severity, :edit_token_hash, :is_test, :instance_id
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


def list_cases(
    limit: int = 50,
    *,
    public_only: bool = False,
    crop: str | None = None,
    class_id: int | None = None,
    severity: str | None = None,
    since: str | None = None,
    record_scope: str = "user",
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if record_scope == "user":
        clauses.append("is_test = 0")
    elif record_scope == "test":
        clauses.append("is_test = 1")
    elif record_scope != "all":
        raise ValueError(f"未知记录范围：{record_scope}")
    if public_only:
        clauses.extend(["public_consent = 1", "expires_at IS NOT NULL", "expires_at > ?"])
        values.append(utc_now())
    if crop:
        clauses.append("crop = ?")
        values.append(crop)
    if severity:
        clauses.append("field_severity = ?")
        values.append(severity)
    if since:
        clauses.append("created_at >= ?")
        values.append(since)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    values.append(limit)
    with connect() as connection:
        rows = connection.execute(
            f"SELECT * FROM diagnosis_cases{where} ORDER BY created_at DESC LIMIT ?",
            values,
        ).fetchall()
    decoded = [item for row in rows if (item := decode_row(row)) is not None]
    if class_id is None:
        return decoded
    return [
        item
        for item in decoded
        if any(
            detection.get("class_id") == class_id
            for detection in (item.get("detections") or [])
        )
    ]


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


def get_edit_token_hash(case_id: str) -> str | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT edit_token_hash FROM diagnosis_cases WHERE id = ?", (case_id,)
        ).fetchone()
    return row["edit_token_hash"] if row else None


def public_expiry(retention_days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=retention_days)).isoformat()


def purge_expired_cases(now: str | None = None) -> dict[str, int]:
    cutoff = now or utc_now()
    upload_root = settings.upload_dir.resolve()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, image_path FROM diagnosis_cases
            WHERE public_consent = 1 AND expires_at IS NOT NULL AND expires_at <= ?
            """,
            (cutoff,),
        ).fetchall()
        connection.executemany(
            "DELETE FROM diagnosis_cases WHERE id = ?",
            [(row["id"],) for row in rows],
        )
    removed_images = 0
    for row in rows:
        path = Path(row["image_path"]).resolve()
        if path.parent == upload_root and path.exists():
            path.unlink()
            removed_images += 1
    return {"cases": len(rows), "images": removed_images}


def integrity_check() -> str:
    with connect() as connection:
        return str(connection.execute("PRAGMA integrity_check").fetchone()[0])


def backup_database(destination: Path) -> Path:
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with connect() as source, sqlite3.connect(destination) as target:
        source.backup(target)
    return destination


def restore_database(source_path: Path) -> None:
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    with sqlite3.connect(source_path) as source:
        result = str(source.execute("PRAGMA integrity_check").fetchone()[0])
        if result != "ok":
            raise ValueError(f"备份数据库完整性检查失败：{result}")
        with sqlite3.connect(settings.database_path) as target:
            source.backup(target)


def validate_image_paths(public_only: bool = False) -> dict[str, Any]:
    records = list_cases(
        10_000,
        public_only=public_only,
        record_scope="user" if public_only else "all",
    )
    missing = [record["id"] for record in records if not stored_image_path(record).is_file()]
    return {"checked": len(records), "missing_case_ids": missing, "ok": not missing}


def mark_existing_cases_as_test(before: str, expected_count: int) -> dict[str, Any]:
    """Mark a verified snapshot as test data without deleting or rewriting cases."""
    with connect() as connection:
        candidate_ids = [
            row["id"]
            for row in connection.execute(
                "SELECT id FROM diagnosis_cases WHERE is_test = 0 AND created_at <= ? ORDER BY created_at",
                (before,),
            ).fetchall()
        ]
        if len(candidate_ids) != expected_count:
            raise ValueError(
                f"待标记病例数量为 {len(candidate_ids)}，与预期 {expected_count} 不一致；未修改数据库"
            )
        connection.executemany(
            "UPDATE diagnosis_cases SET is_test = 1, updated_at = ? WHERE id = ?",
            [(utc_now(), case_id) for case_id in candidate_ids],
        )
    return {"marked": len(candidate_ids), "case_ids": candidate_ids, "before": before}
