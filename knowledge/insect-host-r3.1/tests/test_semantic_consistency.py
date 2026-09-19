from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("semantic", ROOT / "validate_semantic_consistency.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MOD)


def capability(status: str, available: bool, crop: str = "测试作物") -> dict:
    return {"crop": crop, "status": status, "severity_available": available}


def evidence(status: str = "COMPLETE") -> list[dict]:
    return [{"severity": level, "status": status} for level in ("mild", "moderate", "severe")]


def host_markdown(severity: str, vector: str = "") -> str:
    return f"""# 测试

## 已审核寄主

### 寄主：测试作物

### 严重程度

{severity}

## 可能传播的相关病害

{vector}
"""


COMPLETE = """#### 轻度
- 状态：COMPLETE
#### 中度
- 状态：COMPLETE
#### 重度
- 状态：COMPLETE"""


def test_full_host_stale_host_severity_fails() -> None:
    stale = COMPLETE.replace("状态：COMPLETE", "三级分级 = NEEDS_EVIDENCE", 1)
    assert MOD.host_semantic_issues(host_markdown(stale), capability("FULL", True), evidence())


def test_vector_needs_evidence_does_not_fail_full_host() -> None:
    assert not MOD.host_semantic_issues(
        host_markdown(COMPLETE, "### 病害：测试病\n- 严重程度：NEEDS_EVIDENCE"),
        capability("FULL", True),
        evidence(),
    )


def test_partial_host_needs_evidence_passes() -> None:
    needs = COMPLETE.replace("COMPLETE", "NEEDS_EVIDENCE")
    assert not MOD.host_semantic_issues(host_markdown(needs), capability("PARTIAL", False), evidence("NEEDS_EVIDENCE"))


def test_real_cotton_peach_and_potato_hosts_pass() -> None:
    import json

    cap = json.loads((ROOT / "capability-fallback.json").read_text(encoding="utf-8"))
    ev = json.loads((ROOT / "severity-evidence.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    document_by_class = {int(item["class_id"]): item["document"] for item in manifest["documents"]}
    cases = [(9, "棉花"), (9, "桃"), (11, "马铃薯")]
    for class_id, crop in cases:
        record = next(x for x in cap["records"] if x["class_id"] == class_id and x["crop"] == crop)
        records = [x for x in ev["records"] if x.get("object_type") == "insect_host" and x.get("class_id") == class_id and x.get("crop") == crop]
        assert not MOD.host_semantic_issues((ROOT / document_by_class[class_id]).read_text(encoding="utf-8"), record, records)
