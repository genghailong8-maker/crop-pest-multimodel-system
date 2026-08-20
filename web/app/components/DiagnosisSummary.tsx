import type { ReactNode } from "react";

import {
  CaseRecord,
  isConclusive,
  resolutionLabel,
  riskLabel,
  severityLabel,
  userDiagnosisTitle,
} from "../lib/api";

type DiagnosisSummaryProps = {
  record: CaseRecord;
  headingLevel?: "h1" | "h2";
  actions?: ReactNode;
};

function reliabilityTone(record: CaseRecord) {
  if (!record.analysis) return "stopped";
  if (record.resolution_status !== "conclusive") return "stopped";
  if (record.diagnostic_risk === "high" || record.analysis?.needs_human_review || record.detector_summary?.needs_review) return "caution";
  if (record.diagnostic_risk === "medium" || record.diagnostic_risk === "unknown") return "limited";
  return "reliable";
}

export default function DiagnosisSummary({ record, headingLevel = "h2", actions }: DiagnosisSummaryProps) {
  const Heading = headingLevel;
  const conclusive = isConclusive(record);
  const analysisReady = Boolean(record.analysis);
  const needsReview = Boolean(record.analysis?.needs_human_review || record.detector_summary?.needs_review);
  const tone = reliabilityTone(record);
  const findingLabel = !analysisReady
    ? record.detections?.length ? "定位完成，等待综合核对" : "等待分析"
    : conclusive
    ? tone === "reliable" ? "参考结果" : "初步匹配"
    : resolutionLabel(record.resolution_status);
  const nextAction = record.next_action === "查看发现位置、判断依据和下一步处理建议。"
    ? "先查看本次定位与证据；处置前请结合田间调查，结果不够可靠时联系植保人员复核。"
    : record.next_action;

  return (
    <section className={`v3-conclusion v3-conclusion-${tone}`} aria-label="核心诊断结论">
      <div className="v3-conclusion-lead">
        <span className="v3-conclusion-state">{findingLabel}</span>
        <Heading>{userDiagnosisTitle(record)}</Heading>
        <p>{record.user_summary}</p>
      </div>

      <dl className="v3-conclusion-facts">
        <div>
          <dt>证据状态</dt>
          <dd>{riskLabel(record.diagnostic_risk)}</dd>
          {needsReview && <small>建议由植保人员复核</small>}
        </div>
        <div>
          <dt>田间影响</dt>
          <dd>{severityLabel(record.field_severity)}</dd>
          <small>{record.affected_ratio_percent == null ? "未提供受害比例" : `已报告受害比例 ${record.affected_ratio_percent}%`}</small>
        </div>
      </dl>

      <div className="v3-conclusion-action">
        <div><span>现在建议</span><p>{nextAction}</p></div>
        {actions && <div className="v3-conclusion-actions">{actions}</div>}
      </div>
    </section>
  );
}
