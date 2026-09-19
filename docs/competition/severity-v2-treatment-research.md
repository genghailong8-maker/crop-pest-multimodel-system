# B2-R treatment research closure

This is design evidence only. It changes no Local Knowledge treatment body and authorizes neither an implementation nor pesticide dose/frequency. The normative pair-level decision is solely `severity-v2-treatment-alignment.tsv`.

## Former NEEDS_RESEARCH — 13 pair outcomes

| Canonical class | Levels | Outcome | Exact remaining blocker |
| --- | --- | --- | --- |
| 玉米锈病 | 重度 | NEEDS_RESEARCH | Frozen text requires confirmed 南方锈病 and field-stage/economic context; canonical class and current-sample visual severity do not provide these. |
| 盲蝽科 | 轻度 / 中度 / 重度 | NEEDS_RESEARCH | Crop/species, bloom context, scouting and economic threshold are required; a generic family-level visual tier is insufficient. |
| 蝼蛄 | 轻度 / 中度 / 重度 | NEEDS_RESEARCH | Direct soil/root confirmation plus crop and field context are required for a belowground-pest action mapping. |
| 叶蝉科 | 轻度 / 中度 / 重度 | NEEDS_RESEARCH | Existing evidence is crop-specific (notably tea) while the canonical label is family-level; no generic action mapping is validated. |
| 蛴螬 | 轻度 / 中度 / 重度 | NEEDS_RESEARCH | Direct larva/root confirmation plus crop, life stage and field sampling context are required; aboveground symptoms alone are insufficient. |

## Research evidence

- University of Minnesota Extension, [White grubs](https://extension.umn.edu/agriculture/crop-production/corn/white-grubs): root feeding, soil sampling, crop/life-stage dependence and no labeled rescue treatment for economic corn infestations.
- University of Minnesota Extension, [Tarnished plant bug in strawberries](https://blog-fruit-vegetable-ipm.extension.umn.edu/2022/06/how-to-control-tarnished-plant-bug.html): crop-specific scouting, threshold and label/pollinator constraints.

## Former ADJUST — 27 implementation-ready specifications

All former ADJUST pairs are `READY_ADJUST` in the normative TSV. For each row: retain frozen wording; require explicit user V2 confirmation and current target-crop registration/label validation before optional guidance. Severe rows additionally require confirmation before any field-scale, production-value, harvest or regional-control text. No automatic tier selection, knowledge-body edit, dose/frequency generation or historical-record conversion is authorized.

## Final states

- READY_KEEP: 8
- READY_ADJUST: 27
- NEEDS_RESEARCH: 13
