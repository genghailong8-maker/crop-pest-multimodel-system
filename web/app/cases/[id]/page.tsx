"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import WorkspaceShell from "../../components/WorkspaceShell";
import ExternalEvidenceSummary from "../../components/ExternalEvidenceSummary";
import CaseContextCard from "../../components/CaseContextCard";
import ImageEvidenceFrame from "../../components/ImageEvidenceFrame";
import KnowledgeSectionGrid from "../../components/KnowledgeSectionGrid";
import SeveritySelector from "../../components/SeveritySelector";
import R31HostKnowledgePanel from "../../components/R31HostKnowledgePanel";
import { analyzeCase, apiUrl, CaseRecord, editHeaders, formatTime, instanceHeaders, isConclusive, isInsectCase, KnowledgeDocument, publicResolutionReasons, readJson, resolutionLabel, riskLabel, SeverityLevel, severityLabel, userDiagnosisTitle } from "../../lib/api";

function GroundedAssessment({ record }: { record: CaseRecord }) {
  const assessment = record.analysis?.grounded_assessment;
  if (!assessment) return <p>当前历史记录没有逐条绑定的综合分析。</p>;
  return <div className="public-grounded">
    <div><h3>危害</h3>{assessment.harms.length ? <ul>{assessment.harms.map((item, index) => <li key={`${item.conclusion}-${index}`}><strong>{item.conclusion}</strong>{item.evidence.length ? <span>{item.evidence.map((evidence) => `${evidence.observation}（${evidence.source === "image" ? "图片" : evidence.source === "yolo" ? "目标定位" : "田间信息"}）`).join("；")}</span> : null}</li>)}</ul> : <p>无法判断</p>}</div>
    <div><h3>可能诱因</h3>{assessment.causes.length ? <ul>{assessment.causes.map((item, index) => <li key={`${item.conclusion}-${index}`}><strong>{item.conclusion}</strong>{item.evidence.length ? <span>{item.evidence.map((evidence) => `${evidence.observation}（${evidence.source === "image" ? "图片" : evidence.source === "yolo" ? "目标定位" : "田间信息"}）`).join("；")}</span> : null}</li>)}</ul> : <p>无法判断</p>}</div>
  </div>;
}

export default function CasePage() {
  const { id } = useParams<{ id: string }>();
  const [record, setRecord] = useState<CaseRecord | null>(null);
  const [knowledge, setKnowledge] = useState<KnowledgeDocument | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [severityBusy, setSeverityBusy] = useState(false);
  const visibleResolutionReasons = publicResolutionReasons(record?.resolution_reasons);

  async function loadKnowledge(nextRecord: CaseRecord) {
    const classId = nextRecord.detector_summary?.primary_candidate?.class_id ?? nextRecord.detections?.[0]?.class_id;
    if (!isConclusive(nextRecord) || classId == null) { setKnowledge(null); return; }
    try { setKnowledge(await readJson<KnowledgeDocument>(await fetch(apiUrl(`/api/catalog/classes/${classId}/knowledge-document`)))); }
    catch { setKnowledge(null); }
  }

  useEffect(() => {
    fetch(apiUrl(`/api/cases/${id}`)).then(readJson<CaseRecord>).then((nextRecord) => { setRecord(nextRecord); void loadKnowledge(nextRecord); }).catch(() => setError("当前识别服务器暂时无法读取这份病例，请稍后重试或返回病例历史。"));
  }, [id]);

  async function retry() {
    if (!record) return;
    setRetrying(true);
    setError(null);
    try {
      const nextRecord = await analyzeCase(record);
      setRecord(nextRecord);
      await loadKnowledge(nextRecord);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "重试失败");
    } finally {
      setRetrying(false);
    }
  }

  async function chooseSeverity(level: SeverityLevel) {
    if (!record) return;
    setSeverityBusy(true);
    setError(null);
    try {
      const selected = await readJson<CaseRecord>(await fetch(apiUrl(`/api/cases/${id}/severity`), {
        method: "POST",
        headers: { ...editHeaders(id, true), ...instanceHeaders(record) },
        body: JSON.stringify({ severity_level: level }),
      }));
      const nextRecord = !isInsectCase(record) || !selected.analysis?.evidence_analysis
        ? await analyzeCase(selected)
        : selected;
      setRecord(nextRecord);
      await loadKnowledge(nextRecord);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "受害程度保存失败");
    } finally {
      setSeverityBusy(false);
    }
  }

  return <WorkspaceShell service={error && !record ? "offline" : "online"} visualMode="legacy">
    <main className="legacy-public-shell final-public-shell">
      <section className="final-brief final-case-brief">
        {error && <div className="public-alert error" role="alert">{error}</div>}
        {!record ? <p className="public-muted">正在读取病例…</p> : <>
          <header className="final-brief-head">
            <div><span>专业诊断简报</span><h1>{userDiagnosisTitle(record)}</h1><dl><div><dt>病例编号</dt><dd>{record.id.slice(0, 12).toUpperCase()}</dd></div><div><dt>诊断时间</dt><dd>{formatTime(record.created_at)}</dd></div><div><dt>置信度</dt><dd>{Math.round((record.detections?.[0]?.confidence ?? 0) * 100)}%</dd></div></dl><small className="public-case-owner">病例属于：{record.instance_id === "lab_cpu" ? "实验室 CPU" : record.instance_id === "gpu_full" ? "原 GPU" : "创建它的识别服务器"}</small></div>
            <Link className="final-outline-button" href={`/reports/${record.id}`}>打印 / 导出报告</Link>
          </header>
          <div className="final-brief-core">
            <div className="final-brief-image"><p>检测图片</p><ImageEvidenceFrame src={apiUrl(record.image_url)} alt="病例原图及目标定位结果" detections={record.detections ?? undefined} loading="eager" fetchPriority="high" /></div>
            <div className="final-brief-summary"><div className="final-brief-summary-head"><h2>诊断摘要</h2><span>辅助诊断</span></div><div className={`final-resolution resolution-${record.resolution_status}`} role="status"><strong>{resolutionLabel(record.resolution_status)}</strong><span>{record.user_summary} {record.next_action}</span>{visibleResolutionReasons.length > 0 && <small>原因：{visibleResolutionReasons.join("；")}</small>}</div><ExternalEvidenceSummary record={record} variant="report" showTreatment={!record.host_knowledge?.available} /></div>
          </div>
           <CaseContextCard record={record} />
           <R31HostKnowledgePanel record={record} busy={severityBusy} onRecord={setRecord} onSeverity={chooseSeverity} />
           {!isInsectCase(record) && <SeveritySelector record={record} busy={severityBusy} onConfirm={chooseSeverity} />}
          {isConclusive(record) ? <section className="final-knowledge-overview"><h2>完整知识库</h2><div className="final-knowledge-document"><KnowledgeSectionGrid sections={knowledge?.sections} fallbackHtml={knowledge?.full_html} /></div></section> : <section className="final-knowledge-overview"><h2>暂不形成具体诊断</h2><p>当前证据不足，页面不会把候选病虫害当作已经确认的结论。请按照上方提示补拍图片。</p></section>}
          <div className="final-brief-actions">{record.status === "detected" && !record.analysis && <button className="final-secondary" onClick={retry} disabled={retrying}>{retrying ? "正在重试…" : "整理来源证据"}</button>}{record.resolution_status === "retake_required" && <Link className="final-secondary action-link" href="/">重新拍一张图片</Link>}</div>
          <details className="final-technical"><summary>技术详情</summary><div>{record.analysis && <GroundedAssessment record={record} />}<p>诊断风险：{riskLabel(record.diagnostic_risk)}；田间严重度：{severityLabel(record.field_severity)}</p><p>候选：{(record.analysis?.candidate_diagnoses ?? record.detector_summary?.candidate_classes?.map((item) => item.class_name) ?? ["暂无"]).join("、")}</p><p>系统记录：{record.resolution_reasons.length ? record.resolution_reasons.join("；") : "无"}</p><pre>{JSON.stringify({ detector: record.detector_summary?.inference, provenance: record.analysis?.provenance }, null, 2)}</pre></div></details>
        </>}
      </section>
      <footer className="final-footer"><p>本页为辅助识别记录；发生程度和处置阈值需由当地植保人员结合田间调查确认。病例保存在创建它的识别服务器。</p></footer>
    </main>
  </WorkspaceShell>;
}
