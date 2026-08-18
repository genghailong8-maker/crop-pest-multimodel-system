"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import PublicHeader from "../../components/PublicHeader";
import { apiUrl, CaseRecord, editHeaders, isConclusive, readJson, resolutionLabel, riskLabel, severityLabel, userDiagnosisTitle } from "../../lib/api";

export default function CasePage() {
  const { id } = useParams<{ id: string }>();
  const [record, setRecord] = useState<CaseRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  useEffect(() => { fetch(apiUrl(`/api/cases/${id}`)).then(readJson<CaseRecord>).then(setRecord).catch((reason) => setError(reason.message)); }, [id]);
  async function retry() {
    setRetrying(true); setError(null);
    try { setRecord(await readJson<CaseRecord>(await fetch(apiUrl(`/api/cases/${id}/analyze`), { method: "POST", headers: editHeaders(id) }))); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "重试失败"); }
    finally { setRetrying(false); }
  }
  return <main className="public-shell"><PublicHeader service={error && !record ? "offline" : "online"} />
    <section className="public-page-body public-detail">{error && <div className="public-alert error">{error}</div>}{!record ? <p className="public-muted">正在读取病例…</p> : <>
      <div className="public-detail-head"><div><span>病例 {record.id.slice(0, 8).toUpperCase()}</span><h1>{userDiagnosisTitle(record)}</h1><p>{record.crop} · {record.part} · {record.growth_stage}</p></div><Link href={`/reports/${record.id}`}>查看可打印报告</Link></div>
      <div className={`public-resolution resolution-${record.resolution_status}`}><strong>{resolutionLabel(record.resolution_status)}</strong><span>{record.user_summary} {record.next_action}</span>{record.resolution_reasons.length > 0 && <small>原因：{record.resolution_reasons.join("；")}</small>}</div>
      <div className="public-detail-grid"><div className="public-detail-image"><img src={apiUrl(record.image_url)} alt="病例原图" />{(record.detections ?? []).map((item, index) => { const [left, top, width, height] = item.bbox; return <span className="public-box" key={index} style={{ left: `${left * 100}%`, top: `${top * 100}%`, width: `${width * 100}%`, height: `${height * 100}%` }}><b>{item.class_name} {Math.round(item.confidence * 100)}%</b></span>; })}</div><div className="public-detail-summary"><article><span>诊断风险</span><strong>{riskLabel(record.diagnostic_risk)}</strong></article><article><span>田间严重度</span><strong>{severityLabel(record.field_severity)}</strong><p>{record.analysis?.severity_basis || "历史记录未提供严重度依据"}</p></article><article><span>不确定性</span><ul>{(record.analysis?.uncertainty ?? ["历史记录未提供"]).map((item) => <li key={item}>{item}</li>)}</ul></article></div></div>
      {isConclusive(record) ? <section className="public-detail-section"><h2>症状、危害与可能原因</h2><div className="public-three"><article><span>症状</span><ul>{(record.analysis?.symptoms ?? ["历史记录未提供"]).map((item) => <li key={item}>{item}</li>)}</ul></article><article><span>危害</span><ul>{(record.analysis?.harm ?? ["历史记录未提供"]).map((item) => <li key={item}>{item}</li>)}</ul></article><article><span>可能原因</span><ul>{(record.analysis?.possible_causes ?? ["历史记录未提供"]).map((item) => <li key={item}>{item}</li>)}</ul></article></div></section> : <section className="public-detail-section"><h2>暂不形成具体诊断</h2><p>当前证据不足，页面不会把候选病虫害当作已经确认的结论。请按照上方提示补拍图片，或等待识别服务恢复后重试。</p></section>}
      <div className="public-detail-actions">{(record.status === "multimodal_unavailable" || (record.status === "detected" && !record.analysis)) && <button className="public-secondary" onClick={retry} disabled={retrying}>{retrying ? "正在重试…" : "仅重试综合分析"}</button>}{record.resolution_status === "retake_required" && <Link className="public-secondary action-link" href="/">重新拍一张图片</Link>}</div>
      <details className="public-technical"><summary>查看技术证据</summary><p>候选仅供技术核对，未确认，不作为最终诊断。</p><pre>{JSON.stringify({ quality: record.quality, detections: record.detections, detector_summary: record.detector_summary, analysis_provenance: record.analysis?.provenance }, null, 2)}</pre></details>
    </>}</section><footer className="public-footer"><p>本页为辅助识别记录；发生程度和处置阈值需由当地植保人员结合田间调查确认。</p></footer></main>;
}
