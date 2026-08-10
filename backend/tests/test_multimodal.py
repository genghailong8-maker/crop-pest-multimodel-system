from __future__ import annotations

import json
import asyncio
from dataclasses import replace

import httpx
import pytest

from app import config, multimodal


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    last_request = None
    response_payload = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        type(self).last_request = {"url": url, **kwargs}
        return FakeResponse(type(self).response_payload)


def case_record():
    return {
        "id": "case-1",
        "crop": "玉米",
        "part": "叶片",
        "growth_stage": "苗期",
        "environment": {"scene": "露地", "humidity": "80"},
        "notes": "连续降雨",
        "quality": {"acceptable": True, "flags": []},
        "detections": [
            {
                "class_id": 0,
                "class_name": "玉米叶枯病",
                "confidence": 0.87,
                "bbox": [0.1, 0.2, 0.3, 0.4],
            }
        ],
        "detector_summary": {"needs_review": False, "review_reasons": []},
    }


def test_openai_multimodal_payload_and_valid_response(tmp_path, monkeypatch):
    image_path = tmp_path / "leaf.jpg"
    image_path.write_bytes(b"image-bytes")
    test_settings = replace(
        config.settings,
        vlm_endpoint="http://127.0.0.1:8890/v1/chat/completions",
        vlm_api_key=None,
        vlm_model="crop-pest-vlm",
    )
    FakeAsyncClient.response_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "primary_diagnosis": "玉米叶枯病",
                            "candidate_diagnoses": ["玉米叶枯病"],
                            "symptoms": ["叶片出现病斑"],
                            "harm_level": "medium",
                            "possible_causes": ["高湿环境有利于病害发展"],
                            "evidence": ["视觉模型定位到病斑区域"],
                            "uncertainty": [],
                            "detector_alignment": "agree",
                            "needs_human_review": False,
                        },
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }
    monkeypatch.setattr(multimodal, "settings", test_settings)
    monkeypatch.setattr(multimodal.httpx, "AsyncClient", FakeAsyncClient)

    result = asyncio.run(multimodal.request_multimodal_analysis(case_record(), image_path))

    assert result["status"] == "completed"
    assert result["primary_diagnosis"] == "玉米叶枯病"
    assert result["needs_human_review"] is False
    assert result["provenance"]["model"] == "crop-pest-vlm"
    request = FakeAsyncClient.last_request
    assert request["url"].endswith("/v1/chat/completions")
    assert request["json"]["model"] == "crop-pest-vlm"
    assert request["json"]["mm_processor_kwargs"]["max_pixels"] == 1003520
    assert request["json"]["response_format"]["type"] == "json_schema"
    assert set(request["json"]["response_format"]["json_schema"]["schema"]["required"]) == {
        "primary_diagnosis",
        "candidate_diagnoses",
        "symptoms",
        "harm_level",
        "possible_causes",
        "evidence",
        "uncertainty",
        "detector_alignment",
        "needs_human_review",
    }
    content = request["json"]["messages"][1]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "连续降雨" in content[0]["text"]


def test_existing_detector_risk_cannot_be_lowered(tmp_path, monkeypatch):
    image_path = tmp_path / "leaf.png"
    image_path.write_bytes(b"image-bytes")
    risky = case_record()
    risky["quality"] = {"acceptable": False, "flags": ["图像清晰度偏低"]}
    risky["detector_summary"] = {"needs_review": True, "review_reasons": ["最高视觉置信度较低"]}
    FakeAsyncClient.response_payload = {
        "choices": [{"message": {"content": json.dumps({
            "primary_diagnosis": "玉米叶枯病",
            "candidate_diagnoses": [],
            "symptoms": [],
            "harm_level": "unknown",
            "possible_causes": [],
            "evidence": [],
            "uncertainty": [],
            "detector_alignment": "agree",
            "needs_human_review": False,
        }, ensure_ascii=False)}}]
    }
    monkeypatch.setattr(
        multimodal,
        "settings",
        replace(config.settings, vlm_endpoint="http://vlm.test/v1/chat/completions"),
    )
    monkeypatch.setattr(multimodal.httpx, "AsyncClient", FakeAsyncClient)

    result = asyncio.run(multimodal.request_multimodal_analysis(risky, image_path))

    assert result["needs_human_review"] is True
    assert "最高视觉置信度较低" in result["review_reasons"]
    assert "图像清晰度偏低" in result["review_reasons"]


def test_invalid_openai_response_is_rejected():
    with pytest.raises(ValueError, match="choices"):
        multimodal.extract_message_content({"choices": []})
    with pytest.raises(ValueError, match="不符合"):
        multimodal.parse_content('{"primary_diagnosis": 123}')


def test_detector_alignment_is_reconciled_from_primary_names():
    same_name = multimodal.MultimodalContent(
        primary_diagnosis="玉米叶枯病",
        candidate_diagnoses=[],
        symptoms=[],
        harm_level="unknown",
        possible_causes=[],
        evidence=[],
        uncertainty=[],
        detector_alignment="conflict",
        needs_human_review=False,
    )
    different_name = same_name.model_copy(
        update={"primary_diagnosis": "玉米锈病", "detector_alignment": "agree"}
    )

    assert multimodal.reconcile_detector_alignment(case_record(), same_name).detector_alignment == "agree"
    assert multimodal.reconcile_detector_alignment(case_record(), different_name).detector_alignment == "conflict"
    assert multimodal.diagnosis_class_id("田间发现豆芫菁成虫") == 15
    assert multimodal.diagnosis_class_id("田间发现芫菁成虫") == 8


def test_unconfigured_endpoint_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(multimodal, "settings", replace(config.settings, vlm_endpoint=None))
    with pytest.raises(multimodal.MultimodalUnavailable, match="尚未配置"):
        asyncio.run(multimodal.request_multimodal_analysis(case_record(), tmp_path / "missing.jpg"))


def test_upstream_502_retains_bounded_detail(tmp_path, monkeypatch):
    image_path = tmp_path / "leaf.jpg"
    image_path.write_bytes(b"image-bytes")

    class BadGatewayClient(FakeAsyncClient):
        async def post(self, url, **kwargs):
            request = httpx.Request("POST", url)
            return httpx.Response(502, request=request, text="upstream unavailable")

    monkeypatch.setattr(
        multimodal,
        "settings",
        replace(config.settings, vlm_endpoint="http://vlm.test/v1/chat/completions"),
    )
    monkeypatch.setattr(multimodal.httpx, "AsyncClient", BadGatewayClient)

    with pytest.raises(httpx.HTTPStatusError, match="502.*upstream unavailable"):
        asyncio.run(multimodal.request_multimodal_analysis(case_record(), image_path))


def test_upstream_timeout_is_propagated_for_api_502(tmp_path, monkeypatch):
    image_path = tmp_path / "leaf.jpg"
    image_path.write_bytes(b"image-bytes")

    class TimeoutClient(FakeAsyncClient):
        async def post(self, url, **kwargs):
            raise httpx.ReadTimeout("timed out", request=httpx.Request("POST", url))

    monkeypatch.setattr(
        multimodal,
        "settings",
        replace(config.settings, vlm_endpoint="http://vlm.test/v1/chat/completions"),
    )
    monkeypatch.setattr(multimodal.httpx, "AsyncClient", TimeoutClient)

    with pytest.raises(httpx.ReadTimeout, match="timed out"):
        asyncio.run(multimodal.request_multimodal_analysis(case_record(), image_path))
