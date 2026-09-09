"""Build and verify the R3.1 final knowledge-expansion reapproval bundle."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
R31 = PROJECT / "knowledge" / "insect-host-r3.1"
DOCS = PROJECT / "docs" / "competition" / "r3.1"
PLANTS = PROJECT / "knowledge" / "baidu-baike-20260818" / "documents"
ZIP_PATH = PROJECT / "r31-final-knowledge-expansion-reapproval-20260908.zip"
SHA_PATH = PROJECT / "r31-final-knowledge-expansion-reapproval-20260908.sha256.txt"

FORMAL_DOCS = [
    "《R3.1完整知识库归档版》.md",
    "《昆虫×寄主作物知识库总表》.md",
    "《严重程度描述与具体来源总表》.md",
    "《防治措施与农药来源总表》.md",
    "《AI示意图提示词与来源依据》.md",
    "《知识库变更报告》.md",
    "图像生成规格与提示词草案.md",
    "《Final Knowledge Expansion Summary》.md",
    "batch4a-why-not-upgraded.md",
    "final-documentation-consistency-validation-summary.json",
    "final-knowledge-expansion-validation-summary.json",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def include(path: Path) -> bool:
    return "__pycache__" not in path.parts and ".pytest_cache" not in path.parts and path.suffix != ".pyc"


def main() -> None:
    paths = [path for path in R31.rglob("*") if path.is_file() and include(path)]
    paths.extend(DOCS / name for name in FORMAL_DOCS)
    paths.extend(PLANTS / f"{index:02d}.md" for index in range(8))
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError(f"required files missing: {missing}")

    unique = sorted(set(paths), key=lambda path: path.relative_to(PROJECT).as_posix())
    entries = []
    for path in unique:
        data = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(PROJECT).as_posix(),
                "size": len(data),
                "sha256": digest(data),
            }
        )
    manifest = {
        "bundle": ZIP_PATH.name,
        "created_at": "2026-09-08",
        "purpose": "R3.1 Final Documentation Consistency + Final Controlled Knowledge Expansion reapproval",
        "file_count": len(entries) + 1,
        "files": entries + [{"path": "BUNDLE_MANIFEST.json", "size": None, "sha256": "self-described-at-archive-level"}],
        "gates": {
            "documentation_consistency": "PASS",
            "semantic_consistency": "PASS",
            "final_knowledge_expansion": "PASS",
            "archive_knowledge_parity": "PASS",
            "knowledge_expansion_stopped": "YES",
            "ai_images_generated": False,
            "formal_deployed": False,
            "commit_or_push": False,
        },
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in unique:
            archive.write(path, path.relative_to(PROJECT).as_posix())
        archive.writestr("BUNDLE_MANIFEST.json", manifest_bytes)

    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        corrupt = archive.testzip()
        names = archive.namelist()
        if corrupt is not None:
            raise RuntimeError(f"corrupt ZIP member: {corrupt}")
        if len(names) != manifest["file_count"] or set(names) != {item["path"] for item in manifest["files"]}:
            raise RuntimeError("ZIP member list does not match BUNDLE_MANIFEST")
        archived_manifest = json.loads(archive.read("BUNDLE_MANIFEST.json").decode("utf-8"))
        if archived_manifest["file_count"] != len(names):
            raise RuntimeError("archived manifest count mismatch")

    zip_sha = digest(ZIP_PATH.read_bytes())
    SHA_PATH.write_text(f"{zip_sha}  {ZIP_PATH.name}\n", encoding="ascii")
    print(json.dumps({"status": "PASS", "zip_path": str(ZIP_PATH), "sha256": zip_sha, "sha256_file": str(SHA_PATH), "file_count": manifest["file_count"], "files": [item["path"] for item in manifest["files"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
