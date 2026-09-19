# Severity V2 Rubric + Treatment Alignment — Design Only

## Decision

Severity V2 is a user-selected, backend-rubric-guided description of present injury on one selected plant organ or unit. It is not YOLO diagnosis, VLM output, field incidence, disease progress, yield-loss prediction, or a numeric score.

Allowed values: mild, moderate, severe, uncertain. Use uncertain when the stated assessment unit or decisive visual features are not visible. The complete machine-readable contract is severity-v2-rubrics.json.

## Frozen responsibility boundary

| Responsibility | Decision |
| --- | --- |
| Diagnosis | YOLO remains the sole authoritative diagnosis pathway. |
| VLM | Tentative crop_species and affected_part only; no severity. |
| Harms/causes/sources | Curated/Tavily remain responsible. |
| Treatment | Frozen Local Knowledge remains the treatment source. |
| Severity V2 | User chooses a four-state rubric with backend guidance. |

## Common protocol

1. User chooses the listed assessment unit.
2. Compare only directly visible features in that unit.
3. Select mild, moderate, severe, or uncertain.
4. Do not infer unshown tissue, other plants, field coverage, time course, cause, or yield.

Disease states use lesion burden: isolated -> multiple/localized coalescence -> continuous tissue failure. Pest states use direct injury: localized feeding -> repeated/localized deformation or tissue loss -> conspicuous functional loss. Pest counts and field thresholds are excluded.

## Legacy removal / preservation

- REMOVE/REPLACE: V1 composite 0.8 * affected_ratio + 0.2 * spread_speed and automatic low/medium/high selection.
- PRESERVE: YOLO diagnosis authority, Local Knowledge treatment text, Curated/Tavily boundaries, and historical V1 records.
- V2 does not use fixed environment as causality or severity evidence.

## 16-class coverage

| ID | Canonical class | Category | Assessment unit |
| --- | --- | --- | --- | --- |
| 0 | 玉米叶枯病 | disease | 一张清晰玉米叶片或一株可见叶片集合 |
| 1 | 番茄斑枯病 | disease | 一片叶、一个茎段或一个果实（用户选定） |
| 2 | 南瓜白粉病 | disease | 一片南瓜叶片 |
| 3 | 马铃薯早疫病 | disease | 一片叶、一个茎段或一个块茎表面 |
| 4 | 玉米锈病 | disease | 一片叶或一段叶鞘 |
| 5 | 番茄细菌性斑点病 | disease | 一片叶、一个茎或叶柄段或一个果实 |
| 6 | 番茄晚疫病 | disease | 一片叶、一个茎段或一个果实 |
| 7 | 马铃薯晚疫病 | disease | 一片叶、一个茎段或一个块茎表面 |
| 8 | 芫菁 | pest | 一片叶或一株可见冠层 |
| 9 | 蚜虫 | pest | 一片叶或一段嫩梢 |
| 10 | 盲蝽科 | pest | 一片嫩叶、一个芽或嫩梢或一个果实 |
| 11 | 蝼蛄 | pest | 一株幼苗及直接可见茎基或根际 |
| 12 | 叶蝉科 | pest | 一片叶或一段嫩梢 |
| 13 | 蝗总科 | pest | 一片叶或一株可见冠层 |
| 14 | 蛴螬 | pest | 一株植株及可见根系或茎基 |
| 15 | 豆芫菁 | pest | 一片叶、一个花序或一株可见冠层 |


Each JSON rubric contains only visual-rubric fields. It does not carry a treatment-alignment state.

Normative treatment alignment source: `severity-v2-treatment-alignment.tsv`.

## Acceptance snapshot

- 16/16 canonical classes; every record has a unit and all four states.
- No field ratio, spread rate, weighted score, VLM severity, or environmental causality appears in rubric logic.
- 48 treatment pairs are recorded in the normative `severity-v2-treatment-alignment.tsv`; summaries elsewhere are non-normative and this remains a design artifact, not a knowledge-content change.

## Future Severity V2 contract

Future persisted and response fields are design-only:

```json
{
  "severity_level": "mild | moderate | severe | uncertain",
  "severity_source": "user_guided_rubric",
  "severity_scope": "current_sample"
}
```

The V2 request does not ask for affected_ratio_percent or spread_speed. It does not calculate a numeric score or a weighted formula. YOLO diagnosis is not an input to a VLM severity decision, because VLM has no severity role.

### Uncertain behavior

- uncertain is never coerced to moderate, mild, or severe.
- uncertain does not fabricate a severity basis and does not select a tier treatment by default.
- future treatment payload for uncertain is `unavailable` for tier-specific treatment, with only an explicitly labeled general safety/observation message or a request for reassessment.
- this behavior preserves Local Knowledge ownership while preventing a visual ambiguity from becoming a treatment escalation.
