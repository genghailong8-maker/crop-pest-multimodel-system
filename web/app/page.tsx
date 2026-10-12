"use client";

/* eslint-disable @next/next/no-img-element -- Diagnostic previews and no-store case images are not static assets handled by Vinext's image endpoint. */

import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import WorkspaceShell from "./components/WorkspaceShell";
import ExternalEvidenceSummary from "./components/ExternalEvidenceSummary";
import CaseContextCard from "./components/CaseContextCard";
import SeveritySelector from "./components/SeveritySelector";
import R31HostKnowledgePanel from "./components/R31HostKnowledgePanel";
import R3ContextConfirmation from "./components/R3ContextConfirmation";
import CoreKnowledgeSummary from "./components/CoreKnowledgeSummary";
import {
  apiUrl,
  analyzeCase,
  CaseRecord,
  CoreKnowledge,
  DraftRecord,
  draftHeaders,
  editHeaders,
  formatTime,
  HealthStatus,
  instanceHeaders,
  isInsectCase,
  publicResolutionReasons,
  readJson,
  R3Taxonomy,
  saveEditToken,
  saveDraftToken,
  SeverityLevel,
  userDiagnosisTitle,
} from "./lib/api";

const stageText = {
  idle: "开始分析",
  uploading: "正在保存图片…",
  detecting: "正在寻找病斑或害虫…",
  analyzing: "正在综合分析…",
  confirming: "正在保存确认…",
  complete: "分析完成",
};

type PipelineStage = keyof typeof stageText;
type TargetMode = "plant_disease" | "insect_pest";

export default function Home() {
  const searchParams = useSearchParams();
  const libraryInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const requestedCaseId = searchParams.get("case");
  const [service, setService] = useState<"checking" | "online" | "offline">("checking");
  const [publicMode, setPublicMode] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [history, setHistory] = useState<CaseRecord[]>([]);
  const [record, setRecord] = useState<CaseRecord | null>(null);
  const [coreKnowledgeState, setCoreKnowledgeState] = useState<{ caseId: string; value: CoreKnowledge } | null>(null);
  const coreKnowledge = record && coreKnowledgeState?.caseId === record.id ? coreKnowledgeState.value : null;
  const [draft, setDraft] = useState<DraftRecord | null>(null);
  const [taxonomy, setTaxonomy] = useState<R3Taxonomy | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [targetMode, setTargetMode] = useState<TargetMode | null>(null);
  const [contextSubject, setContextSubject] = useState<"plant" | "insect">("plant");
  const [contextCrop, setContextCrop] = useState("");
  const [contextPart, setContextPart] = useState("");
  const [contextInsect, setContextInsect] = useState("");
  const [consent, setConsent] = useState(false);
  const [pipeline, setPipeline] = useState<PipelineStage>("idle");
  const [busy, setBusy] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshHistory = useCallback(async () => {
    const items = await readJson<CaseRecord[]>(await fetch(apiUrl("/api/cases?limit=6")));
    setHistory(items);
    return items;
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetch(apiUrl("/health")).then((response) => readJson<HealthStatus>(response)),
      fetch(apiUrl("/api/cases?limit=6")).then(readJson<CaseRecord[]>),
      fetch(apiUrl("/api/r3/taxonomy")).then(readJson<R3Taxonomy>),
    ]).then(([nextHealth, items, nextTaxonomy]) => {
      if (!active) return;
      setPublicMode(Boolean(nextHealth.public_mode));
      setHealth(nextHealth);
      setHistory(items);
      setTaxonomy(nextTaxonomy);
      setService(nextHealth.model_configured ? "online" : "offline");
    }).catch(() => active && setService("offline"));
    return () => { active = false; };
  }, []);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  useEffect(() => {
    if (!record || record.resolution_status !== "conclusive") return;
    let active = true;
    fetch(apiUrl(`/api/cases/${record.id}/report`))
      .then(readJson<{ core_knowledge?: CoreKnowledge }>)
      .then((report) => active && setCoreKnowledgeState({ caseId: record.id, value: report.core_knowledge ?? null }))
      .catch(() => active && setCoreKnowledgeState({ caseId: record.id, value: null }));
    return () => { active = false; };
  }, [record]);

  useEffect(() => {
    if (!requestedCaseId) return;
    let active = true;
    fetch(apiUrl(`/api/cases/${requestedCaseId}`)).then(readJson<CaseRecord>).then((existing) => {
      if (!active) return;
      setRecord(existing);
      setPipeline("complete");
      setError(null);
    }).catch(() => active && setError("当前识别服务器暂时无法读取这份病例。"));
    return () => { active = false; };
  }, [requestedCaseId]);

  const imageUrl = useMemo(() => record ? apiUrl(record.image_url) : draft ? apiUrl(draft.image_url) : preview, [draft, record, preview]);
  const detections = record?.detections ?? [];
  const analysis = record?.analysis;
  const diagnosis = userDiagnosisTitle(record);
  const visibleResolutionReasons = publicResolutionReasons(record?.resolution_reasons);
  const missingItems = useMemo(() => {
    const items: string[] = [];
    if (!targetMode) items.push("识别模式");
    if (!file) items.push("上传图片");
    if (publicMode && !consent) items.push("公共展示说明");
    return items;
  }, [consent, file, publicMode, targetMode]);
  const formReady = missingItems.length === 0;

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    if (preview) URL.revokeObjectURL(preview);
    setFile(selected);
    setPreview(selected ? URL.createObjectURL(selected) : null);
    setRecord(null);
    setDraft(null);
    setContextSubject("plant"); setContextCrop(""); setContextPart(""); setContextInsect("");
    setPipeline("idle");
    setError(null);
  }

  function openImagePicker(input: HTMLInputElement | null) {
    if (!input || busy) return;
    input.value = "";
    input.click();
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!targetMode) return setError("请先选择植物病害或昆虫虫害识别模式");
    if (!file) return setError("请先拍摄或选择一张图片");
    if (publicMode && !consent) return setError("公网上传前，请先确认 30 天公共展示说明");
    setBusy(true);
    setError(null);
    try {
      setPipeline("uploading");
      const form = new FormData(); form.append("image", file); form.append("target_mode", targetMode); form.append("public_consent", String(consent));
      const created = await readJson<DraftRecord>(await fetch(apiUrl("/api/drafts"), { method: "POST", body: form }));
      saveDraftToken(created.id, created.draft_edit_token);
      setPipeline("detecting");
      const analyzed = await readJson<DraftRecord>(await fetch(apiUrl(`/api/drafts/${created.id}/analyze`), { method: "POST", headers: draftHeaders(created.id) }));
      setDraft(analyzed);
      if (analyzed.status === "low_confidence") {
        setPipeline("idle");
        setError(analyzed.confidence_gate?.message ?? "无法可靠判断，请重新上传图片。");
        return;
      }
      const prediction = analyzed.context_prediction;
      const subject = targetMode === "insect_pest" ? "insect" : "plant";
      setContextSubject(subject);
      if (subject === "plant") {
        setContextCrop(prediction?.crop_species?.top1 ?? "");
        setContextPart(prediction?.affected_part?.top1 ?? "");
      } else setContextInsect(prediction?.insect_species?.top1 ?? "");
      setPipeline("confirming");
    } catch (reason) {
      setPipeline("idle");
      setError(reason instanceof Error ? reason.message : "提交失败，请稍后再试");
    } finally {
      setBusy(false);
    }
  }

  async function confirmContext() {
    if (!draft) return;
    setBusy(true); setError(null); setPipeline("confirming");
    try {
      const confirmed = await readJson<CaseRecord>(await fetch(apiUrl(`/api/drafts/${draft.id}/confirm`), {
        method: "POST", headers: draftHeaders(draft.id, true),
        body: JSON.stringify({ subject_type: contextSubject, crop_species: contextSubject === "plant" ? contextCrop : null, affected_part: contextSubject === "plant" ? contextPart : null, insect_species: contextSubject === "insect" ? contextInsect : null }),
      }));
      saveEditToken(confirmed.id, confirmed.case_edit_token);
      const evidenceRequest = contextSubject === "insect" ? analyzeCase(confirmed) : null;
      setRecord(confirmed); setDraft(null); setPipeline("complete"); await refreshHistory();
      if (evidenceRequest) {
        void evidenceRequest.then((nextRecord) => {
          setRecord((current) => current && current.id === nextRecord.id
            ? { ...nextRecord, host_knowledge: current.host_knowledge ?? nextRecord.host_knowledge }
            : nextRecord);
          void refreshHistory();
        }).catch((reason) => setError(reason instanceof Error ? reason.message : "来源证据整理失败"));
      }
    } catch (reason) { setPipeline("confirming"); setError(reason instanceof Error ? reason.message : "上下文确认失败"); }
    finally { setBusy(false); }
  }

  async function chooseSeverity(severityLevel: SeverityLevel) {
    if (!record) return setError("当前病例尚未读取");
    setBusy(true); setError(null);
    try {
      const selected = await readJson<CaseRecord>(await fetch(apiUrl(`/api/cases/${record.id}/severity`), {
        method: "POST", headers: { ...editHeaders(record.id, true), ...instanceHeaders(record) }, body: JSON.stringify({ severity_level: severityLevel }),
      }));
      const nextRecord = !isInsectCase(record) || !selected.analysis?.evidence_analysis
        ? await analyzeCase(selected)
        : selected;
      setRecord(nextRecord); setPipeline("complete"); await refreshHistory();
    } catch (reason) { setPipeline("idle"); setError(reason instanceof Error ? reason.message : "受害程度保存失败"); }
    finally { setBusy(false); }
  }

  async function retryAnalysis() {
    if (!record) return;
    setRetrying(true);
    setError(null);
    try {
      const analyzed = await analyzeCase(record);
      setRecord(analyzed);
      setPipeline("complete");
      await refreshHistory();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "综合分析重试失败");
    } finally {
      setRetrying(false);
    }
  }

  return (
    <WorkspaceShell service={service} health={health} visualMode="legacy">
      <main className="legacy-public-shell final-public-shell">
        {!requestedCaseId && <><section className="final-home-hero">
          <h1>识别病虫害，先看清风险</h1>
          <p>上传田间图片，获得可追溯的辅助诊断。</p>
          <p className="final-visually-hidden">系统先定位可疑病斑或害虫，并按视觉置信度说明结果是否适合参考。</p>
          <p className="final-visually-hidden">第一步：拍照并告诉我们田里的情况。第二步：查看识别结果，并根据当前样本可见症状选择受害程度。</p>
        </section>

        {service === "offline" && <div className="final-system-state final-system-state-warning"><strong>识别服务暂不可用</strong><span>服务恢复后即可继续上传并分析。</span></div>}
        {error && <div className="final-system-state final-system-state-error" role="alert">{error}</div>}

        <form className="final-diagnosis-entry" onSubmit={submit}>
          <div className="final-upload-column">
            <div className={`final-upload-frame ${preview ? "selected" : ""}`} aria-live="polite">
              {preview ? <img src={preview} alt="待分析图片预览" loading="eager" decoding="async" /> : <div className="final-upload-empty"><span aria-hidden="true" /><strong>请选择图片来源</strong><small>尽量拍清病斑、叶背、整株和周边植株</small></div>}
              {preview && <div className="final-upload-overlay"><b>已选择田间图片</b><span>可重新选择或拍摄</span></div>}
            </div>
            <input ref={libraryInputRef} className="final-file-input" type="file" accept="image/jpeg,image/png,image/webp" aria-hidden="true" tabIndex={-1} onChange={chooseFile} />
            <input ref={cameraInputRef} className="final-file-input" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" aria-hidden="true" tabIndex={-1} onChange={chooseFile} />
            <div className="final-upload-actions" aria-label="选择图片来源">
              <button type="button" className="final-upload-choice" onClick={() => openImagePicker(libraryInputRef.current)} disabled={busy}>
                <strong>本地图库上传</strong><span>选择设备中已有的图片</span>
              </button>
              <button type="button" className="final-upload-choice final-upload-choice-camera" onClick={() => openImagePicker(cameraInputRef.current)} disabled={busy}>
                <strong>拍照上传</strong><span>使用相机拍摄田间图片</span>
              </button>
            </div>
          </div>
          <section className="final-form-panel" aria-labelledby="start-diagnosis-title">
            <h2 id="start-diagnosis-title">开始诊断</h2>
            <fieldset className="final-mode-selector" disabled={busy}>
              <legend>请选择识别模式</legend>
              <div className="final-mode-options">
                <label className={`final-mode-option ${targetMode === "plant_disease" ? "selected" : ""}`}>
                  <input type="radio" name="target_mode" value="plant_disease" checked={targetMode === "plant_disease"} onChange={() => setTargetMode("plant_disease")} />
                  <span><strong>植物病害</strong><small>水稻、玉米病害识别</small></span>
                </label>
                <label className={`final-mode-option ${targetMode === "insect_pest" ? "selected" : ""}`}>
                  <input type="radio" name="target_mode" value="insect_pest" checked={targetMode === "insect_pest"} onChange={() => setTargetMode("insect_pest")} />
                  <span><strong>昆虫虫害</strong><small>五类正式害虫识别</small></span>
                </label>
              </div>
            </fieldset>
            <div className="final-form-grid">
              <p className="final-form-help">上传后将按你选择的模式调用对应识别专家，AI视觉模型提供作物、部位或昆虫种类建议，由你确认或修改。</p>
            </div>
            {publicMode && <label className="public-consent final-consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span>我同意图片、田间备注和诊断报告在公共历史中展示 30 天。请勿上传人脸、车牌或其他个人信息。</span></label>}
            <div className={`final-form-status ${formReady ? "ready" : ""}`} role="status" aria-live="polite" aria-atomic="true">{!formReady ? `还需完成：${missingItems.join("、")}` : service !== "online" ? "识别服务暂不可用，请稍后再试" : "信息完整，可以开始分析"}</div>
            <button className="final-primary" disabled={busy || service !== "online" || !formReady}>{stageText[pipeline]}</button>
            {busy && <div className="final-progress"><span className={pipeline === "uploading" ? "active" : "done"}>保存</span><i /><span className={pipeline === "detecting" ? "active" : pipeline === "analyzing" ? "done" : ""}>定位</span><i /><span className={pipeline === "analyzing" ? "active" : ""}>综合分析</span></div>}
            {record && <div className="final-case-created" aria-live={busy ? "polite" : "off"} aria-atomic="true"><strong>病例编号：{record.id}</strong><span>你可以离开当前页面，稍后从 <Link href="/history">病例历史</Link> 查看结果。</span></div>}
          </section>
        </form></>}

        {requestedCaseId && !record ? <p className="final-loading-case">正在读取诊断结果…</p> : draft && !record ? <section className="final-result-screen r3-draft-screen" aria-live="polite">
          <h2>确认图片上下文</h2>
          <div className="final-result-grid">
            <div className="final-result-image"><p>待确认图片</p><div className="public-annotated"><img src={imageUrl ?? ""} alt="待确认图片" loading="eager" decoding="async" />{(draft.detections ?? []).map((item, index) => { const [left, top, width, height] = item.bbox; return <span className="public-box" key={`${item.class_id}-${index}`} style={{ left: `${left * 100}%`, top: `${top * 100}%`, width: `${width * 100}%`, height: `${height * 100}%` }}><b>{item.class_name} {Math.round(item.confidence * 100)}%</b></span>; })}</div></div>
          <div className="final-result-summary">{draft.status === "model_unavailable" && <div className="final-system-state final-system-state-warning"><strong>识别服务暂不可用</strong><span>请稍后重试图片识别。</span></div>}{draft.status === "low_confidence" && <div className="final-system-state final-system-state-warning" role="status"><strong>无法可靠判断</strong><span>{draft.confidence_gate?.message ?? "最高视觉置信度低于 50%，请重新上传图片。"}</span></div>}{draft.status !== "low_confidence" && taxonomy && <R3ContextConfirmation draft={draft} taxonomy={taxonomy} subjectType={contextSubject} cropSpecies={contextCrop} affectedPart={contextPart} insectSpecies={contextInsect} busy={busy} onCropSpecies={setContextCrop} onAffectedPart={setContextPart} onInsectSpecies={setContextInsect} onConfirm={confirmContext} />}</div>
          </div>
        </section> : !imageUrl ? <section className="final-result-preview" aria-label="结果预览"><span>结果预览</span><p>识别结果 · 风险判断 · 防治建议</p></section> : <section className="final-result-screen" aria-live="polite">
          <h2>诊断结果</h2>
          <div className="final-result-grid final-result-primary-grid">
            <div className="final-result-image"><p>检测图片</p><div className="public-annotated"><img src={imageUrl} alt="本次诊断图片" loading="eager" decoding="async" />{detections.map((item, index) => { const [left, top, width, height] = item.bbox; return <span className="public-box" key={`${item.class_id}-${index}`} style={{ left: `${left * 100}%`, top: `${top * 100}%`, width: `${width * 100}%`, height: `${height * 100}%` }}><b>{item.class_name} {Math.round(item.confidence * 100)}%</b></span>; })}</div><span className="final-recognition-complete">识别完成</span></div>
            <div className="final-result-summary">
              <span className="final-assist-label">辅助诊断</span>
              <div className="final-diagnosis-heading"><h3>{diagnosis}</h3><p><strong>{Math.round((record?.detections?.[0]?.confidence ?? 0) * 100)}%</strong><span>置信度</span></p></div>
              {record && <div className={`final-resolution resolution-${record.resolution_status}`} role="status"><strong>{record.user_summary}</strong><span>{record.next_action}</span>{visibleResolutionReasons.length > 0 && <small>原因：{visibleResolutionReasons.join("；")}</small>}</div>}
              {record && <CaseContextCard record={record} compact />}
            </div>
          </div>
          <div className="final-result-followup">
            {record && <R31HostKnowledgePanel record={record} busy={busy} onRecord={(next) => { setRecord(next); setPipeline("complete"); void refreshHistory(); }} onSeverity={chooseSeverity} />}
            {record && !isInsectCase(record) && record.severity_rubric?.status === "available" && <SeveritySelector record={record} busy={busy} onConfirm={chooseSeverity} />}
            {record && <ExternalEvidenceSummary record={record} showTreatment={!record.host_knowledge?.available} />}
            <p className="final-visually-hidden">这个结果有多可靠？{analysis?.detector_alignment === "conflict" ? "两种识别方法给出的候选不一致" : "由图片质量、识别把握和两种方法是否一致共同决定"}</p>
            {record?.status === "detected" && !analysis && <button className="final-secondary" type="button" onClick={retryAnalysis} disabled={retrying}>{retrying ? "正在重试…" : "整理来源证据"}</button>}
            {record && <div className="final-result-links"><Link href={`/cases/${record.id}`}>查看病例详情</Link><Link href={`/reports/${record.id}`}>打开诊断报告</Link></div>}
          </div>
          {record && <CoreKnowledgeSummary knowledge={coreKnowledge} />}
        </section>}

        <details className="final-history-preview"><summary>最近诊断记录</summary><div>{history.length ? history.map((item) => <Link href={`/cases/${item.id}`} key={item.id}><span>{formatTime(item.created_at)}</span><strong>{userDiagnosisTitle(item)}</strong><small>{isInsectCase(item) ? item.host_knowledge?.confirmed_host && item.host_knowledge.confirmed_host !== "OTHER" ? item.host_knowledge.confirmed_host : "不适用" : item.crop && item.crop !== "不适用" ? item.crop : "不适用"}</small></Link>) : <p>当前识别服务器暂时没有诊断记录。</p>}</div><Link href="/history">查看全部病例历史</Link></details>
      </main>
    </WorkspaceShell>
  );
}
