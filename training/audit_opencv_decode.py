"""Locate images that OpenCV decodes with warnings or failures."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


def decode_issue(path: Path) -> str | None:
    import cv2

    saved_stderr = os.dup(2)
    try:
        with tempfile.TemporaryFile() as diagnostics:
            os.dup2(diagnostics.fileno(), 2)
            try:
                image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            finally:
                os.dup2(saved_stderr, 2)
            diagnostics.seek(0)
            warning = diagnostics.read().decode("utf-8", errors="replace").strip()
        if image is None:
            return warning or "OpenCV returned no image"
        return warning or None
    finally:
        os.close(saved_stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images_file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    images = [Path(line.strip()) for line in args.images_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    issues = []
    for path in images:
        issue = decode_issue(path)
        if issue:
            issues.append({"path": str(path), "issue": issue})
    report = {"images_checked": len(images), "issue_count": len(issues), "issues": issues}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
