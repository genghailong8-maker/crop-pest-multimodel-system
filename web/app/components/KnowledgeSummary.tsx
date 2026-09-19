import { KnowledgeDocument } from "../lib/api";

export default function KnowledgeSummary({ knowledge }: { knowledge: KnowledgeDocument | null }) {
  const unavailable = "<p>知识库暂时无法读取</p>";
  return <section className="v3-knowledge"><header><div><span>一般知识参考</span><h2>症状、特征和防治建议</h2></div><p>{knowledge?.source.attribution || "知识内容来自项目知识库，不作为本次病例证据。"}</p></header><div className="v3-knowledge-body">
    <section><h3>症状</h3><div className="v3-knowledge-prose" dangerouslySetInnerHTML={{ __html: knowledge?.symptoms_html ?? unavailable }} /></section>
    <section><h3>特征</h3><div className="v3-knowledge-prose" dangerouslySetInnerHTML={{ __html: knowledge?.features_html ?? unavailable }} /></section>
    <section><h3>防治建议</h3><div className="v3-knowledge-prose" dangerouslySetInnerHTML={{ __html: knowledge?.prevention_html ?? unavailable }} /></section>
  </div></section>;
}
