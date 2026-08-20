"use client";

/* eslint-disable @next/next/no-img-element -- Diagnostic previews and no-store case images are not static assets handled by Vinext's image endpoint. */

import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import WorkspaceShell from "./components/WorkspaceShell";
import {
  apiUrl,
  CaseRecord,
  editHeaders,
  formatTime,
  HealthStatus,
  instanceHeaders,
  isConclusive,
  publicResolutionReasons,
  readJson,
  riskLabel,
  saveEditToken,
  severityLabel,
  userDiagnosisTitle,
} from "./lib/api";

const cropOptions = ["玉米", "番茄", "南瓜", "马铃薯", "昆虫"] as const;
const partOptions = ["叶片", "茎秆", "果实", "根部", "整株"] as const;
const growthStageOptions = ["苗期", "营养生长期", "开花期", "结果期", "成熟期"] as const;
const sceneOptions = ["露地", "温室", "大棚", "室内样本", "未知"] as const;
const spreadOptions = [
  ["unknown", "不清楚"], ["none", "暂未扩散"], ["slow", "缓慢"], ["moderate", "中等"], ["rapid", "快速"],
] as const;
const stageText = {
  idle: "开始分析",
  uploading: "正在保存图片…",
  detecting: "正在寻找病斑或害虫…",
  analyzing: "正在综合分析…",
  complete: "分析完成",
};

type PipelineStage = keyof typeof stageText;

export default function Home() {
  const [service, setService] = useState<"checking" | "online" | "offline">("checking");
  const [publicMode, setPublicMode] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [history, setHistory] = useState<CaseRecord[]>([]);
  const [record, setRecord] = useState<CaseRecord | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [crop, setCrop] = useState("");
  const [part, setPart] = useState("");
  const [growthStage, setGrowthStage] = useState("");
  const [scene, setScene] = useState("");
  const [affectedRatio, setAffectedRatio] = useState("");
  const [spreadSpeed, setSpreadSpeed] = useState("");
  const [notes, setNotes] = useState("");
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
    ]).then(([nextHealth, items]) => {
      if (!active) return;
      setPublicMode(Boolean(nextHealth.public_mode));
      setHealth(nextHealth);
      setHistory(items);
      setService(nextHealth.model_configured && nextHealth.multimodal_configured ? "online" : "offline");
    }).catch(() => active && setService("offline"));
    return () => { active = false; };
  }, []);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const imageUrl = useMemo(() => record ? apiUrl(record.image_url) : preview, [record, preview]);
  const detections = record?.detections ?? [];
  const summary = record?.detector_summary;
  const analysis = record?.analysis;
  const diagnosis = userDiagnosisTitle(record);
  const conclusive = isConclusive(record);
  const isInsect = crop === "昆虫";
  const activeMode = health?.active_instance_mode;
  const visibleResolutionReasons = publicResolutionReasons(record?.resolution_reasons);
  const nextActions = summary?.explainability?.knowledge_card?.first_actions ?? ["补拍清晰的近景、叶背和整株照片", "记录受害比例与扩散速度后再判断"];
  const missingItems = useMemo(() => {
    const items: string[] = [];
    if (!file) items.push("上传图片");
    if (!crop) items.push("作物 / 识别对象");
    if (!scene) items.push("种植环境");
    if (crop && !isInsect && !part) items.push("植物部位");
    if (crop && !isInsect && !growthStage) items.push("生长阶段");
    if (affectedRatio === "") items.push("受害比例");
    if (!spreadSpeed) items.push("扩散速度");
    if (publicMode && !consent) items.push("公共展示说明");
    return items;
  }, [affectedRatio, consent, crop, file, growthStage, isInsect, part, publicMode, scene, spreadSpeed]);
  const formReady = missingItems.length === 0;

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    if (preview) URL.revokeObjectURL(preview);
    setFile(selected);
    setPreview(selected ? URL.createObjectURL(selected) : null);
    setRecord(null);
    setPipeline("idle");
    setError(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return setError("请先拍摄或选择一张图片");
    if (!crop || !scene || affectedRatio === "" || !spreadSpeed || (!isInsect && (!part || !growthStage))) return setError("请完成所有必填的田间信息");
    if (publicMode && !consent) return setError("公网上传前，请先确认 30 天公共展示说明");
    setBusy(true);
    setError(null);
    try {
      setPipeline("uploading");
      const form = new FormData();
      form.append("image", file);
      form.append("crop", crop);
      if (!isInsect) {
        form.append("part", part);
        form.append("growth_stage", growthStage);
      }
      form.append("environment_json", JSON.stringify({ scene }));
      form.append("affected_ratio_percent", affectedRatio);
      form.append("spread_speed", spreadSpeed);
      form.append("notes", notes);
      form.append("public_consent", String(consent));
      const created = await readJson<CaseRecord>(await fetch(apiUrl("/api/cases"), { method: "POST", body: form }));
      saveEditToken(created.id, created.case_edit_token);
      setRecord(created);

      setPipeline("detecting");
      const detected = await readJson<CaseRecord>(await fetch(apiUrl(`/api/cases/${created.id}/detect`), {
        method: "POST",
        headers: { ...editHeaders(created.id), ...instanceHeaders(created) },
      }));
      setRecord(detected);
      if (detected.status !== "detected") {
        setPipeline("idle");
        await refreshHistory();
        return;
      }

      setPipeline("analyzing");
      try {
        const analyzed = await readJson<CaseRecord>(await fetch(apiUrl(`/api/cases/${created.id}/analyze`), {
          method: "POST",
          headers: { ...editHeaders(created.id), ...instanceHeaders(created) },
        }));
        setRecord(analyzed);
        setPipeline("complete");
      } catch (reason) {
        setPipeline("idle");
        setError(`图片和检测结果已保存。${reason instanceof Error ? reason.message : "综合分析暂时失败"}`);
      }
      await refreshHistory();
    } catch (reason) {
      setPipeline("idle");
      setError(reason instanceof Error ? reason.message : "提交失败，请稍后再试");
    } finally {
      setBusy(false);
    }
  }

  async function retryAnalysis() {
    if (!record) return;
    setRetrying(true);
    setError(null);
    try {
      const analyzed = await readJson<CaseRecord>(await fetch(apiUrl(`/api/cases/${record.id}/analyze`), {
        method: "POST",
        headers: { ...editHeaders(record.id), ...instanceHeaders(record) },
      }));
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
      <main className="legacy-public-shell">
        <section className="public-hero">
          <div>
            <p className="public-eyebrow">拍一张田间照片，先看清风险再行动</p>
            <h1>发现了什么，风险多大，下一步怎么做</h1>
            <p>系统会先定位可疑病斑或害虫，再用第二种方法核对图片。证据足够时给出参考结果，不足时会说明原因并告诉你怎样补拍。</p>
          </div>
          <ol className="public-steps" aria-label="诊断步骤">
            <li><b>1</b><span>拍照或选图</span></li><li><b>2</b><span>填写田间情况</span></li><li><b>3</b><span>查看风险与建议</span></li>
          </ol>
        </section>

        {service === "offline" && <div className="public-alert warning"><strong>识别服务暂时未开放</strong><span>当前识别服务器可能处于关机或模型维护状态。页面不会生成虚假结果，请稍后再试。</span></div>}
        {error && <div className="public-alert error" role="alert">{error}</div>}

        <section className="public-workspace">
          <form className="public-card public-intake" onSubmit={submit}>
            <div className="public-section-title"><span>第一步</span><h2>拍照并告诉我们田里的情况</h2><p>不知道的内容可以选择“不清楚”，系统不会凭空猜测。</p></div>
            <label className={`public-upload ${preview ? "selected" : ""}`}>
              <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onClick={(event) => { event.currentTarget.value = ""; }} onChange={chooseFile} />
              {preview ? <img src={preview} alt="待分析图片预览" loading="eager" decoding="async" /> : <div><b aria-hidden="true">＋</b><strong>拍照或选择图片</strong><span>尽量同时拍清病斑、叶背、整株和周边植株</span><small>JPG / PNG / WebP，最大 15 MB</small></div>}
            </label>
            <div className="public-form-grid">
              <label><span>作物 / 识别对象</span><select required value={crop} onChange={(event) => { setCrop(event.target.value); setPart(""); setGrowthStage(""); }}><option value="" disabled>请选择</option>{cropOptions.map((item) => <option key={item}>{item}</option>)}</select></label>
              <label><span>种植环境</span><select required value={scene} onChange={(event) => setScene(event.target.value)}><option value="" disabled>请选择</option>{sceneOptions.map((item) => <option key={item}>{item}</option>)}</select></label>
              {crop && !isInsect && <>
                <label><span>植物部位</span><select required value={part} onChange={(event) => setPart(event.target.value)}><option value="" disabled>请选择</option>{partOptions.map((item) => <option key={item}>{item}</option>)}</select></label>
                <label><span>生长阶段</span><select required value={growthStage} onChange={(event) => setGrowthStage(event.target.value)}><option value="" disabled>请选择</option>{growthStageOptions.map((item) => <option key={item}>{item}</option>)}</select></label>
              </>}
              <label><span>大约有多少叶片或植株受影响？（%）</span><input required type="number" min="0" max="100" step="0.1" inputMode="decimal" value={affectedRatio} onChange={(event) => setAffectedRatio(event.target.value)} placeholder="例如 12.5" /></label>
              <label><span>问题扩散得快吗？</span><select required value={spreadSpeed} onChange={(event) => setSpreadSpeed(event.target.value)}><option value="" disabled>请选择</option>{spreadOptions.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
            </div>
            <label className="public-notes"><span>补充说明（可选）</span><textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="例如：连续降雨后出现，先从下部叶片开始……" /></label>
            {publicMode && <label className="public-consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span>我同意图片、田间备注和诊断报告在公共历史中展示 30 天。请勿上传人脸、车牌或其他个人信息。</span></label>}
            <div className={`public-form-status ${formReady ? "ready" : ""}`} role="status" aria-live="polite" aria-atomic="true">{!formReady ? `还需完成：${missingItems.join("、")}` : service !== "online" ? "识别服务暂不可用，请稍后再试" : "信息完整，可以开始分析"}</div>
            {activeMode === "cpu" && <p className="legacy-runtime-note">使用实验室 CPU 时，综合分析通常需要约 1–2 分钟；提交后可离开页面，稍后从病例历史查看结果。</p>}
            <button className="public-primary" disabled={busy || service !== "online" || !formReady}>{stageText[pipeline]}</button>
            {busy && <div className="public-progress"><span className={pipeline === "uploading" ? "active" : "done"}>保存</span><i /><span className={pipeline === "detecting" ? "active" : pipeline === "analyzing" ? "done" : ""}>定位</span><i /><span className={pipeline === "analyzing" ? "active" : ""}>综合分析</span></div>}
            {record && <div className="public-case-created" aria-live={busy ? "polite" : "off"} aria-atomic="true"><strong>病例编号：{record.id}</strong><span>你可以离开当前页面，稍后从 <Link href="/history">病例历史</Link> 查看结果。</span></div>}
          </form>

          <section className="public-card public-result" aria-live="polite">
            <div className="public-section-title"><span>第二步</span><h2>查看结果与下一步</h2><p>绿色不是“确诊”，风险和不确定性必须一起看。</p></div>
            {!imageUrl ? <div className="public-empty"><div aria-hidden="true">叶</div><h3>结果会显示在这里</h3><p>先完成左侧信息。系统不会用历史结果代替本次识别。</p><small>证据不足时会提示“无法可靠判断”，不会把候选当作确诊。</small></div> : <>
              <div className="public-image-stage"><div className="public-annotated"><img src={imageUrl} alt="本次诊断图片" loading="eager" decoding="async" />{detections.map((item, index) => { const [left, top, width, height] = item.bbox; return <span className="public-box" key={`${item.class_id}-${index}`} style={{ left: `${left * 100}%`, top: `${top * 100}%`, width: `${width * 100}%`, height: `${height * 100}%` }}><b>{item.class_name} {Math.round(item.confidence * 100)}%</b></span>; })}</div></div>
              {record && <div className={`public-resolution resolution-${record.resolution_status}`} role="status"><strong>{record.user_summary}</strong><span>{record.next_action}</span>{visibleResolutionReasons.length > 0 && <small>原因：{visibleResolutionReasons.join("；")}</small>}</div>}
              <div className="public-answer-grid">
                <article><span>发现了什么</span><h3>{diagnosis}</h3><p>{detections.length ? `定位到 ${detections.length} 个可疑区域` : "视觉模型没有定位到明确目标"}</p></article>
                <article className={`risk-${record?.diagnostic_risk ?? "unknown"}`}><span>这个结果有多可靠？</span><h3>{riskLabel(record?.diagnostic_risk)}</h3><p>{analysis?.detector_alignment === "conflict" ? "两种识别方法给出的候选不一致" : "由图片质量、识别把握和两种方法是否一致共同决定"}</p></article>
                <article><span>田里受影响的程度</span><h3>{severityLabel(record?.field_severity)}</h3><p>{analysis?.severity_basis ?? "这是基于用户信息和图片的辅助判断，不等同经济阈值。"}</p></article>
              </div>
              <div className="public-next"><span>现在建议你</span><ol>{(conclusive ? nextActions : [record?.next_action ?? "请根据页面提示继续操作"]).slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ol></div>
              {(record?.status === "multimodal_unavailable" || (record?.status === "detected" && !analysis)) && <button className="public-secondary" type="button" onClick={retryAnalysis} disabled={retrying}>{retrying ? "正在重试…" : "仅重试综合分析"}</button>}
              {record && <div className="public-result-links"><Link href={`/cases/${record.id}`}>查看病例详情</Link><Link href={`/reports/${record.id}`}>打开诊断报告</Link></div>}
              <details className="public-technical"><summary>查看其他候选和技术证据</summary><div><p>候选：{(analysis?.candidate_diagnoses ?? summary?.candidate_classes?.map((item) => item.class_name) ?? ["暂无"]).join("、")}</p>{!conclusive && <p>以上候选未确认，不作为最终诊断。</p>}<p>不确定性：{(analysis?.uncertainty ?? ["历史记录未提供"]).join("；")}</p><p>需要补拍：{(analysis?.required_additional_photos ?? ["叶背、整株和周边植株"]).join("；")}</p>{analysis?.grounded_assessment?.harms?.length ? <p>有依据的危害：{analysis.grounded_assessment.harms.map((item) => item.conclusion).join("；")}</p> : null}{analysis?.grounded_assessment?.causes?.length ? <p>有依据的诱因：{analysis.grounded_assessment.causes.map((item) => item.conclusion).join("；")}</p> : null}<pre>{JSON.stringify({ quality: record?.quality, detector: summary?.inference, provenance: analysis?.provenance }, null, 2)}</pre></div></details>
            </>}
          </section>
        </section>

        <section className="public-history-preview">
          <div className="public-list-heading"><div><span>最近诊断记录</span><h2>从真实记录回看识别过程</h2></div><Link href="/history">查看全部病例历史 →</Link></div>
          <div className="public-case-grid">{history.length ? history.map((item) => <Link href={`/cases/${item.id}`} className="public-case-tile" key={item.id}><span>{formatTime(item.created_at)}</span><strong>{userDiagnosisTitle(item)}</strong><small>{item.crop} · {item.part} · 严重度 {severityLabel(item.field_severity)}</small></Link>) : <p className="public-muted">当前识别服务器暂时没有诊断记录。</p>}</div>
        </section>

        <footer className="public-footer"><p>田诊协同提供图片辅助判断，不替代现场植保诊断、实验室检测或当地经济阈值。</p><p>病例保存在创建它的识别服务器；涉及用药请查询当地现行登记标签并联系植保人员。</p></footer>
      </main>
    </WorkspaceShell>
  );
}
