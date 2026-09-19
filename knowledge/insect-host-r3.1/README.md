# R3.1 昆虫×寄主作物知识层

这是 R3.1 的独立知识 SSOT，不替换冻结的 `knowledge/baidu-baike-20260818` 产品目录。R3.1 Backend、Web 和候选浏览器验证已 PASS；当前数据完成最终受控知识扩充并等待用户复审。Formal 未执行，AI 最终示意图未生成。

## 目录契约

- `manifest.json`：8 个 YOLO 昆虫类别（8–15）、推荐寄主、已审核寄主、来源台账和 Batch 1B 证据口径。
- `severity-evidence.json`：114 个 insect×host×severity、24 个 plant-disease×severity、12 个 vector-disease×severity 的逐项证据登记；insect/vector 记录另有 `evidence_taxon`、`evidence_taxon_level`、`evidence_taxon_scope` 与 `SOURCE_SEMANTIC_REVIEW`。
- `capability-fallback.json`：38 个寄主的 `FULL/PARTIAL/REJECTED`、六项 capability、Severity 可用性、HOST_GENERAL/HOST_SEVERITY 治疗 provenance、8 个 GENERAL_INSECT_TREATMENT 和 fallback 解析规则。
- `insects/*.md`：人类可审阅的 Markdown SSOT；每个 `寄主：<作物>` 独立记录受害表现、轻/中/重和三层防治。推荐寄主统一表达为“推荐：常见寄主之一——<crop>”，仅表示 reviewed common host，不是 confirmed_host。
- `validate_r31.py`：检查结构、推荐寄主语义、来源解析、悬空引用、taxonomic scope、跨寄主防治来源污染、证据 provenance、定量证据约束、重复 rubric、向量关系、adaptive capability 和 treatment fallback；`NEEDS_EVIDENCE` 永不升级为 `COMPLETE`。
- `validate_narrow_correction.py`：检查关键来源可达性标记、精确种级修正、向量来源替换、38 条 Treatment entailment 元数据和 Prompt 正向视觉特征门禁。
- `validate_archive.py`：检查归档与 SSOT 的 8 类昆虫、38 个寄主、severity 文本/source marker、capability/fallback、taxonomic metadata、关键来源可达性与 Prompt gate parity。
- `validate_final_evidence_sprint.py`：检查 Batch 4A 的来源韧性、动态 evidence/prompt gate、taxonomic scope、正向视觉特征 provenance、WHY_NOT_UPGRADED 与无悬空来源。
- `validate_final_evidence_correction.py`：检查本次窄修正的同种小麦蚜虫证据链、花生蝼蛄 severity fail-closed、防治条款级 provenance、Ordos 死链退出当前能力以及最终计数。
- `build_evidence_closure.py`：按既有来源台账生成证据登记、知识文档索引和审核报告；不接入产品运行时。
- `finalize_adaptive_capability.py`：生成 Batch 1C capability/fallback registry、manifest mirror、文档能力索引和审核表；不接入产品运行时。
- `tests/test_validate_r31.py`：最小相关测试，覆盖 NEEDS_EVIDENCE、悬空来源、跨寄主污染、证据 provenance、定量守门、重复 rubric、capability completeness 和 uncertain=no-treatment。

## Batch 1B 证据口径

本轻/中/重规则为基于可靠农业资料整理形成的系统辅助判定规则，并非宣称原始资料本身采用相同三级分级。`EVIDENCE_SYNTHESIZED` 只整理来源真实描述的可观察症状与进展，不新增虫口、株率、百分比、面积比例、产量数字或数量阈值；证据不足的单元保持 `NEEDS_EVIDENCE`。

防治审计区分 `SEVERITY_SPECIFIC_SUPPORTED` 与 `BASE_IPM_ONLY`。后者表示基础 IPM 措施在不同严重度下均适用，并不伪造三级药剂策略。本批未填入未经当前中国精确登记核验的农药有效成分、剂型、剂量、次数或 PHI。

## Batch 1C 自适应能力与 fallback

Severity 与 Treatment 完全解耦。`severity_available=true` 只表示同一寄主的 mild、moderate、severe 三档证据均完整；Treatment 使用 `HOST_SEVERITY_TREATMENT` → `HOST_GENERAL_TREATMENT` → `GENERAL_INSECT_TREATMENT`。`severity=uncertain` 固定 `NO_TREATMENT`；OTHER 不允许自由输入或 host-specific 内容，只使用昆虫通用 fallback。

## User Knowledge Review 窄修正

宽类别文案只表示“该识别类别中的已审核代表性种类/常见种类在该作物上有以下记录”，不把单一物种证据扩展到整个科或总科。葡萄盲蝽证据主要为 `Apolygus lucorum`；水稻橙叶病传播者明确为 `Recilia dorsalis`；豆芫菁×大豆三档使用 `Epicauta gorhami` 的种级来源。Final Evidence Review 窄修正后，小麦蚜虫三级只使用同一物种 `Schizaphis graminum` × wheat 进展；蝼蛄×花生因缺少 same-host 三级进展而 fail closed。最终受控扩充后当前 39 个 Prompt 为 `TRACEABLE`、75 个保持 `NEEDS_EVIDENCE`；不生成 AI 图片、不执行 Formal、SQLite、commit 或 push。

## 与当前产品目录的关系

当前产品目录入口仍是 `../baidu-baike-20260818/manifest.json`，其 16 份文档和现有 `backend/app/knowledge_documents.py`/`backend/app/severity.py` 解析契约保持不变。当前状态：Knowledge user review = PASS；Backend = PASS；Web = PASS；Candidate Browser Smoke = PASS；Final Evidence Sprint = PASS；Evidence coverage = PARTIAL；Final Evidence Review Narrow Correction = PASS；Formal = NOT RUN；AI final illustrations = NOT GENERATED。

## Final Controlled Knowledge Expansion

- 新增 `validate_semantic_consistency.py` 与 `validate_final_knowledge_expansion.py`，分别守住 FULL host 的语义状态一致性与最终扩充证据边界。
- 叶蝉科×茶使用茶小绿叶蝉 `Matsumurasca (Matsumurasca) onukii` 的同种×同寄主证据链升级为 FULL；水稻和芒果仍 fail closed。
- 最终计数：FULL=13，PARTIAL=25，COMPLETE Severity=39/114，NEEDS_EVIDENCE=75/114，TRACEABLE Prompt=39，未来 AI 图片数=39。
- Final Knowledge Expansion = COMPLETE；Knowledge expansion stopped = YES；Evidence coverage = PARTIAL；Formal = NOT RUN；AI final illustrations = NOT GENERATED。剩余 PARTIAL 转入未来 enhancement backlog。
