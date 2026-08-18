from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]


def optional_path(value: str | None) -> Path | None:
    if not value or not value.strip():
        return None
    path = Path(value.strip())
    return path if path.is_absolute() else (BACKEND_DIR / path).resolve()


def optional_text(value: str | None) -> str | None:
    """Normalize optional environment values before using them as URLs/keys."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def instance_id(value: str) -> str:
    normalized = value.strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,31}", normalized):
        raise ValueError("实例 ID 只能包含小写字母、数字和下划线，且必须以字母开头")
    return normalized


@dataclass(frozen=True)
class Settings:
    storage_dir: Path
    database_path: Path
    upload_dir: Path
    model_path: Path | None
    model_device: str
    model_confidence: float
    detector_endpoint: str | None
    detector_api_key: str | None
    detector_timeout_seconds: float
    vlm_endpoint: str | None
    vlm_api_key: str | None
    vlm_model: str
    vlm_timeout_seconds: float
    prelabel_dir: Path
    allowed_origins: tuple[str, ...]
    instance_id: str
    instance_label: str
    report_dir: Path
    control_dir: Path
    gateway_mode: bool
    remote_instance_id: str
    remote_instance_label: str
    remote_backend_url: str | None
    remote_backend_timeout_seconds: float
    admin_password_hash: str | None
    admin_session_secret: str | None
    admin_session_ttl_seconds: int
    admin_cookie_secure: bool
    public_mode: bool = False
    public_origin_secret: str | None = None
    public_retention_days: int = 30
    public_uploads_per_hour: int = 10
    public_analyses_per_hour: int = 20
    vlm_max_concurrency: int = 2


def load_settings() -> Settings:
    storage_value = os.getenv("CROP_STORAGE_DIR", "runtime")
    storage_dir = Path(storage_value)
    if not storage_dir.is_absolute():
        storage_dir = (BACKEND_DIR / storage_dir).resolve()
    instance_name = instance_id(os.getenv("CROP_INSTANCE_ID", "lab_cpu"))
    remote_name = instance_id(os.getenv("CROP_REMOTE_INSTANCE_ID", "gpu_full"))
    allowed_origins = tuple(
        origin.strip()
        for origin in os.getenv(
            "CROP_ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    )
    return Settings(
        storage_dir=storage_dir,
        database_path=storage_dir / "crop-pest.sqlite3",
        upload_dir=storage_dir / "uploads",
        model_path=optional_path(os.getenv("CROP_MODEL_PATH")),
        model_device=os.getenv("CROP_MODEL_DEVICE", "cpu").strip() or "cpu",
        model_confidence=float(os.getenv("CROP_MODEL_CONFIDENCE", "0.25")),
        detector_endpoint=optional_text(os.getenv("CROP_DETECTOR_ENDPOINT")),
        detector_api_key=optional_text(os.getenv("CROP_DETECTOR_API_KEY")),
        detector_timeout_seconds=float(os.getenv("CROP_DETECTOR_TIMEOUT_SECONDS", "30")),
        vlm_endpoint=optional_text(os.getenv("CROP_VLM_ENDPOINT")),
        vlm_api_key=optional_text(os.getenv("CROP_VLM_API_KEY")),
        vlm_model=os.getenv("CROP_VLM_MODEL", "crop-pest-vlm").strip() or "crop-pest-vlm",
        vlm_timeout_seconds=float(os.getenv("CROP_VLM_TIMEOUT_SECONDS", "120")),
        prelabel_dir=optional_path(
            os.getenv(
                "CROP_PRELABEL_DIR",
                str(BACKEND_DIR.parent / "artifacts" / "dataset-audit" / "pest65-aphids" / "prelabels"),
            )
        )
        or (BACKEND_DIR.parent / "artifacts" / "dataset-audit" / "pest65-aphids" / "prelabels").resolve(),
        allowed_origins=allowed_origins,
        instance_id=instance_name,
        instance_label=os.getenv("CROP_INSTANCE_LABEL", "实验室 CPU").strip() or instance_name,
        report_dir=storage_dir / "reports",
        control_dir=optional_path(os.getenv("CROP_CONTROL_DIR")) or storage_dir / "control",
        gateway_mode=env_bool("CROP_GATEWAY_MODE"),
        remote_instance_id=remote_name,
        remote_instance_label=os.getenv("CROP_REMOTE_INSTANCE_LABEL", "原 GPU 服务器").strip() or remote_name,
        remote_backend_url=optional_text(os.getenv("CROP_REMOTE_BACKEND_URL")),
        remote_backend_timeout_seconds=float(os.getenv("CROP_REMOTE_BACKEND_TIMEOUT_SECONDS", "300")),
        admin_password_hash=optional_text(os.getenv("CROP_ADMIN_PASSWORD_HASH")),
        admin_session_secret=optional_text(os.getenv("CROP_ADMIN_SESSION_SECRET")),
        admin_session_ttl_seconds=max(300, int(os.getenv("CROP_ADMIN_SESSION_TTL_SECONDS", "3600"))),
        admin_cookie_secure=env_bool("CROP_ADMIN_COOKIE_SECURE"),
        public_mode=env_bool("CROP_PUBLIC_MODE"),
        public_origin_secret=optional_text(os.getenv("CROP_PUBLIC_ORIGIN_SECRET")),
        public_retention_days=max(1, int(os.getenv("CROP_PUBLIC_RETENTION_DAYS", "30"))),
        public_uploads_per_hour=max(1, int(os.getenv("CROP_PUBLIC_UPLOADS_PER_HOUR", "10"))),
        public_analyses_per_hour=max(1, int(os.getenv("CROP_PUBLIC_ANALYSES_PER_HOUR", "20"))),
        vlm_max_concurrency=max(1, int(os.getenv("CROP_VLM_MAX_CONCURRENCY", "2"))),
    )


settings = load_settings()
