"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type MetricPoint = {
  epoch?: number;
  elapsed_seconds?: number;
  train_box_loss?: number;
  train_cls_loss?: number;
  train_dfl_loss?: number;
  train_l1_loss?: number;
  val_box_loss?: number;
  val_cls_loss?: number;
  val_dfl_loss?: number;
  val_l1_loss?: number;
  precision?: number;
  recall?: number;
  map50?: number;
  map50_95?: number;
  learning_rate?: number;
};

type GpuPoint = {
  sampled_at?: string;
  utilization_percent?: number;
  memory_used_mb?: number;
  memory_total_mb?: number;
  temperature_c?: number;
  power_w?: number;
  power_limit_w?: number;
};

type RunSummary = {
  name: string;
  modified_at: string;
  current_epoch: number;
  total_epochs: number;
  status: "running" | "completed" | "stopped";
  model?: string;
  image_size?: number;
  batch?: number;
};

type RunDetail = RunSummary & {
  progress_percent: number;
  elapsed_seconds: number;
  eta_seconds?: number | null;
  best_map50: number;
  best_map50_95: number;
  latest?: MetricPoint | null;
  history: MetricPoint[];
};

type MonitorPayload = {
  generated_at: string;
  run: RunDetail | null;
  runs: RunSummary[];
  gpu: GpuPoint | null;
  gpu_history: GpuPoint[];
};

type Series = {
  key: keyof MetricPoint;
  label: string;
  color: string;
};

const MONITOR_BASE = process.env.NEXT_PUBLIC_TRAINING_MONITOR_URL ?? "http://127.0.0.1:8765";

const lossSeries: Series[] = [
  { key: "train_box_loss", label: "训练框损失", color: "#176b47" },
  { key: "train_cls_loss", label: "训练分类损失", color: "#85a832" },
  { key: "val_box_loss", label: "验证框损失", color: "#d47c2f" },
  { key: "val_cls_loss", label: "验证分类损失", color: "#a8443e" },
];

const scoreSeries: Series[] = [
  { key: "map50", label: "mAP50", color: "#176b47" },
  { key: "map50_95", label: "mAP50-95", color: "#86a82f" },
  { key: "precision", label: "精确率", color: "#2d7fb8" },
  { key: "recall", label: "召回率", color: "#cf7b2d" },
];

function formatPercent(value?: number | null) {
  return value == null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function formatNumber(value?: number | null, digits = 3) {
  return value == null ? "—" : value.toFixed(digits);
}

function formatDuration(seconds?: number | null) {
  if (seconds == null || !Number.isFinite(seconds)) return "—";
  const rounded = Math.max(0, Math.round(seconds));
  const hours = Math.floor(rounded / 3600);
  const minutes = Math.floor((rounded % 3600) / 60);
  const rest = rounded % 60;
  if (hours) return `${hours}小时 ${minutes}分`;
  if (minutes) return `${minutes}分 ${rest}秒`;
  return `${rest}秒`;
}

function statusText(status?: RunSummary["status"]) {
  if (status === "running") return "训练中";
  if (status === "completed") return "已完成";
  return "已停止";
}

function MetricChart({
  title,
  subtitle,
  data,
  series,
  fixedRange,
}: {
  title: string;
  subtitle: string;
  data: MetricPoint[];
  series: Series[];
  fixedRange?: [number, number];
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    function draw() {
      if (!canvas) return;
      const width = Math.max(320, canvas.clientWidth);
      const height = 250;
      const ratio = window.devicePixelRatio || 1;
      canvas.width = width * ratio;
      canvas.height = height * ratio;
      const context = canvas.getContext("2d");
      if (!context) return;
      context.scale(ratio, ratio);
      context.clearRect(0, 0, width, height);

      const padding = { left: 46, right: 18, top: 18, bottom: 32 };
      const chartWidth = width - padding.left - padding.right;
      const chartHeight = height - padding.top - padding.bottom;
      const values = data.flatMap((point) =>
        series.map((item) => point[item.key]).filter((value): value is number => typeof value === "number"),
      );
      if (values.length < 2) {
        context.fillStyle = "#7d8c84";
        context.font = "13px Microsoft YaHei, sans-serif";
        context.textAlign = "center";
        context.fillText("等待更多训练轮次生成曲线", width / 2, height / 2);
        return;
      }

      const rawMin = fixedRange?.[0] ?? Math.min(...values);
      const rawMax = fixedRange?.[1] ?? Math.max(...values);
      const margin = fixedRange ? 0 : Math.max((rawMax - rawMin) * 0.12, 0.02);
      const minValue = fixedRange?.[0] ?? Math.max(0, rawMin - margin);
      const maxValue = fixedRange?.[1] ?? rawMax + margin;
      const span = Math.max(maxValue - minValue, 0.0001);

      context.strokeStyle = "#e3e9e5";
      context.fillStyle = "#7d8c84";
      context.lineWidth = 1;
      context.font = "10px Microsoft YaHei, sans-serif";
      context.textAlign = "right";
      for (let index = 0; index <= 4; index += 1) {
        const y = padding.top + (chartHeight * index) / 4;
        context.beginPath();
        context.moveTo(padding.left, y);
        context.lineTo(width - padding.right, y);
        context.stroke();
        const label = maxValue - (span * index) / 4;
        context.fillText(label.toFixed(label >= 10 ? 0 : 2), padding.left - 8, y + 3);
      }

      const pointX = (index: number) =>
        padding.left + (data.length <= 1 ? 0 : (chartWidth * index) / (data.length - 1));
      const pointY = (value: number) => padding.top + chartHeight - ((value - minValue) / span) * chartHeight;

      for (const item of series) {
        context.strokeStyle = item.color;
        context.lineWidth = 2;
        context.lineJoin = "round";
        context.beginPath();
        let started = false;
        data.forEach((point, index) => {
          const value = point[item.key];
          if (typeof value !== "number") return;
          const x = pointX(index);
          const y = pointY(value);
          if (!started) {
            context.moveTo(x, y);
            started = true;
          } else {
            context.lineTo(x, y);
          }
        });
        context.stroke();
      }

      context.fillStyle = "#7d8c84";
      context.textAlign = "left";
      context.fillText(`第 ${Number(data[0]?.epoch ?? 0)} 轮`, padding.left, height - 9);
      context.textAlign = "right";
      context.fillText(`第 ${Number(data.at(-1)?.epoch ?? 0)} 轮`, width - padding.right, height - 9);
    }

    draw();
    window.addEventListener("resize", draw);
    return () => window.removeEventListener("resize", draw);
  }, [data, fixedRange, series]);

  return (
    <article className="monitor-chart-card">
      <div className="monitor-card-heading">
        <div><h2>{title}</h2><p>{subtitle}</p></div>
      </div>
      <canvas className="metric-canvas" ref={canvasRef} aria-label={`${title}折线图`} />
      <div className="chart-legend">
        {series.map((item) => <span key={item.key}><i style={{ background: item.color }} />{item.label}</span>)}
      </div>
    </article>
  );
}

export default function TrainingMonitorPage() {
  const [payload, setPayload] = useState<MonitorPayload | null>(null);
  const [selectedRun, setSelectedRun] = useState("");
  const [connection, setConnection] = useState<"connecting" | "online" | "offline">("connecting");
  const [lastError, setLastError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const query = selectedRun ? `?run=${encodeURIComponent(selectedRun)}` : "";
      const response = await fetch(`${MONITOR_BASE}/api/training/status${query}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`监控服务返回 ${response.status}`);
      const nextPayload = await response.json() as MonitorPayload;
      setPayload(nextPayload);
      setConnection("online");
      setLastError("");
      if (!selectedRun && nextPayload.run) setSelectedRun(nextPayload.run.name);
    } catch (error) {
      setConnection("offline");
      setLastError(error instanceof Error ? error.message : "无法连接监控服务");
    }
  }, [selectedRun]);

  useEffect(() => {
    const initialRefresh = window.setTimeout(() => void refresh(), 0);
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => {
      window.clearTimeout(initialRefresh);
      window.clearInterval(timer);
    };
  }, [refresh]);

  const run = payload?.run;
  const latest = run?.latest;
  const gpu = payload?.gpu;
  const gpuMemoryPercent = gpu?.memory_used_mb && gpu.memory_total_mb
    ? gpu.memory_used_mb / gpu.memory_total_mb * 100
    : null;
  const recentRows = useMemo(() => run?.history.slice(-8).reverse() ?? [], [run?.history]);

  return (
    <main className="monitor-shell">
      <header className="monitor-topbar">
        <Link className="monitor-brand" href="/"><span>田</span><div><strong>田诊协同</strong><small>模型训练控制台</small></div></Link>
        <Link className="back-link" href="/review">进入标注复核</Link>
        <div className={`monitor-connection ${connection}`}><i />{connection === "online" ? "实时数据已连接" : connection === "connecting" ? "正在连接" : "监控连接中断"}</div>
      </header>

      <section className="monitor-hero">
        <div>
          <Link className="back-link" href="/">← 返回诊断系统</Link>
          <p className="eyebrow">训练可观测性 · 每 5 秒刷新 · SSH 私有访问</p>
          <h1>模型训练实时监控</h1>
          <p>集中查看损失收敛、验证指标和 GPU 状态，异常停止或过拟合趋势能够及时发现。</p>
        </div>
        <label className="run-selector">
          <span>当前实验</span>
          <select value={selectedRun} onChange={(event) => setSelectedRun(event.target.value)}>
            {(payload?.runs ?? []).map((item) => <option value={item.name} key={item.name}>{item.name}</option>)}
          </select>
        </label>
      </section>

      {connection === "offline" && (
        <div className="monitor-alert"><strong>暂时无法读取服务器数据。</strong><span>{lastError}。请确认服务器监控服务与 SSH 隧道正在运行。</span></div>
      )}

      <section className="run-overview">
        <article className="run-progress-card">
          <div className="run-title-row">
            <div><span className={`run-status ${run?.status ?? "stopped"}`}><i />{statusText(run?.status)}</span><h2>{run?.name ?? "等待训练任务"}</h2></div>
            <strong>{run ? `${run.current_epoch} / ${run.total_epochs}` : "—"}<small>轮次</small></strong>
          </div>
          <div className="progress-track"><span style={{ width: `${run?.progress_percent ?? 0}%` }} /></div>
          <div className="progress-meta"><span>已完成 {run?.progress_percent?.toFixed(1) ?? "0.0"}%</span><span>已用 {formatDuration(run?.elapsed_seconds)}</span><span>预计剩余 {formatDuration(run?.eta_seconds)}</span></div>
        </article>
        <article className="summary-metric"><span>当前 mAP50</span><strong>{formatPercent(latest?.map50)}</strong><small>最佳 {formatPercent(run?.best_map50)}</small></article>
        <article className="summary-metric"><span>当前 mAP50-95</span><strong>{formatPercent(latest?.map50_95)}</strong><small>最佳 {formatPercent(run?.best_map50_95)}</small></article>
        <article className="summary-metric"><span>学习率</span><strong>{latest?.learning_rate?.toExponential(2) ?? "—"}</strong><small>余弦退火</small></article>
      </section>

      <section className="gpu-grid">
        <article><div><span>GPU 利用率</span><strong>{gpu?.utilization_percent ?? "—"}%</strong></div><div className="mini-track"><i style={{ width: `${gpu?.utilization_percent ?? 0}%` }} /></div></article>
        <article><div><span>显存占用</span><strong>{gpuMemoryPercent == null ? "—" : `${gpuMemoryPercent.toFixed(1)}%`}</strong></div><small>{gpu?.memory_used_mb?.toLocaleString() ?? "—"} / {gpu?.memory_total_mb?.toLocaleString() ?? "—"} MB</small></article>
        <article><div><span>GPU 温度</span><strong>{gpu?.temperature_c ?? "—"}℃</strong></div><small>{(gpu?.temperature_c ?? 0) < 80 ? "温度正常" : "温度偏高，请检查"}</small></article>
        <article><div><span>实时功耗</span><strong>{gpu?.power_w?.toFixed(0) ?? "—"}W</strong></div><small>上限 {gpu?.power_limit_w?.toFixed(0) ?? "—"}W</small></article>
      </section>

      <section className="monitor-charts">
        <MetricChart title="训练与验证误差" subtitle="损失持续下降通常说明模型仍在学习；验证损失反弹需要警惕过拟合。" data={run?.history ?? []} series={lossSeries} />
        <MetricChart title="识别性能" subtitle="同时观察精确率、召回率和两种 mAP，避免只优化单一指标。" data={run?.history ?? []} series={scoreSeries} fixedRange={[0, 1]} />
      </section>

      <section className="epoch-table-card">
        <div className="monitor-card-heading"><div><h2>最近训练轮次</h2><p>每轮完成后自动写入，可用于追踪突变和选择最佳权重。</p></div><span>刷新于 {payload?.generated_at ? new Date(payload.generated_at).toLocaleTimeString("zh-CN") : "—"}</span></div>
        <div className="epoch-table">
          <div className="epoch-row epoch-head"><span>轮次</span><span>训练框损失</span><span>训练分类损失</span><span>验证框损失</span><span>精确率</span><span>召回率</span><span>mAP50</span><span>mAP50-95</span></div>
          {recentRows.map((row) => (
            <div className="epoch-row" key={row.epoch}>
              <span>#{Number(row.epoch ?? 0)}</span><span>{formatNumber(row.train_box_loss)}</span><span>{formatNumber(row.train_cls_loss)}</span><span>{formatNumber(row.val_box_loss)}</span><span>{formatPercent(row.precision)}</span><span>{formatPercent(row.recall)}</span><span>{formatPercent(row.map50)}</span><span>{formatPercent(row.map50_95)}</span>
            </div>
          ))}
          {!recentRows.length && <div className="epoch-empty">训练完成首轮后将在这里显示指标。</div>}
        </div>
      </section>

      <footer className="monitor-footer"><span>田诊协同 · 训练可观测性控制台</span><span>指标用于实验比较，最终成绩以固定测试集评测为准</span></footer>
    </main>
  );
}
