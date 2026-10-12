"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import WorkspaceShell from "../../components/WorkspaceShell";
import ExternalEvidenceSummary from "../../components/ExternalEvidenceSummary";
import CaseContextCard from "../../components/CaseContextCard";
import ImageEvidenceFrame from "../../components/ImageEvidenceFrame";
import CoreKnowledgeSummary from "../../components/CoreKnowledgeSummary";
import SeveritySelector from "../../components/SeveritySelector";
import R31HostKnowledgePanel from "../../components/R31HostKnowledgePanel";
import { analyzeCase, apiUrl, CaseRecord, CoreKnowledge, editHeaders, formatTime, instanceHeaders, isConclusive, isInsectCase, publicResolutionReasons, readJson, resolutionLabel, SeverityLevel, userDiagnosisTitle } from "../../lib/api";

export default function CasePage() {
  const { id } = useParams<{ id: string }>();
  const [recordState, setRecordState] = useState<{ caseId: string; value: CaseRecord | null }>({ caseId: id, value: null });
  const [knowledgeState, setKnowledgeState] = useState<{ caseId: string; value: CoreKnowledge }>({ caseId: id, value: null });
  const [errorState, setErrorState] = useState<{ caseId: string; value: string | null }>({ caseId: id, value: null });
  const record = recordState.caseId === id ? recordState.value : null;
  const knowledge = knowledgeState.caseId === id ? knowledgeState.value : null;
  const error = errorState.caseId === id ? errorState.value : null;
  const knowledgeRequestId = useRef(0);
  const [retrying, setRetrying] = useState(false);
  const [severityBusy, setSeverityBusy] = useState(false);
  const visibleResolutionReasons = publicResolutionReasons(record?.resolution_reasons);

  function setRecord(nextRecord: CaseRecord) {
    setRecordState({ caseId: nextRecord.id, value: nextRecord });
  }

  function setError(value: string | null) {
    setErrorState({ caseId: id, value });
  }

  const loadKnowledge = useCallback(async (nextRecord: CaseRecord) => {
    const requestId = ++knowledgeRequestId.current;
    setKnowledgeState({ caseId: nextRecord.id, value: null });
    if (!isConclusive(nextRecord)) return;
    try {
      const report = await readJson<{ core_knowledge?: CoreKnowledge }>(await fetch(apiUrl(`/api/cases/${nextRecord.id}/report`)));
      if (requestId === knowledgeRequestId.current) setKnowledgeState({ caseId: nextRecord.id, value: report.core_knowledge ?? null });
    } catch {
      if (requestId === knowledgeRequestId.current) setKnowledgeState({ caseId: nextRecord.id, value: null });
    }
  }, []);

  useEffect(() => {
    let active = true;
    knowledgeRequestId.current += 1;
    fetch(apiUrl(`/api/cases/${id}`)).then(readJson<CaseRecord>).then((nextRecord) => {
      if (!active) return;
      setRecord(nextRecord);
      void loadKnowledge(nextRecord);
    }).catch(() => {
      if (active) setErrorState({ caseId: id, value: "当前识别服务器暂时无法读取这份病例，请稍后重试或返回病例历史。" });
    });
    return () => {
      active = false;
      knowledgeRequestId.current += 1;
    };
  }, [id, loadKnowledge]);

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
          {isConclusive(record) ? <CoreKnowledgeSummary knowledge={knowledge} /> : <section className="final-knowledge-overview"><h2>暂不形成具体诊断</h2><p>当前证据不足，页面不会把候选病虫害当作已经确认的结论。请按照上方提示补拍图片。</p></section>}
          <div className="final-brief-actions">{record.status === "detected" && !record.analysis && <button className="final-secondary" onClick={retry} disabled={retrying}>{retrying ? "正在重试…" : "整理来源证据"}</button>}{record.resolution_status === "retake_required" && <Link className="final-secondary action-link" href="/">重新拍一张图片</Link>}</div>
        </>}
      </section>
      <footer className="final-footer"><p>本页为辅助识别记录；发生程度和处置阈值需由当地植保人员结合田间调查确认。病例保存在创建它的识别服务器。</p></footer>
    </main>
  </WorkspaceShell>;
}
