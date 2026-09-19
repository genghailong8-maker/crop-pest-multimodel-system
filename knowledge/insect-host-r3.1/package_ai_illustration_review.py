from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ZIP_PATH = ROOT / "r31-ai-illustration-review-20260908.zip"
SHA_PATH = ROOT / "r31-ai-illustration-review-20260908.sha256.txt"


def main() -> int:
    required = [
        "knowledge/insect-host-r3.1/ai-illustration-manifest.json",
        "knowledge/insect-host-r3.1/build_ai_illustration_manifest.py",
        "knowledge/insect-host-r3.1/finalize_ai_illustration_assets.py",
        "knowledge/insect-host-r3.1/validate_ai_illustration_assets.py",
        "docs/competition/r3.1/《AI示意图正式资产清单》.md",
        "docs/competition/r3.1/《AI示意图生成任务清单》.md",
        "docs/competition/r3.1/《AI示意图提示词与来源依据》.md",
        "docs/competition/r3.1/《R3.1完整知识库归档版》.md",
        "docs/competition/r3.1/ai-image-review-summary.json",
        "docs/competition/r3.1/ai-illustration-build-test-summary.json",
        "web/app/lib/r31SeverityAssets.ts",
        "web/app/components/R31HostKnowledgePanel.tsx",
        "web/app/product-legacy.css",
        "web/tests/r31-ai-assets.test.mjs",
        "web/tests/r31-web.test.mjs",
    ]
    images = sorted((ROOT / "web/public/r31/severity").glob("*.webp"))
    if len(images) != 39:
        raise SystemExit(f"expected 39 images, got {len(images)}")
    members = required + [p.relative_to(ROOT).as_posix() for p in images]
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit(f"missing required files: {missing}")
    entries = []
    for name in members:
        data = (ROOT / name).read_bytes()
        entries.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    bundle_manifest = {
        "bundle": ZIP_PATH.name, "batch": "R3.1 Batch 4B", "file_count": len(members) + 1,
        "approved_images": 39, "entries": entries,
    }
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in members:
            archive.write(ROOT / name, name)
        archive.writestr("BUNDLE_MANIFEST.json", json.dumps(bundle_manifest, ensure_ascii=False, indent=2) + "\n")
    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = archive.namelist()
        corrupt = archive.testzip()
        embedded = json.loads(archive.read("BUNDLE_MANIFEST.json"))
    expected = len(members) + 1
    if corrupt is not None or len(names) != expected or embedded["file_count"] != expected:
        raise SystemExit(f"bundle integrity failure corrupt={corrupt} zip={len(names)} manifest={embedded['file_count']} expected={expected}")
    digest = hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()
    SHA_PATH.write_text(f"{digest}  {ZIP_PATH.name}\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "zip_path": str(ZIP_PATH), "sha256": digest, "sha256_file": str(SHA_PATH), "file_count": expected, "files": names}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
