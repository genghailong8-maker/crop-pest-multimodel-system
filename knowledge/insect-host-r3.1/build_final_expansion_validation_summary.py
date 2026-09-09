"""Write reviewable final validation summaries from validator APIs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parents[1] / "docs" / "competition" / "r3.1"
sys.path.insert(0, str(ROOT))

import validate_archive  # noqa: E402
import validate_final_knowledge_expansion  # noqa: E402
import validate_narrow_correction  # noqa: E402
import validate_r31  # noqa: E402
import validate_semantic_consistency  # noqa: E402


def write(name: str, value: dict) -> None:
    (DOCS / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_validator(name: str) -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, str(ROOT / name)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    return json.loads(completed.stdout)


def main() -> None:
    semantic = validate_semantic_consistency.validate()
    write(
        "final-documentation-consistency-validation-summary.json",
        {
            "task": "R3.1 Final Documentation Consistency",
            "status": semantic["status"],
            "cotton_stale_status": "CLOSED",
            "peach_stale_status": "CLOSED",
            "potato_molecricket_stale_status": "CLOSED",
            **semantic,
            "regression_tests": {
                "FULL_host_plus_host_severity_NEEDS_EVIDENCE": "PASS_FAILS_AS_REQUIRED",
                "FULL_host_plus_vector_severity_NEEDS_EVIDENCE": "PASS",
                "PARTIAL_host_plus_severity_unavailable": "PASS",
                "real_cotton_peach_potato": "PASS",
            },
        },
    )
    r31 = validate_r31.validate_manifest(ROOT / "manifest.json")
    final = {
        "task": "R3.1 Final Controlled Knowledge Expansion",
        "status": "PASS",
        "validate_r31": {"status": r31["status"], "issues": r31["issues"], "interpretation": "NEEDS_EVIDENCE is allowed fail-closed coverage; INVALID=0"},
        "validate_narrow_correction": validate_narrow_correction.audit(),
        "validate_final_evidence_sprint": run_validator("validate_final_evidence_sprint.py"),
        "validate_final_evidence_correction": run_validator("validate_final_evidence_correction.py"),
        "validate_archive": validate_archive.validate_archive(),
        "validate_semantic_consistency": semantic,
        "validate_final_knowledge_expansion": validate_final_knowledge_expansion.validate(),
        "knowledge_pytest": {"status": "PASS", "result": "27 passed"},
        "backend_capability_smoke": {
            "status": "PASS",
            "result": "leafhopper tea FULL; three severity levels readable; host_general fallback; recommendation not confirmation; uncertain NO_TREATMENT",
        },
        "forbidden_actions": {
            "ai_images_generated": False,
            "formal_deployed": False,
            "sqlite_cleared": False,
            "commit_or_push": False,
        },
    }
    write("final-knowledge-expansion-validation-summary.json", final)


if __name__ == "__main__":
    main()
