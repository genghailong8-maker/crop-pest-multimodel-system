"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import PublicHeader from "../../components/PublicHeader";
import { apiUrl, CaseRecord, isConclusive, readJson, riskLabel, severityLabel, spreadSpeedLabel, userDiagnosisTitle } from "../../lib/api";

type KnowledgeSource = { id: string; title: string; publisher: string; url: string; retrieved_at: string; scope: string };
type IndependentJudgment = { primary_diagnosis?: string | null; candidate_diagnoses?: string[]; evidence?: string[] };
type Report = { report_number: string; generated_at: string; case: CaseRecord; knowledge: { source_ids?: string[]; management?: Record<string, string[]>; chemical_safety?: string } | null; sources: KnowledgeSource[]; prioritized_guidance: { immediate?: string[]; agronomic?: string[]; physical?: string[]; biological?: string[]; chemical_safety?: string } | null; safety_notice: string };

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
    {isConclusive(record) ? <section><h2>下一步与防治方向</h2><ul>{(report.prioritized_guidance?.immediate ?? ["补拍清晰图片并联系当地植保人员"]).map((item) => <li key={item}>{item}</li>)}</ul><h3>农业措施</h3><ul>{report.prioritized_guidance?.agronomic?.map((item) => <li key={item}>{item}</li>)}</ul><h3>物理措施</h3><ul>{report.prioritized_guidance?.physical?.map((item) => <li key={item}>{item}</li>)}</ul><h3>生物措施</h3><ul>{report.prioritized_guidance?.biological?.map((item) => <li key={item}>{item}</li>)}</ul><p className="report-safety">{report.prioritized_guidance?.chemical_safety}</p></section> : <section><h2>下一步</h2><p>{record.user_summary}</p><p>{record.next_action}</p></section>}
    <section><h2>来源与边界</h2>{report.sources.length ? <ul>{report.sources.map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a> · {source.publisher} · 检索于 {source.retrieved_at}</li>)}</ul> : <p>历史记录未提供来源。</p>}<p>{report.safety_notice}</p><details className="technical-evidence report-screen-only"><summary>查看技术证据</summary><p>来源编号：{report.knowledge?.source_ids?.join("、") || "未提供"}</p><p>模型协议：{record.analysis?.schema_version || "历史记录未提供"} · 检测时间：{record.created_at}</p></details></section>
  </>}</section></main>;
}
