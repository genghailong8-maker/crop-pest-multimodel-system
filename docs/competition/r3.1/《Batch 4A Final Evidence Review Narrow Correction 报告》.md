# 《Batch 4A Final Evidence Review Narrow Correction 报告》

**日期**：2026-09-07
**范围**：只修正用户最终证据复审指出的 knowledge/provenance/validator 问题；未扩大到其余 PARTIAL 寄主，未修改 R1 Evidence、YOLO/CLIP、Backend/Web 产品逻辑、Formal 或 SQLite，未生成 AI 图片，未 commit/push。

## 1. 蚜虫 × 小麦

- 最终 taxon：绿虫蚜 `Schizaphis graminum`，`evidence_taxon_level=species`。
- 原 University of Idaho cereal-aphid 汇总不再用于该三级 severity，因为其进展混合多个 cereal aphid species。
- 新证据链：`R31-09-KSTATE-GREENBUG-WHEAT` 与 `R31-09-OSU-GREENBUG-WHEAT` 均直接描述 `Schizaphis graminum × wheat`：早期红色/铜色小斑与黄化，随后斑点合并、叶片黄化或红褐化、田间斑块扩展；重发出现组织死亡、矮化、死苗或分蘖减少。
- 最终状态：`FULL`；mild/moderate/severe 均 `COMPLETE`；3 个 Prompt 均 `TRACEABLE`。结论只适用于来源物种和来源地理范围，不外推为所有蚜虫。

## 2. 蝼蛄 × 花生

- 复核来源：`R31-11-UFL` 将花生列为受害作物，但其损伤进展是 mole-cricket 对受害植物的一般描述；`R31-11-HAMI-PEANUT-IPM` 直接将蝼蛄列为花生主要地下害虫并提供花生作物级绿色防控框架。
- 缺口：没有来源给出花生专属的 mild→moderate→severe 可观察损伤进展。
- 最终状态：`PARTIAL`；3 个 severity 单元由 `COMPLETE` 降为 `NEEDS_EVIDENCE`，`severity_available=false`；原 3 个 `TRACEABLE` Prompt 撤销。
- Treatment 与 Severity 解耦：凭哈密花生专门标准保留 `HOST_GENERAL_TREATMENT`；不伪造 severity-specific treatment，也不转录产品、剂量或阈值。

## 3. 大豆蚜虫 Treatment 条款级修正

- 保留“每 7–10 天巡查”：`R31-09-IOWA-SOY-APHID-IPM` 直接支持 `Aphis glycines × soybean` 的该巡查频率。
- 天敌文案改为来源直接支持的“瓢虫、草蛉、小花蝽等捕食性天敌以及寄生性天敌”。
- 抗性品种改为“评估抗大豆蚜 Rag 品种的当地适用性”，并保留来源限制语义。
- 删除无当前条款级依据的“食蚜蝇”“蚜茧蜂”“合理轮作”“桥梁寄主”。
- 每个保留概念均在 `source_entailment_review.clause_source_map` 中映射到 approved Source ID。

## 4. Validator false-negative 修复

- Root cause：旧检查依赖精确 substring，空格、不同横线、顿号/逗号或“至少”等修饰即可绕过。
- 修复：使用 Unicode NFKC；统一连字符；移除无意义空白和格式标点；对巡查频率、天敌、抗性品种、轮作等采用 normalized regex/concept 检查；同时要求概念级 Source ID 映射属于当前记录来源。
- 回归测试：无来源的“至少每 7–10 天巡查一次”、天敌组合、抗虫品种与轮作均 FAIL；空格/顿号/逗号/横线变体不能绕过；有 approved source 且正确映射时 PASS。

## 5. 蝼蛄 Treatment provenance

- 马铃薯：`R31-11-NCSU-POTATO-MOLECRICKET` 直接覆盖 `Neoscapteriscus borellii × potato` 的掘道、根/块茎受害和播前处理方向；最终为 `HOST_GENERAL_TREATMENT`，美国化学建议不迁移为中国处方。
- 花生：`R31-11-HAMI-PEANUT-IPM` 直接覆盖花生×蝼蛄和综合管理框架；最终为 `HOST_GENERAL_TREATMENT`。Severity 仍不可用，两者不互相推导。

## 6. R31-08-ORDOS 来源韧性

- `R31-08-ORDOS`：`DEAD_LINK_HISTORICAL_PROVENANCE_ONLY`，`current_capability_use=false`。
- 当前 COMPLETE severity、TRACEABLE Prompt、有效 HOST_GENERAL_TREATMENT、向量关系和 8 份昆虫 Markdown 均不再引用该死链。
- 备份链：`R31-08-CAU-BACKUP`、`R31-08-BEIJING-STANDARD`、`R31-08-NCSU-SOY`、`R31-08-NDSU-BLISTER`、`R31-08-DAZHOU-PEANUT-BACKUP`。花生当前语义由达川区官方植保情报承接。
- `R31-12-PKU-RDV` 同步补记其页面给出的稳定 DOI `10.1371/journal.ppat.1009118`，消除当前向量来源可达性元数据缺口。

## 7. 最终计数与门禁

| 指标 | 最终值 |
|---|---:|
| TOTAL_FULL_HOSTS | 12 |
| TOTAL_PARTIAL_HOSTS | 26 |
| COMPLETE_INSECT_HOST_SEVERITY | 36 / 114 |
| NEEDS_EVIDENCE_INSECT_HOST_SEVERITY | 78 / 114 |
| TOTAL_TRACEABLE_PROMPTS | 36 |
| TOTAL_AI_IMAGES_REQUIRED | 36 |
| HOST_GENERAL_TREATMENT | 38 / 38 |

保留 `NEEDS_EVIDENCE` 是证据门禁的正确 fail-closed 结果。下一步仍需用户最终复审；本批没有生成任何图片。

## 8. 正式来源

- `R31-09-KSTATE-GREENBUG-WHEAT` — Kansas State University Research and Extension — https://entomology.k-state.edu/extension/crop-protection/wheat/greenbug.html
- `R31-09-OSU-GREENBUG-WHEAT` — Oklahoma State University Extension — https://extension.okstate.edu/e-pest-alerts/2026/check-your-wheat-greenbugs-reported-in-central-oklahoma
- `R31-09-IOWA-SOY-APHID-IPM` — Iowa State University Extension and Outreach — https://crops.extension.iastate.edu/encyclopedia/soybean-aphid
- `R31-11-HAMI-PEANUT-IPM` — 哈密市市场监督管理局／哈密市农业农村局 — https://www.hami.gov.cn/hami/c120122/202409/5d5342f355d34946be8dec33305b177a/files/e5e166dd845846fc9200caa1deadfe99.pdf
- `R31-11-NCSU-POTATO-MOLECRICKET` — NC State Extension — https://content.ces.ncsu.edu/insect-and-related-pests-of-vegetables/pests-of-potato
- `R31-08-DAZHOU-PEANUT-BACKUP` — 达州市达川区农业农村局 — https://www.dachuan.gov.cn/xxgk-show-146920.html
- `R31-12-PKU-RDV` — 北京大学生命科学学院；PLOS Pathogens DOI — https://doi.org/10.1371/journal.ppat.1009118

## 9. 状态

- `R31_FINAL_EVIDENCE_CORRECTION = PASS`
- `SOURCE_ENTAILMENT_REGRESSION = CLOSED`
- `VALIDATOR_FALSE_NEGATIVE = CLOSED`
- `CROSS_SPECIES_SEVERITY = CLOSED`
- `R31_SOURCE_RESILIENCE = PASS`
- `R31_EVIDENCE_COVERAGE = PARTIAL`
- `AI_FINAL_ILLUSTRATIONS = NOT_GENERATED`
- `FORMAL = NOT_RUN`
