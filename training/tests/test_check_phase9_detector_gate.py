from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "check_phase9_detector_gate.py"
SPEC = importlib.util.spec_from_file_location("phase9_gate", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def candidate(delta: float) -> dict[str, object]:
    per_class = []
    for class_id in range(16):
        baseline = module.BASELINE["weak"].get(class_id, 0.5)
        per_class.append({"class_id": class_id, "map50_95": baseline + delta})
    return {
        "overall": {
            "map50_95": module.BASELINE["map50_95"] + delta,
            "map50": module.BASELINE["map50"] + delta,
            "recall": module.BASELINE["recall"] + delta,
        },
        "per_class": per_class,
    }


def test_detector_gate_passes_all_improvements() -> None:
    assert module.evaluate(candidate(0.03))["detector_gate_passed"] is True


def test_detector_gate_rejects_non_improvement() -> None:
    result = module.evaluate(candidate(0.0))
    assert result["detector_gate_passed"] is False
    assert result["checks"]["map50_95_improved"] is False
    assert result["checks"]["weak_mean_gain_at_least_0_02"] is False
