from __future__ import annotations

import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "run_phase9_model_search.py"
SPEC = importlib.util.spec_from_file_location("phase9_search", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def metrics(overall: float, weak: float, recall: float = 0.5) -> dict[str, object]:
    per_class = [overall] * 16
    for index in module.WEAK_CLASS_IDS:
        per_class[index] = weak
    return {
        "map50_95": overall,
        "map50": overall + 0.2,
        "precision_mean": 0.7,
        "recall_mean": recall,
        "class_map50_95": per_class,
        "best_weights": "/tmp/best.pt",
        "training_arguments": {"epochs": 120},
    }


def test_weighted_selection_score() -> None:
    result = module.summarize_metrics("candidate", metrics(0.5, 0.4))
    assert result["weak_map50_95"] == 0.4
    assert result["selection_score"] == 0.47


def test_report_flags_close_score_for_runtime_benchmark(tmp_path: Path) -> None:
    first = module.summarize_metrics("first", metrics(0.5, 0.4, 0.6))
    second = module.summarize_metrics("second", metrics(0.499, 0.4, 0.7))
    path = tmp_path / "result.json"
    module.write_report(path, [first, second], [])
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["provisional_winner"] == "first"
    assert report["tie_requires_runtime_benchmark"] is True
