import ast
import unittest
from pathlib import Path
from typing import Any


SOURCE = Path(__file__).resolve().parents[1] / "app" / "main.py"


def load_snapshot_check():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_report_snapshot_is_current"
    )
    namespace: dict[str, Any] = {
        "Any": Any,
        "build_case_report": lambda record: record["current_report"],
        "present_case": lambda record: record["current_case"],
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["_report_snapshot_is_current"]


class ReportSnapshotCurrentnessTests(unittest.TestCase):
    def setUp(self):
        self.check = load_snapshot_check()
        treatment = {
            "status": "available",
            "reason": None,
            "severity_level": "moderate",
            "severity_label": "中度",
            "source_ids": ["local-kb"],
            "content": {"tier": "moderate", "markdown": "内容", "markdown_html": "<p>内容</p>"},
        }
        self.case = {
            "severity": {"level": "moderate"},
            "severity_rubric": {"id": "r3"},
            "host_knowledge": {"confirmed_host": "玉米"},
            "treatment": treatment,
        }
        self.fresh_report = {
            "evidence_analysis": {"status": "available", "harms": [], "possible_causes": []},
            "core_knowledge": {"title": "蚜虫", "fields": [{"key": "features", "html": "<p>特征</p>"}]},
        }
        self.existing = {
            "case": dict(self.case),
            "treatment": dict(treatment),
        }

    def test_stale_evidence_snapshot_is_invalidated(self):
        self.existing["evidence_analysis"] = {
            "status": "available",
            "harms": [],
            "possible_causes": [{"conclusion": "蚜虫很难彻底根除", "source_ids": ["source-2"]}],
        }
        self.assertFalse(self.check(self.existing, {"current_case": self.case, "current_report": self.fresh_report}))

    def test_snapshot_without_core_knowledge_is_invalidated(self):
        self.existing["evidence_analysis"] = self.fresh_report["evidence_analysis"]
        self.assertFalse(self.check(self.existing, {"current_case": self.case, "current_report": self.fresh_report}))

    def test_snapshot_with_current_evidence_and_core_knowledge_is_kept(self):
        self.existing["evidence_analysis"] = self.fresh_report["evidence_analysis"]
        self.existing["core_knowledge"] = self.fresh_report["core_knowledge"]
        self.assertTrue(self.check(self.existing, {"current_case": self.case, "current_report": self.fresh_report}))


if __name__ == "__main__":
    unittest.main()
