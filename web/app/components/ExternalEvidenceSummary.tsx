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
  const treatmentResult = record.treatment;
  const treatment = treatmentResult?.content;
  const pesticideWarning = treatmentResult?.requires_pesticide_warning ? treatmentResult.pesticide_warning : null;
  const treatmentHtml = treatment?.prevention_html;
  const treatmentMarkdownHtml = treatment?.markdown_html;
  const showPesticideWarning = pesticideWarning && !treatmentHtml;
  const treatmentItems = [
    ...(treatment?.first_actions ?? []),
    ...(treatment?.prevention ?? []),
    ...Object.values(treatment?.management ?? {}).flat(),
  ].filter((item, index, all) => all.indexOf(item) === index).slice(0, 8);
  const treatmentMessage = treatmentResult?.status === "pending_alignment_update"
    ? "当前知识库暂缺足够可靠的该严重程度防治方案，本次不提供具体防治建议。"
    : treatmentResult?.reason === "treatment_context_needs_research"
      ? "当前知识库暂缺足够可靠的该严重程度防治方案，本次不提供具体防治建议。"
      : treatmentResult?.reason === "severity_uncertain"
        ? "受害程度尚未确定，请重新查看参考图和症状说明，选择最符合当前情况的程度。"
        : treatmentResult?.reason === "severity_not_selected"
          ? "请选择当前样本受害程度后再查看分级防治措施。"
          : "对应知识库内容暂时无法读取。";

  const harms = evidence?.status === "available" ? evidence.harms : [];
  const causes = evidence?.status === "available" ? evidence.possible_causes : [];
  const sourceCount = sources.length;
  const unavailable = !isConclusive(record) || !evidence || evidence.status !== "available";
  const unavailableMessage = sourceCount ? "已找到相关农业资料，但暂未提取到可直接支持的结论" : "暂未检索到可靠农业资料";
  const detailGroups = evidence?.status === "available" ? <div className="final-evidence-detail-groups"><ConclusionList title="危害" items={harms} sources={sources} /><ConclusionList title="可能诱因" items={causes} sources={sources} /></div> : null;

  return <section className={`final-evidence-summary final-evidence-${variant}`}>
    <div className="final-evidence-row final-evidence-harm"><div><h3>危害</h3><p>{harms[0]?.conclusion ?? (unavailable ? unavailableMessage : "暂未提取到可直接支持的结论")}</p></div></div>
    <div className="final-evidence-row final-evidence-cause"><div><h3>可能诱因</h3><p>{causes[0]?.conclusion ?? (unavailable ? (isConclusive(record) ? unavailableMessage : "当前证据不足，暂不推断可能诱因") : "暂未提取到可直接支持的结论")}</p></div></div>
    <div className="final-evidence-row final-evidence-treatment" data-source="local_knowledge_base"><div><div className="final-evidence-heading"><h3>防治措施</h3><span>本地知识库</span></div>{treatmentResult?.status && treatmentResult.status !== "available" ? <p>{treatmentMessage}</p> : treatmentMarkdownHtml ? <div className="knowledge-document treatment-document" data-treatment-tier={treatment?.tier || ""} dangerouslySetInnerHTML={{ __html: treatmentMarkdownHtml }} /> : treatmentHtml ? <div className="knowledge-document treatment-document" dangerouslySetInnerHTML={{ __html: treatmentHtml }} /> : treatmentItems.length ? <ul>{treatmentItems.slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ul> : <p>{treatmentMessage}</p>}{showPesticideWarning ? <p className="final-pesticide-warning">{pesticideWarning}</p> : null}</div></div>
    <div className="final-evidence-source-row"><strong>证据来源</strong><span>{sourceCount ? `${sourceCount} 条可靠农业资料` : "来源资料暂不可用"}</span>{sourceCount ? <details><summary>查看来源</summary>{detailGroups}<ul className="final-source-list">{sources.map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title}</a><span>{source.site_name} · 检索于 {source.retrieved_at}</span></li>)}</ul></details> : <small>本次识别不会使用模型自身知识补写危害或可能诱因。</small>}</div>
  </section>;
}
