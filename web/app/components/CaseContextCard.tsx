import type { CaseRecord } from "../lib/api";
import { spreadSpeedLabel } from "../lib/api";

function cropDisplay(record: CaseRecord) {
  const crop = record.case_context?.crop;
  if (crop) return crop.status === "not_applicable" ? "不适用" : crop.status === "available" && crop.value ? crop.value : "暂无法确定";
  return record.crop || "暂无法确定";
}

function growthDisplay(record: CaseRecord) {
  const growth = record.case_context?.growth_stage;
  if (growth) return growth.status === "available" && growth.label ? growth.label : "未提供";
  return record.growth_stage && record.growth_stage !== "不适用" ? record.growth_stage : "未提供";
}

function severityDisplay(record: CaseRecord) {
  const severity = record.case_context?.severity;
  if (severity) return severity.status === "available" ? severity.label || severity.level || "已评估" : "未评估";
  return record.field_severity === "unknown" ? "未评估" : ({ low: "较低", medium: "中等", high: "较高" } as Record<string, string>)[record.field_severity] || "未评估";
}

function ratioDisplay(record: CaseRecord) {
  const ratio = record.case_context?.affected_ratio_percent ?? record.affected_ratio_percent;
  return ratio == null ? "未提供" : `${ratio}%`;
}

function spreadDisplay(record: CaseRecord) {
  const spread = record.case_context?.spread_speed ?? record.spread_speed;
  return spreadSpeedLabel(spread);
}

function r3ContextRows(record: CaseRecord) {
  const context = record.context;
  if (!context) return null;
  const subject = context.subject_type === "plant" ? "植物" : "昆虫";
  return <>
    <div><dt>图片主体</dt><dd data-testid="context-subject-type">{subject}</dd></div>
    {context.subject_type === "plant" ? <>
      <div><dt>作物种类</dt><dd data-testid="context-crop-species">{context.crop_species || "未提供"}</dd></div>
      <div><dt>受影响部位</dt><dd data-testid="context-affected-part">{context.affected_part || "未提供"}</dd></div>
    </> : <div><dt>昆虫种类</dt><dd data-testid="context-insect-species">{context.insect_species || "未提供"}</dd></div>}
  </>;
}

export default function CaseContextCard({ record, compact = false }: { record: CaseRecord; compact?: boolean }) {
  const context = record.case_context;
  const environment = context?.environment;
  const isV2 = context?.severity?.algorithm_version === "severity-v2";
  return <section className={`case-context-card ${compact ? "case-context-card-compact" : ""}`} aria-labelledby="case-context-title">
    <header className="case-context-heading"><div><span>病例概况</span><h2 id="case-context-title">诊断上下文</h2></div><small>{context?.severity?.status === "available" ? "来自 Backend" : "历史兼容展示"}</small></header>
    <div className="case-context-layout">
      <dl className="case-context-facts">
        {r3ContextRows(record)}
        <div><dt>作物</dt><dd data-testid="context-crop">{cropDisplay(record)}</dd></div>
        <div><dt>生育阶段</dt><dd data-testid="context-growth-stage">{growthDisplay(record)}</dd></div>
        {isV2 ? <div><dt>当前样本受害程度</dt><dd data-testid="context-severity">{severityDisplay(record)}</dd></div> : <><div><dt>受害比例</dt><dd data-testid="context-ratio">{ratioDisplay(record)}</dd></div><div><dt>扩散速度</dt><dd data-testid="context-spread">{spreadDisplay(record)}</dd></div><div><dt>严重程度</dt><dd data-testid="context-severity">{severityDisplay(record)}</dd></div></>}
      </dl>
      <div className="case-context-environment">
        <div className="case-context-environment-heading"><h3>系统预设参考环境</h3><span>{environment?.source === "system_default" ? "system_default" : "历史数据未提供"}</span></div>
        {environment ? <dl>
          <div><dt>种植场景</dt><dd>{environment.cultivation_scene}</dd></div>
          <div><dt>环境温度</dt><dd>{environment.temperature_c}℃</dd></div>
          <div><dt>相对湿度</dt><dd>{environment.relative_humidity_percent}%</dd></div>
          <div><dt>土壤湿度</dt><dd>{environment.soil_moisture}</dd></div>
          <div><dt>光照条件</dt><dd>{environment.light_condition}</dd></div>
          <div><dt>通风条件</dt><dd>{environment.ventilation}</dd></div>
          <div><dt>近期极端天气</dt><dd>{environment.recent_extreme_weather}</dd></div>
        </dl> : <p className="case-context-muted">历史记录未提供系统环境信息。</p>}
        <p className="case-context-disclaimer">该环境信息为系统预设参考上下文，不代表当前田间实测数据，也不表示已经证实的发病诱因。</p>
      </div>
    </div>
  </section>;
}
