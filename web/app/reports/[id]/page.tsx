"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import PublicHeader from "../../components/PublicHeader";
import { apiUrl, CaseRecord, isConclusive, KnowledgeDocument, readJson, riskLabel, severityLabel, spreadSpeedLabel, userDiagnosisTitle } from "../../lib/api";

type KnowledgeSource = { id: string; title: string; publisher: string; url: string; retrieved_at: string; scope: string };
type IndependentJudgment = { primary_diagnosis?: string | null; candidate_diagnoses?: string[]; evidence?: string[] };
type Report = { report_number: string; generated_at: string; case: CaseRecord; knowledge: { source_ids?: string[]; management?: Record<string, string[]>; chemical_safety?: string } | null; knowledge_document?: KnowledgeDocument | null; sources: KnowledgeSource[]; prioritized_guidance: { immediate?: string[]; agronomic?: string[]; physical?: string[]; biological?: string[]; chemical_safety?: string } | null; safety_notice: string };

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => { fetch(apiUrl(`/api/cases/${id}/report`)).then(readJson<Report>).then(setReport).catch(() => setError(true)); }, [id]);
  const record = report?.case;
  const independent = record?.analysis?.independent_judgment as IndependentJudgment | undefined;
  return <main className="public-shell report-shell"><div className="report-screen-only"><PublicHeader service={error ? "offline" : "online"} /></div><section className="report-page">{error ? <div className="public-alert error">报告暂时无法读取。</div> : !report || !record ? <p>正在生成报告…</p> : <>
    <header className="report-head"><div><span>田诊协同 · 图片辅助诊断报告</span><h1>{userDiagnosisTitle(record)}</h1><p>报告编号 {report.report_number}</p></div><button className="report-screen-only" onClick={() => window.print()}>打印 / 保存为 PDF</button></header>
    <div className="report-grid"><img src={apiUrl(record.image_url)} alt="病例原图" /><dl><div><dt>作物与部位</dt><dd>{record.crop} · {record.part}</dd></div><div><dt>生育期与环境</dt><dd>{record.growth_stage} · {record.environment?.scene || "未填写"}</dd></div><div><dt>受害比例</dt><dd>{record.affected_ratio_percent == null ? "未填写" : `${record.affected_ratio_percent}%`}</dd></div><div><dt>扩散速度</dt><dd>{spreadSpeedLabel(record.spread_speed)}</dd></div><div><dt>诊断风险</dt><dd>{riskLabel(record.diagnostic_risk)}</dd></div><div><dt>田间严重度</dt><dd>{severityLabel(record.field_severity)}</dd></div></dl></div>
    <section><h2>综合分析</h2><p>{record.analysis?.severity_basis || "历史记录未提供严重度依据。"}</p><h3>视觉候选</h3><p>{(record.detections ?? []).map((item) => `${item.class_name} ${Math.round(item.confidence * 100)}%`).join("；") || "未定位到明确目标"}</p>{isConclusive(record) ? <><h3>独立多模态判断</h3><p>{independent?.primary_diagnosis || independent?.candidate_diagnoses?.join("、") || "历史记录未提供"}</p>{independent?.evidence?.length ? <ul>{independent.evidence.map((item) => <li key={item}>{item}</li>)}</ul> : null}</> : <p>当前状态不是可参考结论，候选未确认，不作为最终诊断。</p>}<h3>不确定性</h3><ul>{(record.analysis?.uncertainty ?? ["历史记录未提供"]).map((item) => <li key={item}>{item}</li>)}</ul></section>
    {isConclusive(record) ? <section className="knowledge-report-section"><h2>综合信息展示</h2>{report.knowledge_document?.full_html ? <div className="knowledge-document" dangerouslySetInnerHTML={{ __html: report.knowledge_document.full_html }} /> : <p>对应知识库内容暂时无法读取。</p>}</section> : <section><h2>下一步</h2><p>{record.user_summary}</p><p>{record.next_action}</p></section>}
    <section><h2>来源与边界</h2><p className="report-source"><a href={report.knowledge_document?.source.url || "https://baike.baidu.com/"} target="_blank" rel="noreferrer">{report.knowledge_document?.source.attribution || "知识内容来源：百度百科（由项目组整理，知识库版本 2026-08-18）"}</a></p>{report.sources.length ? <><h3>辅助原则参考</h3><ul>{report.sources.map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a> · {source.publisher} · 检索于 {source.retrieved_at}</li>)}</ul></> : null}<p>{report.safety_notice}</p></section>
  </>}</section></main>;
}
