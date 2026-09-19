from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


COOKIE_NAME = "crop_admin_session"
_lock = threading.Lock()


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        ).hex()
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def hash_password(password: str, iterations: int = 600_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def issue_session(secret: str, ttl_seconds: int) -> str:
    payload = json.dumps(
        {"exp": int(time.time()) + ttl_seconds, "nonce": secrets.token_urlsafe(12)},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def valid_session(token: str | None, secret: str | None) -> bool:
    if not token or not secret:
        return False
    try:
        encoded, supplied = token.rsplit(".", 1)
        expected = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, supplied):
            return False
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
        return int(payload["exp"]) > int(time.time())
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


class ControlStore:
    def __init__(self, directory: Path, local_instance_id: str) -> None:
        self.directory = directory
        self.local_instance_id = local_instance_id
        self.state_path = directory / "active-instance.json"
        self.audit_path = directory / "switch-audit.jsonl"

    def active_instance(self) -> str:
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            value = str(payload.get("active_instance", ""))
            return value or self.local_instance_id
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return self.local_instance_id

    def switch(self, target: str, actor: str = "admin") -> dict[str, Any]:
        self.directory.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC).isoformat()
        with _lock:
            previous = self.active_instance()
            state = {"active_instance": target, "updated_at": now}
            temporary = self.state_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, self.state_path)
            event = {"previous": previous, "target": target, "actor": actor, "switched_at": now}
            with self.audit_path.open("a", encoding="utf-8") as output:
                output.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def audit(self, limit: int = 20) -> list[dict[str, Any]]:
        try:
            lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        events: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(reversed(events))
