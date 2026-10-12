import ast
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "app" / "main.py"


def load_presenter():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "host_knowledge_for_runtime"
    )
    namespace = {
        "Any": object,
        "record_identity": lambda _record: None,
        "host_knowledge_payload": lambda _record: {
            "available": True,
            "treatment": {"treatment_level": "host_general"},
        },
        "r31_record_adapter": lambda record: record,
        "is_official": lambda _version: False,
    }
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace["host_knowledge_for_runtime"]


class HostKnowledgeUncertainTreatmentTests(unittest.TestCase):
    def test_uncertain_removes_host_general_treatment(self):
        present = load_presenter()
        result = present(
            {"severity": {"status": "available", "level": "uncertain"}}
        )
        self.assertIsNone(result["treatment"])

    def test_moderate_preserves_existing_treatment(self):
        present = load_presenter()
        result = present(
            {"severity": {"status": "available", "level": "moderate"}}
        )
        self.assertEqual(result["treatment"], {"treatment_level": "host_general"})


if __name__ == "__main__":
    unittest.main()
