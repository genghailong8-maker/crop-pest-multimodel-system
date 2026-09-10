"""Check the frozen detector promotion gates against the currently deployed baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


BASELINE = {
    "map50_95": 0.5482240976396971,
    "map50": 0.8275166812267114,
    "recall": 0.7762048083006122,
    "weak": {8: 0.3006412354180316, 10: 0.31803588790281545, 13: 0.3781440072495144, 15: 0.4064577468014091},
}


def evaluate(metrics: dict[str, object]) -> dict[str, object]:
    overall = metrics["overall"]
    per_class = {int(item["class_id"]): float(item["map50_95"]) for item in metrics["per_class"]}
    weak_ids = tuple(BASELINE["weak"])
    weak_mean = sum(per_class[index] for index in weak_ids) / len(weak_ids)
    baseline_weak_mean = sum(BASELINE["weak"].values()) / len(BASELINE["weak"])
    checks = {
        "map50_95_improved": float(overall["map50_95"]) > BASELINE["map50_95"],
        "map50_not_lower": float(overall["map50"]) >= BASELINE["map50"],
        "recall_not_lower": float(overall["recall"]) >= BASELINE["recall"],
        "weak_mean_gain_at_least_0_02": weak_mean >= baseline_weak_mean + 0.02,
        "weak_classes_no_drop_over_0_02": all(per_class[index] >= BASELINE["weak"][index] - 0.02 for index in weak_ids),
        "all_16_classes_have_evidence": set(per_class) == set(range(16)) and all(per_class[index] > 0 for index in range(16)),
    }
    return {
        "baseline": BASELINE,
        "candidate": {"overall": overall, "weak_mean_map50_95": weak_mean, "per_class_map50_95": per_class},
        "checks": checks,
        "detector_gate_passed": all(checks.values()),
        "remaining_system_gates": ["160-image multimodal evaluation", "full-chain P95 <= 7s", "detector and Qwen3-VL 32GB coexistence"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(json.loads(args.metrics.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
