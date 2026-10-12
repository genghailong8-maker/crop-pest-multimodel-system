"use client";

import { useEffect, useState } from "react";

import {
  apiUrl,
  analyzeCase,
  editHeaders,
  instanceHeaders,
  readJson,
  type CaseRecord,
  type R31HostKnowledge,
  type R31Source,
  type R31Treatment,
  type SeverityLevel,
} from "../lib/api";
import { resolveR31SeverityAsset } from "../lib/r31SeverityAssets";

const LEVELS = ["mild", "moderate", "severe"] as const;
const LEVEL_LABELS: Record<SeverityLevel, string> = {
  mild: "轻度",
  moderate: "中度",
  severe: "重度",
  uncertain: "无法判断",
};
const TREATMENT_TITLES: Record<NonNullable<R31Treatment>["treatment_level"], string> = {
  host_severity: "当前作物 · 当前严重程度防治措施",
  host_general: "当前作物通用防治措施",
  insect_general: "害虫通用防治措施",
  none: "防治措施",
};
const BODY_LABELS: Record<string, string> = {
  monitoring: "监测建议",
  management: "管理措施",
  prevention_monitoring: "预防与监测",
  biological_physical: "生物与物理",
  chemical_boundary: "化学防治边界",
  agricultural_control: "农业防治",
  physical_control: "物理防治",
  biological_control: "生物防治",
};

function SourceLinks({ ids, sources }: { ids?: string[]; sources?: R31Source[] }) {
  if (!ids?.length) return null;
  const sourceMap = new Map((sources ?? []).map((source) => [source.id, source]));
  return <div className="r31-source-list"><strong>来源</strong>{ids.map((id) => {
    const source = sourceMap.get(id);
    if (!source?.title) return null;
    const label = source.organization ? `${source.title} · ${source.organization}` : source.title;
    return source.url ? <a key={id} href={source.url} target="_blank" rel="noopener noreferrer">{label}</a> : <span key={id}>{label}</span>;
  })}</div>;
}

function SourceBlock({ sourceIds, sources }: { sourceIds?: string[]; sources?: R31Source[] }) {
  return <SourceLinks ids={sourceIds} sources={sources} />;
}

function TreatmentBody({ treatment }: { treatment: R31Treatment }) {
  if (!treatment.body || treatment.treatment_level === "none") return null;
  const groups = treatment.body.sections ?? treatment.body.measures ?? {};
  const items = Object.entries(groups).filter(([, value]) => typeof value === "string" && value.trim().length > 0);
  const specificControlTexts = new Set(
    ["agricultural_control", "physical_control", "biological_control"]
      .map((key) => groups[key])
      .filter((value): value is string => typeof value === "string" && value.trim().length > 0)
      .map((value) => value.trim()),
  );
  const visibleItems = items.filter(([key, value]) => key !== "management" || !specificControlTexts.has(value.trim()));
  return <>
    {visibleItems.map(([key, value]) => <section className="r31-treatment-group" key={key}>
      <h4>{BODY_LABELS[key] ?? "防治措施"}</h4>
      <p>{value}</p>
    </section>)}
    {treatment.body.severity_note ? <p className="r31-treatment-note">{treatment.body.severity_note}</p> : null}
    {treatment.body.pesticide_policy ? <p className="r31-treatment-policy">{treatment.body.pesticide_policy}</p> : null}
  </>;
}

function HostSeverity({
  record,
  details,
  busy,
  onConfirm,
  classId,
  confirmedHost,
}: {
  record: CaseRecord;
  details: NonNullable<R31HostKnowledge["host_knowledge"]>;
  busy: boolean;
  onConfirm: (level: SeverityLevel) => Promise<void> | void;
  classId: number;
  confirmedHost: string;
}) {
  const current = record.severity?.status === "available" ? record.severity.level : null;
  const [selected, setSelected] = useState<SeverityLevel | "">(current || "");
  const [failedAssets, setFailedAssets] = useState<Set<string>>(() => new Set());
  return <section className="r31-host-severity" aria-labelledby="r31-host-severity-title">
    <header><span>当前寄主</span><h3 id="r31-host-severity-title">选择当前受害程度</h3><p>仅根据当前图片中可观察到的寄主受害表现判断，不代表田块级发生程度。</p></header>
    <div className="r31-severity-options" role="radiogroup" aria-label="当前作物受害程度">
      {LEVELS.map((level) => {
        const item = details.severity.levels[level];
        if (!item) return null;
        const checked = selected === level;
        const asset = resolveR31SeverityAsset(classId, confirmedHost, level, details.severity_available);
        const showAsset = Boolean(asset && !failedAssets.has(asset));
        return <button key={level} type="button" role="radio" aria-checked={checked} className={`r31-severity-option ${checked ? "is-selected" : ""}`} disabled={busy} onClick={() => setSelected(level)}>
          <span className="r31-severity-placeholder">
            {/* Static, reviewed project assets intentionally bypass remote image optimization. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            {showAsset ? <img src={asset!} alt={`${details.severity.levels[level]?.label ?? LEVEL_LABELS[level]} AI受害程度示意图`} onError={() => setFailedAssets((currentFailed) => new Set(currentFailed).add(asset!))} /> : <span aria-label={`${LEVEL_LABELS[level]}示意图暂不可用`}>示意图暂不可用</span>}
            {showAsset ? <small className="severity-image-badge">AI示意图 · 非真实照片 · 仅供辅助判断</small> : null}
          </span>
          <span className="r31-severity-copy"><strong>{LEVEL_LABELS[level]}</strong><span>{item.rubric}</span><small>{item.observable_features.join("；")}</small></span>
          <span className="r31-severity-state">{checked ? "已选择" : "选择"}</span>
        </button>;
      })}
      <button type="button" role="radio" aria-checked={selected === "uncertain"} className={`r31-severity-option r31-severity-uncertain ${selected === "uncertain" ? "is-selected" : ""}`} disabled={busy} onClick={() => setSelected("uncertain")}>
        <span className="r31-severity-copy"><strong>无法判断</strong><span>当前受害程度无法可靠判断。</span></span>
        <span className="r31-severity-state">{selected === "uncertain" ? "已选择" : "选择"}</span>
      </button>
    </div>
    <p className="r31-image-disclaimer">示意图依据经过审核的农业资料生成，不作为病虫害诊断或现场检测依据。</p>
    <button className="final-primary severity-confirm" type="button" disabled={busy || !selected} onClick={() => { if (selected) void onConfirm(selected); }}>
      {busy ? "正在保存…" : current ? "确认新的受害程度" : "确认受害程度并继续"}
    </button>
  </section>;
}

function TreatmentPanel({ treatment }: { treatment: R31Treatment | null }) {
  if (!treatment) return null;
  if (treatment.treatment_level === "none") return <section className="r31-treatment-panel"><h3>{TREATMENT_TITLES.none}</h3><p>{treatment.fallback_message}</p></section>;
  return <section className="r31-treatment-panel" data-treatment-level={treatment.treatment_level}>
    <h3>{TREATMENT_TITLES[treatment.treatment_level]}</h3>
    <p className="r31-fallback-message">{treatment.fallback_message}</p>
    <TreatmentBody treatment={treatment} />
    <SourceLinks ids={treatment.source_ids} />
  </section>;
}

export default function R31HostKnowledgePanel({
  record,
  busy = false,
  onRecord,
  onSeverity,
}: {
  record: CaseRecord;
  busy?: boolean;
  onRecord: (record: CaseRecord) => void;
  onSeverity: (level: SeverityLevel) => Promise<void> | void;
}) {
  const initial = record.host_knowledge?.available ? record.host_knowledge : null;
  const [knowledge, setKnowledge] = useState<R31HostKnowledge | null>(initial);
  const [loading, setLoading] = useState(Boolean(record.host_knowledge?.available));
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const instanceId = record.instance_id;

  useEffect(() => {
    if (!record.host_knowledge?.available) {
      return;
    }
    let active = true;
    queueMicrotask(() => {
      if (active) {
        setLoading(true);
        setError(null);
      }
    });
    fetch(apiUrl(`/api/cases/${record.id}/host-knowledge`), { headers: instanceHeaders({ instance_id: instanceId }) })
      .then(readJson<R31HostKnowledge>)
      .then((next) => active && setKnowledge(next))
      .catch(() => active && setError("寄主资料暂时无法读取，请稍后重试。"))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [record.id, instanceId, record.host_knowledge?.available, record.host_knowledge?.confirmed_host]);

  async function confirmHost(host: string) {
    setConfirming(true);
    setError(null);
    try {
      const next = await readJson<CaseRecord>(await fetch(apiUrl(`/api/cases/${record.id}/host-confirmation`), {
        method: "POST",
        headers: { ...editHeaders(record.id, true), ...instanceHeaders(record) },
        body: JSON.stringify({ confirmed_host: host }),
      }));
      const analyzed = await analyzeCase(next);
      onRecord(analyzed);
      setKnowledge(analyzed.host_knowledge?.available ? analyzed.host_knowledge : null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "寄主确认失败");
    } finally {
      setConfirming(false);
    }
  }

  // The parent record is replaced after host confirmation and severity choice.
  // Prefer that fresh API snapshot so a same-host severity update cannot leave
  // an older fallback treatment rendered in this panel.
  const visibleKnowledge = record.host_knowledge?.available
    ? record.host_knowledge
    : knowledge?.available ? knowledge : null;
  if (!visibleKnowledge?.available) return null;
  const selected = visibleKnowledge.confirmed_host;
  const details = visibleKnowledge.host_knowledge;
  const isOther = selected === visibleKnowledge.other.value;
  const hasUncertainSeverity = record.severity?.status === "available" && record.severity.level === "uncertain";

  return <section className="r31-host-panel" aria-labelledby="r31-host-panel-title" data-testid="r31-host-panel">
    <header className="r31-host-panel-heading"><div><span>诊断上下文</span><h2 id="r31-host-panel-title">寄主与当前作物资料</h2></div>{loading ? <small>正在读取资料…</small> : null}</header>
    {error ? <p className="r31-host-error" role="alert">{error}</p> : null}
    {!selected ? <section className="r31-host-selector" aria-labelledby="r31-host-selector-title">
      <h3 id="r31-host-selector-title">请先确认寄主作物</h3>
      <p>推荐寄主仅表示审核资料支持的常见寄主之一，不会自动成为确认结果。</p>
      {visibleKnowledge.recommended_label ? <p className="r31-recommended-label">{visibleKnowledge.recommended_label}</p> : null}
      <div className="r31-host-options" role="listbox" aria-label="可确认的寄主作物">
        {visibleKnowledge.host_options.map((option) => <button key={option.crop} type="button" role="option" aria-selected={false} className={`r31-host-option ${option.crop === visibleKnowledge.recommended_host ? "is-recommended" : ""}`} disabled={confirming || busy} onClick={() => void confirmHost(option.crop)}>
          <strong>{option.crop}</strong><span>{option.crop === visibleKnowledge.recommended_host ? "推荐：常见寄主之一" : "已审核寄主"}</span>
        </button>)}
        <button type="button" role="option" aria-selected={false} className="r31-host-option r31-host-other" disabled={confirming || busy} onClick={() => void confirmHost(visibleKnowledge.other.value)}>
          <strong>{visibleKnowledge.other.label}</strong><span>不提供自由输入</span><small>仅显示昆虫通用资料</small>
        </button>
      </div>
      <p className="r31-host-authority-note">请选择与图片中实际受害对象一致的寄主作物。</p>
    </section> : <>
      <div className="r31-confirmed-host"><strong>{isOther ? `已确认寄主：${visibleKnowledge.other.label}` : `已确认寄主：${selected}`}</strong></div>
      {isOther && !hasUncertainSeverity ? <p className="r31-other-message">{visibleKnowledge.treatment?.fallback_message || "当前作物暂未收录，以下仅显示该害虫的通用危害、可能诱因和通用防治建议。"}</p> : null}
      {!isOther && details ? <>
        <section className="r31-host-damage"><h3>当前作物受害表现</h3>{details.damage.available && details.damage.text ? <p>{details.damage.text}</p> : <p className="r31-capability-note">当前寄主暂无可用的作物特异受害表现资料。</p>}<SourceBlock sourceIds={details.damage.source_ids} sources={details.damage.sources} /></section>
        {details.severity_available && details.severity.available ? <HostSeverity record={record} details={details} busy={busy} onConfirm={onSeverity} classId={visibleKnowledge.class_id} confirmedHost={selected} /> : <p className="r31-severity-unavailable">当前寄主已有可靠受害资料，但暂缺完整的轻/中/重分级依据。</p>}
      </> : null}
      {hasUncertainSeverity ? null : <TreatmentPanel treatment={visibleKnowledge.treatment} />}
      {!isOther && details ? <SourceBlock sourceIds={details.provenance.host_damage_source_ids as string[] | undefined} sources={details.damage.sources} /> : null}
    </>}
  </section>;
}
