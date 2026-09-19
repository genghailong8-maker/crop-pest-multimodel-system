from __future__ import annotations

import hashlib
import json
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError


TAXONOMY_PATH = Path(os.getenv("CROP_CONTEXT_TAXONOMY_PATH", "/opt/ghl/config/r3-taxonomy.json"))
MODEL_PATH = Path(os.getenv("CROP_CONTEXT_MODEL_PATH", "/models/context/openai-clip-vit-base-patch32"))
MODEL_REVISION = os.getenv("CROP_CONTEXT_REVISION", "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268")
THREADS = max(1, int(os.getenv("CROP_CONTEXT_THREADS", "8")))

torch.set_num_threads(THREADS)
torch.set_num_interop_threads(1)

app = FastAPI(title="R3 CPU Context Inference", version="1.0.0")
_model: Any | None = None
_processor: Any | None = None
_taxonomy: dict[str, Any] | None = None
_text_features: dict[str, torch.Tensor] = {}
_model_sha256: str | None = None


def taxonomy() -> dict[str, Any]:
    global _taxonomy
    if _taxonomy is None:
        _taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    return _taxonomy


def model_sha256() -> str | None:
    global _model_sha256
    if _model_sha256 is not None:
        return _model_sha256
    for name in ("model.safetensors", "pytorch_model.bin"):
        path = MODEL_PATH / name
        if path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            _model_sha256 = digest.hexdigest()
            return _model_sha256
    return None


def load_model() -> tuple[Any, Any]:
    global _model, _processor
    if _model is None or _processor is None:
        try:
            from transformers import CLIPModel, CLIPProcessor
            _processor = CLIPProcessor.from_pretrained(str(MODEL_PATH), local_files_only=True)
            _model = CLIPModel.from_pretrained(str(MODEL_PATH), local_files_only=True)
            _model.eval()
        except Exception as exc:  # pragma: no cover - exercised by runtime smoke
            raise RuntimeError(f"context model unavailable: {exc}") from exc
    return _model, _processor


def text_features(model: Any, processor: Any, section: str) -> torch.Tensor:
    cached = _text_features.get(section)
    if cached is not None:
        return cached
    items = taxonomy()[section]
    prompts = [item["clip_prompt"] for item in items]
    inputs = processor(text=prompts, return_tensors="pt", padding=True, truncation=True)
    with torch.inference_mode():
        features = model.get_text_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)
    _text_features[section] = features
    return features


def rank(image_features: torch.Tensor, features: torch.Tensor, items: list[dict[str, Any]]) -> dict[str, Any]:
    scores = (image_features @ features.T).flatten().tolist()
    ranked = sorted(zip(items, scores), key=lambda pair: pair[1], reverse=True)
    candidates = [
        {"value": item["value"], "score": round(float(score), 6), "rank": index}
        for index, (item, score) in enumerate(ranked[:3], start=1)
    ]
    return {
        "top1": candidates[0]["value"] if candidates else None,
        "candidates": candidates,
        "margin": round(candidates[0]["score"] - candidates[1]["score"], 6)
        if len(candidates) > 1
        else None,
    }


def infer(image: Image.Image) -> dict[str, Any]:
    model, processor = load_model()
    inputs = processor(images=image.convert("RGB"), return_tensors="pt")
    with torch.inference_mode():
        image_features = model.get_image_features(**inputs)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
    data = taxonomy()
    return {
        "status": "available",
        "model": "openai/clip-vit-base-patch32",
        "revision": MODEL_REVISION,
        "subject_type": rank(image_features, text_features(model, processor, "subject_types"), data["subject_types"]),
        "crop_species": rank(image_features, text_features(model, processor, "crops"), data["crops"]),
        "affected_part": rank(image_features, text_features(model, processor, "affected_parts"), data["affected_parts"]),
        "insect_species": rank(image_features, text_features(model, processor, "insects"), data["insects"]),
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model": "openai/clip-vit-base-patch32",
        "revision": MODEL_REVISION,
        "model_path": str(MODEL_PATH),
        "model_configured": MODEL_PATH.is_dir(),
        "model_sha256": model_sha256(),
        "threads": THREADS,
        "device": "cpu",
    }


@app.post("/v1/context")
async def context(image: UploadFile = File(...)) -> dict[str, Any]:
    try:
        payload = await image.read()
        source = Image.open(BytesIO(payload)).convert("RGB")
        return infer(source)
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=422, detail="上传内容不是有效图片") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
