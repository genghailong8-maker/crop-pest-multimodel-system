"use client";

/* eslint-disable @next/next/no-img-element -- Reference assets may be served by the Backend asset endpoint. */

import { useState } from "react";

import type { CaseRecord, SeverityLevel } from "../lib/api";

const LEVELS = ["mild", "moderate", "severe"] as const;
const LABELS: Record<SeverityLevel, string> = {
  mild: "轻度",
  moderate: "中度",
  severe: "重度",
  uncertain: "无法判断",
};

export default function SeveritySelector({
  record,
  busy = false,
  onConfirm,
}: {
  record: CaseRecord;
  busy?: boolean;
  onConfirm: (level: SeverityLevel) => Promise<void> | void;
}) {
  const rubric = record.severity_rubric?.status === "available" ? record.severity_rubric : null;
  const current = record.severity?.status === "available" ? record.severity.level : null;
  const [selected, setSelected] = useState<SeverityLevel | "">(current || "");

  if (!rubric) return null;

  return <section className="severity-selector" aria-labelledby="severity-selector-title">
    <header className="severity-selector-heading">
      <div><span>当前样本判断</span><h2 id="severity-selector-title">选择受害程度</h2></div>
      <p>只评估当前图片中可见的目标部位，不代表田块级发生程度。</p>
    </header>
    <p className="severity-selector-scope"><strong>{rubric.rubric.assessment_unit}</strong>：{rubric.rubric.observable_features}</p>
    <div className="severity-options" role="radiogroup" aria-label="当前样本受害程度">
      {LEVELS.map((level) => {
        const reference = rubric.references[level];
        const checked = selected === level;
        return <button
          key={level}
          type="button"
          className={`severity-option ${checked ? "is-selected" : ""}`}
          role="radio"
          aria-checked={checked}
          onClick={() => setSelected(level)}
          disabled={busy}
        >
          <span className="severity-option-image">
            {reference?.image_asset ? <>
              <img src={reference.image_asset} alt={`${rubric.canonical_class}${LABELS[level]}参考图`} />
              {reference.image_type === "AI_ILLUSTRATION" ? <small className="severity-image-badge">{reference.fallback_label || "AI示意图 · 仅供辅助判断"}</small> : null}
            </> : <span role="img" aria-label={`${rubric.canonical_class}${LABELS[level]}参考图待补齐`}><span>图示待补齐</span><small>{reference?.fallback_label || "AI示意图"}</small></span>}
          </span>
          <span className="severity-option-copy"><strong>{LABELS[level]}</strong><span>{rubric.rubric[level]}</span></span>
          <span className="severity-option-state">{checked ? "已选择" : "选择"}</span>
        </button>;
      })}
      <button
        type="button"
        className={`severity-option severity-option-uncertain ${selected === "uncertain" ? "is-selected" : ""}`}
        role="radio"
        aria-checked={selected === "uncertain"}
        onClick={() => setSelected("uncertain")}
        disabled={busy}
      >
        <span className="severity-option-copy"><strong>{LABELS.uncertain}</strong><span>{rubric.rubric.uncertain}</span></span>
        <span className="severity-option-state">{selected === "uncertain" ? "已选择" : "选择"}</span>
      </button>
    </div>
    <button className="final-primary severity-confirm" type="button" disabled={busy || !selected} onClick={() => { if (selected) void onConfirm(selected); }}>
      {busy ? "正在保存…" : current ? "确认新的受害程度" : "确认受害程度并继续"}
    </button>
  </section>;
}
