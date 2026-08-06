from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import threading
import time
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


MIB = 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def percentile(samples: list[float], percent: float) -> float:
    ordered = sorted(samples)
    position = (len(ordered) - 1) * percent / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


class GpuMemorySampler:
    def __init__(self, device_index: int, interval_seconds: float = 0.01) -> None:
        import pynvml

        pynvml.nvmlInit()
        self.pynvml = pynvml
        self.handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
        self.interval_seconds = interval_seconds
        self.samples: list[int] = []
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def current(self) -> int:
        return int(self.pynvml.nvmlDeviceGetMemoryInfo(self.handle).used)

    def start(self) -> None:
        self.samples = [self.current()]
        self.stop_event.clear()

        def sample() -> None:
            while not self.stop_event.wait(self.interval_seconds):
                self.samples.append(self.current())

        self.thread = threading.Thread(target=sample, daemon=True)
        self.thread.start()

    def stop(self) -> int:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)
        self.samples.append(self.current())
        return max(self.samples)


def synchronize_cuda() -> None:
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.synchronize()
    except Exception:
        return


def load_images(images_file: Path, count: int) -> list[np.ndarray[Any, Any]]:
    paths = [Path(line.strip()) for line in images_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not paths:
        raise ValueError(f"No image paths found in {images_file}")
    images = []
    for path in paths[:count]:
        with Image.open(path) as source:
            images.append(np.asarray(source.convert("RGB")))
    return images


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark PT or ONNX Ultralytics inference end to end.")
    parser.add_argument("model", type=Path)
    parser.add_argument("--images-file", type=Path, required=True)
    parser.add_argument("--device", default="0")
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--batch-sizes", default="1,8,32,64")
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--preload-images", type=int, default=64)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    model_path = args.model.expanduser().resolve(strict=True)
    images_file = args.images_file.expanduser().resolve(strict=True)
    batch_sizes = [int(value) for value in args.batch_sizes.split(",") if value.strip()]
    images = load_images(images_file, max(args.preload_images, max(batch_sizes)))

    from ultralytics import YOLO

    gpu_index = int(args.device.split(":")[-1]) if args.device not in {"cpu", "mps"} else 0
    sampler = GpuMemorySampler(gpu_index)
    gpu_baseline = sampler.current()
    model = YOLO(str(model_path), task="detect")
    results_by_batch = []
    global_peak = gpu_baseline
    for batch_size in batch_sizes:
        batch = [images[index % len(images)] for index in range(batch_size)]
        for _ in range(args.warmup):
            model.predict(
                source=batch,
                imgsz=args.image_size,
                conf=args.confidence,
                device=args.device,
                verbose=False,
            )
        synchronize_cuda()
        memory_before = sampler.current()
        sampler.start()
        elapsed_ms = []
        speed_samples: dict[str, list[float]] = {}
        for _ in range(args.iterations):
            synchronize_cuda()
            started = time.perf_counter()
            predictions = model.predict(
                source=batch,
                imgsz=args.image_size,
                conf=args.confidence,
                device=args.device,
                verbose=False,
            )
            synchronize_cuda()
            elapsed_ms.append((time.perf_counter() - started) * 1000)
            for prediction in predictions:
                for key, value in (prediction.speed or {}).items():
                    speed_samples.setdefault(key, []).append(float(value))
        memory_peak = sampler.stop()
        global_peak = max(global_peak, memory_peak)
        mean_batch_ms = statistics.fmean(elapsed_ms)
        results_by_batch.append(
            {
                "batch_size": batch_size,
                "iterations": args.iterations,
                "latency_batch_ms": {
                    "mean": mean_batch_ms,
                    "p50": percentile(elapsed_ms, 50),
                    "p95": percentile(elapsed_ms, 95),
                    "p99": percentile(elapsed_ms, 99),
                },
                "latency_per_image_ms": mean_batch_ms / batch_size,
                "throughput_images_per_second": batch_size * 1000 / mean_batch_ms,
                "ultralytics_speed_ms_per_image": {
                    key: statistics.fmean(samples) for key, samples in speed_samples.items()
                },
                "gpu_memory_before_mib": memory_before / MIB,
                "gpu_memory_peak_mib": memory_peak / MIB,
                "gpu_memory_peak_delta_from_idle_mib": (memory_peak - gpu_baseline) / MIB,
            }
        )

    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "model": {
            "path": str(model_path),
            "format": model_path.suffix.lower().lstrip("."),
            "sha256": sha256(model_path),
            "size_bytes": model_path.stat().st_size,
        },
        "configuration": {
            "device": args.device,
            "image_size": args.image_size,
            "confidence": args.confidence,
            "warmup": args.warmup,
            "iterations": args.iterations,
            "preloaded_images": len(images),
        },
        "gpu_memory_idle_mib": gpu_baseline / MIB,
        "gpu_memory_global_peak_mib": global_peak / MIB,
        "gpu_memory_global_peak_delta_mib": (global_peak - gpu_baseline) / MIB,
        "batches": results_by_batch,
        "environment": {
            "python": platform.python_version(),
            "ultralytics": package_version("ultralytics"),
            "torch": package_version("torch"),
            "onnxruntime_gpu": package_version("onnxruntime-gpu"),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
