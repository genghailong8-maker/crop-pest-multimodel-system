# 最终复现检查清单

## 1. 复现原则

代码真源是当前 Git 分支；官方验证集、独立 tune/frozen 和模型权重由受控服务器保存。复现检查分为“无需服务器的静态门”和“可选的运行时门”，运行时门不可达时只标记 `unreachable`，不把环境故障误报成模型失败。

## 2. 一键静态检查

在仓库根目录执行：

```powershell
$py = "C:\Users\genghailong\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py scripts\final_repro_check.py --output artifacts\release\final-repro-check-20260810.json
```

该脚本使用标准库完成以下检查：

- 规划文件、README、发布边界、Phase 5 证据和 Phase 6 知识契约文件存在且可解析；
- 16 个类别 ID 完整，4 个来源均被卡片引用，化学建议边界仍为 `not_provided`；
- 官方 3,321/833、独立 101/85、4 个保留模型角色和 `active_routing_allowed=false` 与证据清单一致；
- shadow 配置、模型哈希、冻结门结论和关键指标存在；
- Git 已跟踪文件中不含权重、原始图片、归档、数据库、日志、密钥或 `.env`；
- 可选探测本机后端、推理隧道和网页，记录 HTTP 状态而不修改服务。

需要确认服务器和网页都已启动时，再加 `--require-services`；此时任一运行时端点不可达会使脚本返回非零退出码。

## 3. 回归命令

```powershell
# 后端
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q

# 网页：构建和渲染测试
cd ..\web
npm.cmd test
npm.cmd run lint

# 回到根目录，检查 Python 语法和补丁空白
cd ..
& $py -m py_compile scripts\final_repro_check.py scripts\collect_phase5_evidence.py scripts\collect_phase8_multimodal_evidence.py backend\app\knowledge.py backend\app\multimodal.py
git diff --check
```

预期结果：后端 17 项测试通过；网页构建与 3 条路由渲染通过；lint 0 errors（保留既有 `<img>` warning）；`py_compile` 和 `git diff --check` 成功。

## 4. 冻结指标与证据入口

| 证据 | 路径 | 用途 |
| --- | --- | --- |
| 全量 Phase 5 清单 | `artifacts/server/phase5-full-evidence-20260810.json` | 配置、运行、权重哈希、监控、指标总索引 |
| 官方冻结指标 | `artifacts/experiments/official-plus-public-weak-v1-e120-b64/full-pt-official-metrics.json` | 833 张最终比较 |
| 路由压测 | `artifacts/server/phase5-benchmark-20260810-route.json` | 顺序/并发延迟与吞吐 |
| 主模型 PT 基准 | `artifacts/server/phase5-benchmark-20260810-main-pt.json` | batch 1/8/32 延迟、吞吐、显存 |
| 独立校准 | `artifacts/experiments/independent-field-calibration-10-13-v2/second-round-calibration-v2.json` | 101 tune、85 frozen 门控 |
| 知识契约 | `backend/app/knowledge.py` | 16 类来源、安全边界和解释输出 |
| Phase 8 多模态证据 | `artifacts/server/phase8-multimodal-evidence-20260810.json` | 分层 Top-1、结构/安全、延迟、吞吐、显存和磁盘大小 |
| Phase 9 两阶段证据 | `artifacts/server/phase9-multimodal-evidence-20260812.json` | 两阶段 Top-1、内容、冲突、严重度引用、安全门、延迟和显存 |

正式报告应引用固定官方验证集指标：Precision 0.839196、Recall 0.776205、mAP50 0.827517、mAP50-95 0.548224。类 10/13 独立 frozen 门未通过，因此复现时不得把 shadow 配置改成 active。

Phase 8 多模态报告应引用固定分层 160 张证据：成功率 100%、Top-1 86.25%、结构校验 100%、内容非空 58.13%、冲突识别 1/17（5.88%）、人工复核 132/160；完整链路 P50/P95 2.326/2.949 秒，并发 2 吞吐 0.841 张/秒，峰值显存 24,024 MiB，模型目录 17,545,920,365 bytes。证据 SHA-256 为 `be54b463fcb6a709197510159d963e668d825d68ce7ee780c29f575b74baf415`。

Phase 9 两阶段正式证据使用同一固定分层 160 张：160/160 成功，Top-1 87.50%，Schema、内容完整和严重度输入引用均为 100%，冲突识别 15/17（88.24%），不安全输出与风险错误清除均为 0；完整链路 P50/P95 4.444/5.087 秒，峰值显存 23,058 MiB。证据 SHA-256 为 `9b31bb691063c14759f70c0283d2f78fd5fee5d4f4c92c749d4568c6d2aba45d`。

## 5. 服务器复现分层

| 工作 | 是否需要服务器 | 说明 |
| --- | --- | --- |
| 文档、知识契约、公开仓库审计 | 否 | 本机标准库即可完成 |
| 后端/网页回归 | 否 | 模型不可用时仍验证降级路径 |
| 真实图片 E2E | 是（或兼容推理端点） | 需要远程模型服务和隧道 |

| 真实多模态分层评估 | 是 | 需要检测 8870、Qwen3-VL 8890 和正式冻结验证集；不得使用模拟响应 |
| 官方验证集重跑 | 是 | 按固定划分和既有权重执行，不改 split |
| 重新训练/第二轮校准 | 是 | 需要 GPU；当前没有批准新的训练或 active 切换 |

## 6. Phase 9 CPU 与数据门

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\manage_storage.py check

cd ..\web
npm.cmd test
npm.cmd run lint

cd ..
git diff --check
```

CPU 门应至少覆盖：本地默认显示全部病例、趋势统计全部本机记录、超过 30 天的病例不自动删除、严重度缺失输入为未知、趋势/报告接口、备份恢复、两阶段 prompt 隔离、确定性冲突和风险不降级、16/16 逐类来源。保留的公网兼容测试继续覆盖公开同意与过期、无编辑令牌 403、上传限流 429 和公网管理路由隐藏。

Phase 9 的正式 160 张双阶段评估、16 类真实样本、本机完整 E2E、故障恢复、备份恢复和自动回归已经通过。最终仍需用户在当前电脑的 Chrome/Edge 完成关键用例验收；手机尺寸只做响应式检查，不要求公网、另一台电脑或手机真机。详细状态见 `user-acceptance-matrix-20260811.md` 与 `phase9-evidence-index-20260811.md`。
