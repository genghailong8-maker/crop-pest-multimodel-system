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
& $py -m py_compile scripts\final_repro_check.py scripts\collect_phase5_evidence.py backend\app\knowledge.py
git diff --check
```

预期结果：后端 9 项测试通过；网页构建与 3 条路由渲染通过；lint 0 errors（保留既有 `<img>` warning）；`py_compile` 和 `git diff --check` 成功。

## 4. 冻结指标与证据入口

| 证据 | 路径 | 用途 |
| --- | --- | --- |
| 全量 Phase 5 清单 | `artifacts/server/phase5-full-evidence-20260810.json` | 配置、运行、权重哈希、监控、指标总索引 |
| 官方冻结指标 | `artifacts/experiments/official-plus-public-weak-v1-e120-b64/full-pt-official-metrics.json` | 833 张最终比较 |
| 路由压测 | `artifacts/server/phase5-benchmark-20260810-route.json` | 顺序/并发延迟与吞吐 |
| 主模型 PT 基准 | `artifacts/server/phase5-benchmark-20260810-main-pt.json` | batch 1/8/32 延迟、吞吐、显存 |
| 独立校准 | `artifacts/experiments/independent-field-calibration-10-13-v2/second-round-calibration-v2.json` | 101 tune、85 frozen 门控 |
| 知识契约 | `backend/app/knowledge.py` | 16 类来源、安全边界和解释输出 |

正式报告应引用固定官方验证集指标：Precision 0.839196、Recall 0.776205、mAP50 0.827517、mAP50-95 0.548224。类 10/13 独立 frozen 门未通过，因此复现时不得把 shadow 配置改成 active。

## 5. 服务器复现分层

| 工作 | 是否需要服务器 | 说明 |
| --- | --- | --- |
| 文档、知识契约、公开仓库审计 | 否 | 本机标准库即可完成 |
| 后端/网页回归 | 否 | 模型不可用时仍验证降级路径 |
| 真实图片 E2E | 是（或兼容推理端点） | 需要远程模型服务和隧道 |
| 官方验证集重跑 | 是 | 按固定划分和既有权重执行，不改 split |
| 重新训练/第二轮校准 | 是 | 需要 GPU；当前没有批准新的训练或 active 切换 |
