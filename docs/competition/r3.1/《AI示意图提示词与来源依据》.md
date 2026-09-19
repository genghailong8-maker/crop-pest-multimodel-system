# 《AI示意图提示词与来源依据》

**文档性质**：R3.1 正式 Prompt provenance 与生成门禁文档。它不是农业事实来源，也不是诊断证据；本批不生成最终图片。

## Provenance chain

每条正式候选必须遵循：`agricultural source → severity rubric → observable features → image prompt`。Prompt 根据正式农业资料支持的症状特征整理形成，不声称原始资料采用本项目三级分级；Prompt 本身不是农业事实来源。

## Prompt evidence gate

`PROMPT_EVIDENCE_STATUS` 允许值：`TRACEABLE`、`NEEDS_EVIDENCE`、`REJECTED`。当前只有 `severity-evidence.json` 三档均为 `COMPLETE` 且 capability `severity_available=true` 的 39 个 insect × host × severity 单元可列为 `TRACEABLE` 候选；其余 75 个继续 `NEEDS_EVIDENCE`，不得进入后续生成。用户完成知识审核、来源仍可追溯、图像安全复核通过后才可另行进入 Batch 4。

## 统一禁止项与免责声明

- 不添加来源没有支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量结论或其他阈值。
- 不生成文字、UI、箭头、测量数字、农药包装、施药指令、诊断结论，或把传播相关病害画成当前病例已确诊。
- 每张图必须带或邻接展示：**AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。**

## 正式候选逐项记录

### 芫菁 × 大豆 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Epicauta funebris; Epicauta vittata
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-08-NCSU-SOY", "evidence_taxon": "Epicauta funebris; Epicauta vittata", "evidence_taxon_level": "species", "scope_note": "NCSU 大豆资料涉及这两个来源物种；不是中国豆芫菁 Epicauta gorhami 的种级证据。"}]
- insect：芫菁
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：早期或局部取食，叶片出现局部缺刻或有限脱叶，整体冠层仍连续。
- severity source IDs：`R31-08-NCSU-SOY`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-08-NCSU-SOY | Blister Beetle in Soybean | North Carolina State University Extension | https://content.ces.ncsu.edu/bilster-beetle-in-soybean | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 叶片局部缺刻 | `R31-08-NCSU-SOY` |
| 有限脱叶 | `R31-08-NCSU-SOY` |

#### Final image-generation prompt

> 农业科学示意图：展示芫菁在大豆上的轻度受害状态；仅呈现以下来源支持的可观察特征：叶片局部缺刻、有限脱叶。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-08-NCSU-SOY` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 芫菁 × 大豆 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：芫菁（来源命名组）; Epicauta funebris; Epicauta vittata
- evidence_taxon_level：source_named_group; species
- evidence_taxon_scope：[{"source_id": "R31-08-NCSU-SOY", "evidence_taxon": "Epicauta funebris; Epicauta vittata", "evidence_taxon_level": "species", "scope_note": "NCSU 大豆资料涉及这两个来源物种；不是中国豆芫菁 Epicauta gorhami 的种级证据。"}]
- insect：芫菁
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：成虫出现群集，冠层脱叶已清楚可见，但尚未出现来源所述的快速失叶场景。
- severity source IDs：`R31-08-NCSU-SOY`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-08-NCSU-SOY | Blister Beetle in Soybean | North Carolina State University Extension | https://content.ces.ncsu.edu/bilster-beetle-in-soybean | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 成虫群集 | `R31-08-NCSU-SOY` |
| 冠层脱叶清楚可见 | `R31-08-NCSU-SOY` |

#### Final image-generation prompt

> 农业科学示意图：展示芫菁在大豆上的中度受害状态；仅呈现以下来源支持的可观察特征：成虫群集、冠层脱叶清楚可见。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-08-NCSU-SOY` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 芫菁 × 大豆 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Epicauta funebris; Epicauta vittata
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-08-NCSU-SOY", "evidence_taxon": "Epicauta funebris; Epicauta vittata", "evidence_taxon_level": "species", "scope_note": "NCSU 大豆资料涉及这两个来源物种；不是中国豆芫菁 Epicauta gorhami 的种级证据。"}]
- insect：芫菁
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：群集取食造成快速脱叶，冠层叶量明显下降。
- severity source IDs：`R31-08-NCSU-SOY`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-08-NCSU-SOY | Blister Beetle in Soybean | North Carolina State University Extension | https://content.ces.ncsu.edu/bilster-beetle-in-soybean | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 群集取食 | `R31-08-NCSU-SOY` |
| 快速脱叶 | `R31-08-NCSU-SOY` |
| 冠层叶量明显下降 | `R31-08-NCSU-SOY` |

#### Final image-generation prompt

> 农业科学示意图：展示芫菁在大豆上的重度受害状态；仅呈现以下来源支持的可观察特征：群集取食、快速脱叶、冠层叶量明显下降。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-08-NCSU-SOY` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 大豆 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Aphis glycines; Acyrthosiphon solani
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-HEILONGJIANG-SOY", "evidence_taxon": "Aphis glycines; Acyrthosiphon solani", "evidence_taxon_level": "species", "scope_note": "黑龙江官方资料明确列出大豆蚜和苜蓿蚜；不外推为所有蚜虫。"}]
- insect：蚜虫
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：顶叶、嫩叶或嫩茎出现局部蚜群和不规则黄斑，叶片尚未普遍卷曲变黄。
- severity source IDs：`R31-09-HEILONGJIANG-SOY`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-HEILONGJIANG-SOY | 大豆蚜虫识别与防治技术 | 黑龙江省农业农村厅／全国农技中心体系 | https://nynct.hlj.gov.cn/nynct/c115393/202608/c00_31966422.shtml | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 顶叶/嫩叶/嫩茎局部蚜群 | `R31-09-HEILONGJIANG-SOY` |
| 不规则黄斑 | `R31-09-HEILONGJIANG-SOY` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在大豆上的轻度受害状态；仅呈现以下来源支持的可观察特征：顶叶/嫩叶/嫩茎局部蚜群、不规则黄斑。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-HEILONGJIANG-SOY` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 大豆 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Aphis glycines; Acyrthosiphon solani
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-HEILONGJIANG-SOY", "evidence_taxon": "Aphis glycines; Acyrthosiphon solani", "evidence_taxon_level": "species", "scope_note": "黑龙江官方资料明确列出大豆蚜和苜蓿蚜；不外推为所有蚜虫。"}]
- insect：蚜虫
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：黄斑扩大并转褐，蜜露或煤污在受害部位可见，卷曲开始在多处出现。
- severity source IDs：`R31-09-HEILONGJIANG-SOY`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-HEILONGJIANG-SOY | 大豆蚜虫识别与防治技术 | 黑龙江省农业农村厅／全国农技中心体系 | https://nynct.hlj.gov.cn/nynct/c115393/202608/c00_31966422.shtml | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 黄斑扩大并转褐 | `R31-09-HEILONGJIANG-SOY` |
| 蜜露/煤污 | `R31-09-HEILONGJIANG-SOY` |
| 多处卷曲 | `R31-09-HEILONGJIANG-SOY` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在大豆上的中度受害状态；仅呈现以下来源支持的可观察特征：黄斑扩大并转褐、蜜露/煤污、多处卷曲。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-HEILONGJIANG-SOY` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 大豆 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Aphis glycines; Acyrthosiphon solani
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-HEILONGJIANG-SOY", "evidence_taxon": "Aphis glycines; Acyrthosiphon solani", "evidence_taxon_level": "species", "scope_note": "黑龙江官方资料明确列出大豆蚜和苜蓿蚜；不外推为所有蚜虫。"}]
- insect：蚜虫
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：叶片卷曲变黄，植株矮小，分枝和结荚数减少，或豆粒粒重受到影响。
- severity source IDs：`R31-09-HEILONGJIANG-SOY`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-HEILONGJIANG-SOY | 大豆蚜虫识别与防治技术 | 黑龙江省农业农村厅／全国农技中心体系 | https://nynct.hlj.gov.cn/nynct/c115393/202608/c00_31966422.shtml | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 叶片卷曲变黄 | `R31-09-HEILONGJIANG-SOY` |
| 植株矮小 | `R31-09-HEILONGJIANG-SOY` |
| 分枝/结荚数减少 | `R31-09-HEILONGJIANG-SOY` |
| 豆粒粒重受影响 | `R31-09-HEILONGJIANG-SOY` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在大豆上的重度受害状态；仅呈现以下来源支持的可观察特征：叶片卷曲变黄、植株矮小、分枝/结荚数减少、豆粒粒重受影响。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-HEILONGJIANG-SOY` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 小麦 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Schizaphis graminum
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-KSTATE-GREENBUG-WHEAT", "evidence_taxon": "Schizaphis graminum", "evidence_taxon_level": "species", "geographic_scope": "United States, Kansas/High Plains", "crop_scope": "wheat", "scope_note": "同一物种绿虫蚜在小麦上的斑点合并、黄化、红褐化、叶片死亡和田间斑块扩展；不外推为所有蚜虫。"}, {"source_id": "R31-09-OSU-GREENBUG-WHEAT", "evidence_taxon": "Schizaphis graminum", "evidence_taxon_level": "species", "geographic_scope": "United States, Oklahoma/southern Great Plains", "crop_scope": "winter wheat", "scope_note": "同一物种绿虫蚜在冬小麦上的早期斑点与重发坏死、矮化、死苗、分蘖减少和死株斑块；不外推为所有蚜虫。"}]
- insect：蚜虫
- host：小麦（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：小麦叶片先出现细小的红色或铜色斑点，取食点周围可见黄化。
- severity source IDs：`R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-KSTATE-GREENBUG-WHEAT | Greenbug — wheat crop protection | Kansas State University Research and Extension | https://entomology.k-state.edu/extension/crop-protection/wheat/greenbug.html | 2026-09-07 |
| R31-09-OSU-GREENBUG-WHEAT | Check Your Wheat: Greenbugs Reported in Central Oklahoma | Oklahoma State University Extension | https://extension.okstate.edu/e-pest-alerts/2026/check-your-wheat-greenbugs-reported-in-central-oklahoma | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 细小红色或铜色斑点 | `R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT` |
| 取食点周围黄化 | `R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在小麦上的轻度受害状态；仅呈现以下来源支持的可观察特征：细小红色或铜色斑点、取食点周围黄化。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-KSTATE-GREENBUG-WHEAT, R31-09-OSU-GREENBUG-WHEAT` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 小麦 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Schizaphis graminum
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-KSTATE-GREENBUG-WHEAT", "evidence_taxon": "Schizaphis graminum", "evidence_taxon_level": "species", "geographic_scope": "United States, Kansas/High Plains", "crop_scope": "wheat", "scope_note": "同一物种绿虫蚜在小麦上的斑点合并、黄化、红褐化、叶片死亡和田间斑块扩展；不外推为所有蚜虫。"}, {"source_id": "R31-09-OSU-GREENBUG-WHEAT", "evidence_taxon": "Schizaphis graminum", "evidence_taxon_level": "species", "geographic_scope": "United States, Oklahoma/southern Great Plains", "crop_scope": "winter wheat", "scope_note": "同一物种绿虫蚜在冬小麦上的早期斑点与重发坏死、矮化、死苗、分蘖减少和死株斑块；不外推为所有蚜虫。"}]
- insect：蚜虫
- host：小麦（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：斑点逐渐合并，受害叶片转黄，田间出现并扩展的黄色或红褐色受害斑块。
- severity source IDs：`R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-KSTATE-GREENBUG-WHEAT | Greenbug — wheat crop protection | Kansas State University Research and Extension | https://entomology.k-state.edu/extension/crop-protection/wheat/greenbug.html | 2026-09-07 |
| R31-09-OSU-GREENBUG-WHEAT | Check Your Wheat: Greenbugs Reported in Central Oklahoma | Oklahoma State University Extension | https://extension.okstate.edu/e-pest-alerts/2026/check-your-wheat-greenbugs-reported-in-central-oklahoma | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 斑点逐渐合并 | `R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT` |
| 受害叶片转黄 | `R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT` |
| 黄色或红褐色田间斑块扩展 | `R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在小麦上的中度受害状态；仅呈现以下来源支持的可观察特征：斑点逐渐合并、受害叶片转黄、黄色或红褐色田间斑块扩展。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-KSTATE-GREENBUG-WHEAT, R31-09-OSU-GREENBUG-WHEAT` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 小麦 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Schizaphis graminum
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-KSTATE-GREENBUG-WHEAT", "evidence_taxon": "Schizaphis graminum", "evidence_taxon_level": "species", "geographic_scope": "United States, Kansas/High Plains", "crop_scope": "wheat", "scope_note": "同一物种绿虫蚜在小麦上的斑点合并、黄化、红褐化、叶片死亡和田间斑块扩展；不外推为所有蚜虫。"}, {"source_id": "R31-09-OSU-GREENBUG-WHEAT", "evidence_taxon": "Schizaphis graminum", "evidence_taxon_level": "species", "geographic_scope": "United States, Oklahoma/southern Great Plains", "crop_scope": "winter wheat", "scope_note": "同一物种绿虫蚜在冬小麦上的早期斑点与重发坏死、矮化、死苗、分蘖减少和死株斑块；不外推为所有蚜虫。"}]
- insect：蚜虫
- host：小麦（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：叶片组织变为红褐色并死亡，植株可明显矮化；重发生时出现死苗、分蘖减少和扩展的死株斑块。
- severity source IDs：`R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-KSTATE-GREENBUG-WHEAT | Greenbug — wheat crop protection | Kansas State University Research and Extension | https://entomology.k-state.edu/extension/crop-protection/wheat/greenbug.html | 2026-09-07 |
| R31-09-OSU-GREENBUG-WHEAT | Check Your Wheat: Greenbugs Reported in Central Oklahoma | Oklahoma State University Extension | https://extension.okstate.edu/e-pest-alerts/2026/check-your-wheat-greenbugs-reported-in-central-oklahoma | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 红褐色坏死叶片 | `R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT` |
| 植株矮化 | `R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT` |
| 死苗 | `R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT` |
| 分蘖减少 | `R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT` |
| 死株斑块扩展 | `R31-09-KSTATE-GREENBUG-WHEAT`, `R31-09-OSU-GREENBUG-WHEAT` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在小麦上的重度受害状态；仅呈现以下来源支持的可观察特征：红褐色坏死叶片、植株矮化、死苗、分蘖减少、死株斑块扩展。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-KSTATE-GREENBUG-WHEAT, R31-09-OSU-GREENBUG-WHEAT` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 桃 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Myzus persicae
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-VT-PEACH-GPA", "evidence_taxon": "Myzus persicae", "evidence_taxon_level": "species", "scope_note": "来源明确对应桃蚜 Myzus persicae；不得扩展为所有蚜虫种类的桃树表现。"}]
- insect：蚜虫
- host：桃（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：嫩梢或幼叶出现蚜虫取食，叶片开始卷曲或变形。
- severity source IDs：`R31-09-VT-PEACH-GPA`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-VT-PEACH-GPA | Green Peach Aphid | Virginia Tech Extension | https://www.virginiafruit.ento.vt.edu/GPA.html | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 嫩梢/幼叶取食 | `R31-09-VT-PEACH-GPA` |
| 叶片卷曲或变形 | `R31-09-VT-PEACH-GPA` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在桃上的轻度受害状态；仅呈现以下来源支持的可观察特征：嫩梢/幼叶取食、叶片卷曲或变形。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-VT-PEACH-GPA` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 桃 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Myzus persicae
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-VT-PEACH-GPA", "evidence_taxon": "Myzus persicae", "evidence_taxon_level": "species", "scope_note": "来源明确对应桃蚜 Myzus persicae；不得扩展为所有蚜虫种类的桃树表现。"}]
- insect：蚜虫
- host：桃（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：叶片出现明显卷曲、变形和黄化，并见蜜露或煤污。
- severity source IDs：`R31-09-VT-PEACH-GPA`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-VT-PEACH-GPA | Green Peach Aphid | Virginia Tech Extension | https://www.virginiafruit.ento.vt.edu/GPA.html | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 叶片卷曲 | `R31-09-VT-PEACH-GPA` |
| 叶片变形 | `R31-09-VT-PEACH-GPA` |
| 叶片黄化 | `R31-09-VT-PEACH-GPA` |
| 蜜露 | `R31-09-VT-PEACH-GPA` |
| 煤污 | `R31-09-VT-PEACH-GPA` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在桃上的中度受害状态；仅呈现以下来源支持的可观察特征：叶片卷曲、叶片变形、叶片黄化、蜜露、煤污。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-VT-PEACH-GPA` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 桃 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Myzus persicae
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-VT-PEACH-GPA", "evidence_taxon": "Myzus persicae", "evidence_taxon_level": "species", "scope_note": "来源明确对应桃蚜 Myzus persicae；不得扩展为所有蚜虫种类的桃树表现。"}]
- insect：蚜虫
- host：桃（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：伴随新梢生长受抑、叶片早落，花或果实出现变形或脱落。
- severity source IDs：`R31-09-VT-PEACH-GPA`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-VT-PEACH-GPA | Green Peach Aphid | Virginia Tech Extension | https://www.virginiafruit.ento.vt.edu/GPA.html | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 新梢生长受抑 | `R31-09-VT-PEACH-GPA` |
| 叶片早落 | `R31-09-VT-PEACH-GPA` |
| 花或果实变形 | `R31-09-VT-PEACH-GPA` |
| 花或果实脱落 | `R31-09-VT-PEACH-GPA` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在桃上的重度受害状态；仅呈现以下来源支持的可观察特征：新梢生长受抑、叶片早落、花或果实变形、花或果实脱落。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-VT-PEACH-GPA` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 棉花 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Aphis gossypii
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-UC-COTTON-APHID", "evidence_taxon": "Aphis gossypii", "evidence_taxon_level": "species", "scope_note": "来源明确对应棉蚜 Aphis gossypii；不得扩展为所有蚜虫种类的棉花表现。"}]
- insect：蚜虫
- host：棉花（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：棉花叶片出现皱缩或杯状卷曲，并可见蜜露污染。
- severity source IDs：`R31-09-UC-COTTON-APHID`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-UC-COTTON-APHID | Cotton aphid | UC Statewide Integrated Pest Management Program | https://ipm.ucanr.edu/agriculture/cotton/cotton-aphid/ | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 叶片皱缩 | `R31-09-UC-COTTON-APHID` |
| 杯状卷曲 | `R31-09-UC-COTTON-APHID` |
| 蜜露污染 | `R31-09-UC-COTTON-APHID` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在棉花上的轻度受害状态；仅呈现以下来源支持的可观察特征：叶片皱缩、杯状卷曲、蜜露污染。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-UC-COTTON-APHID` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 棉花 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Aphis gossypii
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-UC-COTTON-APHID", "evidence_taxon": "Aphis gossypii", "evidence_taxon_level": "species", "scope_note": "来源明确对应棉蚜 Aphis gossypii；不得扩展为所有蚜虫种类的棉花表现。"}]
- insect：蚜虫
- host：棉花（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：叶片不能正常展开，皱缩/杯状卷曲加重，并伴随蜜露或煤污；植株生长受到抑制。
- severity source IDs：`R31-09-UC-COTTON-APHID`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-UC-COTTON-APHID | Cotton aphid | UC Statewide Integrated Pest Management Program | https://ipm.ucanr.edu/agriculture/cotton/cotton-aphid/ | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 叶片不能展开 | `R31-09-UC-COTTON-APHID` |
| 皱缩或杯状卷曲 | `R31-09-UC-COTTON-APHID` |
| 蜜露 | `R31-09-UC-COTTON-APHID` |
| 煤污 | `R31-09-UC-COTTON-APHID` |
| 生长受抑 | `R31-09-UC-COTTON-APHID` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在棉花上的中度受害状态；仅呈现以下来源支持的可观察特征：叶片不能展开、皱缩或杯状卷曲、蜜露、煤污、生长受抑。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-UC-COTTON-APHID` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 棉花 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Aphis gossypii
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-09-UC-COTTON-APHID", "evidence_taxon": "Aphis gossypii", "evidence_taxon_level": "species", "scope_note": "来源明确对应棉蚜 Aphis gossypii；不得扩展为所有蚜虫种类的棉花表现。"}]
- insect：蚜虫
- host：棉花（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：出现脱叶或严重幼苗矮化，并可见棉铃受害相关的生长/发育影响。
- severity source IDs：`R31-09-UC-COTTON-APHID`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-UC-COTTON-APHID | Cotton aphid | UC Statewide Integrated Pest Management Program | https://ipm.ucanr.edu/agriculture/cotton/cotton-aphid/ | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 脱叶 | `R31-09-UC-COTTON-APHID` |
| 严重幼苗矮化 | `R31-09-UC-COTTON-APHID` |
| 棉铃受害相关影响 | `R31-09-UC-COTTON-APHID` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在棉花上的重度受害状态；仅呈现以下来源支持的可观察特征：脱叶、严重幼苗矮化、棉铃受害相关影响。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-UC-COTTON-APHID` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 玉米 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：corn aphid complex (source-named group)
- evidence_taxon_level：source_named_group
- evidence_taxon_scope：[{"source_id": "R31-09-PURDUE-CORN", "evidence_taxon": "corn aphid complex (source-named group)", "evidence_taxon_level": "source_named_group", "scope_note": "来源讨论玉米上的蚜虫类群及其受害表现；本记录只覆盖这些来源命名的玉米蚜虫组，不外推为所有蚜虫种类。"}, {"source_id": "R31-09-UMN-CORN", "evidence_taxon": "corn aphid complex (source-named group)", "evidence_taxon_level": "source_named_group", "scope_note": "来源讨论玉米上的蚜虫类群及其受害表现；本记录只覆盖这些来源命名的玉米蚜虫组，不外推为所有蚜虫种类。"}]
- insect：蚜虫
- host：玉米（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：玉米叶片可见蚜虫取食相关的小片变色区域或蜜露污染。
- severity source IDs：`R31-09-PURDUE-CORN`, `R31-09-UMN-CORN`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-PURDUE-CORN | Aphids in Corn | Purdue University Extension | https://ag.purdue.edu/department/entm/extension/field-crops-ipm/corn/aphids.html | 2026-09-07 |
| R31-09-UMN-CORN | Aphids in corn (post-pollination) | University of Minnesota Extension | https://extension.umn.edu/corn-pest-management/aphids-corn-post-pollination | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 小片变色区域 | `R31-09-PURDUE-CORN`, `R31-09-UMN-CORN` |
| 蜜露污染 | `R31-09-PURDUE-CORN`, `R31-09-UMN-CORN` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在玉米上的轻度受害状态；仅呈现以下来源支持的可观察特征：小片变色区域、蜜露污染。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-PURDUE-CORN, R31-09-UMN-CORN` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 玉米 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：corn aphid complex (source-named group)
- evidence_taxon_level：source_named_group
- evidence_taxon_scope：[{"source_id": "R31-09-PURDUE-CORN", "evidence_taxon": "corn aphid complex (source-named group)", "evidence_taxon_level": "source_named_group", "scope_note": "来源讨论玉米上的蚜虫类群及其受害表现；本记录只覆盖这些来源命名的玉米蚜虫组，不外推为所有蚜虫种类。"}, {"source_id": "R31-09-UMN-CORN", "evidence_taxon": "corn aphid complex (source-named group)", "evidence_taxon_level": "source_named_group", "scope_note": "来源讨论玉米上的蚜虫类群及其受害表现；本记录只覆盖这些来源命名的玉米蚜虫组，不外推为所有蚜虫种类。"}]
- insect：蚜虫
- host：玉米（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：叶片出现卷曲、失绿，并可见蜜露或煤污等取食伴随表现。
- severity source IDs：`R31-09-PURDUE-CORN`, `R31-09-UMN-CORN`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-PURDUE-CORN | Aphids in Corn | Purdue University Extension | https://ag.purdue.edu/department/entm/extension/field-crops-ipm/corn/aphids.html | 2026-09-07 |
| R31-09-UMN-CORN | Aphids in corn (post-pollination) | University of Minnesota Extension | https://extension.umn.edu/corn-pest-management/aphids-corn-post-pollination | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 叶片卷曲 | `R31-09-PURDUE-CORN`, `R31-09-UMN-CORN` |
| 叶片失绿 | `R31-09-PURDUE-CORN`, `R31-09-UMN-CORN` |
| 蜜露 | `R31-09-PURDUE-CORN`, `R31-09-UMN-CORN` |
| 煤污 | `R31-09-PURDUE-CORN`, `R31-09-UMN-CORN` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在玉米上的中度受害状态；仅呈现以下来源支持的可观察特征：叶片卷曲、叶片失绿、蜜露、煤污。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-PURDUE-CORN, R31-09-UMN-CORN` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蚜虫 × 玉米 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：corn aphid complex (source-named group)
- evidence_taxon_level：source_named_group
- evidence_taxon_scope：[{"source_id": "R31-09-PURDUE-CORN", "evidence_taxon": "corn aphid complex (source-named group)", "evidence_taxon_level": "source_named_group", "scope_note": "来源讨论玉米上的蚜虫类群及其受害表现；本记录只覆盖这些来源命名的玉米蚜虫组，不外推为所有蚜虫种类。"}, {"source_id": "R31-09-UMN-CORN", "evidence_taxon": "corn aphid complex (source-named group)", "evidence_taxon_level": "source_named_group", "scope_note": "来源讨论玉米上的蚜虫类群及其受害表现；本记录只覆盖这些来源命名的玉米蚜虫组，不外推为所有蚜虫种类。"}]
- insect：蚜虫
- host：玉米（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：出现叶片萎蔫或死亡；抽雄前的重害还可能干扰授粉并导致籽粒不完整或穗部不育。
- severity source IDs：`R31-09-PURDUE-CORN`, `R31-09-UMN-CORN`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-09-PURDUE-CORN | Aphids in Corn | Purdue University Extension | https://ag.purdue.edu/department/entm/extension/field-crops-ipm/corn/aphids.html | 2026-09-07 |
| R31-09-UMN-CORN | Aphids in corn (post-pollination) | University of Minnesota Extension | https://extension.umn.edu/corn-pest-management/aphids-corn-post-pollination | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 叶片萎蔫 | `R31-09-PURDUE-CORN`, `R31-09-UMN-CORN` |
| 叶片死亡 | `R31-09-PURDUE-CORN`, `R31-09-UMN-CORN` |
| 授粉受扰 | `R31-09-PURDUE-CORN`, `R31-09-UMN-CORN` |
| 籽粒不完整或穗部不育 | `R31-09-PURDUE-CORN`, `R31-09-UMN-CORN` |

#### Final image-generation prompt

> 农业科学示意图：展示蚜虫在玉米上的重度受害状态；仅呈现以下来源支持的可观察特征：叶片萎蔫、叶片死亡、授粉受扰、籽粒不完整或穗部不育。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-09-PURDUE-CORN, R31-09-UMN-CORN` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 盲蝽科 × 葡萄 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Apolygus lucorum
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-10-XILINGOL", "evidence_taxon": "Apolygus lucorum", "evidence_taxon_level": "species", "scope_note": "葡萄严重度证据主要来自绿盲蝽；不外推到盲蝽科所有成员。"}]
- insect：盲蝽科
- host：葡萄（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：未展开芽或刚展开的幼叶出现针头大小的红褐色斑点。
- severity source IDs：`R31-10-XILINGOL`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-10-XILINGOL | 葡萄绿盲蝽防控技术 | 锡林郭勒盟农牧局 | https://www.xlgl.gov.cn/eportal/ui?articleKey=e62fe17b3b1743c3984c01379280c817&columnId=6e17a1ed3b684162abd0322628d20e83&pageId=c449e8dfef194a729e341df57d903d59 | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 未展开芽/刚展开幼叶 | `R31-10-XILINGOL` |
| 针头大小红褐色斑点 | `R31-10-XILINGOL` |

#### Final image-generation prompt

> 农业科学示意图：展示盲蝽科在葡萄上的轻度受害状态；仅呈现以下来源支持的可观察特征：未展开芽/刚展开幼叶、针头大小红褐色斑点。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-10-XILINGOL` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 盲蝽科 × 葡萄 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Apolygus lucorum
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-10-XILINGOL", "evidence_taxon": "Apolygus lucorum", "evidence_taxon_level": "species", "scope_note": "葡萄严重度证据主要来自绿盲蝽；不外推到盲蝽科所有成员。"}]
- insect：盲蝽科
- host：葡萄（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：危害扩展后幼叶出现不规则孔洞，多个刺伤孔使叶片皱缩或畸形。
- severity source IDs：`R31-10-XILINGOL`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-10-XILINGOL | 葡萄绿盲蝽防控技术 | 锡林郭勒盟农牧局 | https://www.xlgl.gov.cn/eportal/ui?articleKey=e62fe17b3b1743c3984c01379280c817&columnId=6e17a1ed3b684162abd0322628d20e83&pageId=c449e8dfef194a729e341df57d903d59 | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 不规则孔洞 | `R31-10-XILINGOL` |
| 多个刺伤孔 | `R31-10-XILINGOL` |
| 叶片皱缩/畸形 | `R31-10-XILINGOL` |

#### Final image-generation prompt

> 农业科学示意图：展示盲蝽科在葡萄上的中度受害状态；仅呈现以下来源支持的可观察特征：不规则孔洞、多个刺伤孔、叶片皱缩/畸形。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-10-XILINGOL` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 盲蝽科 × 葡萄 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Apolygus lucorum
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-10-XILINGOL", "evidence_taxon": "Apolygus lucorum", "evidence_taxon_level": "species", "scope_note": "葡萄严重度证据主要来自绿盲蝽；不外推到盲蝽科所有成员。"}]
- insect：盲蝽科
- host：葡萄（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：叶片出现撕裂状损伤并生长受阻，或幼果伤口形成小黑斑且外观损伤不可恢复。
- severity source IDs：`R31-10-XILINGOL`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-10-XILINGOL | 葡萄绿盲蝽防控技术 | 锡林郭勒盟农牧局 | https://www.xlgl.gov.cn/eportal/ui?articleKey=e62fe17b3b1743c3984c01379280c817&columnId=6e17a1ed3b684162abd0322628d20e83&pageId=c449e8dfef194a729e341df57d903d59 | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 撕裂状叶片损伤 | `R31-10-XILINGOL` |
| 生长受阻 | `R31-10-XILINGOL` |
| 幼果小黑斑 | `R31-10-XILINGOL` |
| 幼果外观损伤不可恢复 | `R31-10-XILINGOL` |

#### Final image-generation prompt

> 农业科学示意图：展示盲蝽科在葡萄上的重度受害状态；仅呈现以下来源支持的可观察特征：撕裂状叶片损伤、生长受阻、幼果小黑斑、幼果外观损伤不可恢复。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-10-XILINGOL` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蝼蛄 × 玉米 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：蝼蛄/蛴螬（来源命名地下害虫组）
- evidence_taxon_level：source_named_group
- evidence_taxon_scope：[{"source_id": "R31-11-CHENGDE", "evidence_taxon": "蝼蛄/蛴螬（来源命名地下害虫组）", "evidence_taxon_level": "source_named_group", "scope_note": "承德资料按地下害虫名称描述，未在当前条目中提供单一精确种。"}]
- insect：蝼蛄
- host：玉米（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：未出苗种子或幼苗根茎出现咬食痕迹，尚未观察到成片缺苗。
- severity source IDs：`R31-11-CHENGDE`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-11-CHENGDE | 2020年承德市主要玉米虫害防控技术指导意见 | 承德市农业农村局 | https://www.chengde.gov.cn/art/2020/4/22/art_9944_538515.html | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 未出苗种子/幼苗根茎咬食 | `R31-11-CHENGDE` |

#### Final image-generation prompt

> 农业科学示意图：展示蝼蛄在玉米上的轻度受害状态；仅呈现以下来源支持的可观察特征：未出苗种子/幼苗根茎咬食。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-11-CHENGDE` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蝼蛄 × 玉米 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：蝼蛄/蛴螬（来源命名地下害虫组）
- evidence_taxon_level：source_named_group
- evidence_taxon_scope：[{"source_id": "R31-11-CHENGDE", "evidence_taxon": "蝼蛄/蛴螬（来源命名地下害虫组）", "evidence_taxon_level": "source_named_group", "scope_note": "承德资料按地下害虫名称描述，未在当前条目中提供单一精确种。"}]
- insect：蝼蛄
- host：玉米（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：较大幼苗根茎部受害，根茎呈乱麻状，局部缺苗或断垄可见。
- severity source IDs：`R31-11-CHENGDE`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-11-CHENGDE | 2020年承德市主要玉米虫害防控技术指导意见 | 承德市农业农村局 | https://www.chengde.gov.cn/art/2020/4/22/art_9944_538515.html | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 较大幼苗根茎受害 | `R31-11-CHENGDE` |
| 根茎呈乱麻状 | `R31-11-CHENGDE` |
| 局部缺苗/断垄 | `R31-11-CHENGDE` |

#### Final image-generation prompt

> 农业科学示意图：展示蝼蛄在玉米上的中度受害状态；仅呈现以下来源支持的可观察特征：较大幼苗根茎受害、根茎呈乱麻状、局部缺苗/断垄。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-11-CHENGDE` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蝼蛄 × 玉米 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：蝼蛄/蛴螬（来源命名地下害虫组）
- evidence_taxon_level：source_named_group
- evidence_taxon_scope：[{"source_id": "R31-11-CHENGDE", "evidence_taxon": "蝼蛄/蛴螬（来源命名地下害虫组）", "evidence_taxon_level": "source_named_group", "scope_note": "承德资料按地下害虫名称描述，未在当前条目中提供单一精确种。"}]
- insect：蝼蛄
- host：玉米（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：幼苗枯死并出现缺苗断垄。
- severity source IDs：`R31-11-CHENGDE`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-11-CHENGDE | 2020年承德市主要玉米虫害防控技术指导意见 | 承德市农业农村局 | https://www.chengde.gov.cn/art/2020/4/22/art_9944_538515.html | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 幼苗枯死 | `R31-11-CHENGDE` |
| 缺苗 | `R31-11-CHENGDE` |
| 断垄 | `R31-11-CHENGDE` |

#### Final image-generation prompt

> 农业科学示意图：展示蝼蛄在玉米上的重度受害状态；仅呈现以下来源支持的可观察特征：幼苗枯死、缺苗、断垄。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-11-CHENGDE` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蝼蛄 × 马铃薯 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Neoscapteriscus borellii (source-named mole cricket)
- evidence_taxon_level：species; source_named_group
- evidence_taxon_scope：[{"source_id": "R31-11-NCSU-POTATO-MOLECRICKET", "evidence_taxon": "Neoscapteriscus borellii (source-named mole cricket)", "evidence_taxon_level": "species", "scope_note": "NCSU以 Neoscapteriscus borellii 为来源命名对象，UFL按 mole cricket 组补充根区受害；不外推为所有直翅目或所有蝼蛄种类。"}, {"source_id": "R31-11-UFL", "evidence_taxon": "Neoscapteriscus borellii (source-named mole cricket)", "evidence_taxon_level": "species", "scope_note": "NCSU以 Neoscapteriscus borellii 为来源命名对象，UFL按 mole cricket 组补充根区受害；不外推为所有直翅目或所有蝼蛄种类。"}]
- insect：蝼蛄
- host：马铃薯（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：马铃薯根区或土壤中可见掘道，根或块茎附近出现取食损伤迹象。
- severity source IDs：`R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-11-NCSU-POTATO-MOLECRICKET | Pests of Potato — mole crickets | NC State Extension | https://content.ces.ncsu.edu/insect-and-related-pests-of-vegetables/pests-of-potato | 2026-09-07 |
| R31-11-UFL | Mole Cricket IPM Guide for Florida | University of Florida IFAS Extension | https://ask.ifas.ufl.edu/publication/IN1021 | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 根区掘道 | `R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL` |
| 根/块茎取食损伤 | `R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL` |

#### Final image-generation prompt

> 农业科学示意图：展示蝼蛄在马铃薯上的轻度受害状态；仅呈现以下来源支持的可观察特征：根区掘道、根/块茎取食损伤。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-11-NCSU-POTATO-MOLECRICKET, R31-11-UFL` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蝼蛄 × 马铃薯 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Neoscapteriscus borellii (source-named mole cricket)
- evidence_taxon_level：species; source_named_group
- evidence_taxon_scope：[{"source_id": "R31-11-NCSU-POTATO-MOLECRICKET", "evidence_taxon": "Neoscapteriscus borellii (source-named mole cricket)", "evidence_taxon_level": "species", "scope_note": "NCSU以 Neoscapteriscus borellii 为来源命名对象，UFL按 mole cricket 组补充根区受害；不外推为所有直翅目或所有蝼蛄种类。"}, {"source_id": "R31-11-UFL", "evidence_taxon": "Neoscapteriscus borellii (source-named mole cricket)", "evidence_taxon_level": "species", "scope_note": "NCSU以 Neoscapteriscus borellii 为来源命名对象，UFL按 mole cricket 组补充根区受害；不外推为所有直翅目或所有蝼蛄种类。"}]
- insect：蝼蛄
- host：马铃薯（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：根系或块茎受损，并伴随植株衰退或缺水样表现。
- severity source IDs：`R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-11-NCSU-POTATO-MOLECRICKET | Pests of Potato — mole crickets | NC State Extension | https://content.ces.ncsu.edu/insect-and-related-pests-of-vegetables/pests-of-potato | 2026-09-07 |
| R31-11-UFL | Mole Cricket IPM Guide for Florida | University of Florida IFAS Extension | https://ask.ifas.ufl.edu/publication/IN1021 | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 根系受损 | `R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL` |
| 块茎受损 | `R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL` |
| 植株衰退 | `R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL` |
| 缺水样表现 | `R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL` |

#### Final image-generation prompt

> 农业科学示意图：展示蝼蛄在马铃薯上的中度受害状态；仅呈现以下来源支持的可观察特征：根系受损、块茎受损、植株衰退、缺水样表现。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-11-NCSU-POTATO-MOLECRICKET, R31-11-UFL` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蝼蛄 × 马铃薯 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Neoscapteriscus borellii (source-named mole cricket)
- evidence_taxon_level：species; source_named_group
- evidence_taxon_scope：[{"source_id": "R31-11-NCSU-POTATO-MOLECRICKET", "evidence_taxon": "Neoscapteriscus borellii (source-named mole cricket)", "evidence_taxon_level": "species", "scope_note": "NCSU以 Neoscapteriscus borellii 为来源命名对象，UFL按 mole cricket 组补充根区受害；不外推为所有直翅目或所有蝼蛄种类。"}, {"source_id": "R31-11-UFL", "evidence_taxon": "Neoscapteriscus borellii (source-named mole cricket)", "evidence_taxon_level": "species", "scope_note": "NCSU以 Neoscapteriscus borellii 为来源命名对象，UFL按 mole cricket 组补充根区受害；不外推为所有直翅目或所有蝼蛄种类。"}]
- insect：蝼蛄
- host：马铃薯（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：根或块茎遭到严重掘食，幼苗可能被拔起，严重植株可死亡。
- severity source IDs：`R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-11-NCSU-POTATO-MOLECRICKET | Pests of Potato — mole crickets | NC State Extension | https://content.ces.ncsu.edu/insect-and-related-pests-of-vegetables/pests-of-potato | 2026-09-07 |
| R31-11-UFL | Mole Cricket IPM Guide for Florida | University of Florida IFAS Extension | https://ask.ifas.ufl.edu/publication/IN1021 | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 根/块茎严重受损 | `R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL` |
| 幼苗被拔起 | `R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL` |
| 植株死亡 | `R31-11-NCSU-POTATO-MOLECRICKET`, `R31-11-UFL` |

#### Final image-generation prompt

> 农业科学示意图：展示蝼蛄在马铃薯上的重度受害状态；仅呈现以下来源支持的可观察特征：根/块茎严重受损、幼苗被拔起、植株死亡。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-11-NCSU-POTATO-MOLECRICKET, R31-11-UFL` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 叶蝉科 × 茶 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Matsumurasca (Matsumurasca) onukii (Matsuda, 1952); Empoasca (Matsumurasca) onukii Matsuda
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-12-WEIHAI-TEA-DAMAGE", "evidence_taxon": "茶小绿叶蝉（来源命名种组）", "evidence_taxon_level": "source_named_group", "scope_note": "仅用于茶树上已审核的茶小绿叶蝉范围；不外推为叶蝉科全体。"}]
- insect：叶蝉科
- host：茶（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：叶脉开始变红，叶尖和叶缘出现变红的可见受害表现。
- severity source IDs：`R31-12-WEIHAI-TEA-DAMAGE`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-12-WEIHAI-TEA-DAMAGE | 山东早春茶树主要病虫害绿色防控技术 | 威海市农业局／山东省现代农业产业技术体系茶叶创新团队 | https://nyj.weihai.gov.cn/art/2018/4/12/art_24524_1327014.html | 2026-09-08 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 叶脉变红 | `R31-12-WEIHAI-TEA-DAMAGE` |
| 叶尖和叶缘变红 | `R31-12-WEIHAI-TEA-DAMAGE` |

#### Final image-generation prompt

> 农业科学示意图：展示叶蝉科在茶上的轻度受害状态；仅呈现以下来源支持的可观察特征：叶脉变红、叶尖和叶缘变红。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-12-WEIHAI-TEA-DAMAGE` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 叶蝉科 × 茶 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Matsumurasca (Matsumurasca) onukii (Matsuda, 1952); Empoasca (Matsumurasca) onukii Matsuda
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-12-WEIHAI-TEA-DAMAGE", "evidence_taxon": "茶小绿叶蝉（来源命名种组）", "evidence_taxon_level": "source_named_group", "scope_note": "仅用于茶树上已审核的茶小绿叶蝉范围；不外推为叶蝉科全体。"}]
- insect：叶蝉科
- host：茶（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：芽叶出现凋萎，节间短缩，受害芽叶质地变脆，表明嫩梢生长已受阻。
- severity source IDs：`R31-12-WEIHAI-TEA-DAMAGE`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-12-WEIHAI-TEA-DAMAGE | 山东早春茶树主要病虫害绿色防控技术 | 威海市农业局／山东省现代农业产业技术体系茶叶创新团队 | https://nyj.weihai.gov.cn/art/2018/4/12/art_24524_1327014.html | 2026-09-08 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 芽叶凋萎 | `R31-12-WEIHAI-TEA-DAMAGE` |
| 节间短缩 | `R31-12-WEIHAI-TEA-DAMAGE` |
| 受害芽叶质地变脆 | `R31-12-WEIHAI-TEA-DAMAGE` |

#### Final image-generation prompt

> 农业科学示意图：展示叶蝉科在茶上的中度受害状态；仅呈现以下来源支持的可观察特征：芽叶凋萎、节间短缩、受害芽叶质地变脆。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-12-WEIHAI-TEA-DAMAGE` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 叶蝉科 × 茶 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Matsumurasca (Matsumurasca) onukii (Matsuda, 1952); Empoasca (Matsumurasca) onukii Matsuda
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-12-FRONTIERS-ONUKII", "evidence_taxon": "Empoasca (Matsumurasca) onukii Matsuda", "evidence_taxon_level": "species", "scope_note": "仅用于茶树上已审核的茶小绿叶蝉范围；不外推为叶蝉科全体。"}, {"source_id": "R31-12-WEIHAI-TEA-DAMAGE", "evidence_taxon": "茶小绿叶蝉（来源命名种组）", "evidence_taxon_level": "source_named_group", "scope_note": "仅用于茶树上已审核的茶小绿叶蝉范围；不外推为叶蝉科全体。"}, {"source_id": "R31-12-ANKANG-TEA-DAMAGE", "evidence_taxon": "茶小绿叶蝉（来源命名种组）", "evidence_taxon_level": "source_named_group", "scope_note": "仅用于茶树上已审核的茶小绿叶蝉范围；不外推为叶蝉科全体。"}]
- insect：叶蝉科
- host：茶（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：叶尖和叶缘转为红褐并焦枯、萎缩，茶园可出现大面积发黄或火烧状受害景象。
- severity source IDs：`R31-12-FRONTIERS-ONUKII`, `R31-12-WEIHAI-TEA-DAMAGE`, `R31-12-ANKANG-TEA-DAMAGE`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-12-FRONTIERS-ONUKII | Fumigant activity and transcriptomic analysis of two plant essential oils against the tea green leafhopper, Empoasca onukii Matsuda | Frontiers in Physiology | 10.3389/fphys.2023.1217608 | 2026-09-08 |
| R31-12-WEIHAI-TEA-DAMAGE | 山东早春茶树主要病虫害绿色防控技术 | 威海市农业局／山东省现代农业产业技术体系茶叶创新团队 | https://nyj.weihai.gov.cn/art/2018/4/12/art_24524_1327014.html | 2026-09-08 |
| R31-12-ANKANG-TEA-DAMAGE | 茶小绿叶蝉防治技术 | 安康市农业技术推广中心／安康市农业农村局 | https://nyj.ankang.gov.cn/Content-2290998.html | 2026-09-08 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 叶尖和叶缘红褐焦枯 | `R31-12-FRONTIERS-ONUKII`, `R31-12-WEIHAI-TEA-DAMAGE`, `R31-12-ANKANG-TEA-DAMAGE` |
| 受害芽叶萎缩 | `R31-12-FRONTIERS-ONUKII` |
| 茶园大面积发黄或火烧状 | `R31-12-ANKANG-TEA-DAMAGE` |

#### Final image-generation prompt

> 农业科学示意图：展示叶蝉科在茶上的重度受害状态；仅呈现以下来源支持的可观察特征：叶尖和叶缘红褐焦枯、受害芽叶萎缩、茶园大面积发黄或火烧状。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-12-FRONTIERS-ONUKII, R31-12-WEIHAI-TEA-DAMAGE, R31-12-ANKANG-TEA-DAMAGE` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蝗总科 × 大豆 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Acrididae（草地蝗虫来源组）
- evidence_taxon_level：family
- evidence_taxon_scope：[{"source_id": "R31-13-UMN-GRASSHOPPER", "evidence_taxon": "Acrididae（草地蝗虫来源组）", "evidence_taxon_level": "family", "scope_note": "资料对象为草地蝗虫组；不表示蝗总科所有成员均有相同寄主关系。"}]
- insect：蝗总科
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：田边或局部叶片出现蝗虫取食形成的锯齿状孔洞，尚未见豆荚或种子直接受害。
- severity source IDs：`R31-13-UMN-GRASSHOPPER`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-13-UMN-GRASSHOPPER | Grasshoppers in Minnesota soybean | University of Minnesota Extension | https://extension.umn.edu/agriculture/crop-production/soybean/grasshoppers-in-minnesota-soybean | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 田边/局部叶片锯齿状孔洞 | `R31-13-UMN-GRASSHOPPER` |

#### Final image-generation prompt

> 农业科学示意图：展示蝗总科在大豆上的轻度受害状态；仅呈现以下来源支持的可观察特征：田边/局部叶片锯齿状孔洞。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-13-UMN-GRASSHOPPER` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蝗总科 × 大豆 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Acrididae（草地蝗虫来源组）
- evidence_taxon_level：family
- evidence_taxon_scope：[{"source_id": "R31-13-UMN-GRASSHOPPER", "evidence_taxon": "Acrididae（草地蝗虫来源组）", "evidence_taxon_level": "family", "scope_note": "资料对象为草地蝗虫组；不表示蝗总科所有成员均有相同寄主关系。"}]
- insect：蝗总科
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：叶片取食扩展并出现明显脱叶，或蝗虫开始取食豆荚。
- severity source IDs：`R31-13-UMN-GRASSHOPPER`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-13-UMN-GRASSHOPPER | Grasshoppers in Minnesota soybean | University of Minnesota Extension | https://extension.umn.edu/agriculture/crop-production/soybean/grasshoppers-in-minnesota-soybean | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 叶片取食扩展 | `R31-13-UMN-GRASSHOPPER` |
| 明显脱叶 | `R31-13-UMN-GRASSHOPPER` |
| 开始取食豆荚 | `R31-13-UMN-GRASSHOPPER` |

#### Final image-generation prompt

> 农业科学示意图：展示蝗总科在大豆上的中度受害状态；仅呈现以下来源支持的可观察特征：叶片取食扩展、明显脱叶、开始取食豆荚。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-13-UMN-GRASSHOPPER` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蝗总科 × 大豆 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Acrididae（草地蝗虫来源组）
- evidence_taxon_level：family
- evidence_taxon_scope：[{"source_id": "R31-13-UMN-GRASSHOPPER", "evidence_taxon": "Acrididae（草地蝗虫来源组）", "evidence_taxon_level": "family", "scope_note": "资料对象为草地蝗虫组；不表示蝗总科所有成员均有相同寄主关系。"}]
- insect：蝗总科
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：豆荚被咬穿并直接伤及种子，或出现来源明确的 Severe/Very severe 高密度取食场景；本条不复制阈值数字。
- severity source IDs：`R31-13-UMN-GRASSHOPPER`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-13-UMN-GRASSHOPPER | Grasshoppers in Minnesota soybean | University of Minnesota Extension | https://extension.umn.edu/agriculture/crop-production/soybean/grasshoppers-in-minnesota-soybean | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 豆荚被咬穿 | `R31-13-UMN-GRASSHOPPER` |
| 种子直接受害 | `R31-13-UMN-GRASSHOPPER` |

#### Final image-generation prompt

> 农业科学示意图：展示蝗总科在大豆上的重度受害状态；仅呈现以下来源支持的可观察特征：豆荚被咬穿、种子直接受害。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-13-UMN-GRASSHOPPER` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蛴螬 × 玉米 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Scarabaeidae larvae（蛴螬）
- evidence_taxon_level：family
- evidence_taxon_scope：[{"source_id": "R31-14-UMN-WHITE-GRUBS", "evidence_taxon": "Scarabaeidae larvae（蛴螬）", "evidence_taxon_level": "family", "scope_note": "白蛴螬资料的范围是金龟甲科幼虫组，不扩展到所有土壤害虫。"}]
- insect：蛴螬
- host：玉米（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：根毛减少或侧根被修剪，地上部尚未出现明显持续萎蔫。
- severity source IDs：`R31-14-UMN-WHITE-GRUBS`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-14-UMN-WHITE-GRUBS | White grubs | University of Minnesota Extension | https://extension.umn.edu/agriculture/crop-production/corn/white-grubs | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 根毛减少 | `R31-14-UMN-WHITE-GRUBS` |
| 侧根被修剪 | `R31-14-UMN-WHITE-GRUBS` |

#### Final image-generation prompt

> 农业科学示意图：展示蛴螬在玉米上的轻度受害状态；仅呈现以下来源支持的可观察特征：根毛减少、侧根被修剪。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-14-UMN-WHITE-GRUBS` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蛴螬 × 玉米 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Scarabaeidae larvae（蛴螬）
- evidence_taxon_level：family
- evidence_taxon_scope：[{"source_id": "R31-14-UMN-WHITE-GRUBS", "evidence_taxon": "Scarabaeidae larvae（蛴螬）", "evidence_taxon_level": "family", "scope_note": "白蛴螬资料的范围是金龟甲科幼虫组，不扩展到所有土壤害虫。"}]
- insect：蛴螬
- host：玉米（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：根系修剪加重，植株出现类似干旱或缺素的萎蔫，或长势受到抑制。
- severity source IDs：`R31-14-UMN-WHITE-GRUBS`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-14-UMN-WHITE-GRUBS | White grubs | University of Minnesota Extension | https://extension.umn.edu/agriculture/crop-production/corn/white-grubs | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 根系修剪加重 | `R31-14-UMN-WHITE-GRUBS` |
| 类似干旱/缺素的萎蔫 | `R31-14-UMN-WHITE-GRUBS` |
| 长势受抑 | `R31-14-UMN-WHITE-GRUBS` |

#### Final image-generation prompt

> 农业科学示意图：展示蛴螬在玉米上的中度受害状态；仅呈现以下来源支持的可观察特征：根系修剪加重、类似干旱/缺素的萎蔫、长势受抑。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-14-UMN-WHITE-GRUBS` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 蛴螬 × 玉米 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Scarabaeidae larvae（蛴螬）
- evidence_taxon_level：family
- evidence_taxon_scope：[{"source_id": "R31-14-UMN-WHITE-GRUBS", "evidence_taxon": "Scarabaeidae larvae（蛴螬）", "evidence_taxon_level": "family", "scope_note": "白蛴螬资料的范围是金龟甲科幼虫组，不扩展到所有土壤害虫。"}]
- insect：蛴螬
- host：玉米（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：中胚轴被破坏导致植株死亡，或根系损伤已造成明显缺苗。
- severity source IDs：`R31-14-UMN-WHITE-GRUBS`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-14-UMN-WHITE-GRUBS | White grubs | University of Minnesota Extension | https://extension.umn.edu/agriculture/crop-production/corn/white-grubs | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 中胚轴破坏 | `R31-14-UMN-WHITE-GRUBS` |
| 植株死亡 | `R31-14-UMN-WHITE-GRUBS` |
| 明显缺苗 | `R31-14-UMN-WHITE-GRUBS` |

#### Final image-generation prompt

> 农业科学示意图：展示蛴螬在玉米上的重度受害状态；仅呈现以下来源支持的可观察特征：中胚轴破坏、植株死亡、明显缺苗。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-14-UMN-WHITE-GRUBS` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 豆芫菁 × 大豆 × 轻度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Epicauta gorhami
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-15-ENTOMOLOGY-1956", "evidence_taxon": "Epicauta gorhami", "evidence_taxon_level": "species", "scope_note": "1956 年《昆虫学报》资料直接讨论豆芫菁 Epicauta gorhami 的大豆取食和受害进展。"}]
- insect：豆芫菁
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：mild / 轻度
- final severity rubric：嫩叶开始出现取食，叶片可见局部缺刻。
- severity source IDs：`R31-15-ENTOMOLOGY-1956`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-15-ENTOMOLOGY-1956 | 豆芫菁 Epicauta gorhami Marseul 的生活史及复变态讨论 | 昆虫学报 | 10.16380/j.kcxb.1956.01.003 | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 嫩叶开始取食 | `R31-15-ENTOMOLOGY-1956` |
| 叶片出现局部缺刻 | `R31-15-ENTOMOLOGY-1956` |

#### Final image-generation prompt

> 农业科学示意图：展示豆芫菁在大豆上的轻度受害状态；仅呈现以下来源支持的可观察特征：嫩叶开始取食、叶片出现局部缺刻。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-15-ENTOMOLOGY-1956` 支持的真实症状/进展证据，整理为本项目的 轻度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 豆芫菁 × 大豆 × 中度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Epicauta gorhami
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-15-ENTOMOLOGY-1956", "evidence_taxon": "Epicauta gorhami", "evidence_taxon_level": "species", "scope_note": "1956 年《昆虫学报》资料直接讨论豆芫菁 Epicauta gorhami 的大豆取食和受害进展。"}]
- insect：豆芫菁
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：moderate / 中度
- final severity rubric：成虫聚集取食，叶片出现多处缺刻或部分叶脉显露。
- severity source IDs：`R31-15-ENTOMOLOGY-1956`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-15-ENTOMOLOGY-1956 | 豆芫菁 Epicauta gorhami Marseul 的生活史及复变态讨论 | 昆虫学报 | 10.16380/j.kcxb.1956.01.003 | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 成虫聚集取食 | `R31-15-ENTOMOLOGY-1956` |
| 叶片出现多处缺刻或部分叶脉显露 | `R31-15-ENTOMOLOGY-1956` |

#### Final image-generation prompt

> 农业科学示意图：展示豆芫菁在大豆上的中度受害状态；仅呈现以下来源支持的可观察特征：成虫聚集取食、叶片出现多处缺刻或部分叶脉显露。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-15-ENTOMOLOGY-1956` 支持的真实症状/进展证据，整理为本项目的 中度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

### 豆芫菁 × 大豆 × 重度

- `PROMPT_EVIDENCE_STATUS`: `TRACEABLE`
- evidence_taxon：Epicauta gorhami
- evidence_taxon_level：species
- evidence_taxon_scope：[{"source_id": "R31-15-ENTOMOLOGY-1956", "evidence_taxon": "Epicauta gorhami", "evidence_taxon_level": "species", "scope_note": "1956 年《昆虫学报》资料直接讨论豆芫菁 Epicauta gorhami 的大豆取食和受害进展。"}]
- insect：豆芫菁
- host：大豆（reviewed common host；不得自动成为 confirmed_host）
- severity：severe / 重度
- final severity rubric：大面积叶片被取食至仅剩叶脉，并可伴随嫩茎受损、开花结实受影响。
- severity source IDs：`R31-15-ENTOMOLOGY-1956`
- SOURCE_SEMANTIC_REVIEW：`PASS`
- capability gate：status=`FULL`；severity_available=`true`

#### Source provenance

| Source ID | Source Title | Organization / Journal | URL / DOI | accessed_at |
|---|---|---|---|---|
| R31-15-ENTOMOLOGY-1956 | 豆芫菁 Epicauta gorhami Marseul 的生活史及复变态讨论 | 昆虫学报 | 10.16380/j.kcxb.1956.01.003 | 2026-09-07 |

#### Observable visual features and source mapping

| Observable visual feature | Supporting Source ID(s) |
|---|---|
| 大面积叶片被取食至仅剩叶脉 | `R31-15-ENTOMOLOGY-1956` |
| 嫩茎受损 | `R31-15-ENTOMOLOGY-1956` |
| 开花结实受影响 | `R31-15-ENTOMOLOGY-1956` |

#### Final image-generation prompt

> 农业科学示意图：展示豆芫菁在大豆上的重度受害状态；仅呈现以下来源支持的可观察特征：大面积叶片被取食至仅剩叶脉、嫩茎受损、开花结实受影响。保持作物与受害部位清晰、自然田间尺度，不补充来源未支持的颜色、斑纹、卷曲、器官损伤、虫口密度、比例、产量数字或其他阈值；不出现文字、UI、箭头、测量数字、农药包装或诊断结论。

#### Synthesis explanation

本条为 `EVIDENCE_SYNTHESIZED`：根据 `R31-15-ENTOMOLOGY-1956` 支持的真实症状/进展证据，整理为本项目的 重度 辅助判定档，并仅将 `observable_features` 中列出的现象转译为视觉特征。该 Prompt 不是来源原文。

#### Unsupported / forbidden visual features

来源未支持的特定颜色、斑纹、卷曲、器官损伤、虫口密度、受害比例、产量损失、数量阈值、药剂或病害确诊表现均禁止加入。

#### AI illustration disclaimer

AI 示意图仅用于辅助理解，不是现场诊断证据；实际判断应以现场观察、检测和农业技术人员意见为准。

<!-- R31_AI_ASSET_STATUS_START -->
## Batch 4B generated asset status

农业 Prompt 正文保持冻结；以下仅增加生成资产与审核状态。

| Asset ID | Generated asset | IMAGE_REVIEW_STATUS |
|---|---|---|
| `r31-class8-soybean-mild` | `web/public/r31/severity/class8-soybean-mild.webp` | `PASS` |
| `r31-class8-soybean-moderate` | `web/public/r31/severity/class8-soybean-moderate.webp` | `PASS` |
| `r31-class8-soybean-severe` | `web/public/r31/severity/class8-soybean-severe.webp` | `PASS` |
| `r31-class9-soybean-mild` | `web/public/r31/severity/class9-soybean-mild.webp` | `PASS` |
| `r31-class9-soybean-moderate` | `web/public/r31/severity/class9-soybean-moderate.webp` | `PASS` |
| `r31-class9-soybean-severe` | `web/public/r31/severity/class9-soybean-severe.webp` | `PASS` |
| `r31-class9-wheat-mild` | `web/public/r31/severity/class9-wheat-mild.webp` | `PASS` |
| `r31-class9-wheat-moderate` | `web/public/r31/severity/class9-wheat-moderate.webp` | `PASS` |
| `r31-class9-wheat-severe` | `web/public/r31/severity/class9-wheat-severe.webp` | `PASS` |
| `r31-class9-peach-mild` | `web/public/r31/severity/class9-peach-mild.webp` | `PASS` |
| `r31-class9-peach-moderate` | `web/public/r31/severity/class9-peach-moderate.webp` | `PASS` |
| `r31-class9-peach-severe` | `web/public/r31/severity/class9-peach-severe.webp` | `PASS` |
| `r31-class9-cotton-mild` | `web/public/r31/severity/class9-cotton-mild.webp` | `PASS` |
| `r31-class9-cotton-moderate` | `web/public/r31/severity/class9-cotton-moderate.webp` | `PASS` |
| `r31-class9-cotton-severe` | `web/public/r31/severity/class9-cotton-severe.webp` | `PASS` |
| `r31-class9-corn-mild` | `web/public/r31/severity/class9-corn-mild.webp` | `PASS` |
| `r31-class9-corn-moderate` | `web/public/r31/severity/class9-corn-moderate.webp` | `PASS` |
| `r31-class9-corn-severe` | `web/public/r31/severity/class9-corn-severe.webp` | `PASS` |
| `r31-class10-grape-mild` | `web/public/r31/severity/class10-grape-mild.webp` | `PASS` |
| `r31-class10-grape-moderate` | `web/public/r31/severity/class10-grape-moderate.webp` | `PASS` |
| `r31-class10-grape-severe` | `web/public/r31/severity/class10-grape-severe.webp` | `PASS` |
| `r31-class11-corn-mild` | `web/public/r31/severity/class11-corn-mild.webp` | `PASS` |
| `r31-class11-corn-moderate` | `web/public/r31/severity/class11-corn-moderate.webp` | `PASS` |
| `r31-class11-corn-severe` | `web/public/r31/severity/class11-corn-severe.webp` | `PASS` |
| `r31-class11-potato-mild` | `web/public/r31/severity/class11-potato-mild.webp` | `PASS` |
| `r31-class11-potato-moderate` | `web/public/r31/severity/class11-potato-moderate.webp` | `PASS` |
| `r31-class11-potato-severe` | `web/public/r31/severity/class11-potato-severe.webp` | `PASS` |
| `r31-class12-tea-mild` | `web/public/r31/severity/class12-tea-mild.webp` | `PASS` |
| `r31-class12-tea-moderate` | `web/public/r31/severity/class12-tea-moderate.webp` | `PASS` |
| `r31-class12-tea-severe` | `web/public/r31/severity/class12-tea-severe.webp` | `PASS` |
| `r31-class13-soybean-mild` | `web/public/r31/severity/class13-soybean-mild.webp` | `PASS` |
| `r31-class13-soybean-moderate` | `web/public/r31/severity/class13-soybean-moderate.webp` | `PASS` |
| `r31-class13-soybean-severe` | `web/public/r31/severity/class13-soybean-severe.webp` | `PASS` |
| `r31-class14-corn-mild` | `web/public/r31/severity/class14-corn-mild.webp` | `PASS` |
| `r31-class14-corn-moderate` | `web/public/r31/severity/class14-corn-moderate.webp` | `PASS` |
| `r31-class14-corn-severe` | `web/public/r31/severity/class14-corn-severe.webp` | `PASS` |
| `r31-class15-soybean-mild` | `web/public/r31/severity/class15-soybean-mild.webp` | `PASS` |
| `r31-class15-soybean-moderate` | `web/public/r31/severity/class15-soybean-moderate.webp` | `PASS` |
| `r31-class15-soybean-severe` | `web/public/r31/severity/class15-soybean-severe.webp` | `PASS` |
<!-- R31_AI_ASSET_STATUS_END -->
