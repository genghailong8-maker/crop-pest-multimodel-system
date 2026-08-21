from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from app import config, multimodal
from app.search import SearchSource


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    requests: list[dict] = []
    response_payloads: list[dict] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        type(self).requests = []
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        type(self).requests.append({"url": url, **kwargs})
        return FakeResponse(type(self).response_payloads.pop(0))


def response(content: dict) -> dict:
    return {"choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}]}


def independent_content() -> dict:
    return {
        "primary_diagnosis": "玉米叶枯病",
        "candidate_diagnoses": ["玉米叶枯病"],
        "symptoms": ["叶片出现病斑"],
        "possible_causes": ["高湿环境"],
        "evidence": ["叶片有长条形病斑"],
        "uncertainty": ["缺少叶背近照"],
        "required_additional_photos": ["补拍叶背和整株"],
        "observed_part": "叶片",
        "observed_growth_stage": "苗期",
    }


def final_content(**overrides) -> dict:
    value = {
        "primary_diagnosis": "玉米叶枯病",
        "candidate_diagnoses": ["玉米叶枯病"],
        "symptoms": ["叶片出现病斑"],
        "harm_level": "medium",
        "grounded_assessment": {
            "harms": [
                {
                    "conclusion": "叶片可见区域存在受损",
                    "evidence": [
                        {
                            "source": "image",
                            "reference": "original_image",
                            "observation": "原图可见叶片长条形病斑",
                        },
                        {
                            "source": "field_input",
                            "reference": "field.affected_ratio_percent",
                            "observation": "用户填写受害比例12.5%",
                        },
                    ],
                }
            ],
            "causes": [
                {
                    "conclusion": "当前证据支持玉米叶枯病候选",
                    "evidence": [
                        {
                            "source": "image",
                            "reference": "original_image",
                            "observation": "原图可见叶片长条形病斑",
                        },
                        {
                            "source": "yolo",
                            "reference": "yolo_primary",
                            "observation": "YOLO主候选为玉米叶枯病",
                        },
                        {
                            "source": "field_input",
                            "reference": "field.crop",
                            "observation": "用户选择作物为玉米",
                        },
                    ],
                }
            ],
        },
        "uncertainty": ["单张图片无法确认田间分布"],
        "required_additional_photos": ["补拍叶背和整株"],
        "detector_alignment": "agree",
        "field_input_consistency": "consistent",
        "content_sufficiency": "sufficient",
        "diagnostic_risk": "low",
        "field_severity": "medium",
        "severity_basis": "受害比例 12.5%，扩散速度缓慢，结合图片作辅助判断。",
        "needs_human_review": False,
    }
    value.update(overrides)
    return value


def case_record():
    return {
        "id": "case-1",
        "crop": "玉米",
        "part": "叶片",
        "growth_stage": "苗期",
        "environment": {"scene": "露地", "humidity": "80"},
        "notes": "连续降雨",
        "affected_ratio_percent": 12.5,
        "spread_speed": "slow",
        "quality": {"acceptable": True, "flags": []},
        "detections": [
            {
                "class_id": 0,
                "class_name": "玉米叶枯病",
                "confidence": 0.87,
                "bbox": [0.1, 0.2, 0.3, 0.4],
            }
        ],
        "detector_summary": {
            "needs_review": False,
            "review_reasons": [],
            "inference": {"routing": {"mode": "shadow", "candidate_count": 1}},
        },
    }


def configure(monkeypatch):
    monkeypatch.setattr(
        multimodal,
        "settings",
        replace(
            config.settings,
            vlm_endpoint="http://127.0.0.1:8890/v1/chat/completions",
            vlm_api_key=None,
            vlm_model="crop-pest-vlm",
        ),
    )
    monkeypatch.setattr(multimodal.httpx, "AsyncClient", FakeAsyncClient)


def test_two_stage_payload_is_independent_then_compared(tmp_path, monkeypatch):
    image_path = tmp_path / "leaf.jpg"
    image_path.write_bytes(b"image-bytes")
    configure(monkeypatch)
    FakeAsyncClient.response_payloads = [
        response(independent_content()),
        response(final_content()),
    ]

    result = asyncio.run(multimodal.request_multimodal_analysis(case_record(), image_path))

    assert result["status"] == "completed"
    assert result["schema_version"] == "phase9-multimodal-v4-external-evidence"
    assert result["primary_diagnosis"] == "玉米叶枯病"
    assert result["field_severity"] == "medium"
    assert "受害比例 12.5%" in result["severity_basis"]
    assert "扩散速度缓慢" in result["severity_basis"]
    assert result["needs_human_review"] is False
    assert [stage["name"] for stage in result["provenance"]["stages"]] == [
        "independent_image_judgment",
        "evidence_comparison",
    ]
    assert len(FakeAsyncClient.requests) == 2
    first_text = FakeAsyncClient.requests[0]["json"]["messages"][1]["content"][0]["text"]
    second_content = FakeAsyncClient.requests[1]["json"]["messages"][1]["content"]
    second_text = second_content[0]["text"]
    assert "yolo_detections" not in first_text
    assert "玉米叶枯病" not in first_text
    for excluded_field in (
        "crop",
        "part",
        "growth_stage",
        "notes",
        "environment",
        "affected_ratio_percent",
        "spread_speed",
    ):
        assert excluded_field not in first_text
    assert "yolo_detections" in second_text
    assert "shadow_expert_evidence" in second_text
    assert "affected_ratio_percent" in second_text
    assert '"crop":"玉米"' in second_text
    assert '"part":"叶片"' in second_text
    assert '"growth_stage":"苗期"' in second_text
    assert '"environment":{"scene":"露地","humidity":"80"}' in second_text
    assert '"spread_speed":"slow"' in second_text
    assert "external_evidence" in second_text
    assert '"notes"' not in second_text
    assert FakeAsyncClient.requests[0]["json"]["response_format"]["type"] == "json_schema"
    assert FakeAsyncClient.requests[0]["json"]["max_tokens"] == 500
    assert FakeAsyncClient.requests[1]["json"]["max_tokens"] == 700
    assert second_content[1]["type"] == "image_url"
    assert result["provenance"]["primary_diagnosis_source"] == "detector_primary"
    assert result["independent_judgment"]["observed_part"] == "叶片"
    assert result["provenance"]["input_metadata"]["part"]["source"] == "user_input"
    assert result["provenance"]["independent_observations"]["part"] == "叶片"


def test_mock_external_evidence_is_passed_to_qwen_and_source_bound(tmp_path, monkeypatch):
    image_path = tmp_path / "leaf.jpg"
    image_path.write_bytes(b"image-bytes")
    monkeypatch.setattr(config, "settings", replace(config.settings, search_provider="mock"))
    configure(monkeypatch)
    final = final_content(
        evidence_analysis={
            "status": "available",
            "harms": [{"conclusion": "原始资料描述叶片可能受损", "source_ids": ["source-1"]}],
            "possible_causes": [{"conclusion": "原始资料描述高湿可能相关", "source_ids": ["source-1"]}],
        }
    )
    FakeAsyncClient.response_payloads = [response(independent_content()), response(final)]

    result = asyncio.run(multimodal.request_multimodal_analysis(case_record(), image_path))

    assert result["evidence_analysis"]["status"] == "available"
    assert result["evidence_analysis"]["harms"][0]["source_ids"] == ["source-1"]
    assert result["sources"][0]["id"] == "source-1"


def test_invalid_or_missing_observations_become_system_undetermined(tmp_path, monkeypatch):
    image_path = tmp_path / "grub.jpg"
    image_path.write_bytes(b"image-bytes")
    configure(monkeypatch)
    invalid = independent_content()
    invalid["observed_part"] = "叶片和根部"
    invalid["observed_growth_stage"] = "猜测为苗期"
    FakeAsyncClient.response_payloads = [
        response(invalid),
        response(final_content()),
    ]

    result = asyncio.run(multimodal.request_multimodal_analysis(case_record(), image_path))

    assert result["independent_judgment"]["observed_part"] == "系统未判断"
    assert result["independent_judgment"]["observed_growth_stage"] == "系统未判断"


def test_existing_risk_cannot_be_lowered_and_conflict_is_deterministic(tmp_path, monkeypatch):
    image_path = tmp_path / "leaf.png"
    image_path.write_bytes(b"image-bytes")
    configure(monkeypatch)
    risky = case_record()
    risky["quality"] = {"acceptable": False, "flags": ["图像清晰度偏低"]}
    risky["detector_summary"]["needs_review"] = True
    risky["detector_summary"]["review_reasons"] = ["最高视觉置信度较低"]
    independent_conflict = independent_content()
    independent_conflict["primary_diagnosis"] = "玉米锈病"
    FakeAsyncClient.response_payloads = [
        response(independent_conflict),
        response(final_content(primary_diagnosis="玉米锈病", diagnostic_risk="low")),
    ]

    result = asyncio.run(multimodal.request_multimodal_analysis(risky, image_path))

    assert result["detector_alignment"] == "conflict"
    assert result["primary_diagnosis"] == "玉米叶枯病"
    assert result["provenance"]["raw_primary_diagnosis"] == "玉米锈病"
    assert result["diagnostic_risk"] == "high"
    assert result["needs_human_review"] is True
    assert "最高视觉置信度较低" in result["review_reasons"]
    assert "图像清晰度偏低" in result["review_reasons"]
    assert "独立图像判断与视觉候选冲突" in result["review_reasons"]


def test_missing_field_inputs_force_unknown_inside_protocol(tmp_path, monkeypatch):
    image_path = tmp_path / "leaf.jpg"
    image_path.write_bytes(b"image-bytes")
    configure(monkeypatch)
    record = case_record()
    record["affected_ratio_percent"] = None
    record["spread_speed"] = "unknown"
    final = final_content(field_severity="high")
    final["grounded_assessment"] = {
        "harms": [
            {
                "conclusion": "无法判断",
                "evidence": [
                    {
                        "source": "image",
                        "reference": "original_image",
                        "observation": "原图无法显示田间受害范围",
                    }
                ],
            }
        ],
        "causes": [
            {
                "conclusion": "当前证据支持玉米叶枯病候选",
                "evidence": [
                    {
                        "source": "yolo",
                        "reference": "yolo_primary",
                        "observation": "YOLO主候选为玉米叶枯病",
                    }
                ],
            }
        ],
    }
    FakeAsyncClient.response_payloads = [
        response(independent_content()),
        response(final),
    ]

    result = asyncio.run(multimodal.request_multimodal_analysis(record, image_path))
    assert result["field_severity"] == "unknown"
    assert "无法判断" in result["severity_basis"]
    assert result["needs_human_review"] is True


def test_empty_critical_content_is_rejected():
    invalid = final_content(symptoms=[])
    with pytest.raises(ValueError, match="不符合"):
        multimodal.parse_content(json.dumps(invalid, ensure_ascii=False))
    with pytest.raises(ValueError, match="choices"):
        multimodal.extract_message_content({"choices": []})
    with pytest.raises(ValueError, match="不符合"):
        multimodal.parse_content(
            json.dumps(final_content(primary_diagnosis=""), ensure_ascii=False)
        )


def test_invalid_field_evidence_is_removed_when_valid_image_evidence_remains():
    invalid = final_content()
    invalid["grounded_assessment"]["harms"][0]["evidence"][1]["observation"] = (
        "用户填写受害比例88%"
    )
    parsed = multimodal.MultimodalContent.model_validate(invalid)
    validated = multimodal.validate_grounded_assessment(case_record(), parsed)
    harm = validated.grounded_assessment.harms[0]
    assert harm.conclusion == "叶片可见区域存在受损"
    assert [item.source for item in harm.evidence] == ["image"]


def test_speculative_evidence_is_replaced_with_safe_fallback():
    invalid = final_content()
    invalid["grounded_assessment"]["harms"][0]["evidence"][0]["observation"] = (
        "模型认为叶片受损"
    )
    parsed = multimodal.MultimodalContent.model_validate(invalid)
    validated = multimodal.validate_grounded_assessment(case_record(), parsed)
    assert validated.grounded_assessment.harms[0].conclusion == "无法判断"


def test_external_evidence_requires_real_source_ids():
    result = multimodal.MultimodalContent.model_validate(
        final_content(
            evidence_analysis={
                "status": "available",
                "harms": [
                    {"conclusion": "根部受害可能影响植株稳定", "source_ids": ["source-1", "missing"]}
                ],
                "possible_causes": [
                    {"conclusion": "高湿环境可能与发生有关", "source_ids": ["missing", "source-99"]}
                ],
            }
        )
    )
    evidence = multimodal.SearchEvidence(
        class_name="蛴螬",
        status="available",
        sources=[
            SearchSource(
                id="source-1",
                title="农业资料",
                site_name="测试来源",
                url="https://agri.gov.cn/pest",
                content="根部受害可能影响植株稳定。",
            )
        ],
    )
    normalized = multimodal.normalize_external_evidence_analysis(result, evidence)
    assert normalized.status == "available"
    assert normalized.harms[0].source_ids == ["source-1"]
    assert normalized.possible_causes == []


def test_external_evidence_without_content_cannot_create_claims():
    result = multimodal.MultimodalContent.model_validate(
        final_content(
            evidence_analysis={
                "status": "available",
                "harms": [{"conclusion": "外部资料结论", "source_ids": ["source-1"]}],
                "possible_causes": [],
            }
        )
    )
    evidence = multimodal.SearchEvidence(
        class_name="蛴螬",
        status="unavailable",
        sources=[
            SearchSource(
                id="source-1",
                title="只有摘要",
                site_name="测试来源",
                url="https://example.com/snippet",
                snippet="只有搜索摘要，没有原文正文。",
            )
        ],
    )
    normalized = multimodal.normalize_external_evidence_analysis(result, evidence)
    assert normalized.status == "unavailable"
    assert normalized.harms == []


def test_unobserved_consequence_is_replaced_with_safe_fallback():
    invalid = final_content()
    invalid["grounded_assessment"]["harms"][0]["conclusion"] = (
        "蛴螬啃食根系导致植株萎蔫"
    )
    parsed = multimodal.MultimodalContent.model_validate(invalid)
    validated = multimodal.validate_grounded_assessment(case_record(), parsed)
    assert validated.grounded_assessment.harms[0].conclusion == "无法判断"


def test_cause_requires_image_and_yolo_evidence():
    invalid = final_content()
    invalid["grounded_assessment"]["causes"][0]["evidence"] = [
        {
            "source": "field_input",
            "reference": "field.environment",
            "observation": "用户填写环境为露地",
        }
    ]
    parsed = multimodal.MultimodalContent.model_validate(invalid)
    validated = multimodal.validate_grounded_assessment(case_record(), parsed)
    assert validated.grounded_assessment.causes[0].conclusion == "无法判断"
    assert "病原检测" in validated.grounded_assessment.causes[0].evidence[0].observation


def test_stage_two_cannot_invent_image_evidence_after_stage_one_saw_nothing():
    stage_one = multimodal.IndependentImageContent.model_validate(
        {
            **independent_content(),
            "primary_diagnosis": "无法判断",
            "candidate_diagnoses": ["无法判断"],
            "symptoms": ["无法判断"],
            "evidence": ["无法判断"],
        }
    )
    parsed = multimodal.MultimodalContent.model_validate(final_content())
    validated = multimodal.validate_grounded_assessment(case_record(), parsed, stage_one)
    assert validated.grounded_assessment.harms[0].conclusion == "无法判断"
    assert validated.grounded_assessment.causes[0].conclusion == "无法判断"


def test_indoor_sample_cannot_be_reported_as_field_presence():
    record = case_record()
    record["environment"] = {"scene": "室内样本"}
    invalid = final_content()
    invalid["grounded_assessment"]["causes"][0]["conclusion"] = "田间存在蛴螬幼虫"
    parsed = multimodal.MultimodalContent.model_validate(invalid)
    validated = multimodal.validate_grounded_assessment(record, parsed)
    assert validated.grounded_assessment.causes[0].conclusion == "无法判断"


def test_detector_alignment_longest_name_resolution():
    result = multimodal.MultimodalContent.model_validate(final_content())
    assert multimodal.reconcile_detector_alignment(case_record(), result).detector_alignment == "agree"
    conflict = result.model_copy(update={"primary_diagnosis": "玉米锈病"})
    assert multimodal.reconcile_detector_alignment(case_record(), conflict).detector_alignment == "conflict"
    assert multimodal.diagnosis_class_id("田间发现豆芫菁成虫") == 15
    assert multimodal.diagnosis_class_id("田间发现芫菁成虫") == 8


def test_detector_alignment_can_use_independent_judgment():
    result = multimodal.MultimodalContent.model_validate(final_content())
    reconciled = multimodal.reconcile_detector_alignment(
        case_record(), result, independent_primary_diagnosis="玉米锈病"
    )
    assert reconciled.detector_alignment == "conflict"


def test_crop_conflict_is_recorded_without_changing_detector_class():
    record = case_record()
    record["crop"] = "番茄"
    result = multimodal.MultimodalContent.model_validate(final_content())
    reconciled = multimodal.reconcile_field_input_consistency(record, result)
    integrated, source = multimodal.apply_detector_primary_diagnosis(
        record, reconciled, "玉米锈病"
    )
    assert integrated.primary_diagnosis == "玉米叶枯病"
    assert integrated.field_input_consistency == "conflict"
    assert source == "detector_primary"


def test_no_detection_keeps_multimodal_primary():
    record = case_record()
    record["detections"] = []
    result = multimodal.MultimodalContent.model_validate(
        final_content(primary_diagnosis="玉米锈病")
    )
    integrated, source = multimodal.apply_detector_primary_diagnosis(
        record, result, "玉米锈病"
    )
    assert integrated.primary_diagnosis == "玉米锈病"
    assert source == "multimodal_no_detection"


def test_unconfigured_endpoint_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(multimodal, "settings", replace(config.settings, vlm_endpoint=None))
    with pytest.raises(multimodal.MultimodalUnavailable, match="尚未配置"):
        asyncio.run(multimodal.request_multimodal_analysis(case_record(), tmp_path / "missing.jpg"))


def test_upstream_timeout_is_propagated(tmp_path, monkeypatch):
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
