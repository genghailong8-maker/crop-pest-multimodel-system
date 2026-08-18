from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.database import init_database, list_cases  # noqa: E402
from app.main import build_case_report, snapshot_case_report  # noqa: E402
from app.reports import load_latest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Upgrade eligible v1 report snapshots to knowledge v2.")
    parser.add_argument("--apply", action="store_true", help="Write v2 snapshots; otherwise only report candidates.")
    args = parser.parse_args()

    init_database()
    candidates: list[dict[str, str]] = []
    skipped_v2 = 0
    for record in list_cases(10_000, record_scope="all"):
        existing = load_latest(settings.report_dir, record["id"])
        if not existing:
            continue
        if existing.get("snapshot", {}).get("format") == "crop-report-json-v2":
            skipped_v2 += 1
            continue
        report = build_case_report(record)
        document = report.get("knowledge_document")
        if not document:
            continue
        candidates.append({"case_id": record["id"], "class_name": document["class_name"]})
        if args.apply:
            snapshot_case_report(record)

    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "check",
                "eligible": len(candidates),
                "already_v2": skipped_v2,
                "cases": candidates,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
