"use client";

/* eslint-disable @next/next/no-img-element -- The review canvas needs the original API image dimensions for exact pointer-to-box coordinates. */

import Link from "next/link";
import { PointerEvent, useCallback, useEffect, useMemo, useState } from "react";

type BBox = [number, number, number, number];

type ReviewBox = {
  class_id: number;
  bbox: BBox;
  confidence: number;
  prelabel_method?: string;
  original_class_id?: number | null;
  source?: string;
};

type QueueItem = {
  image_id: string;
  source_relative_path: string;
  label_relative_path: string;
  review_priority: "P0" | "P1" | "P2";
  target_box_count: number;
  native_box_count: number;
  remapped_box_count: number;
  other_box_count: number;
  minimum_target_confidence?: number | null;
  maximum_target_confidence?: number | null;
  flags: string[];
  review_status: "pending" | "accepted" | "needs_rework" | "skipped";
  reviewed_at?: string | null;
};

type QueuePayload = {
  total: number;
  reviewed: number;
  remaining: number;
  priority_counts: Record<string, number>;
  items: QueueItem[];
  summary: Record<string, unknown>;
};

type ReviewRecord = {
  decision: string;
  boxes: ReviewBox[];
  notes: string;
  reviewed_at: string;
};

type Detail = QueueItem & {
  image_url: string;
  source_size: { width: number; height: number };
  working_size: { width: number; height: number };
  model_sha256: string;
  detections: ReviewBox[];
  target_detections: ReviewBox[];
  review: ReviewRecord | null;
};

type Filter = "all" | "P0" | "P1" | "P2";
type Point = { x: number; y: number };
type DragState =
  | { kind: "draw"; start: Point; current: Point }
  | { kind: "move" | "resize"; index: number; start: Point; initial: BBox; handle?: string };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const PRIORITIES: Filter[] = ["all", "P0", "P1", "P2"];
const ACTIVE_REVIEW_STATUSES = new Set(["pending", "needs_rework"]);
const flagLabels: Record<string, string> = {
  no_target_box: "没有候选框",
  other_class_prediction: "有其他类别预测",
  low_confidence_box: "低置信度",
  remapped_class_box: "类别重映射",
  oversized_box: "过大框",
  overlapping_boxes: "框重叠",
  many_boxes: "目标密集",
};

function apiUrl(path: string) {
  return `${API_BASE}${path}`;
}

function clamp(value: number) {
  return Math.max(0, Math.min(1, value));
}

function boxFromDrag(start: Point, end: Point): BBox {
  const left = Math.min(start.x, end.x);
  const top = Math.min(start.y, end.y);
  return [left, top, Math.abs(end.x - start.x), Math.abs(end.y - start.y)];
}

function confidenceText(value?: number | null) {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

function priorityLabel(priority: Filter) {
  return priority === "all" ? "全部队列" : `${priority} · ${priority === "P0" ? "必须重做" : priority === "P1" ? "重点核验" : "快速确认"}`;
}

export default function ReviewPage() {
  const [queue, setQueue] = useState<QueuePayload | null>(null);
  const [filter, setFilter] = useState<Filter>("P0");
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [boxes, setBoxes] = useState<ReviewBox[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [notes, setNotes] = useState("");
  const [drag, setDrag] = useState<DragState | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const loadQueue = useCallback(async () => {
    const response = await fetch(apiUrl("/api/prelabels/queue"), { cache: "no-store" });
    if (!response.ok) throw new Error("无法读取人工复核队列");
    const payload = (await response.json()) as QueuePayload;
    setQueue(payload);
    return payload;
  }, []);

  const filteredItems = useMemo(() => {
    const items = queue?.items ?? [];
    return items.filter((item) => filter === "all" || item.review_priority === filter);
  }, [filter, queue]);

  const currentPosition = useMemo(
    () => filteredItems.findIndex((item) => item.image_id === currentId),
    [currentId, filteredItems],
  );

  const pendingCount = useMemo(
    () => filteredItems.filter((item) => ACTIVE_REVIEW_STATUSES.has(item.review_status)).length,
    [filteredItems],
  );

  const loadDetail = useCallback(async (imageId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(apiUrl(`/api/prelabels/${imageId}`), { cache: "no-store" });
      if (!response.ok) throw new Error("无法读取图片详情");
      const payload = (await response.json()) as Detail;
      setDetail(payload);
      setBoxes(payload.review ? payload.review.boxes : payload.target_detections);
      setNotes(payload.review?.notes ?? "");
      setSelectedIndex(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "图片读取失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // This effect synchronizes the client queue with the review API.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadQueue().catch((requestError) => {
      setError(requestError instanceof Error ? requestError.message : "队列读取失败");
      setLoading(false);
    });
  }, [loadQueue]);

  useEffect(() => {
    if (!queue) return;
    const current = filteredItems.find((item) => item.image_id === currentId);
    if (!current) {
      const next = filteredItems.find((item) => ACTIVE_REVIEW_STATUSES.has(item.review_status)) ?? filteredItems[0];
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (next) setCurrentId(next.image_id);
    }
  }, [currentId, filteredItems, queue]);

  useEffect(() => {
    // The detail request updates loading/detail state when the selected item changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (currentId) loadDetail(currentId);
  }, [currentId, loadDetail]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Delete" && selectedIndex != null) {
        setBoxes((current) => current.filter((_, index) => index !== selectedIndex));
        setSelectedIndex(null);
      }
      if (event.key === "ArrowRight" && currentPosition >= 0 && currentPosition < filteredItems.length - 1) {
        setCurrentId(filteredItems[currentPosition + 1].image_id);
      }
      if (event.key === "ArrowLeft" && currentPosition > 0) {
        setCurrentId(filteredItems[currentPosition - 1].image_id);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentPosition, filteredItems, selectedIndex]);

  function pointFromEvent(event: PointerEvent<HTMLDivElement>): Point | null {
    const stage = event.currentTarget.closest<HTMLElement>(".review-image-stage");
    const rect = stage?.getBoundingClientRect();
    if (!rect || rect.width === 0 || rect.height === 0) return null;
    return {
      x: clamp((event.clientX - rect.left) / rect.width),
      y: clamp((event.clientY - rect.top) / rect.height),
    };
  }

  function startDrawing(event: PointerEvent<HTMLDivElement>) {
    if (event.button !== 0 || (event.target as HTMLElement).dataset.box === "true") return;
    const point = pointFromEvent(event);
    if (!point) return;
    event.currentTarget.closest<HTMLElement>(".review-image-stage")?.setPointerCapture(event.pointerId);
    setSelectedIndex(null);
    setDrag({ kind: "draw", start: point, current: point });
  }

  function startMove(event: PointerEvent<HTMLDivElement>, index: number) {
    event.stopPropagation();
    const point = pointFromEvent(event);
    if (!point) return;
    event.currentTarget.closest<HTMLElement>(".review-image-stage")?.setPointerCapture(event.pointerId);
    setSelectedIndex(index);
    setDrag({ kind: "move", index, start: point, initial: boxes[index].bbox });
  }

  function startResize(event: PointerEvent<HTMLDivElement>, index: number, handle: string) {
    event.stopPropagation();
    const point = pointFromEvent(event);
    if (!point) return;
    event.currentTarget.closest<HTMLElement>(".review-image-stage")?.setPointerCapture(event.pointerId);
    setSelectedIndex(index);
    setDrag({ kind: "resize", index, handle, start: point, initial: boxes[index].bbox });
  }

  function movePointer(event: PointerEvent<HTMLDivElement>) {
    if (!drag) return;
    const point = pointFromEvent(event);
    if (!point) return;
    if (drag.kind === "draw") {
      setDrag({ ...drag, current: point });
      return;
    }
    const dx = point.x - drag.start.x;
    const dy = point.y - drag.start.y;
    const [x, y, width, height] = drag.initial;
    let next: BBox = [x, y, width, height];
    if (drag.kind === "move") {
      next = [clamp(x + dx), clamp(y + dy), width, height];
      next[0] = Math.min(next[0], 1 - width);
      next[1] = Math.min(next[1], 1 - height);
    } else {
      let left = x;
      let top = y;
      let right = x + width;
      let bottom = y + height;
      if (drag.handle?.includes("w")) left = clamp(point.x);
      if (drag.handle?.includes("e")) right = clamp(point.x);
      if (drag.handle?.includes("n")) top = clamp(point.y);
      if (drag.handle?.includes("s")) bottom = clamp(point.y);
      if (right - left < 0.005) right = Math.min(1, left + 0.005);
      if (bottom - top < 0.005) bottom = Math.min(1, top + 0.005);
      next = [Math.min(left, right - 0.005), Math.min(top, bottom - 0.005), right - left, bottom - top];
    }
    setBoxes((current) => current.map((box, index) => index === drag.index ? { ...box, bbox: next } : box));
  }

  function endPointer(event: PointerEvent<HTMLDivElement>) {
    if (!drag) return;
    const stage = event.currentTarget.closest<HTMLElement>(".review-image-stage");
    if (stage?.hasPointerCapture(event.pointerId)) stage.releasePointerCapture(event.pointerId);
    if (drag.kind === "draw") {
      const bbox = boxFromDrag(drag.start, drag.current);
      if (bbox[2] >= 0.006 && bbox[3] >= 0.006) {
        setBoxes((current) => [
          ...current,
          { class_id: 9, bbox, confidence: 0, prelabel_method: "manual", source: "manual" },
        ]);
      }
    }
    setDrag(null);
  }

  function deleteSelected() {
    if (selectedIndex == null) return;
    setBoxes((current) => current.filter((_, index) => index !== selectedIndex));
    setSelectedIndex(null);
  }

  async function saveReview(decision: "accepted" | "needs_rework" | "skipped") {
    if (!detail || busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(apiUrl(`/api/prelabels/${detail.image_id}/review`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, boxes, notes }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "复核保存失败");
      }
      const nextQueue = await loadQueue();
      setMessage(decision === "accepted" ? "已确认并写入复核标签" : decision === "skipped" ? "已暂存为跳过" : "已保存待返工状态");
      const nextItems = nextQueue.items.filter((item) => (filter === "all" || item.review_priority === filter) && ACTIVE_REVIEW_STATUSES.has(item.review_status));
      const next = nextItems[0] ?? nextQueue.items.find((item) => filter === "all" || item.review_priority === filter);
      if (next) setCurrentId(next.image_id);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "复核保存失败");
    } finally {
      setBusy(false);
    }
  }

  const drawnBox = drag?.kind === "draw" ? boxFromDrag(drag.start, drag.current) : null;

  return (
    <main className="review-shell">
      <header className="review-topbar">
        <Link className="monitor-brand" href="/"><span>田</span><div><strong>田诊协同</strong><small>人工标注复核台</small></div></Link>
        <nav className="review-nav" aria-label="系统导航">
          <Link href="/">智能诊断</Link>
          <Link href="/training">训练监控</Link>
          <span className="review-nav-active">标注复核</span>
        </nav>
        <div className="review-state"><i />{queue ? "复核数据已连接" : "正在读取队列"}</div>
      </header>

      <section className="review-hero">
        <div>
          <Link className="back-link" href="/">← 返回诊断系统</Link>
          <p className="eyebrow">Pest65 · Aphid candidate set · human-in-the-loop</p>
          <h1>蚜虫预标注复核</h1>
          <p>逐张确认、删除、移动或调整候选框；确认后的标签才会进入下一轮训练。</p>
        </div>
        <div className="review-stat-strip">
          <div><strong>{queue?.remaining ?? "—"}</strong><span>待处理</span></div>
          <div><strong>{queue?.reviewed ?? "—"}</strong><span>已复核</span></div>
          <div><strong>{queue?.summary?.target_box_count ?? "—"}</strong><span>自动候选框</span></div>
        </div>
      </section>

      {error && <div className="review-notice error">{error}</div>}
      {message && <div className="review-notice good">{message}</div>}

      <section className="review-layout">
        <aside className="review-queue-panel">
          <div className="review-panel-heading"><div><span className="step-label">QUEUE</span><h2>审核队列</h2></div><button className="icon-button" type="button" onClick={() => loadQueue()} aria-label="刷新队列">↻</button></div>
          <div className="review-filter-row">
            {PRIORITIES.map((item) => <button key={item} type="button" className={filter === item ? "active" : ""} onClick={() => setFilter(item)}>{item === "all" ? "全部" : item}</button>)}
          </div>
          <div className="review-queue-summary">
            <span>{priorityLabel(filter)}</span><strong>{pendingCount} 待处理</strong>
          </div>
          <div className="review-queue-list">
            {filteredItems.map((item) => (
              <button key={item.image_id} type="button" className={`review-queue-item ${currentId === item.image_id ? "active" : ""} ${item.review_status === "accepted" || item.review_status === "skipped" ? "reviewed" : ""} ${item.review_status === "needs_rework" ? "needs-rework" : ""}`} onClick={() => setCurrentId(item.image_id)}>
                <span className={`priority-badge ${item.review_priority.toLowerCase()}`}>{item.review_priority}</span>
                <span className="queue-item-main"><strong>{item.source_relative_path.split("/").pop()}</strong><small>{item.source_relative_path.split("/").slice(0, 2).join(" / ")}</small></span>
                <span className="queue-item-meta">{item.review_status === "pending" ? `${item.target_box_count}框` : item.review_status === "needs_rework" ? "待返工" : "已处理"}</span>
              </button>
            ))}
            {!filteredItems.length && <div className="review-empty">当前筛选没有图片</div>}
          </div>
        </aside>

        <section className="review-canvas-panel">
          {loading && !detail ? <div className="review-loading">正在读取图片与候选框…</div> : detail ? (
            <>
              <div className="review-canvas-heading">
                <div><span className={`priority-badge ${detail.review_priority.toLowerCase()}`}>{detail.review_priority}</span><h2>{detail.source_relative_path}</h2><p>{detail.source_size.width} × {detail.source_size.height} · 模型 {detail.model_sha256.slice(0, 12)}…</p></div>
                <div className="review-nav-buttons"><button type="button" onClick={() => currentPosition > 0 && setCurrentId(filteredItems[currentPosition - 1].image_id)} disabled={currentPosition <= 0}>← 上一张</button><span>{currentPosition + 1} / {filteredItems.length}</span><button type="button" onClick={() => currentPosition < filteredItems.length - 1 && setCurrentId(filteredItems[currentPosition + 1].image_id)} disabled={currentPosition < 0 || currentPosition >= filteredItems.length - 1}>下一张 →</button></div>
              </div>
              <div className="review-canvas-help"><span>拖动空白处绘制新框</span><span>拖动框体移动</span><span>拖动四角调整</span><span>Delete 删除选中框</span></div>
              <div className="review-image-wrap">
                <div className="review-image-stage" style={{ aspectRatio: `${detail.source_size.width} / ${detail.source_size.height}` }} onPointerDown={startDrawing} onPointerMove={movePointer} onPointerUp={endPointer} onPointerCancel={endPointer}>
                  <img src={apiUrl(detail.image_url)} alt="待复核的蚜虫图片" width={detail.source_size.width} height={detail.source_size.height} loading="eager" fetchPriority="high" decoding="async" draggable={false} />
                  {boxes.map((box, index) => {
                    const [left, top, width, height] = box.bbox;
                    const selected = selectedIndex === index;
                    return <div key={`${index}-${box.bbox.join("-")}`} data-box="true" className={`review-box ${selected ? "selected" : ""} ${box.prelabel_method === "folder_label_remap" ? "remapped" : ""}`} style={{ left: `${left * 100}%`, top: `${top * 100}%`, width: `${width * 100}%`, height: `${height * 100}%` }} onPointerDown={(event) => startMove(event, index)}><span>{box.prelabel_method === "folder_label_remap" ? "重映射" : "模型"} · {confidenceText(box.confidence)}</span>{selected && ["nw", "ne", "sw", "se"].map((handle) => <i key={handle} className={`resize-handle ${handle}`} onPointerDown={(event) => startResize(event, index, handle)} />)}</div>;
                  })}
                  {drawnBox && <div className="review-box drawing" style={{ left: `${drawnBox[0] * 100}%`, top: `${drawnBox[1] * 100}%`, width: `${drawnBox[2] * 100}%`, height: `${drawnBox[3] * 100}%` }} />}
                </div>
              </div>
            </>
          ) : <div className="review-loading">请选择一张待复核图片</div>}
        </section>

        <aside className="review-inspector-panel">
          {detail ? <>
            <div className="review-panel-heading"><div><span className="step-label">INSPECTOR</span><h2>框与结论</h2></div><span className="box-count">{boxes.length} 框</span></div>
            <div className="review-flag-list">{detail.flags.length ? detail.flags.map((flag) => <span key={flag} className="review-flag">{flagLabels[flag] ?? flag}</span>) : <span className="review-flag good">暂无风险标记</span>}</div>
            <div className="review-box-list">
              {boxes.map((box, index) => <button type="button" key={`box-row-${index}`} className={`review-box-row ${selectedIndex === index ? "active" : ""}`} onClick={() => setSelectedIndex(index)}><span className="box-number">{String(index + 1).padStart(2, "0")}</span><span><strong>蚜虫</strong><small>{box.prelabel_method === "folder_label_remap" ? `原类别 ${box.original_class_id}` : "模型原生"}</small></span><b>{confidenceText(box.confidence)}</b></button>)}
              {!boxes.length && <div className="review-empty small">暂无框，请在图片上拖动绘制</div>}
            </div>
            <div className="review-edit-actions"><button type="button" onClick={deleteSelected} disabled={selectedIndex == null}>删除选中框</button><button type="button" onClick={() => { setBoxes([]); setSelectedIndex(null); }} disabled={!boxes.length}>清空全部框</button></div>
            <label className="review-notes"><span>复核备注</span><textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="记录漏检、误检、边界调整或图片质量问题…" /></label>
            <div className="review-save-actions"><button className="review-save primary" type="button" onClick={() => saveReview("accepted")} disabled={busy}>{busy ? "保存中…" : boxes.length ? "确认标签并下一张" : "确认无目标并下一张"}</button><button className="review-save secondary" type="button" onClick={() => saveReview("needs_rework")} disabled={busy}>保存待返工</button><button className="review-save ghost" type="button" onClick={() => saveReview("skipped")} disabled={busy}>跳过此张</button></div>
            <div className="review-shortcuts">快捷键：← → 切图 · Delete 删除 · 鼠标拖动调整</div>
          </> : <div className="review-loading">等待复核数据…</div>}
        </aside>
      </section>
      <footer className="monitor-footer review-footer"><span>田诊协同 · 预标注仅供人工复核</span><span>原始图片与自动标签保持独立</span></footer>
    </main>
  );
}
