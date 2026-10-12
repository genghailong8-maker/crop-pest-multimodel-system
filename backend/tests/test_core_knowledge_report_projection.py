import ast
import re
import unittest
from pathlib import Path
from html import escape


SOURCE = Path(__file__).resolve().parents[1] / "app" / "main.py"


def load_projection(*, item, legacy_document=None):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {"_core_knowledge_for_report", "_insect_core_basic_rows"}]
    namespace = {
        "Any": object,
        "re": re,
        "escape": escape,
        "_insect_core_basic_rows": None,
        "is_official": lambda _version: True,
        "official_item_for_key": lambda _key: item,
        "legacy_insect_id_for_key": lambda _key: 9,
        "get_knowledge_document": lambda _legacy_id: legacy_document,
        "official_knowledge_card": lambda *_args: {"basic_info": {"rows": [{"field": "中文名", "value": item.get("name_zh", "")}, {"field": "主要病原", "value": "pathogen"}]}} if item.get("type") == "病害" else None,
    }
    module = ast.Module(body=functions, type_ignores=[])
    exec(compile(module, str(SOURCE), "exec"), namespace)
    namespace["_core_knowledge_for_report"].__globals__["_insect_core_basic_rows"] = namespace["_insect_core_basic_rows"]
    return namespace["_core_knowledge_for_report"]


class CoreKnowledgeReportProjectionTests(unittest.TestCase):
    def test_disease_projects_only_three_core_sections_and_hides_empty_fields(self):
        project = load_projection(item={"type": "病害", "name_zh": "病害A"})
        doc = {
            "class_name": "病害A",
            "sections": [
                {"title": "基础信息", "html": "<p>病害信息</p>"},
                {"title": "特征", "html": "<p>外观特征</p>"},
                {"title": "为害症状", "html": "<p>受害症状</p>"},
                {"title": "防治方法", "html": "<p>不得展示此项</p>"},
            ],
        }
        result = project(0, {"taxonomy_version": "official"}, doc)
        self.assertEqual([field["title"] for field in result["fields"]], ["病虫害信息", "特征", "危害症状"])
        self.assertEqual(result["fields"][0]["rows"], [{"label": "中文名", "value": "病害A"}, {"label": "主要病原", "value": "pathogen"}])
        self.assertNotIn("防治方法", str(result))

    def test_insect_uses_mapped_local_document_without_disease_endpoint_payload(self):
        project = load_projection(
            item={"type": "害虫", "name_zh": "蚜虫"},
            legacy_document={"class_name": "蚜虫", "title": "蚜虫", "markdown": "# 蚜虫\n\n| 中文名 | 蚜虫 | 外文名 | Aphids |\n| --- | --- | --- | --- |\n\n## 特征\n\n内容", "features_html": "<p>特征</p>", "symptoms_html": "<p>危害</p>"},
        )
        result = project(6, {"taxonomy_version": "official", "canonical_key": "aphid"}, None)
        self.assertEqual([field["title"] for field in result["fields"]], ["病虫害信息", "特征", "危害症状"])
        self.assertEqual(result["fields"][0]["rows"], [{"label": "外文名", "value": "Aphids"}])

    def test_unavailable_local_document_fails_closed(self):
        project = load_projection(item={"type": "害虫", "name_zh": "蚜虫"})
        self.assertIsNone(project(6, {"taxonomy_version": "official", "canonical_key": "aphid"}, None))

    def test_empty_core_sections_are_omitted_without_placeholders(self):
        project = load_projection(item={"type": "病害", "name_zh": "病害A"})
        result = project(0, {"taxonomy_version": "official"}, {"class_name": "病害A", "sections": []})
        self.assertEqual([field["key"] for field in result["fields"]], ["basic_info"])


if __name__ == "__main__":
    unittest.main()
