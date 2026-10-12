"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import WorkspaceShell from "../../components/WorkspaceShell";
import ExternalEvidenceSummary from "../../components/ExternalEvidenceSummary";
import CaseContextCard from "../../components/CaseContextCard";
import ImageEvidenceFrame from "../../components/ImageEvidenceFrame";
import CoreKnowledgeSummary from "../../components/CoreKnowledgeSummary";
import SeveritySelector from "../../components/SeveritySelector";
import R31HostKnowledgePanel from "../../components/R31HostKnowledgePanel";
import { analyzeCase, apiUrl, CaseRecord, CoreKnowledge, editHeaders, formatTime, instanceHeaders, instanceLabel, isInsectCase, KnowledgeDocument, readJson, SeverityLevel, userDiagnosisTitle } from "../../lib/api";

type KnowledgeSource = { id?: string; source_id?: string; title: string; publisher: string; url: string; retrieved_at: string; scope: string };
type Report = { report_number: string; generated_at: string; case: CaseRecord; knowledge: { source_ids?: string[]; management?: Record<string, string[]>; chemical_safety?: string } | null; knowledge_document?: KnowledgeDocument | null; core_knowledge?: CoreKnowledge; sources: KnowledgeSource[]; prioritized_guidance: { immediate?: string[]; agronomic?: string[]; physical?: string[]; biological?: string[]; chemical_safety?: string } | null; safety_notice: string };

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState(false);
  const [severityBusy, setSeverityBusy] = useState(false);
  useEffect(() => { fetch(apiUrl(`/api/cases/${id}/report`)).then(readJson<Report>).then(setReport).catch(() => setError(true)); }, [id]);
  const record = report?.case;

  async function chooseSeverity(level: SeverityLevel) {
    if (!record) return;
    setSeverityBusy(true);
    setError(false);
    try {
      const selected = await readJson<CaseRecord>(await fetch(apiUrl(`/api/cases/${id}/severity`), {
        method: "POST",
        headers: { ...editHeaders(id, true), ...instanceHeaders(record) },
        body: JSON.stringify({ severity_level: level }),
      }));
      if (!isInsectCase(record) || !selected.analysis?.evidence_analysis) await analyzeCase(selected);
      setReport(await readJson<Report>(await fetch(apiUrl(`/api/cases/${id}/report`))));
    } catch {
      setError(true);
    } finally {
      setSeverityBusy(false);
    }
  }

  return <WorkspaceShell service={error ? "offline" : "online"} visualMode="legacy">
    <main className="legacy-public-shell final-public-shell report-shell">
      <section className="report-page final-report-page">
        {error ? <div className="public-alert error" role="alert">报告暂时无法读取。</div> : !report || !record ? <p>正在生成报告…</p> : <>
          <header className="final-brief-head final-report-head"><div><span>专业诊断简报</span><h1>{userDiagnosisTitle(record)}</h1><dl><div><dt>病例编号</dt><dd>{report.report_number}</dd></div><div><dt>诊断时间</dt><dd>{formatTime(record.created_at)}</dd></div><div><dt>置信度</dt><dd>{Math.round((record.detections?.[0]?.confidence ?? 0) * 100)}%</dd></div></dl><p>田诊协同 · 图片辅助诊断报告 · 病例属于 {instanceLabel(record.instance_id)}</p></div><button className="final-outline-button report-screen-only" onClick={() => window.print()}>打印 / 导出报告</button></header>
           <div className="final-brief-core">
            <div className="final-brief-image"><p>检测图片</p><ImageEvidenceFrame src={apiUrl(record.image_url)} alt="病例原图及目标定位结果" detections={record.detections ?? undefined} loading="eager" fetchPriority="high" /></div>
            <div className="final-brief-summary"><div className="final-brief-summary-head"><h2>诊断摘要</h2><span>辅助诊断</span></div><CaseContextCard record={record} compact /><ExternalEvidenceSummary record={record} variant="report" showTreatment={!record.host_knowledge?.available} /></div>
           </div>
           <R31HostKnowledgePanel record={record} busy={severityBusy} onRecord={(next) => setReport((current) => current ? { ...current, case: next } : current)} onSeverity={chooseSeverity} />
           {!isInsectCase(record) && <SeveritySelector record={record} busy={severityBusy} onConfirm={chooseSeverity} />}
          <CoreKnowledgeSummary knowledge={report.core_knowledge ?? null} />
          <details className="final-report-boundary"><summary>来源与边界</summary><p className="report-source"><a href={report.knowledge_document?.source.url || "https://baike.baidu.com/"} target="_blank" rel="noopener noreferrer">{report.knowledge_document?.source.attribution || "知识内容来源：百度百科（由项目组整理，知识库版本 2026-08-18）"}</a><span className="report-source-url">{report.knowledge_document?.source.url || "https://baike.baidu.com/"}</span></p>{report.sources.length ? <><h3>辅助原则参考</h3><ul>{report.sources.map((source) => <li key={source.id ?? source.source_id ?? source.url}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title}</a><span>{source.publisher} · 检索于 {source.retrieved_at}</span><code className="report-source-url">{source.url}</code></li>)}</ul></> : null}<p>{report.safety_notice}</p></details>
        </>}
      </section>
    </main>
  </WorkspaceShell>;
}
