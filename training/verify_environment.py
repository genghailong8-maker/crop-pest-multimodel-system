from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def package_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def nvidia_smi() -> str | None:
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a CUDA training environment and record it as JSON.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()

    try:
        import torch
    except ImportError as exc:
        raise SystemExit("PyTorch is not installed in this environment.") from exc

    report = {
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count(),
        "cuda_devices": [
            {
                "index": index,
                "name": torch.cuda.get_device_name(index),
                "total_memory_gb": round(
                    torch.cuda.get_device_properties(index).total_memory / 1024**3,
                    2,
                ),
                "compute_capability": ".".join(
                    str(part) for part in torch.cuda.get_device_capability(index)
                ),
            }
            for index in range(torch.cuda.device_count())
        ],
        "nvidia_smi": nvidia_smi(),
        "ultralytics": package_version("ultralytics"),
    }

    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")

    if not report["cuda_available"] and not args.allow_cpu:
        raise SystemExit("CUDA is unavailable; do not start the full training run.")


if __name__ == "__main__":
    main()
