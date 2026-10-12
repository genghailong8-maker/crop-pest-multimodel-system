# 缺失运行依赖及影响

## 0. 外部运行依赖（未随公开副本分发）

- E2、Frozen 和 OpenAI CLIP 权重未上传；按 `MODEL_IDENTITIES.md` 中的模型 ID / SHA 从授权来源获取并校验。
- Tavily API Key、Web Origin Secret、Detector/API 认证值及任何真实 `.env` 均未收录；部署者须通过授权 Secret 管理方式注入相应环境变量，不能将密钥加入仓库或日志。
- `web/dist` 生产输出被排除；必须按冻结版依赖声明/lockfile 在目标环境重新构建。源代码与 lockfile 保留。

这些是完整运行时的外部依赖；其缺失不等于候选源码实现被删除。

## 1. 百度百科知识目录（未随公开副本分发）

缺失路径：`knowledge/baidu-baike-20260818/`，原目录包含 manifest、16 份 Markdown 知识文档与 98 个图像文件。冻结 Backend 的 `backend/app/config.py` 在未设置 `CROP_KNOWLEDGE_DIR` 时默认指向该路径。`backend/app/knowledge_documents.py` 从该目录读取 `manifest.json`、文档和 assets；找不到目录时相应文档/asset resolver 返回缺失。

### 会受影响的调用

- 未使用 official taxonomy 的 legacy 类别知识文档接口：`GET /api/catalog/classes/{class_id}/knowledge-document` 会无法读取文档并返回 404。
- 以 legacy 知识目录生成的文档图片接口 `GET /api/catalog/knowledge/assets/{version}/{asset_path}` 无法提供被排除图片。
- legacy 分支的危害/特征/症状文档和依赖该文档的病例报告知识摘要不可用；legacy 病例对应的本地文档型 Treatment/图像部分可能为空或 unavailable，具体取决于既有卡片和记录。
- 官方昆虫病例报告的“基础信息/特征/危害症状”摘要，在 `main.py::_core_knowledge_for_report` 中通过 canonical insect key 映射到 legacy 文档；该摘要会缺失。

### 不受该目录缺失影响（其资产位于其他冻结目录，源码保留）

- official 五类植物的基础知识、特征、危害症状、Severity 和 official Treatment，使用 `knowledge/official_10class_20260917/` 与相应官方资产。
- official 五类昆虫 24 个寄主组合、72 个 Severity 层级以及本地寄主特异 Treatment，使用 `knowledge/insect-host-r3.1/` 和对应正式资产；注意报告中的通用昆虫知识摘要仍受上一节影响。
- 检测、双专家路由、CLIP、Tavily/Evidence、病例/历史/报告持久化业务源码不读取该百度目录。

**原代码、resolver、默认配置和 fallback 均未更改。**因此该副本不可视为完整可运行冻结包，默认知识目录依赖未满足。

## 2. 候选对 Severity V2 alignment 审查材料的最小裁剪

`backend/app/severity_v2.py` 的运行 loader 实际只读取 `canonical_class`、`severity_level`、`current_alignment`。候选保留从冻结 TSV 逐值提取的 48 行、上述 3 列运行合同；删除其余评估文字、知识文档路径、来源映射和研究备注，避免传播与缺失知识资产绑定的摘录/映射。业务 Python 文件、分类/等级映射值及 fallback 未改。冻结原 TSV 保持原样。

## 3. 可选预标注审核数据

`backend/app/config.py` 默认将 `CROP_PRELABEL_DIR` 指向源码树之外的 `artifacts/dataset-audit/pest65-aphids/prelabels`。该目录未公开；本地管理员接口 `/api/prelabels/queue` 和 `/api/prelabels/{image_id}` 依赖它。缺少时，预标注队列/详情审核工具不能正常使用。此项不影响用户病虫害识别、知识、病例与报告主流程。数据来源及再分发权限未经本次批准，因此未包含。

## 合法补齐方式

仅当取得相关文字及每张图片权利人的明确书面公开再分发许可（覆盖该用途、地域和授权期限），并核验文件逐项授权后，方可由获授权者按原目录结构、安全渠道补齐并复核 manifest/SHA。否则只能通过独立审批使用来源、授权、字段和映射均兼容的替代知识资产；不能将其伪称为原冻结知识包，也不能在此公开副本中静默改默认路径或 fallback。
## 4. 训练复现材料边界

冻结源码中没有可确认属于最终 `E2_P1_seed_20260919` 权重的完整训练脚本、配置、固定划分和运行日志。其他工作区的候选训练代码没有被并入公开副本；因此完整重训不是当前公开包可复现能力。数据概况和 24 张获准公开子集见 `docs/MODEL_AND_TRAINING_REPRODUCTION.md`。
