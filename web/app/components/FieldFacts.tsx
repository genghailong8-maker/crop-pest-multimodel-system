import { CaseRecord, spreadSpeedLabel } from "../lib/api";

export default function FieldFacts({ record, compact = false }: { record: CaseRecord; compact?: boolean }) {
  return (
    <section className={`v3-field-facts ${compact ? "v3-field-facts-compact" : ""}`}>
      <header>
        <span>田间信息</span>
        <h2>采样记录</h2>
      </header>
      <dl>
        <div><dt>作物 / 识别对象</dt><dd>{record.crop}</dd></div>
        <div><dt>植物部位</dt><dd>{record.part}</dd></div>
        <div><dt>生长阶段</dt><dd>{record.growth_stage}</dd></div>
        <div><dt>种植环境</dt><dd>{record.environment?.scene || "未填写"}</dd></div>
        <div><dt>受害比例</dt><dd>{record.affected_ratio_percent == null ? "未填写" : `${record.affected_ratio_percent}%`}</dd></div>
        <div><dt>扩散速度</dt><dd>{spreadSpeedLabel(record.spread_speed)}</dd></div>
      </dl>
    </section>
  );
}
