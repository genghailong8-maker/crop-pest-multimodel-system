import type { CoreKnowledge } from "../lib/api";

export default function CoreKnowledgeSummary({ knowledge }: { knowledge: CoreKnowledge }) {
  const fields = knowledge?.fields.filter((field) => field.rows?.some((row) => row.label.trim() && row.value.trim()) || field.html?.trim()) ?? [];
  if (!fields.length) return null;

  return <section className="final-core-knowledge" aria-labelledby="final-core-knowledge-title">
    <h2 id="final-core-knowledge-title">病虫害知识</h2>
    {knowledge?.title ? <h3 className="final-core-knowledge-name">{knowledge.title}</h3> : null}
    {fields.map((field) => <section className="final-core-knowledge-field" key={field.key}>
      <h3>{field.title}</h3>
      {field.rows?.length ? <div className="final-core-knowledge-table-wrap"><table><tbody>{field.rows.filter((row) => row.label.trim() && row.value.trim()).map((row) => <tr key={`${row.label}:${row.value}`}><th scope="row">{row.label}</th><td>{row.value}</td></tr>)}</tbody></table></div> : null}
      {field.html?.trim() ? <div className="knowledge-document" dangerouslySetInnerHTML={{ __html: field.html }} /> : null}
    </section>)}
  </section>;
}
