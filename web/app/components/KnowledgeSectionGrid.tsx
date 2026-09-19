import { KnowledgeSection } from "../lib/api";

export default function KnowledgeSectionGrid({ sections, fallbackHtml }: { sections?: KnowledgeSection[]; fallbackHtml?: string | null }) {
  if (!sections?.length) return <div className="knowledge-document" dangerouslySetInnerHTML={{ __html: fallbackHtml ?? "<p>知识库暂时无法读取</p>" }} />;
  return <div className="knowledge-section-grid">{sections.map((section) => <section className="knowledge-section-block" data-full-width={section.full_width || undefined} key={section.title}><div className="knowledge-document" dangerouslySetInnerHTML={{ __html: section.html }} /></section>)}</div>;
}
