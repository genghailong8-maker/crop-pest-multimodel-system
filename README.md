# 农作物病虫害智能识别系统 — 可公开源码版

> 版本身份：`COMPETITION_FINAL_20261009` 的可公开源码候选。此目录保留冻结版本的业务源码，但为遵守第三方再分发限制，**不包含完整冻结运行资产，不是可以不经补齐就完整运行的冻结包**。本公开副本面向现有公开仓库的独立分支发布；发布前仍以最终安全门禁和远程核验结果为准。

## 本次公开范围

- 保留冻结版 Web、Backend、Detector/Inference、CLIP 服务、Knowledge 解析与业务代码。
- 排除 `knowledge/baidu-baike-20260818/`（文字知识资料及 98 个图片文件），因为目前没有可核实的公开再分发授权。
- 保留其他冻结版正式知识资产，包括 official 10-class 植物知识和昆虫寄主/Severity/Treatment 源码资产。
- 排除 E2、Frozen、CLIP 权重二进制；其身份与 SHA 见 `docs/MODEL_IDENTITIES.md`。
- 仅随附有来源页面明确标注 CC BY 4.0 的 P1 子集 24 张图及对应标注；剩余 116 张暂不公开。
- 不包含运行数据库、病例图片、报告、媒体、备份、凭证、`.git` 历史或生产构建目录。

## 系统流程

用户选择植物或昆虫模式并上传图片 → 直接路由到对应专家（植物 E2 / 昆虫 Frozen）→ OpenAI CLIP 提供视觉上下文建议 → 用户确认或纠正 → Tavily 检索与 Evidence 处理 → 本地知识、用户选择 Severity 与 Treatment → SQLite 病例、历史和报告。CLIP 不决定诊断类别、Severity 或 Treatment；Tavily 不生成本地防治措施。

## 缺失依赖与运行限制

公开副本缺少默认配置所指向的百度知识资产；冻结 Backend 默认 `CROP_KNOWLEDGE_DIR` 至 `knowledge/baidu-baike-20260818`。未获得许可前，不应将相关资产恢复到公开部署。具体受影响端点、功能及不受影响功能见 [`docs/MISSING_RUNTIME_DEPENDENCIES.md`](docs/MISSING_RUNTIME_DEPENDENCIES.md)。候选中保留原 Resolver、默认值和 fallback，未用简化实现替代。要合法补齐，需要内容/图片权利人提供书面再分发许可，或取得另行审核通过且许可兼容的替代资产及其清单；任何运行配置变更需单独评审批准。

模型权重为外部依赖：必须从其权利人/官方来源获取，并在加载前按 `docs/MODEL_IDENTITIES.md` 校验 SHA。真实凭证只通过部署环境的受保护 Secret 管理设施配置，不能放入仓库。

## P1 数据

`training-data/p1-licensed-mendeley-24/` 仅有 24 张许可可核实样本与本项目标注，保留来源、版本、署名和 SHA 清单。完整原 P1 是 140 张；其中来自 Zenodo 记录的 116 张页面显示版权归 University of Makeni，未核实到明确开放再分发许可，故暂不包含。

## 运行状态与完整性

本公开副本不是冻结服务副本；本次未在公开副本执行部署或端到端验收。发布历史与冻结原件分离，公开文件、来源类型、冻结 SHA 对照和许可状态记录在 `PUBLIC_CANDIDATE_FILE_MANIFEST.csv`。依赖、测试、许可和排除范围见 `docs/`。

## 正式知识库与追溯

- 植物病害：保留官方 5 类（ID 0–4）基础知识、来源登记、Severity 字段、15 项正式示意图映射和 `treatment_v4.json`。
- 昆虫虫害：保留官方 ID 5–9 的 24 个寄主组合、72 个寄主×Severity 单元及 216 个防治类别证据状态格（SUPPORTED/UNAVAILABLE）。历史 R3.1 的 38 个 legacy 组合单独作为历史来源资产，不等同于官方 24 组。
- Severity/Treatment：保留正式映射、图片、逐项状态、fallback 顺序和 `uncertain → NO_TREATMENT` 规则。示意图片不是现场诊断证据。
- 来源追溯与复现说明见 [`docs/knowledge-reproduction/`](docs/knowledge-reproduction/KNOWLEDGE_BASE_README.md)，包括 199 条来源登记、资产 SHA256 清单、完整性报告、Severity 与 Treatment 映射参考，以及裁剪后的 Severity V2 研究元数据。
- 百度百科文字/图片目录仍排除；权重为外部依赖；第三方资料的再分发审查为 PARTIAL。详见对应公开范围和缺失依赖文档。

## 模型与训练复现边界

冻结模型身份、权重 SHA、数据概况和可复现限制见 [`docs/MODEL_AND_TRAINING_REPRODUCTION.md`](docs/MODEL_AND_TRAINING_REPRODUCTION.md)。公开候选仅含许可核实通过的 24 张 P1 样本与标签；不含 E2/Frozen/CLIP 权重，也没有已确认对应最终 E2 权重的完整训练代码和配置。因此仓库可用于源码与正式知识研究，但不能声称能够直接完整重训或开箱运行双专家推理。

项目没有在冻结资料中声明统一适用于所有文件的总许可证。第三方模型、数据和来源网页分别遵循各自权利人条款；对未记录的许可状态需在使用前单独核实。公开知识来源索引只保留元数据、关联键和 URL，不授予对来源原文或图片的再分发权。

