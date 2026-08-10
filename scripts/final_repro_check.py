"""Run Phase 7 static reproducibility and public-boundary checks.

The command is intentionally stdlib-only. Runtime probes are optional so the
same check can run with the GPU server and web services offline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TRACKED = re.compile(
    r"(?:^|/)(?:\.env(?:\..*)?|.*\.(?:pt|onnx|jpg|jpeg|png|bmp|webp|zip|tar|gz|7z|db|sqlite|log|pem|key)|id_rsa(?:\..*)?)$",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def probe(url: str, timeout: float = 1.5) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "phase7-repro-check/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(256 * 1024)
            payload: Any = None
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            return {"url": url, "reachable": True, "status": response.status, "json": payload}
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return {"url": url, "reachable": False, "error": str(exc)}


def check_knowledge() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.knowledge import KNOWLEDGE_SCHEMA_VERSION, knowledge_contract

    contract = knowledge_contract()
    classes = contract.get("classes")
    sources = contract.get("sources")
    class_ids = sorted(item.get("class_id") for item in classes or [] if isinstance(item, dict))
    source_ids = {item.get("id") for item in sources or [] if isinstance(item, dict)}
    referenced = {
        source_id
        for card in classes or []
        if isinstance(card, dict)
        for source_id in card.get("source_ids", [])
    }
    safety = contract.get("safety_boundary") or {}
    checks = {
        "schema_version": contract.get("schema_version") == KNOWLEDGE_SCHEMA_VERSION,
        "class_count_16": len(classes or []) == 16,
        "class_ids_0_to_15": class_ids == list(range(16)),
        "source_count_at_least_4": len(sources or []) >= 4,
        "all_card_sources_registered": referenced <= source_ids,
        "chemical_boundary_present": all(
            term in str(safety.get("chemical_limit")) for term in ("产品", "剂量", "安全间隔")
        ),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "schema_version": contract.get("schema_version"),
        "class_count": len(classes or []),
        "source_count": len(sources or []),
    }


def check_phase5_evidence() -> dict[str, Any]:
    path = ROOT / "artifacts/server/phase5-full-evidence-20260810.json"
    evidence = read_json(path)
    scope = evidence.get("scope", {})
    routing = evidence.get("configuration", {}).get("inference_health_routing", {})
    gate = evidence.get("configuration", {}).get("routing_gate")
    metrics = evidence.get("metrics", {}).get("main_official_frozen", {}).get("overall", {})
    checks = {
        "official_classes_16": scope.get("official_classes") == 16,
        "official_train_3321": scope.get("official_training_images") == 3321,
        "official_frozen_833": scope.get("official_frozen_validation_images") == 833,
        "independent_tune_101": scope.get("independent_tune_images") == 101,
        "independent_frozen_85": scope.get("independent_frozen_images") == 85,
        "active_routing_forbidden": scope.get("active_routing_allowed") is False,
        "routing_shadow": routing.get("mode") == "shadow",
        "routing_gate_explicit": isinstance(gate, str) and "shadow" in gate,
        "main_metrics_present": all(key in metrics for key in ("precision", "recall", "map50", "map50_95")),
        "retained_roles_four": scope.get("retained_model_roles") == 4,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "sha256": sha256(path),
        "metrics": metrics,
        "routing_mode": routing.get("mode"),
        "active_routing_allowed": scope.get("active_routing_allowed"),
    }


def check_required_files() -> dict[str, Any]:
    relative_paths = [
        "task_plan.md",
        "findings.md",
        "progress.md",
        "README.md",
        "PUBLICATION_POLICY.md",
        "backend/app/knowledge.py",
        "backend/app/main.py",
        "backend/tests/test_api.py",
        "web/app/page.tsx",
        "docs/competition/architecture-and-innovation.md",
        "docs/competition/demo-runbook.md",
        "docs/competition/reproducibility-checklist.md",
        "docs/competition/presentation-outline.md",
        "docs/competition/submission-package.md",
        "scripts/final_repro_check.py",
        "scripts/collect_phase5_evidence.py",
        "artifacts/server/phase5-full-evidence-20260810.json",
        "artifacts/server/phase5-benchmark-20260810-route.json",
        "artifacts/server/phase5-benchmark-20260810-main-pt.json",
        "artifacts/experiments/independent-field-calibration-10-13-v2/second-round-calibration-v2.json",
    ]
    missing = [path for path in relative_paths if not (ROOT / path).is_file()]
    return {"required_count": len(relative_paths), "missing": missing, "passed": not missing}


def check_public_boundary() -> dict[str, Any]:
    tracked = [item for item in run_git("ls-files").splitlines() if item]
    allowed_examples = {"backend/.env.example"}
    forbidden = [
        item
        for item in tracked
        if item not in allowed_examples and FORBIDDEN_TRACKED.search(item.replace("\\", "/"))
    ]
    claude_tracked = "CLAUDE.md" in tracked
    return {
        "tracked_file_count": len(tracked),
        "forbidden_tracked_files": forbidden,
        "claude_md_tracked": claude_tracked,
        "passed": not forbidden and not claude_tracked,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write a JSON report to this path")
    parser.add_argument("--require-services", action="store_true", help="fail if runtime probes are unreachable")
    args = parser.parse_args()

    required_files = check_required_files()
    knowledge = check_knowledge()
    phase5 = check_phase5_evidence()
    public_boundary = check_public_boundary()
    runtime = [
        probe("http://127.0.0.1:8000/health"),
        probe("http://127.0.0.1:8000/api/catalog/knowledge"),
        probe("http://127.0.0.1:8870/health"),
        probe("http://localhost:3000/"),
    ]
    runtime_passed = all(item.get("reachable") for item in runtime)
    report: dict[str, Any] = {
        "schema_version": "phase7-final-repro-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "git": {
            "branch": run_git("branch", "--show-current"),
            "commit": run_git("rev-parse", "HEAD"),
            "status_short": run_git("status", "--short", "--branch"),
        },
        "checks": {
            "required_files": required_files,
            "knowledge_contract": knowledge,
            "phase5_evidence": phase5,
            "public_boundary": public_boundary,
            "runtime_services": {
                "required": args.require_services,
                "passed": runtime_passed if args.require_services else True,
                "probes": runtime,
            },
        },
    }
    report["passed"] = all(
        [
            required_files["passed"],
            knowledge["passed"],
            phase5["passed"],
            public_boundary["passed"],
            runtime_passed if args.require_services else True,
        ]
    )
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
