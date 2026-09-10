import type { CaseRecord } from "../lib/api";

export type DiagnosisPathStage = "sampling" | "locating" | "checking" | "synthesizing" | "result" | "report";

const steps: Array<{ id: DiagnosisPathStage; label: string }> = [
  { id: "sampling", label: "田间采样" },
  { id: "locating", label: "目标定位" },
  { id: "checking", label: "信息核对" },
  { id: "synthesizing", label: "证据综合" },
  { id: "result", label: "诊断结果" },
  { id: "report", label: "诊断报告" },
];

export function diagnosisPathForRecord(record: CaseRecord): { stage: DiagnosisPathStage; blocked: boolean } {
  if (record.resolution_status === "service_unavailable") {
    const locatingFinished = Boolean(record.detector_summary || record.detections?.length);
    return { stage: locatingFinished ? "checking" : "locating", blocked: true };
  }
  if (record.status === "detected" && !record.analysis) {
    return { stage: "checking", blocked: true };
  }
  return { stage: "result", blocked: false };
}

export default function DiagnosisPath({ stage, compact = false, blocked = false, variant = "default" }: { stage: DiagnosisPathStage; compact?: boolean; blocked?: boolean; variant?: "default" | "workbench" }) {
  const currentIndex = steps.findIndex((step) => step.id === stage);
  const currentStep = steps[Math.max(currentIndex, 0)];

  return <div className={`v3-path ${compact ? "v3-path-compact" : ""} ${blocked ? "v3-path-blocked" : ""} ${variant === "workbench" ? "workspace-v4-path" : ""}`} role="group" aria-label="诊断路径">
    <div className="v3-path-heading"><strong>{blocked ? "处理已停止" : "诊断路径"}</strong><span>当前：{currentStep?.label ?? "田间采样"}</span></div>
    <ol>
      {steps.map((step, index) => {
        const state = index < currentIndex ? "done" : index === currentIndex ? (blocked ? "blocked" : "current") : "pending";
        const stateLabel = state === "done" ? "已完成" : state === "current" ? "当前步骤" : state === "blocked" ? "在此停止" : "尚未开始";
        return <li className={`v3-path-step ${state}`} key={step.id} aria-current={state === "current" || state === "blocked" ? "step" : undefined} aria-label={`${step.label}，${stateLabel}`}>
          <span className="v3-path-node" aria-hidden="true" />
          <span className="v3-path-label">{step.label}</span>
          <small>{stateLabel}</small>
        </li>;
      })}
    </ol>
  </div>;
}
