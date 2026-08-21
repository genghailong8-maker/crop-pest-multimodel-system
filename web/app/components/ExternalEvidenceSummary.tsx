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

export default function ExternalEvidenceSummary({ record }: { record: CaseRecord }) {
  const evidence = record.evidence_analysis ?? record.analysis?.evidence_analysis;
  const sources = record.sources ?? record.analysis?.sources ?? [];
  const treatment = record.treatment?.content;
  const treatmentItems = [
    ...(treatment?.first_actions ?? []),
    ...(treatment?.prevention ?? []),
    ...Object.values(treatment?.management ?? {}).flat(),
  ].filter((item, index, all) => all.indexOf(item) === index).slice(0, 8);

  if (!isConclusive(record)) return <section className="public-external-evidence public-external-refusal"><header><span>外部资料增强</span><h2>危害与可能诱因</h2></header><p>当前病例尚未形成可靠结论，暂不展示外部资料整理结果。</p></section>;

  return <section className="public-external-evidence">
    <header><div><span>外部资料增强</span><h2>危害与可能诱因</h2></div><p>仅根据已核验的公开资料整理，不代表确定因果关系。</p></header>
    {!evidence || evidence.status !== "available" ? <div className="public-external-unavailable"><p>暂未检索到可靠资料</p><small>本次识别不会使用模型自身知识补写危害或可能诱因。</small></div> : <>
      <div className="public-external-grid">
        <ConclusionList title="危害" items={evidence.harms} sources={sources} />
        <ConclusionList title="可能诱因" items={evidence.possible_causes} sources={sources} />
      </div>
      {sources.length ? <div className="public-external-sources"><h3>参考来源</h3><ul>{sources.map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title}</a><span>{source.site_name} · 检索于 {source.retrieved_at}</span></li>)}</ul></div> : null}
    </>}
    <section className="public-treatment-summary" data-source="local_knowledge_base"><h3>防治措施</h3><p>来自本地审核知识库，不由外部搜索或多模态模型生成。</p>{treatmentItems.length ? <ul>{treatmentItems.map((item) => <li key={item}>{item}</li>)}</ul> : <span>对应知识库内容暂时无法读取。</span>}</section>
  </section>;
}
