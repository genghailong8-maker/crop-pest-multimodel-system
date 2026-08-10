"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Detection = {
  class_id: number;
  class_name: string;
  class_name_en: string;
  category_type: string;
  confidence: number;
  bbox: [number, number, number, number];
};

type Quality = {
  width: number;
  height: number;
  brightness: number;
  contrast: number;
  edge_energy: number;
  flags: string[];
  acceptable: boolean;
};

type KnowledgeCard = {
  class_id: number;
  name_zh: string;
  name_en: string;
  crop: string;
  type: string;
  observation_focus: string;
  prevention: string[];
  first_actions: string[];
  source_ids: string[];
  knowledge_scope: string;
};

type Explainability = {
  schema_version: string;
  decision_scope: string;
  primary_class_id: number | null;
  primary_class_name: string | null;
  primary_confidence: number | null;
  primary_confidence_band: "none" | "low" | "medium" | "high";
  model_evidence: {
    mode?: string | null;
    model_sha256?: string | null;
    speed_ms?: { request_model_ms?: number; routing_ms?: number } | null;
    routing?: { mode?: string; candidate_count?: number; selected_candidate_count?: number } | null;
    routing_is_shadow?: boolean;
  };
  knowledge_card: KnowledgeCard | null;
  source_ids: string[];
  human_review: { required: boolean; reasons: string[]; review_endpoint: string };
  safety: { chemical_recommendations: string; requires_local_label_and_agronomist: boolean; boundary_version: string };
};

type DetectorSummary = {
  target_count: number | null;
  inference?: {
    mode?: string;
    model_sha256?: string | null;
    speed_ms?: { request_model_ms?: number; routing_ms?: number };
    routing?: {
      mode?: string;
      candidate_count?: number;
      selected_candidate_count?: number;
      timing_ms?: { total?: number };
    } | null;
  } | null;
  primary_candidate?: {
    class_id: number;
    class_name: string;
    max_confidence: number;
    mean_confidence: number;
    target_count: number;
  } | null;
  candidate_classes?: Array<{
    class_id: number;
    class_name: string;
    max_confidence: number;
    mean_confidence: number;
    target_count: number;
  }>;
  needs_review: boolean;
  review_reasons: string[];
  explainability?: Explainability;
};

type Analysis = {
  status?: string;
  message?: string;
  schema_version?: string;
  primary_diagnosis?: string | null;
  candidate_diagnoses?: string[];
  symptoms?: string[];
  harm_level?: string;
  possible_causes?: string[];
  evidence?: string[];
  uncertainty?: string[];
  detector_alignment?: "agree" | "uncertain" | "conflict";
  needs_human_review?: boolean;
  review_reasons?: string[];
  provenance?: { model?: string; protocol?: string; latency_ms?: number };
};

type CaseRecord = {
  id: string;
  created_at: string;
  crop: string;
  part: string;
  growth_stage: string;
  environment: Record<string, string>;
  notes: string;
  image_filename: string;
  image_url: string;
  status: string;
  quality: Quality | null;
  detections: Detection[] | null;
  detector_summary: DetectorSummary | null;
  analysis: Analysis | null;
  review: ReviewRecord | null;
  review_events?: Array<{ event_id: string; recorded_at: string; decision: string; reviewer_id: string; notes: string }>;
};

type ReviewRecord = {
  decision: "accepted" | "needs_more_evidence" | "rejected";
  final_class_id?: number | null;
  final_diagnosis?: string | null;
  severity?: string;
  accepted_detection_indexes: number[];
  reviewer_notes: string;
  reviewer_id: string;
  reviewed_at: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const statusLabels: Record<string, string> = {
  uploaded: "图片已登记",
  detected: "视觉识别完成",
  analyzed: "综合分析完成",
  reviewed: "人工复核完成",
  review_pending: "等待人工复核",
  model_unavailable: "等待视觉模型",
  multimodal_unavailable: "等待多模态服务",
};

const cropOptions = ["玉米", "番茄", "马铃薯", "南瓜", "葡萄", "芒果", "苜蓿", "豆科作物"];
const partOptions = ["叶片", "茎秆", "果实", "根部", "整株", "田间环境"];
const stageOptions = ["苗期", "营养生长期", "开花期", "结果期", "成熟期", "未知"];

const pipelineLabels = {
  idle: "开始完整分析",
  uploading: "正在上传并登记图片…",
  detecting: "正在完成质量检查与视觉识别…",
  analyzing: "正在进行多模态综合分析…",
  complete: "完整分析已完成",
};

function apiUrl(path: string) {
  return `${API_BASE}${path}`;
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function confidenceText(value: number) {
  return `${Math.round(value * 100)}%`;
}

async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? "请求失败，请稍后重试");
  }
  return payload as T;
}

export default function Home() {
  const [connection, setConnection] = useState<"checking" | "online" | "offline">("checking");
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [activeCase, setActiveCase] = useState<CaseRecord | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [crop, setCrop] = useState("玉米");
  const [part, setPart] = useState("叶片");
  const [growthStage, setGrowthStage] = useState("苗期");
  const [temperature, setTemperature] = useState("");
  const [humidity, setHumidity] = useState("");
  const [environment, setEnvironment] = useState("露地");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [pipelineStage, setPipelineStage] = useState<keyof typeof pipelineLabels>("idle");
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewNotes, setReviewNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refreshCases = useCallback(async () => {
    const response = await fetch(apiUrl("/api/cases?limit=30"));
    const records = await readJson<CaseRecord[]>(response);
    setCases(records);
    return records;
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function connect() {
      try {
        const health = await fetch(apiUrl("/health"));
        if (!health.ok) throw new Error("offline");
        const records = await refreshCases();
        if (!cancelled) {
          setConnection("online");
          if (records.length > 0) setActiveCase(records[0]);
        }
      } catch {
        if (!cancelled) setConnection("offline");
      }
    }
    connect();
    return () => {
      cancelled = true;
    };
  }, [refreshCases]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const activeImageUrl = useMemo(() => {
    if (activeCase) return apiUrl(activeCase.image_url);
    return previewUrl;
  }, [activeCase, previewUrl]);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(selected);
    setPreviewUrl(selected ? URL.createObjectURL(selected) : null);
    setActiveCase(null);
    setReviewNotes("");
    setError(null);
    setPipelineStage("idle");
  }

  async function submitCase(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("请先选择一张作物图片");
      return;
    }
    setBusy(true);
    setPipelineStage("uploading");
    setError(null);
    try {
      const form = new FormData();
      form.append("image", file);
      form.append("crop", crop);
      form.append("part", part);
      form.append("growth_stage", growthStage);
      form.append(
        "environment_json",
        JSON.stringify({ temperature, humidity, scene: environment }),
      );
      form.append("notes", notes);
      const uploadResponse = await fetch(apiUrl("/api/cases"), { method: "POST", body: form });
      const created = await readJson<CaseRecord>(uploadResponse);
      setActiveCase(created);
      setPipelineStage("detecting");
      const detectResponse = await fetch(apiUrl(`/api/cases/${created.id}/detect`), { method: "POST" });
      const detected = await readJson<CaseRecord>(detectResponse);
      setActiveCase(detected);
      if (detected.status === "detected") {
        setPipelineStage("analyzing");
        try {
          const analyzeResponse = await fetch(apiUrl(`/api/cases/${created.id}/analyze`), { method: "POST" });
          const analyzed = await readJson<CaseRecord>(analyzeResponse);
          setActiveCase(analyzed);
          setPipelineStage(analyzed.status === "analyzed" ? "complete" : "idle");
        } catch (analysisError) {
          setPipelineStage("idle");
          setError(`视觉识别已保存；${analysisError instanceof Error ? analysisError.message : "综合分析失败，可单独重试"}`);
        }
      } else {
        setPipelineStage("idle");
      }
      await refreshCases();
    } catch (requestError) {
      setPipelineStage("idle");
      setError(requestError instanceof Error ? requestError.message : "提交失败");
    } finally {
      setBusy(false);
    }
  }

  async function runAnalysis() {
    if (!activeCase) return;
    setAnalysisBusy(true);
    setError(null);
    try {
      const response = await fetch(apiUrl(`/api/cases/${activeCase.id}/analyze`), { method: "POST" });
      const analyzed = await readJson<CaseRecord>(response);
      setActiveCase(analyzed);
      if (analyzed.status === "analyzed") setPipelineStage("complete");
      await refreshCases();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "综合分析失败");
    } finally {
      setAnalysisBusy(false);
    }
  }

  async function openCase(caseId: string) {
    setError(null);
    try {
      const response = await fetch(apiUrl(`/api/cases/${caseId}`));
      setActiveCase(await readJson<CaseRecord>(response));
      setReviewNotes("");
      setFile(null);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      setPipelineStage("idle");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "记录读取失败");
    }
  }

  async function submitReview(decision: "accepted" | "needs_more_evidence") {
    if (!activeCase) return;
    setReviewBusy(true);
    setError(null);
    const primary = summary?.primary_candidate;
    const primaryIndex = primary ? detections.findIndex((item) => item.class_id === primary.class_id) : -1;
    try {
      const response = await fetch(apiUrl(`/api/cases/${activeCase.id}/review`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision,
          final_class_id: primary?.class_id ?? null,
          accepted_detection_indexes: decision === "accepted" && primaryIndex >= 0 ? [primaryIndex] : [],
          reviewer_notes: reviewNotes.trim(),
          reviewer_id: "web-reviewer",
        }),
      });
      const reviewed = await readJson<CaseRecord>(response);
      setActiveCase(reviewed);
      setReviewNotes("");
      await refreshCases();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "人工复核保存失败");
    } finally {
      setReviewBusy(false);
    }
  }

  const detections = activeCase?.detections ?? [];
  const summary = activeCase?.detector_summary;
  const analysis = activeCase?.analysis;
  const analysisReviewReasons = analysis?.review_reasons ?? [];
  const reviewRequired = Boolean(
    summary?.explainability?.human_review.required || analysis?.needs_human_review,
  );
  const combinedReviewReasons = Array.from(new Set([
    ...(summary?.explainability?.human_review.reasons ?? []),
    ...analysisReviewReasons,
  ]));

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark">田</div>
          <div>
            <div className="brand-name">田诊协同</div>
            <div className="brand-subtitle">农作物病虫害识别与防治系统</div>
          </div>
        </div>
        <nav className="topnav" aria-label="主导航">
          <a className="nav-item active" href="#diagnosis">智能诊断</a>
          <a className="nav-item" href="#history">历史记录</a>
          <a className="nav-item" href="#dataset">数据概览</a>
          <a className="nav-item" href="/training">训练监控</a>
          <a className="nav-item" href="/review">标注复核</a>
        </nav>
        <div className={`connection-pill ${connection}`}>
          <span className="status-dot" />
          {connection === "online" ? "本地服务正常" : connection === "checking" ? "正在连接" : "本地服务未启动"}
        </div>
      </header>

      <section className="hero" id="diagnosis">
        <div>
          <p className="eyebrow">多模型协同 · 证据化诊断 · 人工可复核</p>
          <h1>从一张田间图片，建立完整诊断证据链</h1>
          <p className="hero-copy">视觉模型负责定位，多模态模型负责综合研判，知识库与人工复核守住结论边界。</p>
        </div>
        <div className="dataset-strip" id="dataset">
          <div><strong>4,164</strong><span>官方训练图片</span></div>
          <div><strong>5,920</strong><span>标注目标框</span></div>
          <div><strong>16</strong><span>病害与害虫类别</span></div>
        </div>
      </section>

      {connection === "offline" && (
        <div className="notice warning">
          <strong>界面已就绪，正在等待本地分析服务。</strong>
          <span>服务启动后刷新页面即可上传和保存真实记录。</span>
        </div>
      )}
      {error && <div className="notice error">{error}</div>}

      <section className="workspace-grid">
        <form className="panel intake-panel" onSubmit={submitCase}>
          <div className="panel-heading">
            <div>
              <span className="step-label">步骤 01</span>
              <h2>采集诊断信息</h2>
            </div>
            <span className="required-note">信息越完整，综合分析越可靠</span>
          </div>

          <label className={`upload-zone ${previewUrl ? "has-image" : ""}`}>
            <input type="file" accept="image/jpeg,image/png,image/webp" onClick={(event) => { event.currentTarget.value = ""; }} onChange={selectFile} />
            {previewUrl ? (
              <img src={previewUrl} alt="待识别图片预览" />
            ) : (
              <div className="upload-empty">
                <div className="upload-symbol">+</div>
                <strong>上传或拍摄作物图片</strong>
                <span>支持叶片、茎秆、果实、根部及田间环境</span>
                <small>JPG / PNG / WebP，单张不超过 15 MB</small>
              </div>
            )}
            {previewUrl && <span className="replace-chip">重新选择</span>}
          </label>

          <div className="form-grid">
            <label>
              <span>作物种类</span>
              <select value={crop} onChange={(event) => setCrop(event.target.value)}>
                {cropOptions.map((option) => <option key={option}>{option}</option>)}
              </select>
            </label>
            <label>
              <span>拍摄部位</span>
              <select value={part} onChange={(event) => setPart(event.target.value)}>
                {partOptions.map((option) => <option key={option}>{option}</option>)}
              </select>
            </label>
            <label>
              <span>生育阶段</span>
              <select value={growthStage} onChange={(event) => setGrowthStage(event.target.value)}>
                {stageOptions.map((option) => <option key={option}>{option}</option>)}
              </select>
            </label>
            <label>
              <span>种植环境</span>
              <select value={environment} onChange={(event) => setEnvironment(event.target.value)}>
                <option>露地</option><option>温室</option><option>大棚</option><option>室内样本</option><option>未知</option>
              </select>
            </label>
            <label>
              <span>温度（℃）</span>
              <input value={temperature} onChange={(event) => setTemperature(event.target.value)} placeholder="可选" inputMode="decimal" />
            </label>
            <label>
              <span>相对湿度（%）</span>
              <input value={humidity} onChange={(event) => setHumidity(event.target.value)} placeholder="可选" inputMode="decimal" />
            </label>
          </div>
          <label className="notes-field">
            <span>现场补充信息</span>
            <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="例如：近期连续降雨、叶片自下而上出现症状……" />
          </label>
          <button className="primary-button" type="submit" disabled={busy || connection !== "online"}>
            {pipelineLabels[pipelineStage]}
          </button>
          {busy && <div className="pipeline-progress"><span className={pipelineStage === "uploading" ? "active" : "done"}>上传</span><i>→</i><span className={pipelineStage === "detecting" ? "active" : pipelineStage === "analyzing" ? "done" : ""}>检测</span><i>→</i><span className={pipelineStage === "analyzing" ? "active" : ""}>分析</span></div>}
        </form>

        <section className="panel result-panel" aria-live="polite">
          <div className="panel-heading">
            <div>
              <span className="step-label">步骤 02</span>
              <h2>诊断证据工作台</h2>
            </div>
            {activeCase && <span className={`case-status status-${activeCase.status}`}>{statusLabels[activeCase.status] ?? activeCase.status}</span>}
          </div>

          {!activeImageUrl ? (
            <div className="result-empty">
              <div className="empty-orbit"><span>AI</span></div>
              <h3>等待诊断图片</h3>
              <p>提交图片后，这里将展示真实检测框、置信度、质量提示和综合分析依据。</p>
              <div className="pipeline-preview">
                <span>图片质检</span><i>→</i><span>目标定位</span><i>→</i><span>综合研判</span><i>→</i><span>人工复核</span>
              </div>
            </div>
          ) : (
            <div className="result-content">
              <div className="image-stage">
                <div className="annotated-image">
                  <img src={activeImageUrl} alt="作物诊断图片" />
                  {detections.map((detection, index) => {
                    const [left, top, width, height] = detection.bbox;
                    return (
                      <div
                        className="detection-box"
                        key={`${detection.class_id}-${index}`}
                        style={{ left: `${left * 100}%`, top: `${top * 100}%`, width: `${width * 100}%`, height: `${height * 100}%` }}
                      >
                        <span>{detection.class_name} · {confidenceText(detection.confidence)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="evidence-grid">
                <article className="evidence-card">
                  <div className="card-kicker">图像质量</div>
                  {activeCase?.quality ? (
                    <>
                      <strong>{activeCase.quality.acceptable ? "适合进一步识别" : "建议复核拍摄质量"}</strong>
                      <p>{activeCase.quality.width} × {activeCase.quality.height} · 亮度 {Math.round(activeCase.quality.brightness)} · 清晰度 {Math.round(activeCase.quality.edge_energy)}</p>
                      <div className="chip-row">
                        {activeCase.quality.flags.length ? activeCase.quality.flags.map((flag) => <span className="chip warn" key={flag}>{flag}</span>) : <span className="chip good">质量通过</span>}
                      </div>
                    </>
                  ) : <p>提交后自动检查分辨率、亮度、对比度和清晰度。</p>}
                </article>

                <article className="evidence-card">
                  <div className="card-kicker">视觉模型</div>
                  {activeCase?.status === "model_unavailable" ? (
                    <><strong>模型权重待接入</strong><p>{summary?.review_reasons?.[0]}</p></>
                  ) : summary ? (
                    <>
                      <strong>{summary.primary_candidate?.class_name ?? "未发现明确目标"}</strong>
                      <p>{summary.target_count ?? 0} 个定位目标{summary.primary_candidate ? ` · 最高置信度 ${confidenceText(summary.primary_candidate.max_confidence)}` : ""}</p>
                      <div className="chip-row">
                        {(summary.review_reasons ?? []).map((reason) => <span className="chip warn" key={reason}>{reason}</span>)}
                        {summary.inference?.routing ? (
                          <span className="chip good">
                            路由 {summary.inference.routing.mode ?? "unknown"} · 专家候选 {summary.inference.routing.candidate_count ?? 0}
                            {summary.inference.speed_ms?.routing_ms != null ? ` · ${Math.round(summary.inference.speed_ms.routing_ms)} ms` : ""}
                          </span>
                        ) : null}
                      </div>
                    </>
                  ) : <p>模型输出将在此形成候选类别和人工复核触发条件。</p>}
                </article>

                <article className="evidence-card explainability-card">
                  <div className="card-kicker">可信边界</div>
                  {summary?.explainability ? (
                    <>
                      <strong>{summary.explainability.primary_confidence_band === "none" ? "暂无可解释候选" : `置信度 ${summary.explainability.primary_confidence_band}`}</strong>
                      <p>{summary.explainability.knowledge_card?.observation_focus ?? "请补充整株、近景和环境信息后再判断。"}</p>
                      <div className="chip-row">
                        <span className="chip warn">仅作候选线索</span>
                        <span className="chip">不提供药剂剂量</span>
                        {summary.explainability.model_evidence.routing?.mode && <span className="chip good">路由 {summary.explainability.model_evidence.routing.mode}</span>}
                      </div>
                      {summary.explainability.knowledge_card && <ul className="evidence-list">{summary.explainability.knowledge_card.first_actions.slice(0, 2).map((action) => <li key={action}>{action}</li>)}</ul>}
                      <small>依据：{summary.explainability.source_ids.join("、") || "待补充来源"} · {summary.explainability.schema_version}</small>
                    </>
                  ) : <p>识别完成后显示知识卡片、模型路由、来源和安全边界。</p>}
                </article>
              </div>

              <article className="analysis-card">
                <div className="analysis-main">
                  <div className="card-kicker">多模型协同分析</div>
                  <h3>{analysis ? (analysis.primary_diagnosis || "未能确认主诊断") : "等待服务器端多模态分析"}</h3>
                  <p>{analysis?.message ?? "检测结果、原图、作物信息和环境信息将共同提交，输出诊断依据、不确定性及复核建议。"}</p>
                  {analysis?.status === "completed" && (
                    <div className="analysis-detail-grid">
                      <div><strong>候选诊断</strong><span>{analysis.candidate_diagnoses?.join("、") || "无其他候选"}</span></div>
                      <div><strong>危害程度</strong><span>{analysis.harm_level ?? "unknown"}</span></div>
                      <div><strong>视觉一致性</strong><span>{analysis.detector_alignment ?? "uncertain"}</span></div>
                      <div><strong>模型与耗时</strong><span>{analysis.provenance?.model ?? "未记录"}{analysis.provenance?.latency_ms != null ? ` · ${Math.round(analysis.provenance.latency_ms)} ms` : ""}</span></div>
                    </div>
                  )}
                  {analysis?.status === "completed" && <>
                    <strong className="analysis-label">症状</strong><ul className="evidence-list">{analysis.symptoms?.length ? analysis.symptoms.map((item) => <li key={item}>{item}</li>) : <li>未提供可确认症状</li>}</ul>
                    <strong className="analysis-label">可能原因</strong><ul className="evidence-list">{analysis.possible_causes?.length ? analysis.possible_causes.map((item) => <li key={item}>{item}</li>) : <li>未提供可确认原因</li>}</ul>
                    <strong className="analysis-label">诊断证据</strong><ul className="evidence-list">{analysis.evidence?.length ? analysis.evidence.map((item) => <li key={item}>{item}</li>) : <li>当前没有足够证据</li>}</ul>
                    <strong className="analysis-label">不确定性</strong><ul className="evidence-list">{analysis.uncertainty?.length ? analysis.uncertainty.map((item) => <li key={item}>{item}</li>) : <li>未记录额外不确定性</li>}</ul>
                  </>}
                </div>
                <button className="secondary-button" type="button" onClick={runAnalysis} disabled={analysisBusy || busy || !activeCase?.detections}>
                  {analysisBusy ? "正在综合研判…" : activeCase?.status === "analyzed" ? "重新分析" : "仅重试综合分析"}
                </button>
              </article>

              {reviewRequired && activeCase.status !== "reviewed" && (
                <article className="review-action-card">
                  <div>
                    <div className="card-kicker">人工复核闭环</div>
                    <h3>该结果需要人工确认</h3>
                    <p>{combinedReviewReasons.join("；") || "综合分析建议人工确认"}</p>
                    <textarea value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} placeholder="记录补拍要求、现场观察或最终判断依据…" />
                  </div>
                  <div className="review-action-buttons">
                    <button className="secondary-button" type="button" onClick={() => submitReview("needs_more_evidence")} disabled={reviewBusy}>{reviewBusy ? "保存中…" : "请求补充证据"}</button>
                    <button className="primary-button compact" type="button" onClick={() => submitReview("accepted")} disabled={reviewBusy}>{reviewBusy ? "保存中…" : "确认当前候选"}</button>
                  </div>
                </article>
              )}

              {detections.length > 0 && (
                <div className="detection-list">
                  {detections.slice(0, 6).map((detection, index) => (
                    <div key={`${detection.class_id}-row-${index}`}>
                      <span className="target-index">{String(index + 1).padStart(2, "0")}</span>
                      <span><strong>{detection.class_name}</strong><small>{detection.class_name_en}</small></span>
                      <b>{confidenceText(detection.confidence)}</b>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </section>

      <section className="history-section" id="history">
        <div className="section-heading">
          <div><span className="step-label">持续追踪</span><h2>最近识别记录</h2></div>
          <span>{cases.length} 条已保存记录</span>
        </div>
        <div className="history-table">
          <div className="history-head"><span>时间</span><span>作物与部位</span><span>视觉候选</span><span>流程状态</span><span /></div>
          {cases.length === 0 ? (
            <div className="history-empty">尚无识别记录。完成第一次上传后，原图、模型结果和复核状态会保存在这里。</div>
          ) : cases.map((record) => (
            <button className="history-row" key={record.id} onClick={() => openCase(record.id)}>
              <span>{formatTime(record.created_at)}</span>
              <span><strong>{record.crop}</strong><small>{record.part} · {record.growth_stage}</small></span>
              <span>{record.detector_summary?.primary_candidate?.class_name ?? "待确认"}</span>
              <span><i className={`mini-dot status-${record.status}`} />{statusLabels[record.status] ?? record.status}</span>
              <span>查看 →</span>
            </button>
          ))}
        </div>
      </section>

      <footer>
        <span>田诊协同 · 比赛原型系统</span>
        <span>结论保留证据、不确定性与人工复核边界</span>
      </footer>
    </main>
  );
}
