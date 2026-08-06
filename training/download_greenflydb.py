"""Download and verify the public GreenFlyDB YOLO files."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


FILES = {
    "train": {
        "filename": "GreenflyDB_YOLO_train.zip",
        "url": "https://data.mendeley.com/public-files/datasets/rty8hdb2xm/files/3ad6494e-de7d-4b12-8a73-e2f1cbed61a4/file_downloaded",
        "sha256": "117a9936ff6c2cfb86b586b8cfa04a61fdf9c2ab710afd20572e23df9f17c9fe",
        "size": 127933287,
    },
    "valid": {
        "filename": "GreenflyDB_YOLO_valid.zip",
        "url": "https://data.mendeley.com/public-files/datasets/rty8hdb2xm/files/b677306b-2a34-45d9-906b-413055cfb9ef/file_downloaded",
        "sha256": "0179b734f289595d0638a2f63f44fb9c18bb990ded308b30b1ac0b276b45e32b",
        "size": 35244616,
    },
    "test": {
        "filename": "GreenflyDB_YOLO_test_and_config.zip",
        "url": "https://data.mendeley.com/public-files/datasets/rty8hdb2xm/files/7774a603-9cde-420a-800a-dc560559648b/file_downloaded",
        "sha256": "d3ecfe92d0036568383c06fe7ab098da7cc252fcb57692b8d1b118cddf273030",
        "size": 17858267,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/public/greenflydb"))
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for split, metadata in FILES.items():
        destination = output_dir / metadata["filename"]
        if not destination.is_file() or destination.stat().st_size != metadata["size"]:
            request = urllib.request.Request(metadata["url"], headers={"User-Agent": "crop-pest-system/1.0"})
            with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as stream:
                while chunk := response.read(1024 * 1024):
                    stream.write(chunk)
        digest = sha256(destination)
        if digest != metadata["sha256"]:
            raise RuntimeError(f"{destination} sha256 mismatch: {digest} != {metadata['sha256']}")
        downloaded.append({"split": split, **metadata, "path": str(destination)})

    provenance = {
        "dataset": "GreenFlyDB",
        "doi": "10.17632/rty8hdb2xm.1",
        "homepage": "https://data.mendeley.com/datasets/rty8hdb2xm/1",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "description": "Aphid/greenfly YOLO detection data with Green Fly and Not Green Fly classes.",
        "downloaded_files": downloaded,
        "usage_note": "Green Fly can be mapped to official class 9 after audit; Not Green Fly is a hard-negative candidate and is not automatically converted to a 16-class label.",
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(provenance, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
