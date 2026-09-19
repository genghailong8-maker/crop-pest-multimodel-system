# Phase 9 本机 GPU 与真实浏览器测试报告

> **历史架构记录：** 本文记录 2026-08-13 的 Phase 9 多模态测试；当前运行架构已移除 Qwen3-VL / 8890，不可作为当前启动、部署或验收说明。

日期：2026-08-13
范围：恢复服务器 GPU 后，验证当前本机交付链路；不执行新训练、不切换模型、不启用专家 `active`。

## 结论

系统当前可以交给用户在本机继续测试，核心正常链路已经跑通；但不能宣称“完全满足满分要求”或关闭 Phase 9。测试发现两个需要优先整改的问题：

1. 无支持目标时，后端已经返回 `no_supported_target` 和“无法可靠判断/请补拍”，但病例详情标题仍可能显示 Qwen3-VL 的独立候选类别，容易让普通用户误以为系统已确认诊断。
2. Qwen3-VL 不可用时病例和检测证据会保留，恢复后仅重试分析成功，但当前接口返回 HTTP `502`，尚未统一为用户可理解的结构化“服务暂不可用/稍后重试”状态。

## 运行环境

| 项目 | 实测结果 |
|---|---|
| SSH | `root@connect.bjb2.seetacloud.com:10373` 可用 |
| GPU | NVIDIA GeForce RTX 5090，32,607 MiB；结束时约 22,242 MiB 使用，GPU 利用率 0% |
| detector | 8870 健康；PID 4842；16 类；路由 `shadow` |
| Qwen3-VL | 8890 `/v1/models` 健康；PID 3904 |
| 本机 | 前端 3000、FastAPI 8000、双隧道 8870/8890 均健康 |

## 真实链路结果

- 正常有目标样本：类 10“盲蝽科”检测 1 框，置信度约 `0.9437`；自动状态 `conclusive`；Qwen3-VL 使用 `phase9-multimodal-v2`；严重度 `low`；完整分析约 `4.53s`；报告生成成功，含 5 个来源和安全说明。
- 无目标样本：后端状态 `no_supported_target`，风险为高，给出补拍动作，并保留仅重试综合分析入口；页面主标题存在候选诊断泄漏问题。
- detector 故障：返回 `service_unavailable`，病例仍保存，提示服务恢复后重试。
- Qwen3-VL 故障：病例和检测结果保留，接口 HTTP `502`；恢复后仅重试分析成功，无需重新上传。
- FastAPI 重启：健康检查、病例详情、报告和趋势仍可访问。
- 数据库：`integrity_check=ok`；当前 29 条记录均为测试记录，普通历史/趋势为 0，管理区可追溯。

## 模型与评分证据

- 当前线上主模型仍是 `official-plus-public-weak-v1-e120-b64`，SHA 前缀 `cbb26d83`；官方冻结 833 张基线为 Precision `0.839196`、Recall `0.776205`、mAP50 `0.827517`、mAP50-95 `0.548224`。
- Qwen3-VL 既有 160 张证据：成功率和 Schema/内容/田间输入引用 100%，Top-1 `87.50%`，冲突识别 `15/17=88.24%`，不安全输出 `0`，风险错误清除 `0`，完整链路 P95 `5.105s`。
- 六模型对照已完成，但 YOLO12s 最终冻结结果低于线上基线（mAP50-95 `0.523463`），不切换；类 10/13 专家 active 反事实下降，继续 `shadow`；类 8/15 没有独立专家冻结证据。

## 自动化与浏览器检查

- 后端：`24 passed`。
- 前端：build 和 6 个 render tests 通过；lint `0 errors`、5 个既有 `<img>` warnings。
- 浏览器：普通导航不展示管理入口；首页上传入口、桌面 DOM、390×844 视口和键盘焦点基础检查通过。Chrome/Edge 的完整人工用例仍待用户执行。

## 证据文件

- `artifacts/server/phase9-real-test-20260813.json`
- `artifacts/server/phase9-detector-smoke-20260813.json`
- `artifacts/server/phase9-detector-failure-20260813.json`
- `artifacts/server/phase9-failure-recovery-v3-20260813.json`
- `artifacts/server/phase9-post-remediation-multimodal-evidence-20260812.json`

Phase 9 保持 `in_progress`；用户完成当前电脑 Chrome/Edge 人工测试并反馈前，不进入 Phase 9.9 最终 UI 重构。
