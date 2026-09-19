from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image

from build_ai_illustration_manifest import DOC, KNOWLEDGE, ROOT, parse_prompt_sections


def main() -> int:
    manifest = json.loads((KNOWLEDGE / "ai-illustration-manifest.json").read_text(encoding="utf-8"))
    capability = json.loads((KNOWLEDGE / "capability-fallback.json").read_text(encoding="utf-8"))
    prompts = parse_prompt_sections(DOC.read_text(encoding="utf-8"))
    records = manifest["records"]
    full = {(r["class_id"], r["insect"], r["crop"]) for r in capability["records"] if r["status"] == "FULL" and r["capabilities"]["severity"]}
    errors: list[str] = []
    seen_hosts = Counter((r["class_id"], r["insect"], r["host"]) for r in records)
    if len(records) != 39: errors.append(f"record_count={len(records)}")
    if len({r["asset_id"] for r in records}) != 39: errors.append("duplicate_asset_id")
    if len({r["target_relative_path"] for r in records}) != 39: errors.append("duplicate_target_path")
    if len(seen_hosts) != 13 or any(count != 3 for count in seen_hosts.values()): errors.append(f"host_triplets={dict(seen_hosts)}")
    for row in records:
        key = (row["insect"], row["host"], row["severity"])
        if row["prompt_evidence_status"] != "TRACEABLE" or key not in prompts or prompts[key]["prompt_evidence_status"] != "TRACEABLE": errors.append(f"prompt_gate:{row['asset_id']}")
        elif row["final_prompt"] != prompts[key]["final_prompt"]: errors.append(f"prompt_drift:{row['asset_id']}")
        if (row["class_id"], row["insect"], row["host"]) not in full: errors.append(f"not_full:{row['asset_id']}")
        if row["severity"] not in {"mild", "moderate", "severe"} or row["host"] == "OTHER": errors.append(f"forbidden_scope:{row['asset_id']}")
        if row["generation_status"] != "COMPLETE" or row["review_status"] != "PASS": errors.append(f"not_approved:{row['asset_id']}")
        path = ROOT / row["target_relative_path"]
        if not path.exists(): errors.append(f"missing:{row['asset_id']}"); continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["image_sha256"]: errors.append(f"hash:{row['asset_id']}")
        try:
            with Image.open(path) as image:
                if image.format != "WEBP" or image.width < 1024 or image.height < 1024: errors.append(f"format_or_size:{row['asset_id']}:{image.format}:{image.size}")
        except Exception as exc: errors.append(f"decode:{row['asset_id']}:{exc}")
    extras = sorted(p.name for p in (ROOT / "web/public/r31/severity").iterdir() if p.is_file() and p.suffix.lower() != ".webp")
    if extras: errors.append(f"non_webp_assets={extras}")
    result = {
        "status": "PASS" if not errors else "FAIL", "record_count": len(records),
        "unique_asset_ids": len({r["asset_id"] for r in records}), "unique_target_paths": len({r["target_relative_path"] for r in records}),
        "full_hosts": len(seen_hosts), "severity_counts": dict(Counter(r["severity"] for r in records)),
        "approved_images": sum(r["review_status"] == "PASS" for r in records), "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
