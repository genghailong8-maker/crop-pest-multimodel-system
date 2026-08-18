from __future__ import annotations

import argparse
import hashlib
import json
import re
import runpy
import shutil
from pathlib import Path


VERSION = "baidu-baike-20260818"
MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HTML_IMAGE = re.compile(r'<img\s+[^>]*src="([^"]+)"[^>]*>', re.IGNORECASE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Package the curated Baidu Baike knowledge base.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("knowledge") / VERSION)
    args = parser.parse_args()

    source_dir = args.source.resolve()
    output_dir = args.output.resolve()
    if not source_dir.is_dir():
        raise SystemExit(f"Knowledge source does not exist: {source_dir}")
    if output_dir.exists():
        raise SystemExit(f"Output already exists; remove it explicitly before rebuilding: {output_dir}")

    catalog = runpy.run_path(str(Path(__file__).resolve().parents[1] / "backend" / "app" / "catalog.py"))[
        "CLASS_CATALOG"
    ]
    documents_dir = output_dir / "documents"
    assets_dir = output_dir / "assets"
    documents_dir.mkdir(parents=True)
    assets_dir.mkdir(parents=True)

    manifest_documents: list[dict[str, object]] = []
    referenced_images = 0

    for item in catalog:
        class_id = int(item["id"])
        class_name = str(item["name_zh"])
        source_path = source_dir / f"{class_name}.md"
        if not source_path.is_file():
            raise SystemExit(f"Missing class document: {source_path.name}")

        raw = source_path.read_text(encoding="utf-8-sig")
        class_assets = assets_dir / f"{class_id:02d}"
        copied: dict[Path, str] = {}

        def package_image(raw_path: str) -> str:
            nonlocal referenced_images
            normalized = raw_path.strip()
            source_image = Path(normalized)
            if not source_image.is_absolute():
                source_image = (source_path.parent / source_image).resolve()
            if not source_image.is_file():
                raise SystemExit(f"Missing referenced image in {source_path.name}: {normalized}")
            if source_image.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                raise SystemExit(f"Unsupported image type in {source_path.name}: {normalized}")
            referenced_images += 1
            if source_image not in copied:
                class_assets.mkdir(parents=True, exist_ok=True)
                destination = class_assets / source_image.name
                if destination.exists() and sha256(destination) != sha256(source_image):
                    raise SystemExit(f"Image name collision for class {class_name}: {source_image.name}")
                shutil.copy2(source_image, destination)
                copied[source_image] = f"../assets/{class_id:02d}/{destination.name}"
            return copied[source_image]

        raw = MARKDOWN_IMAGE.sub(
            lambda match: f"![{match.group(1)}]({package_image(match.group(2))})",
            raw,
        )
        raw = HTML_IMAGE.sub(lambda match: f"![知识库图片]({package_image(match.group(1))})", raw)
        if re.search(r"[A-Za-z]:\\", raw):
            raise SystemExit(f"Absolute Windows path remains in {source_path.name}")

        document_path = documents_dir / f"{class_id:02d}.md"
        normalized = "\n".join(line.rstrip() for line in raw.splitlines()).rstrip() + "\n"
        document_path.write_text(normalized, encoding="utf-8", newline="\n")
        manifest_documents.append(
            {
                "class_id": class_id,
                "class_name": class_name,
                "document": document_path.relative_to(output_dir).as_posix(),
                "document_sha256": sha256(document_path),
                "images": [
                    {
                        "path": path.relative_to(output_dir).as_posix(),
                        "sha256": sha256(path),
                    }
                    for path in sorted(class_assets.glob("*"))
                ],
            }
        )

    if referenced_images != 61:
        raise SystemExit(f"Expected 61 referenced images, found {referenced_images}")

    manifest = {
        "schema_version": "baidu-knowledge-v1",
        "version": VERSION,
        "source": {
            "title": "百度百科",
            "url": "https://baike.baidu.com/",
            "attribution": "知识内容来源：百度百科（由项目组整理，知识库版本 2026-08-18）",
        },
        "documents": manifest_documents,
        "referenced_image_count": referenced_images,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output_dir / "README.md").write_text(
        "# 百度百科自建知识库\n\n"
        "知识内容来源：百度百科（由项目组整理，知识库版本 2026-08-18）。\n\n"
        "本目录是部署副本；原始 Markdown 的事实内容未被自动改写，只将本地图片引用规范化为相对路径。\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Packaged {len(manifest_documents)} documents and {referenced_images} image references into {output_dir}")


if __name__ == "__main__":
    main()
