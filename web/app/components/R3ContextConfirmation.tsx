import type { DraftRecord, R3ContextPrediction, R3Taxonomy } from "../lib/api";

type Props = {
  draft: DraftRecord;
  taxonomy: R3Taxonomy;
  subjectType: "plant" | "insect";
  cropSpecies: string;
  affectedPart: string;
  insectSpecies: string;
  busy: boolean;
  onSubjectType: (value: "plant" | "insect") => void;
  onCropSpecies: (value: string) => void;
  onAffectedPart: (value: string) => void;
  onInsectSpecies: (value: string) => void;
  onConfirm: () => void;
};

function candidates(prediction: R3ContextPrediction | null | undefined, key: "subject_type" | "crop_species" | "affected_part" | "insect_species") {
  return prediction?.[key]?.candidates ?? [];
}

function CandidateHint({ draft, field }: { draft: DraftRecord; field: "subject_type" | "crop_species" | "affected_part" | "insect_species" }) {
  const values = candidates(draft.context_prediction, field);
  if (!values.length) return null;
  return <small className="r3-candidate-hint">AI候选：{values.map((item) => item.value).join("、")}</small>;
}

export default function R3ContextConfirmation(props: Props) {
  const { draft, taxonomy, subjectType, cropSpecies, affectedPart, insectSpecies, busy } = props;
  const available = draft.context_prediction?.status === "available";
  const missing = subjectType === "plant" ? !cropSpecies || !affectedPart : !insectSpecies;
  return <section className="r3-context-confirmation" aria-labelledby="r3-context-title">
    <header>
      <span className="final-assist-label">AI辅助识别</span>
      <h2 id="r3-context-title">请确认图片主体和上下文</h2>
      <p>{available ? "以下是基于图片的候选结果，最终以你的确认和修改为准。" : "主体识别服务暂不可用，你可以手动选择后继续。"}</p>
    </header>
    <div className="r3-context-fields">
      <label><span>图片主体</span><select value={subjectType} onChange={(event) => props.onSubjectType(event.target.value as "plant" | "insect")}>
        {taxonomy.subject_types.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
      </select><CandidateHint draft={draft} field="subject_type" /></label>
      {subjectType === "plant" ? <>
        <label><span>作物种类</span><select value={cropSpecies} onChange={(event) => props.onCropSpecies(event.target.value)}><option value="">请选择作物</option>{taxonomy.crops.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select><CandidateHint draft={draft} field="crop_species" /></label>
        <label><span>受影响部位</span><select value={affectedPart} onChange={(event) => props.onAffectedPart(event.target.value)}><option value="">请选择部位</option>{taxonomy.affected_parts.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select><CandidateHint draft={draft} field="affected_part" /></label>
      </> : <label><span>昆虫种类</span><select value={insectSpecies} onChange={(event) => props.onInsectSpecies(event.target.value)}><option value="">请选择昆虫</option>{taxonomy.insects.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select><CandidateHint draft={draft} field="insect_species" /></label>}
    </div>
    <button className="final-primary" type="button" disabled={busy || missing} onClick={props.onConfirm}>{busy ? "正在保存…" : "确认并继续"}</button>
  </section>;
}
