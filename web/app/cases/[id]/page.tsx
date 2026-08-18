"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import PublicHeader from "../../components/PublicHeader";
import { apiUrl, CaseRecord, editHeaders, isConclusive, KnowledgeDocument, readJson, resolutionLabel, riskLabel, severityLabel, userDiagnosisTitle } from "../../lib/api";

export default function CasePage() {
  const { id } = useParams<{ id: string }>();
  const [record, setRecord] = useState<CaseRecord | null>(null);
  const [knowledge, setKnowledge] = useState<KnowledgeDocument | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  async function loadKnowledge(nextRecord: CaseRecord) {
    const classId = nextRecord.detections?.[0]?.class_id;
    if (!isConclusive(nextRecord) || classId == null) { setKnowledge(null); return; }
    try { setKnowledge(await readJson<KnowledgeDocument>(await fetch(apiUrl(`/api/catalog/classes/${classId}/knowledge-document`)))); }
    catch { setKnowledge(null); }
  }
  useEffect(() => { fetch(apiUrl(`/api/cases/${id}`)).then(readJson<CaseRecord>).then((nextRecord) => { setRecord(nextRecord); void loadKnowledge(nextRecord); }).catch((reason) => setError(reason.message)); }, [id]);
  async function retry() {
    setRetrying(true); setError(null);
    try { const nextRecord = await readJson<CaseRecord>(await fetch(apiUrl(`/api/cases/${id}/analyze`), { method: "POST", headers: editHeaders(id) })); setRecord(nextRecord); await loadKnowledge(nextRecord); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "重试失败"); }
    finally { setRetrying(false); }
  }
  return <main className="public-shell"><PublicHeader service={error && !record ? "offline" : "online"} />
    <section className="public-page-body public-detail">{error && <div className="public-alert error">{error}</div>}{!record ? <p className="public-muted">正在读取病例…</p> : <>
      <div className="public-detail-head"><div><span>病例 {record.id.slice(0, 8).toUpperCase()}</span><h1>{userDiagnosisTitle(record)}</h1><p>{record.crop} · {record.part} · {record.growth_stage}</p></div><Link href={`/reports/${record.id}`}>查看可打印报告</Link></div>
      <div className={`public-resolution resolution-${record.resolution_status}`}><strong>{resolutionLabel(record.resolution_status)}</strong><span>{record.user_summary} {record.next_action}</span>{record.resolution_reasons.length > 0 && <small>原因：{record.resolution_reasons.join("；")}</small>}</div>
      <div className="public-detail-grid"><div className="public-detail-image"><img src={apiUrl(record.image_url)} alt="病例原图" />{(record.detections ?? []).map((item, index) => { const [left, top, width, height] = item.bbox; return <span className="public-box" key={index} style={{ left: `${left * 100}%`, top: `${top * 100}%`, width: `${width * 100}%`, height: `${height * 100}%` }}><b>{item.class_name} {Math.round(item.confidence * 100)}%</b></span>; })}</div><div className="public-detail-summary"><article><span>诊断风险</span><strong>{riskLabel(record.diagnostic_risk)}</strong></article><article><span>田间严重度</span><strong>{severityLabel(record.field_severity)}</strong><p>{record.analysis?.severity_basis || "历史记录未提供严重度依据"}</p></article><article><span>不确定性</span><ul>{(record.analysis?.uncertainty ?? ["历史记录未提供"]).map((item) => <li key={item}>{item}</li>)}</ul></article></div></div>
      {isConclusive(record) ? <section className="public-detail-section"><h2>症状、特征和防治建议</h2><div className="public-three knowledge-summary"><article><span>症状</span><div className="knowledge-prose" dangerouslySetInnerHTML={{ __html: knowledge?.symptoms_html ?? "<p>知识库暂时无法读取</p>" }} /></article><article><span>特征</span><div className="knowledge-prose" dangerouslySetInnerHTML={{ __html: knowledge?.features_html ?? "<p>知识库暂时无法读取</p>" }} /></article><article><span>防治建议</span><div className="knowledge-prose" dangerouslySetInnerHTML={{ __html: knowledge?.prevention_html ?? "<p>知识库暂时无法读取</p>" }} /></article></div></section> : <section className="public-detail-section"><h2>暂不形成具体诊断</h2><p>当前证据不足，页面不会把候选病虫害当作已经确认的结论。请按照上方提示补拍图片，或等待识别服务恢复后重试。</p></section>}
      <div className="public-detail-actions">{(record.status === "multimodal_unavailable" || (record.status === "detected" && !record.analysis)) && <button className="public-secondary" onClick={retry} disabled={retrying}>{retrying ? "正在重试…" : "仅重试综合分析"}</button>}{record.resolution_status === "retake_required" && <Link className="public-secondary action-link" href="/">重新拍一张图片</Link>}</div>
    </>}</section><footer className="public-footer"><p>本页为辅助识别记录；发生程度和处置阈值需由当地植保人员结合田间调查确认。</p></footer></main>;
}
