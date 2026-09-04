from __future__ import annotations

import json
import re
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import settings


DRAFT_TTL_SECONDS = 30 * 60
_DRAFT_ID = re.compile(r"^[a-f0-9]{32}$")


def _root() -> Path:
    root = settings.storage_dir / "drafts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path(draft_id: str) -> Path:
    if not _DRAFT_ID.fullmatch(draft_id):
        raise KeyError(draft_id)
    return _root() / f"{draft_id}.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def create_draft(**fields: Any) -> dict[str, Any]:
    now = _now()
    requested_id = fields.get("id")
    draft_id = requested_id if isinstance(requested_id, str) and _DRAFT_ID.fullmatch(requested_id) else secrets.token_hex(16)
    payload = {
        "id": draft_id,
        "created_at": now,
        "updated_at": now,
        "expires_at": (datetime.now(UTC) + timedelta(seconds=DRAFT_TTL_SECONDS)).isoformat(),
        "status": "uploaded",
        "final_case_id": None,
        **fields,
    }
    _write(_path(draft_id), payload)
    return payload


def get_draft(draft_id: str) -> dict[str, Any] | None:
    try:
        path = _path(draft_id)
    except KeyError:
        return None
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def update_draft(draft_id: str, **fields: Any) -> dict[str, Any]:
    payload = get_draft(draft_id)
    if payload is None:
        raise KeyError(draft_id)
    payload.update(fields)
    payload["updated_at"] = _now()
    _write(_path(draft_id), payload)
    return payload


def draft_image_path(draft: dict[str, Any]) -> Path:
    path = Path(str(draft.get("image_path", ""))).resolve()
    allowed_parents = {_root().resolve(), settings.upload_dir.resolve()}
    if path.parent not in allowed_parents:
        raise ValueError("draft image path is outside the draft storage")
    return path


def draft_response(draft: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in draft.items()
        if key not in {"edit_token_hash", "image_path"}
    } | {
        "image_url": f"/api/drafts/{draft['id']}/image",
        "final_case_id": draft.get("final_case_id"),
    }
