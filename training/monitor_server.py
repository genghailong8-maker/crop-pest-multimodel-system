from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


METRIC_ALIASES = {
    "epoch": "epoch",
    "time": "elapsed_seconds",
    "train/box_loss": "train_box_loss",
    "train/cls_loss": "train_cls_loss",
    "train/dfl_loss": "train_dfl_loss",
    "train/l1_loss": "train_l1_loss",
    "metrics/precision(B)": "precision",
    "metrics/recall(B)": "recall",
    "metrics/mAP50(B)": "map50",
    "metrics/mAP50-95(B)": "map50_95",
    "val/box_loss": "val_box_loss",
    "val/cls_loss": "val_cls_loss",
    "val/dfl_loss": "val_dfl_loss",
    "val/l1_loss": "val_l1_loss",
    "lr/pg0": "learning_rate",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def number(value: str | None) -> float | int | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return int(parsed) if parsed.is_integer() else parsed


def parse_simple_yaml(path: Path) -> dict[str, str | int | float | bool]:
    values: dict[str, str | int | float | bool] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^([A-Za-z0-9_]+):\s*(.*?)\s*$", raw_line)
        if not match:
            continue
        key, raw_value = match.groups()
        raw_value = raw_value.strip("'\"")
        if raw_value.lower() in {"true", "false"}:
            values[key] = raw_value.lower() == "true"
        else:
            values[key] = number(raw_value) if number(raw_value) is not None else raw_value
    return values


class TrainingMonitor:
    def __init__(self, project_root: Path, sample_seconds: float = 5.0) -> None:
        self.project_root = project_root.resolve()
        self.runs_root = self.project_root / "runs" / "detect"
        self.artifacts_root = self.project_root / "artifacts" / "server"
        self.sample_seconds = sample_seconds
        self.gpu_history: deque[dict[str, object]] = deque(maxlen=720)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._collect_loop, name="gpu-collector", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def _collect_loop(self) -> None:
        while not self._stop.is_set():
            sample = self.read_gpu()
            if sample:
                sample["sampled_at"] = utc_now()
                with self._lock:
                    self.gpu_history.append(sample)
            self._stop.wait(self.sample_seconds)

    @staticmethod
    def read_gpu() -> dict[str, object] | None:
        fields = [
            "utilization.gpu",
            "memory.used",
            "memory.total",
            "temperature.gpu",
            "power.draw",
            "power.limit",
        ]
        try:
            completed = subprocess.run(
                ["nvidia-smi", f"--query-gpu={','.join(fields)}", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=4,
                check=True,
            )
            values = [item.strip() for item in completed.stdout.splitlines()[0].split(",")]
            parsed = [number(value) for value in values]
            return {
                "utilization_percent": parsed[0],
                "memory_used_mb": parsed[1],
                "memory_total_mb": parsed[2],
                "temperature_c": parsed[3],
                "power_w": parsed[4],
                "power_limit_w": parsed[5],
            }
        except (FileNotFoundError, IndexError, subprocess.SubprocessError):
            return None

    def list_runs(self) -> list[dict[str, object]]:
        if not self.runs_root.exists():
            return []
        runs: list[dict[str, object]] = []
        for directory in self.runs_root.iterdir():
            if not directory.is_dir() or not (directory / "args.yaml").exists():
                continue
            args = parse_simple_yaml(directory / "args.yaml")
            rows = self.read_metrics(directory)
            current_epoch = int(rows[-1]["epoch"]) if rows else 0
            epochs = int(args.get("epochs", 0) or 0)
            runs.append(
                {
                    "name": directory.name,
                    "modified_at": datetime.fromtimestamp(directory.stat().st_mtime, timezone.utc).isoformat(),
                    "current_epoch": current_epoch,
                    "total_epochs": epochs,
                    "status": self.run_status(directory.name, current_epoch, epochs),
                    "model": args.get("model"),
                    "image_size": args.get("imgsz"),
                    "batch": args.get("batch"),
                }
            )
        return sorted(runs, key=lambda item: str(item["modified_at"]), reverse=True)

    def run_status(self, name: str, current_epoch: int, epochs: int) -> str:
        pid_path = self.artifacts_root / f"{name}.pid"
        if pid_path.exists():
            try:
                pid = int(pid_path.read_text(encoding="utf-8").strip())
                Path(f"/proc/{pid}").stat()
                return "running"
            except (OSError, ValueError):
                pass
        if epochs and current_epoch >= epochs:
            return "completed"
        run_dir = self.runs_root / name
        if (run_dir / "competition-metrics.json").exists():
            return "completed"
        return "stopped"

    @staticmethod
    def read_metrics(run_dir: Path) -> list[dict[str, object]]:
        results_path = run_dir / "results.csv"
        if not results_path.exists():
            return []
        rows: list[dict[str, object]] = []
        try:
            with results_path.open("r", encoding="utf-8", newline="") as handle:
                for raw_row in csv.DictReader(handle):
                    row: dict[str, object] = {}
                    for source, target in METRIC_ALIASES.items():
                        if source in raw_row:
                            row[target] = number(raw_row[source])
                    rows.append(row)
        except (OSError, csv.Error):
            return []
        return rows

    def status(self, requested_run: str | None = None) -> dict[str, object]:
        runs = self.list_runs()
        if not runs:
            return {"generated_at": utc_now(), "run": None, "runs": [], "gpu": None, "gpu_history": []}
        selected = next((item for item in runs if item["name"] == requested_run), runs[0])
        run_dir = self.runs_root / str(selected["name"])
        args = parse_simple_yaml(run_dir / "args.yaml")
        rows = self.read_metrics(run_dir)
        latest = rows[-1] if rows else None
        best_map50 = max((float(row.get("map50") or 0) for row in rows), default=0.0)
        best_map50_95 = max((float(row.get("map50_95") or 0) for row in rows), default=0.0)
        current_epoch = int(selected["current_epoch"])
        total_epochs = int(selected["total_epochs"])
        elapsed = float(latest.get("elapsed_seconds") or 0) if latest else 0.0
        eta = None
        if current_epoch and total_epochs > current_epoch and elapsed > 0:
            eta = elapsed / current_epoch * (total_epochs - current_epoch)
        with self._lock:
            gpu_history = list(self.gpu_history)[-180:]
        return {
            "generated_at": utc_now(),
            "run": {
                **selected,
                "progress_percent": round(current_epoch / total_epochs * 100, 2) if total_epochs else 0,
                "elapsed_seconds": elapsed,
                "eta_seconds": eta,
                "best_map50": best_map50,
                "best_map50_95": best_map50_95,
                "latest": latest,
                "history": rows,
                "arguments": args,
            },
            "runs": runs,
            "gpu": self.read_gpu(),
            "gpu_history": gpu_history,
        }


def make_handler(monitor: TrainingMonitor) -> type[BaseHTTPRequestHandler]:
    class MonitorHandler(BaseHTTPRequestHandler):
        server_version = "CropTrainingMonitor/1.0"

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self._cors_headers()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._json({"status": "ok", "generated_at": utc_now()})
                return
            if parsed.path == "/api/training/status":
                query = parse_qs(parsed.query)
                requested_run = query.get("run", [None])[0]
                self._json(monitor.status(requested_run))
                return
            self._json({"detail": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def _cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Cache-Control", "no-store")

        def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors_headers()
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return MonitorHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve live Ultralytics training and GPU metrics.")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--sample-seconds", type=float, default=5.0)
    args = parser.parse_args()

    monitor = TrainingMonitor(args.project_root, sample_seconds=args.sample_seconds)
    monitor.start()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(monitor))
    print(f"Training monitor listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        monitor.stop()


if __name__ == "__main__":
    main()
