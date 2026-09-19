import type { CaseRecord, GroundedEvidence, KnowledgeDocument } from "../lib/api";
import { spreadSpeedLabel } from "../lib/api";

type EvidenceRailProps = {
  record: CaseRecord;
  knowledge?: KnowledgeDocument | null;
};

const sourceLabels: Record<GroundedEvidence["source"], string> = {
  image: "图片观察",
  yolo: "目标定位",
  field_input: "田间信息",
};

function groundedEvidence(record: CaseRecord, source: GroundedEvidence["source"]) {
  const grounded = record.analysis?.grounded_assessment;
  if (!grounded) return [];
  return [...grounded.harms, ...grounded.causes].flatMap((item) => item.evidence.filter((evidence) => evidence.source === source));
}

function uniqueEvidence(items: GroundedEvidence[]) {
  return items.filter((item, index, list) => list.findIndex((candidate) => candidate.observation === item.observation) === index);
}

export default function EvidenceRail({ record, knowledge }: EvidenceRailProps) {
  const imageItems = uniqueEvidence(groundedEvidence(record, "image"));
  const yoloItems = uniqueEvidence(groundedEvidence(record, "yolo"));
  const fieldItems = uniqueEvidence(groundedEvidence(record, "field_input"));
  const detections = record.detections ?? [];
  const fieldFacts = [
    `对象：${record.crop}`,
    `部位：${record.part}`,
    `环境：${record.environment?.scene || "未填写"}`,
    `受害比例：${record.affected_ratio_percent == null ? "未填写" : `${record.affected_ratio_percent}%`}`,
    `扩散速度：${spreadSpeedLabel(record.spread_speed)}`,
  ];

  return (
    <aside className="workspace-v4-evidence-rail" aria-label="证据与来源">
      <header className="workspace-v4-rail-heading"><span className="workspace-v4-eyebrow">证据与来源</span><h2>本次诊断依据</h2></header>

      <section className="workspace-v4-evidence-group">
        <h3><span className="workspace-v4-source-mark" aria-hidden="true">图</span>图片观察</h3>
        {imageItems.length ? <ul>{imageItems.map((item, index) => <li key={`${item.observation}-${index}`}>{item.observation}</li>)}</ul> : <p className="workspace-v4-muted">当前分析没有形成可单独引用的图片观察。</p>}
      </section>

      <section className="workspace-v4-evidence-group">
        <h3><span className="workspace-v4-source-mark" aria-hidden="true">定</span>目标定位</h3>
        {detections.length ? <ul>{detections.map((item, index) => <li key={`${item.class_id}-${index}`}><strong>{item.class_name}</strong><span>位置 {Math.round(item.bbox[0] * 100)}% / {Math.round(item.bbox[1] * 100)}%，置信度 {Math.round(item.confidence * 100)}%</span></li>)}</ul> : <p className="workspace-v4-muted">未定位到明确区域。</p>}
        {yoloItems.length > 0 && <div className="workspace-v4-evidence-detail"><b>{sourceLabels.yolo}</b>{yoloItems.map((item, index) => <span key={`${item.observation}-${index}`}>{item.observation}</span>)}</div>}
      </section>

      <section className="workspace-v4-evidence-group">
        <h3><span className="workspace-v4-source-mark" aria-hidden="true">田</span>田间信息</h3>
        <ul>{fieldFacts.map((item) => <li key={item}>{item}</li>)}</ul>
        {fieldItems.length > 0 && <div className="workspace-v4-evidence-detail"><b>{sourceLabels.field_input}</b>{fieldItems.map((item, index) => <span key={`${item.observation}-${index}`}>{item.observation}</span>)}</div>}
      </section>

      {knowledge && <section className="workspace-v4-evidence-group workspace-v4-knowledge-source">
        <h3><span className="workspace-v4-source-mark" aria-hidden="true">知</span>知识参考</h3>
        <p><strong>{knowledge.title}</strong></p>
        <span>{knowledge.source.attribution}</span>
      </section>}
    </aside>
  );
}
