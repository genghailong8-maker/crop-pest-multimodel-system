from __future__ import annotations

import os
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


def load_settings() -> Settings:
    storage_value = os.getenv("CROP_STORAGE_DIR", "runtime")
    storage_dir = Path(storage_value)
    if not storage_dir.is_absolute():
        storage_dir = (BACKEND_DIR / storage_dir).resolve()
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
    )


settings = load_settings()
