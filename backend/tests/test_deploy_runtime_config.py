from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_RUNTIME_TERMS = ("qwen", "vlm", "8890", "crop_vlm")


def test_current_deploy_configuration_has_no_qwen_runtime_dependency() -> None:
    matches: list[str] = []
    for path in (ROOT / "deploy").rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for term in FORBIDDEN_RUNTIME_TERMS:
            if term in lowered:
                matches.append(f"{path.relative_to(ROOT)}:{term}")
    assert matches == []
