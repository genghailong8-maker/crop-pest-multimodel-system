# Findings & Decisions

## Requirements

- 题目：第三届“农信杯”题目二《基于多模型协同的农作物病虫害识别与防治系统开发》。
- 所有训练使用 GPU 服务器；新增公开数据必须确实有助于训练。
- 公开数据必须有明确类别映射、检测框、许可证和低重复率。
- 先做小规模试训/校准，再决定是否从头训练。
- 官方验证集永久冻结，所有实验保留复现配置、指标和权重。
- 系统需覆盖真实识别、多模型协同、防治知识、可解释性、人工复核和比赛材料。
- 每次向用户汇报时必须包含：当前已完成的工作、当前状态、下一步工作。
- 使用 `task_plan.md`、`findings.md`、`progress.md` 作为跨对话持久上下文。

## Dataset Findings

### 官方数据

- 4,164 张图片，5,920 个检测框，16 类。
- 固定种子：`20260729`。
- 训练 3,321 张，验证 833 张。
- 10 个冲突重复样本已隔离。
- 划分元数据位于 `data/official/splits/`；不得根据后续结果重新划分。

### 本地新增数据

- 用户提供目录：`C:\编程大赛数据\Dataset\图片`。
- 可选目录：`C:\编程大赛数据\Dataset\pest65`。
- 已建立数据审计、自动预标注和人工复核流程；用户已确认复核完成。

### 类 10 独立数据

- SciDB 独立列表已在服务器准备：32 张 tune、16 张 frozen test。
- 服务器旧路径记录在 `artifacts/server/shutdown-checkpoint-20260807.json`；恢复时应先确认服务器是否仍保留该目录。

### 类 13 独立数据

- GHCID 数据质量较强，但全量约 31.2GB，曾因服务器磁盘与选择性下载限制暂缓。
- 当前较小候选：Roboflow `grasshopper-qpkes-i1pbc v1`，587 张，固定 train/valid/test 为 445/70/72，YOLO 检测框，页面声明 CC BY 4.0。
- 候选页面：`https://universe.roboflow.com/amiruls-workspace-wyolc/grasshopper-qpkes-i1pbc/dataset/1`。
- 下载需要 Roboflow 登录；未得到登录条件前不应假设数据已经取得。
- 预定独立校准规模：类 10 为 32 tune + 16 frozen；类 13 候选为 70 tune + 72 frozen，总计 102 tune + 88 frozen。
- 类 13 数据必须先人工复核框质量、类别纯度、许可证与重复率，再进入校准。

## Model Findings

### 官方 YOLO26n 基线

- 训练配置：batch 64，计划 120 轮，第 105 轮因 `patience=30` 正常早停。
- 独立验证：mAP50 `0.705030`、mAP50-95 `0.425336`、Precision `0.733906`、Recall `0.683310`。
- 本机权重：`artifacts/server/official-baseline-yolo26n-e120-b64/weights/best.pt`。
- SHA-256：`0443b179564564fce071b7595e1c4a68484a339230951c5e8cefe279af066192`。

### 当前 16 类生产候选

- PT：`artifacts/server/remote-runs/official-plus-public-weak-v1-e120-b64/weights/best.pt`。
- PT SHA-256：`cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071`。
- ONNX：`artifacts/server/remote-runs/official-plus-public-weak-v1-e120-b64/weights/best.onnx`。
- ONNX SHA-256：`048b9050caa2db6389881865fe16818968e75d3f11fd288d4fa6a88181a258e2`。

### 类 10/13 专家模型

- 类 10 弱类检测专家：`artifacts/server/experiments/weak-expert-v2-full-public10-ft-freeze10-lr1e4-e18-b64/best.pt`。
- 类 10/13 crop 专家 best：`artifacts/server/experiments/pairwise-crop-cls-10-13-v5-e30-b128/best.pt`。
- best SHA-256：`9804458da627e30299114f31e032ad5bcc08a7f74694f6559dcf45b27d7c242c`。
- last SHA-256：`50fc0af58e3254aac910683670a31b715ad3731a11c80113f28cc8aa3a40364d`。
- 可复现实验数据归档：`artifacts/server/pairwise-hard-crops-10-13-v5.tar.gz`。
- 第一轮校准报告：`artifacts/experiments/pairwise-calibration-v1/report.json`。
- 专家重排报告：`artifacts/experiments/pairwise-crop-reranker-v2/report.json`。

## Weak-Class Audit Findings

### 类 8 / 15

- 报告：`artifacts/experiments/class-pair-audit-8-15-v1/report.json`。
- 类 8，阈值 0.50：P `0.7381`、R `0.6327`、F1 `0.6813`，98 个 GT。
- 类 8 主要错误：15 个误为类 15、18 个漏检、2 个误为类 13、1 个误为类 12。
- 类 15，阈值 0.70：P `0.8421`、R `0.7711`、F1 `0.8050`，83 个 GT。
- 类 15 主要错误：13 个误为类 8、4 个漏检。
- 结论：8/15 存在明显双向混淆，后续可评估专家路由，但不应仅凭该审计重划官方数据。

### 类 6 / 12

- 报告：`artifacts/experiments/class-pair-audit-6-12-v1/report.json`。
- 类 6，阈值 0.20：P `0.8077`、R `0.6774`、F1 `0.7368`，31 个 GT。
- 类 6 主要错误：7 个漏检、4 个误为类 7、各 1 个误为类 2/3。
- 类 12，阈值 0.25：P `0.9383`、R `0.8837`、F1 `0.9102`，86 个 GT。
- 类 12 主要错误：3 个误为类 10、3 个误为类 8、2 个漏检、各 1 个误为类 0/15。
- 结论：类 12 已较强；类 6 更需要召回与困难样本优化，不能将 6/12 当作主要双向混淆对。

## System Findings

- 网页包含诊断首页、人工复核页 `/review`、训练监控页 `/training`。
- 后端为 FastAPI，支持远程视觉推理接口。
- 训练工具覆盖数据审计/划分、服务器训练、验证、导出与实时监控。
- 本地验证曾通过：后端 5 个 pytest；网页 production build；`/`、`/review`、`/training` 共 3 个渲染测试。
- 网页 lint 无错误，有 3 个既有 `<img>` 警告。

## GitHub & Publication Findings

- 公开仓库：`https://github.com/genghailong8-maker/crop-pest-multimodel-system`。
- 默认分支 `master`：`0925002`。
- 当前工作分支 `codex/publish-audits-and-calibration-plan`：`4574d82`。
- 草稿 PR：`https://github.com/genghailong8-maker/crop-pest-multimodel-system/pull/1`。
- 已确认远程不含 `.pt`、`.onnx`、原始图片、压缩归档、私钥或令牌。
- `data/official/` 在公开仓库中只包含 YAML、固定划分清单和审计元数据。
- `.gitignore` 排除数据图片/标注、权重、ONNX、归档、环境和日志。
- 仓库尚未选择项目级 LICENSE；公开可见不等于授权他人复用。

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| 主模型、弱类专家和阈值校准分层处理 | 便于控制风险、定位收益并保持整体模型稳定 |
| 类 13 先找小型合法检测集 | GHCID 全量过大，当前只需要独立校准与现场验证样本 |
| 冻结 tune/test 职责 | tune 选阈值，test 只做一次最终报告，降低过拟合风险 |
| 大模型和所有训练放在 GPU 服务器 | 符合用户要求，本机主要承担代码、报告和安全备份 |
| 权重只做本机/服务器备份，不上传公共 Git | 控制体积、版权和安全风险 |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| 原 AutoDL 实例无可用 GPU 或被占用 | 暂停并在用户提供可用服务器后恢复 |
| GitHub CLI App 令牌不能创建仓库或写入 | 用户网页创建仓库，使用 Git Credential Manager 设备授权完成推送 |
| 浏览器自动化控制 GitHub 标签页超时 | 改为一次明确的用户手动点击，避免反复失败 |
| 服务器关机可能丢失实验上下文 | 创建本地权重/数据备份、哈希核验和关机检查点 |

## Resources

- 比赛通知：`E:\第三届“农信杯”编程大赛\2026第三届“农信杯”编程大赛 .pdf`
- 官方数据：`E:\第三届“农信杯”编程大赛\基于多模型协同的农作物病虫害识别与防治系统开发`
- 本地新增数据：`C:\编程大赛数据\Dataset\图片`
- Pest65：`C:\编程大赛数据\Dataset\pest65`
- 关机检查点：`artifacts/server/shutdown-checkpoint-20260807.json`
- 发布规范：`PUBLICATION_POLICY.md`
- GHCID 论文：`https://www.nature.com/articles/s41598-020-57674-8`

## Visual/Browser Findings

- GitHub 新仓库页面最终由用户手动提交，仓库可见性为 Public。
- GitHub PR #1 已验证为 Open、Draft，合并状态为 Clean。
- 本地系统页面曾在 `http://localhost:3000/`、`/review`、`/training` 使用。

---

每进行 2 次新的网页、PDF、图片或搜索查看后，应立即把关键结论补充到本文件。

