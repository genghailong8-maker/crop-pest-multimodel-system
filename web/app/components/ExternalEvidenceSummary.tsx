import { CaseRecord, EvidenceConclusion, EvidenceSource, isConclusive } from "../lib/api";

function linkedSources(item: EvidenceConclusion, sources: EvidenceSource[]) {
  return sources.filter((source) => item.source_ids.includes(source.id));
}

function ConclusionList({
  title,
  items,
  sources,
}: {
  title: string;
  items: EvidenceConclusion[];
  sources: EvidenceSource[];
}) {
  return <section className="public-external-group">
    <h3>{title}</h3>
    {items.length ? <ol>{items.map((item, index) => <li key={`${item.conclusion}-${index}`}>
      <strong>{item.conclusion}</strong>
      <div className="public-source-links">{linkedSources(item, sources).map((source) => <a key={source.id} href={source.url} target="_blank" rel="noopener noreferrer">{source.site_name} · {source.title}</a>)}</div>
    </li>)}</ol> : <p>暂未检索到可靠资料</p>}
  </section>;
}

export default function ExternalEvidenceSummary({ record, variant = "summary" }: { record: CaseRecord; variant?: "summary" | "report" }) {
  const evidence = record.evidence_analysis ?? record.analysis?.evidence_analysis;
  const sources = record.sources ?? record.analysis?.sources ?? [];
  const treatment = record.treatment?.content;
  const pesticideWarning = record.treatment?.requires_pesticide_warning ? record.treatment.pesticide_warning : null;
  const treatmentItems = [
    ...(treatment?.first_actions ?? []),
    ...(treatment?.prevention ?? []),
    ...Object.values(treatment?.management ?? {}).flat(),
  ].filter((item, index, all) => all.indexOf(item) === index).slice(0, 8);

  const harms = evidence?.status === "available" ? evidence.harms : [];
  const causes = evidence?.status === "available" ? evidence.possible_causes : [];
  const sourceCount = sources.length;
  const unavailable = !isConclusive(record) || !evidence || evidence.status !== "available";
  const detailGroups = evidence?.status === "available" ? <div className="final-evidence-detail-groups"><ConclusionList title="危害" items={harms} sources={sources} /><ConclusionList title="可能诱因" items={causes} sources={sources} /></div> : null;

  return <section className={`final-evidence-summary final-evidence-${variant}`}>
    <div className="final-evidence-row final-evidence-harm"><div><h3>危害</h3><p>{harms[0]?.conclusion ?? "暂未检索到可靠资料"}</p></div></div>
    <div className="final-evidence-row final-evidence-cause"><div><h3>可能诱因</h3><p>{causes[0]?.conclusion ?? (unavailable ? "当前证据不足，暂不推断可能诱因" : "暂未检索到可靠资料")}</p></div></div>
    <div className="final-evidence-row final-evidence-treatment" data-source="local_knowledge_base"><div><div className="final-evidence-heading"><h3>防治措施</h3><span>本地知识库</span></div>{treatmentItems.length ? <ul>{treatmentItems.slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ul> : <p>对应知识库内容暂时无法读取。</p>}{pesticideWarning ? <p className="final-pesticide-warning">{pesticideWarning}</p> : null}</div></div>
    <div className="final-evidence-source-row"><strong>证据来源</strong><span>{sourceCount ? `${sourceCount} 条可靠农业资料` : "来源资料暂不可用"}</span>{sourceCount ? <details><summary>查看来源</summary>{detailGroups}<ul className="final-source-list">{sources.map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title}</a><span>{source.site_name} · 检索于 {source.retrieved_at}</span></li>)}</ul></details> : <small>本次识别不会使用模型自身知识补写危害或可能诱因。</small>}</div>
  </section>;
}
