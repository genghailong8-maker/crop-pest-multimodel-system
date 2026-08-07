# Progress Log

## Session History

### Phase 1: 项目迁移与系统基础

- **Status:** complete
- Actions taken:
  - 将既有 `crop-pest-system` 实现迁移到当前仓库并保留用户内容。
  - 完成网页诊断、FastAPI 后端、远程推理接口、人工复核和训练监控。
  - 建立服务器训练与实时状态同步工具。
- Key outputs:
  - `web/`
  - `backend/`
  - `training/`
  - `scripts/`

### Phase 2: 官方数据审计与基线

- **Status:** complete
- Actions taken:
  - 审计 4,164 张图、5,920 个框、16 类。
  - 固定 3,321/833 训练验证划分，隔离 10 个冲突重复样本。
  - 在 RTX 5090 上训练 YOLO26n 基线，105 轮正常早停。
  - 完成 PT/ONNX 验证、性能分析、逐类指标和混淆矩阵。
- Key outputs:
  - `data/official/splits/`
  - `artifacts/server/official-baseline-yolo26n-e120-b64/`
  - `artifacts/server/evaluation/`
  - `artifacts/server/benchmarks/`

### Phase 3: 新增数据、预标注与复核

- **Status:** complete
- Actions taken:
  - 检查用户新增图片与 Pest65 数据。
  - 完成自动预标注工具和 `/review` 人工复核流程。
  - 用户确认全部标注复核完成。
  - 审计并选择弱类相关公开检测数据，保留来源和许可证元数据。
- Key outputs:
  - `artifacts/dataset-audit/`
  - `artifacts/public/`
  - `artifacts/review/`

### Phase 4: 弱类模型、专项审计与校准

- **Status:** in_progress
- Actions taken:
  - 训练弱类检测专家和 crop 分类专家。
  - 完成类 10/13 第一轮阈值校准与专家重排分析。
  - 完成类 8/15、6/12 混淆矩阵和困难样本审计。
  - 准备类 10 的独立 SciDB tune/test 清单。
  - 审计类 13 独立数据候选；GHCID 因约 31.2GB 暂缓，选择更小的 CC BY 4.0 候选等待下载与人工复核。
- Key outputs:
  - `artifacts/experiments/pairwise-calibration-v1/`
  - `artifacts/experiments/pairwise-crop-reranker-v2/`
  - `artifacts/experiments/class-pair-audit-8-15-v1/`
  - `artifacts/experiments/class-pair-audit-6-12-v1/`
  - `artifacts/experiments/independent-field-calibration-10-13-v2/`
- Remaining:
  - 取得并人工复核类 13 独立现场样本。
  - 执行第二轮独立校准。
  - 决定是否进一步微调或从头训练。

### Server Shutdown Checkpoint — 2026-08-07

- **Status:** complete
- Actions taken:
  - 确认 GPU 0% 利用率、显存 0 MiB，无训练/推理、tmux 或 screen 任务。
  - 核对主模型、官方基线、弱类专家、类 10/13 专家的本地 SHA-256。
  - 补充下载类 10/13 专家 `last.pt`。
  - 服务器执行 `sync` 后允许安全关机。
  - 创建 `artifacts/server/shutdown-checkpoint-20260807.json`。
- Git commit: `4574d82`（包含关机检查点；当前分支最新提交）

### GitHub Publication — 2026-08-07

- **Status:** complete
- Actions taken:
  - 安装 GitHub CLI 2.97.0。
  - 创建公开仓库 `genghailong8-maker/crop-pest-multimodel-system`。
  - 通过 Git Credential Manager 完成标准写入授权。
  - 推送 `master` 和 `codex/publish-audits-and-calibration-plan`。
  - 创建草稿 PR #1。
  - 扫描远程树：模型/图片/归档文件 0，密钥标记 0。
- Links:
  - Repository: `https://github.com/genghailong8-maker/crop-pest-multimodel-system`
  - Draft PR: `https://github.com/genghailong8-maker/crop-pest-multimodel-system/pull/1`

### Persistent Planning Setup — 2026-08-07

- **Status:** complete
- Actions taken:
  - 启用 `planning-with-files` 工作方式。
  - 执行 `session-catchup.py`，未发现旧规划文件或未同步规划上下文。
  - 新建 `task_plan.md`、`findings.md`、`progress.md`。
  - 将当前阶段、关键指标、模型路径、问题解决记录和恢复步骤写入磁盘。
- Files created:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

## Test Results

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Backend pytest | API/backend tests pass | 5 passed；1 个 Starlette 弃用警告 | PASS |
| Web production build | Build succeeds | 成功 | PASS |
| Web render tests | `/`、`/review`、`/training` render | 3/3 passed | PASS |
| Web lint | 0 errors | 0 errors；3 个既有 `<img>` warnings | PASS |
| Training utility compile | Relevant Python files compile | 成功 | PASS |
| Experiment JSON validation | New reports parse | 成功 | PASS |
| GitHub remote safety scan | No secrets/weights/raw images/archives | secret markers 0；binary/data artifacts 0 | PASS |
| Shutdown backup hashes | Local critical files match server | 已匹配 | PASS |

## Error Log

| Date | Error | Attempt | Resolution |
|------|-------|---------|------------|
| 2026-08-07 | GitHub App token lacked repository creation/write permissions | 1 | Switched to user-created repo plus Git Credential Manager |
| 2026-08-07 | Chrome control timed out on GitHub form | 2 | Requested one manual submit instead of repeating automation |
| 2026-08-07 | Initial SSH audit command expanded locally in PowerShell | 1 | Sent remote script through SSH stdin |
| 2026-08-07 | CRLF affected final remote Bash argument | 2 | Used simpler single-line command for final sync check |
| 2026-08-07 | Git push waited on hidden credential dialog | 1 | Explicitly ran GCM device authorization, then repeated push successfully |
| 2026-08-07 | PowerShell default `Get-Content` rendered UTF-8 Chinese as mojibake | 1 | Read planning files with explicit `-Encoding UTF8` |

## 5-Question Reboot Check

| Question | Answer |
|----------|--------|
| Where am I? | Phase 4：类 10/13 独立现场样本与第二轮校准 |
| Where am I going? | 多模型生产集成、防治知识与可信交互、比赛最终交付 |
| What's the goal? | 完成可复现、可演示、可解释的多模型病虫害识别与防治系统 |
| What have I learned? | 见 `findings.md`，尤其数据许可、冻结评估、弱类混淆和模型哈希 |
| What have I done? | 见本文件的阶段日志；Phase 1–3 已完成，Phase 4 进行中 |

## Immediate Resume Checklist

- [ ] 读取三个规划文件并检查 Git 状态。
- [ ] 向用户确认可用服务器地址/GPU 状态。
- [ ] 检查类 10 独立列表和本地关键备份是否仍可用。
- [ ] 下载并人工复核类 13 合法检测样本。
- [ ] 固定 tune/test 并执行第二轮类 10/13 校准。
- [ ] 更新三个规划文件并汇报已完成工作与下一步。
