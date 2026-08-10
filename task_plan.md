# Task Plan: 第三届“农信杯”农作物病虫害识别与防治系统

## Goal

完成一个可复现、可演示、可解释的多模型协同农作物病虫害识别与防治系统：在冻结的官方验证集上可靠评估，针对弱类定向优化，将真实模型接入网页与后端，并形成比赛提交材料。

## Next Step

Phase 8 已完成。下一步是复核本地提交并由用户手动推送 GitHub，然后按 `docs/competition/demo-runbook.md` 做赛前演练；若继续优化，应优先针对当前 1/17（5.88%）的视觉/多模态错误冲突识别能力建立独立改进门，不得因此开启 active 或重训。

## Current Phase

Phase 8 — 真实多模态端点与一键完整分析（complete）

## Mandatory Karpathy Guidelines

后续所有代码与配置工作必须遵守：

1. 修改代码前先列出并核对假设；存在高影响歧义时先停止并说明。
2. 优先采用满足需求的最简单实现，不添加未要求的抽象或配置。
3. 避免无关重构；每一处修改都必须能直接追溯到当前任务。
4. 所有修改必须有明确、可重复的验证方法，并在修改后立即执行。
5. 修改范围只包含任务直接相关文件；保留用户已有改动，尤其不修改或提交未跟踪的 `CLAUDE.md`。

## Resume Protocol

新对话或上下文清空后，按顺序执行：

1. 完整读取 `task_plan.md`、`findings.md`、`progress.md`；Windows PowerShell 使用 `Get-Content -Raw -Encoding UTF8`。
2. 检查 `git status --short --branch`，保留用户已有改动。
3. 确认当前服务器是否开机、地址是否仍有效；不要默认继续使用旧服务器。
4. 从本文件的 `Next Step` 继续，不要重跑已经标记 complete 的实验。
5. 每完成一个阶段，同步更新三个规划文件；完成本轮工作后的总结性回复使用下方固定模板，不只汇报局部操作。

## End-of-Task Reporting

默认每次小任务结束后的最终汇报只包含：

1. 当前小任务完成了什么。
2. 下一个小任务要做什么。

只有用户明确要求项目全局汇报，或上下文接近上限触发下方协议时，才额外包含：整体计划/目标进度、已完成优化、当前阶段及目的、后续优化、模型数量、最佳模型和数据集构成。模型数量仍须区分训练实验与保留模型角色，数据集仍须区分训练、验证、独立评测和仅审计未采用的数据。

## Context-Capacity Reporting Protocol

当上下文占用率接近上限、即将发生压缩或需要开启新对话时，任务结束汇报自动升级为项目全局状态报告，即使用户没有再次提出要求。报告必须说明：

1. 整体项目计划与最终目标目前进行到哪一步。
2. 已完成哪些阶段和优化；当前正在做哪一步、目的是什么。
3. 后续还需要完成哪些优化、验证和交付工作。
4. 当前训练实验数量与保留模型角色数量（分开统计）、目前最好的模型及依据。
5. 当前数据集组成，并区分训练、官方冻结验证、独立 tune、独立 frozen/test、仅审计未采用数据。
6. 当前所在阶段、阶段状态和下一阶段入口。

该全局报告发出前，先把最新状态、指标、模型/数据口径和下一步写入 `task_plan.md`、`findings.md`、`progress.md`；报告结尾明确提醒用户开启新的对话以继续工作。上下文未接近上限时，继续使用上面的简短小任务汇报模板。

## Phases

### Phase 1: 项目迁移与系统基础

- [x] 将既有实现谨慎迁移到当前 Git 仓库
- [x] 保留用户内容并确认工作区边界
- [x] 建立网页诊断、FastAPI 后端、远程视觉推理接口
- [x] 建立人工复核页与实时训练监控页
- **Status:** complete

### Phase 2: 官方数据审计与基线

- [x] 审计官方 4,164 张图片、5,920 个检测框、16 类
- [x] 固定随机种子 `20260729`
- [x] 固定 3,321 训练、833 验证，隔离 10 个冲突重复样本
- [x] 训练并独立验证 YOLO26n 官方基线
- [x] 导出 ONNX，保存指标、权重和复现配置
- **Status:** complete

### Phase 3: 补充数据与人工复核

- [x] 审计 `C:\编程大赛数据\Dataset\图片` 与 `pest65`
- [x] 完成自动预标注和人工标注复核流程
- [x] 仅使用有明确类别映射、检测框、许可证和低重复率的公开数据
- [x] 保存公开数据来源审计和固定清单
- **Status:** complete

### Phase 4: 弱类优化与独立校准

- [x] 完成类 8/15 专项混淆与困难样本审计
- [x] 完成类 6/12 专项混淆与困难样本审计
- [x] 建立类 10/13 专家分类器及第一轮阈值校准
- [x] 准备类 10 的 SciDB 独立 tune/test 清单
- [x] 建立类 13 ZIP 自动审计、人工复核门控和可移植冻结清单工具
- [x] 下载并独立人工复核类 13 现场检测样本
- [x] 对新样本进行哈希去重、框质量检查和候选冻结划分
- [x] 执行类 10/13 第二轮校准并与第一轮对比
- [x] 根据冻结结果决定是否继续小规模微调或从头训练
- **Status:** complete

### Phase 5: 多模型协同生产集成

- [x] 将主检测器与类 10/13 专家模型接入服务器推理链
- [x] 根据校准结果实现逐类阈值与专家路由（默认 shadow，active 需显式开启）
- [x] 在网页完成真实图片端到端识别验证（`phase5-e2e-class10.jpg`，本地网页→FastAPI→远程 shadow 推理链路成功）
- [x] 测量准确率、延迟、吞吐、显存和模型大小（官方冻结验证集 + RTX 5090 主模型基准 + shadow 路由 HTTP 压测）
- [x] 所有实验接入实时监控并保留配置、指标、权重（训练监控 20 个运行、四个保留模型角色、实时健康探测及证据清单已固化）
- **Status:** complete（`phase5-full-evidence-20260810.json` 已生成并校验；active 仍不允许）

### Phase 6: 防治知识与可信交互

- [x] 建立 16 类知识卡片、来源登记和非化学/综合防治安全边界（明确为 general IPM orientation，不输出药剂剂量）
- [x] 将知识卡片、检测框、置信度和模型路由证据接入诊断结果
- [x] 完善低置信度、无目标和候选冲突结果的人工复核闭环
- [x] 验证建议不得越过证据范围，并保留来源版本与复核审计记录
- **Status:** complete（Phase 6 安全知识/解释性/复核闭环已通过后端、网页和接口验证；后续可在有逐类权威标签时扩展知识来源）

### Phase 7: 比赛材料与最终交付

- [x] 完成系统架构、数据治理、实验对比和创新点材料（含答辩幻灯片提纲）
- [x] 固化演示流程和离线容错方案（含真实识别和无模型降级路径）
- [x] 完成最终回归测试与复现检查
- [x] 审核公开仓库和比赛提交包
- **Status:** complete（材料五件套、标准库复现门、服务探测和发布边界检查均通过；active 仍禁止）

### Phase 8: 真实多模态端点与一键完整分析

- [x] 在 RTX 5090 隔离环境部署 Qwen3-VL-8B-Instruct/vLLM，并提供可重复启动、停止、状态和隧道入口
- [x] 将后端多模态请求改为 OpenAI 兼容接口，增加严格结构校验、风险升级与模型溯源
- [x] 将网页主操作改为一键上传、检测和多模态分析，并完整展示 C 项字段与失败重试
- [x] 完成真实网页 E2E、16 类分层验证、准确率/完整率/延迟/吞吐/显存/模型大小测量
- [x] 更新比赛材料、证据清单和三份规划文件
- **Status:** complete（160/160 成功、Top-1 86.25%、结构校验 100%；冲突识别 5.88% 为已记录限制，active 仍禁止）
- **Final gate:** `phase8-final-repro-v1` 通过，25/25 必需文件、Phase 5/8 证据、公开边界和 8000/8870/8890/3000 实时探测全部通过。

## Decision Gates

1. 类 13 独立样本未完成许可证审计、人工复核和去重前，不启动第二轮校准。
2. 第二轮校准只使用独立 tune 集选阈值，frozen test 仅作一次最终比较。
3. 是否从头训练由冻结验证提升、弱类召回、误报和部署成本共同决定，不因新增数据而自动重训。
4. 官方 833 张验证集保持冻结，禁止因弱类结果调整划分。
5. 原始图片、标注、模型权重、私钥和大归档不进入公开 Git 仓库。
6. Phase 8 只补齐解释端点和一键闭环；类 10/13 独立 frozen 门未通过前，任何多模态结果都不能批准 detector active 路由。

## Key Questions

1. 类 13 候选公开数据能否合法下载、检测框质量是否足够、与官方数据重复率是否可接受？
2. 第二轮校准是否能改善类 10/13，同时不损害其他类别和总体指标？
3. 专家模型路由带来的准确率收益是否大于延迟与维护成本？
4. 是否需要第二轮从头训练，还是阈值校准与专家路由已经满足比赛需求？

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 官方划分使用种子 `20260729` 并永久冻结 | 保证实验可比较，避免验证集泄漏 |
| 当前生产候选使用补充弱类数据训练的 16 类模型 | 相比官方基线更适合作为后续协同主模型 |
| 类 10/13 使用专家分类器和独立校准 | 两类存在专项混淆，逐类路由比盲目全量重训风险低 |
| 先小规模试验，再决定从头训练 | 节省 GPU 成本并避免低质量公开数据破坏整体性能 |
| GitHub 只发布代码与可公开元数据 | 避免泄漏原始数据、权重、密钥并控制仓库体积 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| GitHub CLI 的 `ghu_` GitHub App 令牌无 `CreateRepository`/写入权限 | 1 | 用户在 GitHub 网页创建公开仓库，随后使用 Git Credential Manager 标准授权推送 |
| Chrome 自动控制 GitHub 创建页多次超时 | 2 | 停止重复自动尝试，明确让用户手动点击一次“创建存储库” |
| PowerShell 双引号提前展开远程 Bash 命令 | 1 | 改用 PowerShell here-string 通过 SSH 标准输入发送脚本 |
| SSH here-string 的 CRLF 影响最后一条 Bash 命令 | 2 | 对关键检查改用单行远程命令或避免续行末尾参数 |
| 恢复服务器时首条远程命令再次被 PowerShell 提前展开 `$f`，随后标准输入脚本末尾受行尾影响 | 2 | 停止使用远程循环/here-string；改用不含远程变量的单行命令并成功完成检查 |
| 远程 `/root/autodl-tmp/crop-pest-system` 不是 Git 工作树 | 1 | 将本地仓库作为代码真源，只向远程同步经过验证的训练工具和必要数据 |
| 长内联合成测试被本机安全策略拒绝 | 1 | 改为仓库内可重复运行的标准 `unittest`，本机与服务器均通过 |
| 服务器非交互 shell 中 `python` 不在 PATH | 1 | 改用明确解释器 `/root/miniconda3/bin/python` 完成编译和测试 |
| GHCID 类 13 全量数据约 31.2GB，当前服务器空间和选择性下载条件不合适 | 1 | 暂不下载，改为审计更小且有 CC BY 4.0 的检测数据候选 |
| Windows PowerShell 默认 `Get-Content` 将无 BOM UTF-8 中文显示为乱码 | 1 | 后续读取规划文件显式使用 `-Encoding UTF8` |
| Windows `python.exe` 命中 Microsoft Store 占位启动器，`session-catchup.py` 无输出并退出 1 | 1 | 改用 Codex 工作区依赖提供的 Python，恢复检查成功完成且无未同步输出 |
| Roboflow 动态页面 DOM 在内置浏览器中连续超时 | 2 | 停止重复 DOM 抓取，改用精确公开搜索核对数据集元数据；下载仍保留为登录后人工/浏览器步骤 |
| Roboflow 选择 YOLOv11 后点击 Continue，完整 DOM 读取超时并重置控制连接 | 1 | 改用轻量标签定位；发现流程短暂进入 `/fork`，推断下载前需要创建账户内副本，等待用户确认该外部变更 |
| 重连后 `/fork` 标签页已不在可接管列表，仅剩原数据集页 | 1 | 不臆测页面状态；回到原数据集页，在获得 Fork 授权后重新走直接 YOLOv11 路径 |
| Fork 对话框的 DOM 节点在点击时变为 stale | 1 | 未重复旧节点；重新读取页面并改用可访问角色定位对话框中的最后一个 `Fork Dataset` 按钮 |
| Playwright 角色定位未识别 Fork 对话框中的第二个同名按钮 | 2 | 未提交；第三次改为同一调用内读取可见 DOM、提取末尾 Fork 节点并立即点击，避免跨调用失效 |
| Web 工具直接打开 Roboflow 版本 URL 被安全层拒绝，随后打开搜索结果出现解析错误 | 2 | 使用一次精确搜索结果作为公开元数据证据，不再重复直接打开 |
| 推送规划日志小修时 HTTPS 重置，随后 443 不可达 | 3 | DNS 正常但 HTTPS 超时；停止重复尝试，本地保留领先提交，网络恢复后补推 |
| 类 13 审计扫描外部对比库时遇到截断图片并中止 | 1 | 保持目标 ZIP 严格校验；外部对比库坏图改为记录路径与错误后跳过，并增加回归测试 |
| 终结门把 16×16 平均哈希距离 0 直接当成跨 split 完全重复，合成回归测试出现误报 | 1 | 保留近重复提示；增加解码像素 SHA 硬门，并要求跨 split 距离 0 接受项有显式 `[cross-split-distinct]` 人工标记 |
| PowerShell 在 `foreach` 代码块后直接接管道时报 empty pipe element | 1 | 先将循环输出收集到任务专用变量，再单独管道格式化 |
| Git 忽略审计命令再次在 `foreach` 后直接使用管道并触发相同解析错误 | 2 | 立即停止该写法，改为 `$ignoreResults` 收集后再格式化；将该模式固定为禁止重复 |
| 最终状态检查在 PowerShell 哈希表字段中内联多语句表达式导致括号解析失败 | 1 | 将 `check-ignore` 与退出码判断拆成独立语句后再构造结果对象 |
| 从仓库根目录用模块名启动类 13 回归测试时，同目录导入不在 `sys.path` | 1 | 改用测试文件的直接脚本入口，6 项回归测试全部通过 |
| 远程组合核对命令因 PowerShell 转义/远程引号组合超时 | 1 | 拆成不含远程变量的短命令后，清单、文件和哈希核对通过 |
| 远程核对命令未引用 `grep` 管道，超时后留下孤立 grep 子进程 | 1 | 定位并清理本次命令的精确 PID；改用不含管道的短检查，确认 GPU 仍空闲 |
| 第一轮第二轮校准报告的独立数据 baseline 指标全为 0 | 1 | 诊断发现类 10 SciDB 标签仍是专家数据集本地类别 0，且类 13 首张样本在 0.05 置信度下无预测；保留报告为无效诊断，先建立官方类 10 重映射副本并重新评估 |
| 首次类 10 重映射假设源标签只有类别 0，遇到类别 1；一次 `sed` 重写也因远程引号失败 | 1 | 阅读 `TARGET_TO_EXPERT={8:0,10:1}` 后建立全新副本，正确映射 `0→8、1→10`，不修改原始 SciDB 数据 |
| 远程 Python 诊断脚本嵌套引号被 Bash 剥离 | 1 | 改用 Base64 传递只读诊断脚本；确认类 13 首样本主模型在 conf=0.05 无预测框 |
| `CLAUDE.md` 是 `Invoke-WebRequest` 序列化输出而非完整 Markdown | 1 | 保持用户文件原样，不提交；按可见的谨慎原则执行并把实际 Phase 6 约束写入规划文件 |
| 使用 `Start-Process` 重启本地后端被安全策略拦截 | 1 | 只停止已确认的本地 PID，改用 detached Python 子进程恢复 8000 端口并验证健康接口 |
| PowerShell `Get-NetTCPConnection` 不接受端口数组 | 1 | 改用逐端口 HTTP 探测和单端口查询，未影响服务状态 |
| 在 `web` 工作目录读取 `web/package.json` | 1 | 纠正为当前目录的 `package.json`，随后 lint/build/test 均通过 |
| Phase 7 GitHub push 与只读 `git ls-remote` 遇到 HTTPS 连接重置/不可达 | 2 | 停止重复网络尝试；本地 Phase 7 commit 完整保留，网络恢复后 fast-forward 推送 |

## Notes

- 2026-08-07 本次恢复已确认当前 `Next Step`（填写类 13 人工复核并运行终结器）不需要服务器；第二轮模型推理与校准才需要 RTX 5090 服务器。
- 用户已确认类 13 复核建议；`review.csv` 已写入 138 条接受、4 条带理由拒绝及 9 条必要备注，严格终结得到 69 tune + 69 frozen，且 `calibration_eligible=true`。
- 2026-08-07 终结后探测旧 AutoDL 地址：DNS 解析到 `106.38.204.136`，但端口 `10373` 的 TCP 测试失败；未执行任何远程写入或 frozen 评测，等待用户开机或提供新地址。
- 服务器恢复后已同步终结数据和六个校准/审计工具；类 10+类 13 最终合并清单为 101 tune（32+69）和 85 frozen（16+69），候选阶段的 102/88 不再作为最终规模。
- 第二轮有效报告为 `artifacts/experiments/independent-field-calibration-10-13-v2/second-round-calibration-v2.json`：101 tune 上 3,888 个候选中 36 个通过 tune 门，选中 `background_threshold=0.9`、`score_mode=keep`、temperature10/13=`1.25/0.75`、threshold10/13=`0.15/0.15`；85 frozen 上类 10 mAP50-95 从 baseline `0.387952` 变为 `0.363993`，类 13 仍为 `0.0`，`frozen_acceptable=false`，决策 `keep_current_main_model`。
- 首次未映射标签的 `second-round-calibration.json` 只作为诊断记录；有效 v2 报告使用官方类别映射。第一轮报告使用 214 tune/833 official frozen，与本轮 101/85 独立数据不可作直接数值排名。
- 当前服务器在 2026-08-07 已完成关机前同步；恢复时先确认新地址和 GPU 状态。
- 2026-08-07 用户重新开机后，旧地址 `connect.bjb2.seetacloud.com:10373` 已恢复可用；RTX 5090 空闲、项目盘剩余 43G。
- 服务器类 10 的 48 张图片与标签已逐项确认存在；主模型和 crop 专家哈希与关机检查点一致。
- 公开仓库：`https://github.com/genghailong8-maker/crop-pest-multimodel-system`
- 草稿 PR：`https://github.com/genghailong8-maker/crop-pest-multimodel-system/pull/1`
- 关机检查点：`artifacts/server/shutdown-checkpoint-20260807.json`
- 当前本地分支在 Phase 7 本地提交后领先远程 1 个 commit；`git push origin codex/publish-audits-and-calibration-plan` 因 GitHub HTTPS 连接重置未完成，网络恢复后补推本阶段 commit。
- 规划文件是后续对话的首要上下文来源；任何关键发现应写入文件，而不是只保留在聊天中。
- 2026-08-10 Phase 5 恢复与收尾：SSH `connect.bjb2.seetacloud.com:10373` 已重新可用，RTX 5090 当前约 729 MiB 显存占用；远程推理服务已以 `shadow` 启动，三份模型均已加载且 SHA-256 与关机检查点一致。网页真实图片 E2E、准确率/延迟/吞吐/显存/模型大小测量及全量监控/配置/指标/权重固化均已完成；证据清单为 `artifacts/server/phase5-full-evidence-20260810.json`，`active` 仍禁止，下一步进入 Phase 6。

## Phase 7 Completion — 2026-08-10

- 比赛材料已固化：`docs/competition/architecture-and-innovation.md`、`demo-runbook.md`、`reproducibility-checklist.md`、`presentation-outline.md`、`submission-package.md`；README 已提供入口和复现命令。
- 演示流程覆盖本机后端、网页、远程推理隧道、知识/复核展示、训练监控，以及后端不可达、模型不可用、远程超时时的安全降级。真实识别仍以 Phase 5 已留存的浏览器 E2E 证据为准，当前 runtime 复核再次确认推理服务 16 类、三模型加载、shadow 路由。
- `scripts/final_repro_check.py --require-services` 通过：必需文件 20/20、知识契约 16 类/4 来源、Phase 5 证据与 16 类/3,321/833/101/85 口径一致、active 禁止、公开边界无禁用跟踪文件、后端/知识接口/推理隧道/网页均可达。
- 回归结果：backend `9 passed`（1 个既有 Starlette 弃用警告）；web `npm test` 通过（构建 + 3 路由渲染）；web lint `0 errors`、3 个既有 `<img>` warnings；相关 Python `py_compile` 和 `git diff --check` 通过。
- 生成的复现 JSON 保存在被忽略的 `artifacts/release/` 下，作为本机运行证据，不进入公开提交；拟提交范围仅包含代码、材料、规划和可公开元数据。用户未跟踪的 `CLAUDE.md` 仍不修改、不暂存。
- Git 提交已创建（本阶段本地 commit，推送待网络恢复）；首次 push 与随后一次 `git ls-remote` 均因 `github.com:443` 连接失败/重置停止重试，未发生远端部分写入。
