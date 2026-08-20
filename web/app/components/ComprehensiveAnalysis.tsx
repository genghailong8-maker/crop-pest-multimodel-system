import { CaseRecord, GroundedConclusion, isConclusive } from "../lib/api";

const sourceLabels = {
  image: "图片观察",
  yolo: "目标定位",
  field_input: "田间信息",
} as const;

function meaningful(items: GroundedConclusion[]) {
  return items.some((item) => item.conclusion !== "无法判断");
}

export function ComprehensiveAnalysisContent({ record }: { record: CaseRecord }) {
  const grounded = record.analysis?.grounded_assessment;
  const hasGroundedConclusion = grounded && (meaningful(grounded.harms) || meaningful(grounded.causes));

  if (!isConclusive(record) || (grounded && !hasGroundedConclusion)) {
    return <div className="v3-grounded-refusal"><strong>暂不展示综合分析</strong><p>当前图片或田间证据不足，系统不会把未证实的危害或诱因写成肯定结论。</p></div>;
  }

  if (!grounded) {
    const harms = record.analysis?.harm ?? [];
    const causes = record.analysis?.possible_causes ?? [];
    return <div className="v3-evidence-ledger legacy-grounded">
      <section><h3>可能危害</h3>{harms.length ? <ul>{harms.map((item) => <li key={item}>{item}</li>)}</ul> : <p>历史记录未提供</p>}</section>
      <section><h3>可能诱因</h3>{causes.length ? <ul>{causes.map((item) => <li key={item}>{item}</li>)}</ul> : <p>历史记录未提供</p>}</section>
      <aside><h3>证据说明</h3><p>该病例采用旧版分析协议，未提供逐条关联依据；旧的公共依据不会冒充本次证据。</p></aside>
    </div>;
  }

  const evidenceGroups = [
    ...grounded.harms.map((item, index) => ({ ...item, relation: `支持危害 ${index + 1}` })),
    ...grounded.causes.map((item, index) => ({ ...item, relation: `支持诱因 ${index + 1}` })),
  ];
  return <div className="v3-evidence-ledger">
    <div className="v3-assessment-columns">
      <section><h3>可能危害</h3><ol>{grounded.harms.map((item, index) => <li key={`${item.conclusion}-${index}`}>{item.conclusion}</li>)}</ol></section>
      <section><h3>可能诱因</h3><ol>{grounded.causes.map((item, index) => <li key={`${item.conclusion}-${index}`}>{item.conclusion}</li>)}</ol></section>
    </div>
    <aside className="v3-evidence-rail"><h3>结论依据</h3>{evidenceGroups.map((item, index) => <div key={`${item.relation}-${item.conclusion}-${index}`}><strong>{item.relation}</strong><p>{item.conclusion}</p><ul>{item.evidence.map((evidence, evidenceIndex) => <li key={`${evidence.reference}-${evidenceIndex}`}><b className={`v3-evidence-source v3-source-${evidence.source}`}><span aria-hidden="true" />{sourceLabels[evidence.source]}</b><span>{evidence.observation}</span></li>)}</ul></div>)}</aside>
  </div>;
}

export default function ComprehensiveAnalysis({ record }: { record: CaseRecord }) {
  return <section className="v3-analysis-section"><header className="v3-section-heading"><div><span>本次病例证据</span><h2>为什么形成这个结论</h2></div><p><b className="v3-evidence-source v3-source-synthesis"><span aria-hidden="true" />综合核对</b>只使用本次图片、目标定位结果和田间信息。</p></header><ComprehensiveAnalysisContent record={record} /></section>;
}
