# R3.1 Batch 4A — WHY_NOT_UPGRADED

本文件记录本批快速检索后仍保持 `PARTIAL` 的候选。`PARTIAL` 是 fail-closed 结果，不代表寄主关系或受害事实不存在，而是当前证据没有同时满足三个可追溯、host-specific 的 mild/moderate/severe 闭环。

## 蝼蛄 × 花生（Final Evidence Review 窄修正）

- `searched_evidence_scope`：复核 UF/IFAS mole-cricket 资料，并检索中国官方花生×蝼蛄资料；新增哈密市地方标准 DB 6505/T 188—2024《花生病虫害绿色防控技术规程》。
- `found_evidence`：UF/IFAS 将花生列为蝼蛄受害作物，但损伤进展是对受害植物的一般描述；哈密标准直接将蝼蛄列为花生主要地下害虫并支持花生作物级综合防控。
- `missing_requirement`：两者均未提供可逐档归属于花生的 mild→moderate→severe 可观察损伤进展。
- `why_severity_cannot_be_upgraded`：不能把一般 mole-cricket 损伤或花生防治规程转写成花生专属三级 rubric；原 3 个 COMPLETE 和 3 个 TRACEABLE Prompt 因而撤销。
- `retained_capability_state`：`PARTIAL`；`severity_available=false`；防治因哈密标准的直接寄主×害虫支持而保留 `HOST_GENERAL_TREATMENT`，不是 severity-specific treatment。

## 蛴螬 × 大豆

- `searched_evidence_scope`：现有 University of Minnesota Extension white-grub 资料，覆盖大豆作为寄主及白蛴螬根系取食的一般表现。
- `found_evidence`：资料明确列出大豆寄主关系，并描述根毛/侧根受损、吸水吸肥能力下降及地上部萎蔫等一般后果。
- `missing_requirement`：没有足够的大豆专属症状进展来把这些现象安全拆为三档；部分更严重的描述属于玉米或一般白蛴螬情境。
- `why_severity_cannot_be_upgraded`：不能把“列为寄主”或跨作物根系描述改写成大豆的三级严重度。
- `retained_capability_state`：`PARTIAL`；severity unavailable；继续使用既有 host-general/insect-general fallback。

## 蛴螬 × 马铃薯

- `searched_evidence_scope`：现有 University of Minnesota Extension white-grub 资料，覆盖马铃薯寄主关系及根系受害的一般信息。
- `found_evidence`：资料列出马铃薯寄主并描述根系受损和植株水分/养分胁迫。
- `missing_requirement`：缺少马铃薯块茎和地上部的连续、作物专属三级症状证据。
- `why_severity_cannot_be_upgraded`：不能用玉米或一般根害描述替代马铃薯特异的 mild/moderate/severe 证据。
- `retained_capability_state`：`PARTIAL`；severity unavailable；继续 fail closed。

## 叶蝉科 × 茶（历史未升级记录，已被本轮新证据关闭）

- `searched_evidence_scope`：全国农技中心/中国农业农村信息网茶树病虫害方案，关注茶小绿叶蝉在嫩梢叶片上的刺吸危害与绿色防控。
- `found_evidence`：存在寄主和受害部位记录，并有监测与管理依据。
- `missing_requirement`：现有材料没有足够的茶树专属症状进展，不能在不引入通用模板的前提下形成三档 rubric。
- `why_severity_cannot_be_upgraded`：叶蝉科是宽类别，来源对象为茶小绿叶蝉等已命名类群；寄主关系和管理资料不自动等于三级严重度。
- `retained_capability_state`：`PARTIAL`；保留 host damage/treatment，severity unavailable。

## 盲蝽科 × 棉花、枣、核桃

- `searched_evidence_scope`：喀什地区官方绿盲蝽预测预报资料及现有盲蝽科寄主记录。
- `found_evidence`：资料支持绿盲蝽在这些作物上的发生、迁移及芽叶花果取食表现。
- `missing_requirement`：证据主要是绿盲蝽等来源命名种类，缺少每一作物的连续三级损伤进展。
- `why_severity_cannot_be_upgraded`：不能从 `Apolygus lucorum` 或绿盲蝽资料泛化到盲蝽科全部成员，也不能用同一模板拆分三档。
- `retained_capability_state`：三项均 `PARTIAL`；保留来源限定的 host relation/damage/treatment。

## 芫菁类剩余 PARTIAL 寄主与豆芫菁非大豆寄主

- `searched_evidence_scope`：达拉特旗历史芫菁来源、其官方/大学备份、现有中国农业技术资料及 exact-species 资料。
- `found_evidence`：部分寄主关系和取食表现可追溯；中国农业大学备份明确支持 `Epicauta gorhami` 在大豆上的取食与受害。
- `missing_requirement`：剩余作物缺少与识别类别/来源物种精确对应的三级症状进展；历史 Ordos 页面本身已标记为死链，仅作为历史 provenance。
- `why_severity_cannot_be_upgraded`：不能把 `Epicauta gorhami` 或其他芫菁种类的资料跨作物、跨种类扩展。
- `retained_capability_state`：除已有 FULL 外，剩余项保持 `PARTIAL`；severity 和相关能力按现有 fail-closed 规则处理。

## 最终受控扩充决策（2026-09-08）

### 叶蝉科 × 茶：已升级 FULL

- `searched_evidence_scope`：安康市农技中心、国家林草局技术资料、Frontiers 稳定 DOI，以及 PLOS/中国农科院分类学来源。
- `found_evidence`：同一茶小绿叶蝉 taxon×茶树的受害进展：初期叶缘黄化/叶尖卷曲/叶脉暗红 → 芽小、节间缩短与生长停止 → 叶尖叶缘红褐焦枯、萎缩及茶园大面积火烧状。
- `final_decision`：`FULL`；3 档 Severity `COMPLETE`；3 个 Prompt `TRACEABLE`。
- `treatment`：保持既有 `HOST_GENERAL_TREATMENT`，不人为拆分 severity-specific 策略。

### 叶蝉科 × 水稻：仍 PARTIAL

- `searched_evidence_scope`：中国政府水稻病毒病指引与 `Recilia dorsalis`×水稻的 DOI/同行评议资料，专门区分直接取食与传毒症状。
- `found_evidence`：电光叶蝉传播水稻橙叶病等关系有直接高质量证据。
- `missing_requirement`：缺少同一电光叶蝉 taxon×水稻的直接取食 mild→moderate→severe 进程。
- `why_severity_cannot_be_upgraded`：不能把病毒/植原体感染症状等同于叶蝉直接取食损伤。
- `retained_capability_state`：`PARTIAL`；`severity_available=false`；已审核 vector relation 独立保留。

### 叶蝉科 × 芒果：仍 PARTIAL

- `searched_evidence_scope`：海南省官方芒果生产标准与 `Idioscopus clypealis`×芒果同行评议资料。
- `found_evidence`：支持若虫/成虫在嫩梢、花序、叶片和幼果刺吸，以及不坐果、幼果脱落等后果。
- `missing_requirement`：缺少同一 taxon×芒果的三档连续损伤证据；来源不支持本项目拟定阈值。
- `why_severity_cannot_be_upgraded`：寄主关系和严重后果不足以无推断地拆出 mild/moderate/severe。
- `retained_capability_state`：`PARTIAL`；`severity_available=false`。

## 结论

本轮只在同种×同寄主证据闭环后将叶蝉科×茶升级为 FULL；水稻、芒果及其余缺口保持 `WHY_NOT_UPGRADED`。`KNOWLEDGE_EXPANSION_STOPPED = YES`，剩余 PARTIAL 转入未来 enhancement backlog。
