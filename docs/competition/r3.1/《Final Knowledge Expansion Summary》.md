# Final Knowledge Expansion Summary

## Scope and decision

本轮先关闭蚜虫×棉花、蚜虫×桃、蝼蛄×马铃薯三处 FULL host 的旧 `NEEDS_EVIDENCE` 文案，再以叶蝉科为最高优先级执行有限研究。没有修改 R1 harms/possible_causes、Backend/Web 产品逻辑、YOLO/CLIP authority、Formal 或 SQLite，也没有生成 AI 图片。

## Documentation consistency

- 蚜虫×棉花 stale status：CLOSED。
- 蚜虫×桃 stale status：CLOSED。
- 蝼蛄×马铃薯 stale status：CLOSED。
- `FULL_HOST_STALE_NEEDS_EVIDENCE = 0`。
- 新增 Semantic Consistency Guard，并区分 host severity 与 vector-disease severity。

## Leafhopper research

### 叶蝉科×茶 — FULL

- evidence taxon：`Matsumurasca (Matsumurasca) onukii (Matsuda, 1952)`；来源同物异名 `Empoasca (Matsumurasca) onukii Matsuda`。
- taxonomy scope：species；仅代表叶蝉科识别类别中的已审核茶小绿叶蝉，不外推至 Cicadellidae 全体。
- mild：叶脉变红，叶尖和叶缘变红。
- moderate：芽叶凋萎、节间短缩，受害芽叶质地变脆。
- severe：叶尖/叶缘红褐焦枯、受害芽叶萎缩，茶园大面积发黄或火烧状。
- Severity：3/3 COMPLETE；Prompt：3/3 TRACEABLE。
- Treatment：保持 `HOST_GENERAL_TREATMENT`；没有伪造三级管理策略。

### 叶蝉科×水稻 — PARTIAL

高质量证据主要支持电光叶蝉传播水稻病害，缺少同一 taxon×水稻的直接取食三级进展。vector relationship 不等于当前诊断，也不与 host severity 混合。

### 叶蝉科×芒果 — PARTIAL

资料支持嫩梢、花序、叶片和幼果受害及落花/落果后果，但未给出同一 taxon×芒果的三档连续进展，故保持 fail closed。

## Final counts

- `TOTAL_FULL_HOSTS = 13`
- `TOTAL_PARTIAL_HOSTS = 25`
- `COMPLETE_INSECT_HOST_SEVERITY = 39 / 114`
- `NEEDS_EVIDENCE_INSECT_HOST_SEVERITY = 75 / 114`
- `TOTAL_TRACEABLE_PROMPTS = 39`
- `TOTAL_AI_IMAGES_REQUIRED = 39`
- `LEAFHOPPER_COVERAGE = FULL_AVAILABLE`
- `R31_EVIDENCE_COVERAGE = PARTIAL`

## Expansion stop

`KNOWLEDGE_EXPANSION_STOPPED = YES`。茶小绿叶蝉已完成同种×同寄主闭环；后续高价值叶蝉候选开始缺少可分离的直接取食三级进展，继续搜索会提高跨病害、跨 taxon 或人为模板推断风险。剩余 25 个 PARTIAL 转入未来 enhancement backlog，不再阻塞后续 AI illustration gate。
