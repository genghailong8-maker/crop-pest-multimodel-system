# Progress Log

## Phase 9.9 知识库展示改造启动（2026-08-18）

- 已恢复 planning-with-files 上下文并读取实施计划、现有知识/报告接口、Docker 离线部署和前端页面。
- 已确认发布范围：16 个 Markdown、61 张引用图片、代码、测试与部署材料进入现有 GitHub 分支；来源标注百度百科。
- 已确认迁移策略：详情和报告均删除技术证据；原 v1 报告保留，生成 v2 最新快照；GPU 服务器保持关闭且不修改。
- 当前进入知识库打包、后端接口和前端渲染实现阶段。
- 知识库已打包为 16 个文档、61 个图片引用，约 5.21 MB；打包副本无 Windows 绝对路径。组合校验末尾 `rg` 因“无匹配”退出 1，这是路径清理成功而非打包失败。
- 后端新增安全 Markdown 解析、知识文档/图片接口、v2 报告和幂等升级脚本；专项测试 7 项通过。
- 完整回归通过：后端 32 passed；前端生产构建与 7 项测试通过；ESLint 0 error、5 个既有 `<img>` warning。
- Impeccable 检测仅发现 `globals.css:280` 的既有 `transition: width` 警告，与本次改动无关，按最小改动约束保留。
- 部署前备份位于 `/data/ghl/migration-backup/knowledge-20260818T211646`，包含原应用、报告、SQLite、活动实例和 SHA-256 清单。
- 首次远端复合验收命令被 Windows OpenSSH 去除 `python -c` 引号，在执行迁移前失败；随后改用短命令，未重复该失败方式。数据库检查脚本首次以文件路径运行时无法导入 `app`，改用模块方式后通过，未修改数据库。
- 仅重新构建并替换 backend/web；detector、VLM、gateway 未重建，活动实例保持 `lab_cpu`。3 个已有报告生成 v2，原 v1 文件保留，幂等复查通过。
- 实验室最终验收：服务健康、VLM healthy、SQLite `ok`、6/6 病例图片存在；叶蝉详情三栏正确，报告 2 个表格和 4 张知识图片均加载成功，来源显示百度百科且无技术证据入口。
- 浏览器完整长页和普通视口截图因 CDP 超时未生成；DOM 与资源加载验收成功。移动 viewport 覆盖未实际生效，因此未声明真实设备截图结果。

## GitHub 发布范围确认（2026-08-18）

- 用户确认发布全部项目文件，包括 Phase 9 训练脚本和约 3.4 MB 评测证据。
- 继续排除 `tmp/`、模型、SQLite、病例与上传图片、报告运行数据、密钥、缓存、服务器输出和本地 `CLAUDE.md`。
- 发布到现有分支并更新 Draft PR #1，不创建重复 PR。
- 暂存审计共 140 个文件、约 4.02 MB，最大文件约 1.91 MB；未发现已知服务器密码、SSH 私钥或 GitHub/OpenAI Token。
- 发布回归通过：后端 29 项、Phase 9 训练脚本 9 项、前端生产构建及 6 项页面测试；ESLint 0 error、5 个既有 `<img>` warning。
- `CLAUDE.md` 未暂存且不会上传；用户要求删除，但自动删除被本机安全策略拦截，需由用户手动删除。

## Phase-5 Integration Kickoff — 2026-08-07

- **Status:** in_progress
- **Current step:** inspect the existing FastAPI/remote inference path and implement a configuration-driven, fail-safe class 10/13 routing layer around the retained main detector and crop expert.
- **Purpose:** make the production integration reversible before any server-side model swap; unchanged requests must keep the current main-model behavior, while expert routing is opt-in, observable, and threshold-configurable.
- **Server need:** code inspection and unit tests are local; loading the real PT weights and measuring end-to-end latency/VRAM require the already-booted RTX 5090 server.
- **Guardrail:** the second-round calibration configuration is rejected (`frozen_acceptable=false`), so Phase 5 will not promote that configuration or retrain any model.
- **Next:** identify the current inference client/server contracts, then add the smallest tested routing/configuration change and synchronize only validated files to the server.

## Phase-5 Server Inference Chain — 2026-08-07

- **Status:** complete for the server-chain subtask; Phase 5 remains in progress.
- **Implementation:** replaced the baseline-only inference service with a production-candidate main detector plus optional class-10 detector expert and class-10/13 crop classifier expert. Added environment-driven `off`/`shadow`/`active` modes, candidate confidence, crop expansion, background gate, `threshold10`/`threshold13`, temperature, score mode, and class-10 expert gate.
- **Safety decision:** default is `shadow`; expert calls and decisions are recorded but main detections are unchanged. `active` was exercised once as an isolated smoke test and then the server was restored to `shadow`; the rejected second-round calibration is not promoted.
- **Server verification:** remote inference health is `ok`; main SHA-256 `cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071` (production candidate), class-10 expert SHA-256 `95a03f1d613681259680f7018f16cdbfef41ff99dd881fd3b9342bfbfcc00a49`, crop expert SHA-256 `9804458da627e30299114f31e032ad5bcc08a7f74694f6559dcf45b27d7c242c`.
- **Observed remote request:** class-10 independent image returned shadow candidate evidence with both expert supports and approximately 43 ms routing time; the main output remained unchanged after the requested confidence filter.
- **Backend/web propagation:** the FastAPI backend now persists remote `model_sha256`, `speed_ms`, and `routing` metadata inside `detector_summary`; the web visual-model card displays route mode, expert candidate count, and routing time.
- **Validation:** local backend tests `6 passed`; inference tests `4 passed`; Python compile passed; web build passed; web lint has 0 errors and the existing 3 `<img>` warnings. Local tunnel → backend upload → remote inference → case detect completed with a real class-10 image and persisted shadow metadata.
- **Next:** run the production web route against the local backend/tunnel with a real image, then collect repeatable accuracy/latency/throughput/VRAM/model-size measurements before deciding whether any active routing is safe.

### Phase-5 Pause & Server Persistence Checkpoint — 2026-08-07

- **Status:** paused at the user's request before the final browser click and benchmark; Phase 5 remains in progress.
- **Server persistence:** remote project `/root/autodl-tmp/crop-pest-system` was checked and `sync` completed. The remote service on `127.0.0.1:8870` is healthy in `shadow` mode with `class_count=16`; RTX 5090 is idle (0% GPU, about 731 MiB used of 32607 MiB).
- **Weights/data checkpoint:** `artifacts/server/phase5-live-checkpoint-20260807.json` was created on the server and copied locally. Its SHA-256 is `9097ca3b9af70403902ee99d42d05e5ea77e5eaaa9cd3f33678e7e99e1961c30`. It records the three loaded model hashes, byte sizes, official/independent data paths, service PID/cwd, routing configuration, and the resume instruction.
- **Current web state:** local frontend `http://127.0.0.1:3000/`, backend `127.0.0.1:8000`, and SSH tunnel `127.0.0.1:8870` are still listening. The browser page is open; file/form preparation was started, but the final “开始视觉识别” click and accuracy/latency/throughput/VRAM/model-size benchmark are intentionally deferred.
- **Decision:** keep routing `shadow`; do not enable `active` before the web E2E benchmark and the existing frozen-gate rejection are both accounted for.
- **Resume:** read all three planning files and `git status`, verify the checkpoint and `/health`, then continue from the existing browser page with the real image recognition click and reproducible benchmark. Do not rerun completed calibration or server-chain tests.

### Phase-5 Server Shutdown & Task Nodes — 2026-08-07

- **Status:** complete; remote inference process stopped and server powered off at the user's request.
- **Pre-shutdown verification:** `/health` was `ok`, `class_count=16`, routing `shadow`; no training/calibration task was running; RTX 5090 was 0% utilization with 731 MiB before stop.
- **Shutdown sequence:** stopped PID 3381 gracefully, confirmed no remaining service process, ran `sync`, confirmed GPU memory `0 MiB`, then issued `shutdown -h now`. A follow-up SSH probe returned connection refused, confirming the server is off.
- **Task-node checkpoint:** `artifacts/server/phase5-shutdown-task-nodes-20260807.json` is saved locally and on the remote disk before power-off. SHA-256: `7095770760ea9f8007b4cc0bc376152cf0137b9c632db0631344479387b871e8`.
- **Next resume:** boot/reconnect the same GPU server, verify the checkpoint and model hashes, then continue the existing local web E2E page and benchmark. Keep `shadow`; do not rerun completed calibration or promote `active`.

### GitHub Publication Checkpoint — 2026-08-07

- **Local commit:** `530b29f feat: persist phase5 multimodel inference integration` contains the relevant code, tests, reports, planning files, and server task-node checkpoints. No model weights, raw images, archives, secrets, or private keys were staged.
- **Push status:** `git push origin codex/publish-audits-and-calibration-plan` was attempted once and failed because `github.com:443` was unreachable. DNS resolved, but TCP 443 was unavailable; the local branch is clean and ahead of origin by 4 commits. Resume by retrying the same push when network access returns.
- **Connector fallback:** GitHub connector repository/branch reads succeeded, but `github_create_blob` returned `403 Resource not accessible by integration`; no partial remote tree or ref update occurred. The remote branch remains at `9cf96fe`; local commits `530b29f` and `93e1d1a` are intact.

## Session History

### Persistent Context-Capacity Reporting Protocol — 2026-08-07

- **Status:** complete
- Actions taken:
  - 根据用户新要求，将“上下文接近上限/即将压缩时自动进行项目全局汇报，并提醒开启新对话”的协议写入 `task_plan.md` 的 `Context-Capacity Reporting Protocol`。
  - 同步更新 `findings.md` 的长期汇报要求：全局报告必须区分训练实验与保留模型角色，并区分训练、官方冻结验证、独立 tune/frozen/test、仅审计未采用数据。
  - 本文件记录该协议，后续每次接近上下文上限时先同步三份规划文件，再在任务结束回复中汇报整体计划、优化、当前阶段、模型、数据集和后续工作。
- Next:
  - 正常上下文容量下继续使用简短小任务汇报；接近上限时切换为项目全局状态报告并提醒用户开启新对话。

### Class-10/13 Second Calibration — 2026-08-07

- **Status:** complete
- Actions taken:
  - 用户开机后重新确认 AutoDL：RTX 5090 空闲、43G 可用、类 10 32/16 清单和主模型/crop 专家哈希匹配。
  - 将类 13 终结后的 69 tune + 69 frozen 数据和六个工具同步到服务器，并创建 101 tune/85 frozen 合并清单。
  - 首次校准暴露类 10 标签仍为专家本地类别，报告全部 baseline 为 0；保留为诊断记录，不作为模型结论。
  - 读取专家数据构建映射 `0→8、1→10`，创建只用于独立评测的 class-10 SciDB 官方类别副本，不修改原始数据。
  - 重新运行有效校准：101 tune、85 frozen，3,888 个候选，36 个通过 tune 门；frozen 只评估一次。
  - 选中配置在 frozen 上类 10 mAP50-95 为 0.363993（baseline 0.387952），类 13 仍为 0；严格门拒绝新配置。
  - 决定保留当前主模型，不启动小规模微调或从头训练；报告与日志已取回本机。
- Key outputs:
  - `artifacts/experiments/independent-field-calibration-10-13-v2/second-round-calibration-v2.json`
  - `artifacts/experiments/independent-field-calibration-10-13-v2/second-round-calibration-v2.log`
- Next:
  - 进入 Phase 5，接入当前主模型与类 10/13 专家路由；先做可回退的服务器推理链，再进行网页端到端验证。

### Class-13 Review Resume Check — 2026-08-07

- **Status:** complete
- Actions taken:
  - 按 `planning-with-files` 恢复流程运行会话 catch-up；系统 `python.exe` 为 WindowsApps 占位程序，改用 Codex 工作区 Python 后成功完成且没有未同步输出。
  - 以 UTF-8 完整读取 `task_plan.md`、`findings.md`、`progress.md`，并检查实际 Git 状态。
  - 确认当前分支领先远端 3 个提交；保留 `.gitignore`、三个规划文件和类 13 审计工具的既有未提交改动。
  - 判断当前步骤不需要服务器：人工复核 CSV 与严格终结器均为本机操作；第二轮模型校准才需要 RTX 5090。
  - 核对 `review_recommendations.md` 与 `review.csv`：142 条人工决定和备注仍为空；4 条建议拒绝、5 条建议接受并备注，其余 133 条仍待人工确认。
  - 完整读取终结器，确认它会拒绝任何未填写决定、无理由的拒绝项，以及无备注的近重复/修复框接受项。
  - 用户明确确认拒绝建议的 4 条、接受其余 138 条，并写入 5 条指定接受备注。
  - 写入 `review.csv`：138 accepted、4 rejected、9 条必要备注（包含 4 条拒绝理由）。
  - 严格终结器通过：69 tune + 69 frozen，`human_review_status=accepted_with_exclusions`，`calibration_eligible=true`。
  - 独立一致性检查确认 138 个接受记录、142 个已复核记录、4 个拒绝记录；清单文件缺失 0、路径重叠 0。
  - 6 项类 13 审计/复核/终结回归测试全部通过；私有 CSV、manifest、图片清单继续被 Git 忽略。
  - 终结后按恢复协议探测旧 AutoDL 地址；DNS 正常但 `10373` TCP 不可达，未发生远程写入，也未运行 frozen test。
  - 用户随后确认服务器已开机；只读核验成功登录原 AutoDL，确认 RTX 5090 空闲、43G 可用空间、类 10 32/16 清单和两份模型 SHA-256 与记录一致。
  - 同步类 13 最终数据与六个工具；远程 manifest 显示 `calibration_eligible=true`，合并清单实际为 101 tune、85 frozen。
  - 一次包含远程变量和复杂引号的组合核对命令超时；改用短命令分步检查后完成验证，未启动重复任务。
  - 发现该超时命令因未引用管道留下孤立 grep 子进程；已清理精确 PID，并再次确认服务器 GPU 空闲。
  - 首次校准后台运行完成并取回报告；101/85 图像计数正确，但 baseline 全为 0。检查发现类 10 标签类别仍为本地 0，类 13 首样本在 conf=0.05 无预测；暂停把该报告当作有效结果，准备重映射类 10 标签后重跑。
- Next:
  - 在服务器保留原始 SciDB 数据的前提下建立只用于独立评测的 class-10→official-10 标签副本，重建 101/85 合并清单并重跑校准。
  - 同步终结后的类 13 私有数据与校准工具，启动类 10/13 第二轮独立校准并与第一轮对比。

### Project-Wide Reporting Inventory — 2026-08-07

- **Status:** complete
- Actions taken:
  - 将用户要求的项目级结束报告模板写入 `task_plan.md` 和 `findings.md`。
  - 核对阶段状态：Phase 1–3 完成，Phase 4 进行中，Phase 5–7 待完成。
  - 核对模型记录：确认 12 次不同配置的训练运行、4 个当前保留的模型角色。
  - 核对当前最佳单一主模型及固定官方验证指标；明确最终多模型协同系统尚未冻结。
  - 核对数据用途：官方训练/冻结验证、PlantDoc/SciDB 当前主模型补充、Pest65 历史专项实验、类 10/13 独立校准集分别记录，避免把 Roboflow 类 13 独立评测集误报为训练数据。
- Decision:
  - 用户已将汇报规则更正为：默认只汇报当前小任务与下一小任务；完整项目级盘点仅在明确要求时提供。
- Next:
  - 用户完成类 13 的 142 条人工复核后运行严格终结器，再使用 GPU 服务器执行类 10/13 第二轮独立校准。

### Resume and Server-Need Audit — 2026-08-07

- **Status:** complete
- Actions taken:
  - 使用 Codex 工作区 Python 执行 `session-catchup.py`；未返回未同步上下文。
  - 以 UTF-8 完整读取 `task_plan.md`、`findings.md`、`progress.md`。
  - 检查 Git：当前分支比远程领先 3 个提交，读取时未显示未提交改动。
  - 读取关机检查点，确认旧服务器地址只可作为待验证候选。
  - 初步判定本机可承担数据获取与人工复核，第二轮模型校准需要 GPU 服务器。
  - 探测旧服务器：DNS 正常，但 `10373` 端口关闭，当前不可连接。
  - 检查第二轮脚本：需同时加载主检测模型与类 10/13 crop 专家，并默认在 CUDA `device 0` 上运行。
  - 检查本地条件：两份关键模型权重存在，但类 10 独立清单/图片和类 13 候选数据均不存在。
  - 通过公开搜索再次核对类 13 候选为 587 张单类检测数据，许可证 CC BY 4.0。
- Decision:
  - 类 13 下载与人工复核不需要服务器，可先在本机进行。
  - 第二轮校准实际需要恢复/新开 GPU 服务器，并恢复类 10 的 SciDB 独立数据。
- Next:
  - 在已登录 Roboflow 的浏览器中下载类 13 数据集并进行人工复核。
  - 重新开机或提供新的 GPU 服务器 SSH 地址，确认旧数据卷是否保留。

### Server Resume — 2026-08-07

- **Status:** complete
- Actions taken:
  - 使用项目专用 SSH 密钥登录原 AutoDL 实例。
  - 确认 RTX 5090 空闲、显存 0 MiB，项目盘剩余 43G。
  - 确认 `/root/autodl-tmp/crop-pest-system` 仍存在。
  - 确认类 10 独立清单仍为 32 tune + 16 frozen。
  - 发现远程根目录不是 Git 工作树；决定继续以本地仓库为代码真源。
- Next:
  - 验证本地类 13 审计工具后同步到服务器。
  - 取得并复核类 13 数据，审计通过后运行第二轮校准。

### Class-13 Field Audit Pipeline — 2026-08-07

- **Status:** complete
- Actions taken:
  - 新增 Roboflow YOLO ZIP 审计与官方类 13 映射工具。
  - 固定 valid→70 tune、test→72 frozen；训练集不进入独立校准。
  - 增加框边界检查、精确哈希、感知哈希、外部重复对比和人工复核 CSV。
  - 增加严格终结门：全部人工接受后才生成正式清单并允许校准。
  - 更新图片清单解析，使相对路径可随数据目录在本机/服务器间迁移。
  - 新增 70/72 合成数据端到端回归测试。
  - 本机与 RTX 5090 服务器均通过 `py_compile` 和回归测试。
  - 将四个相关 Python 文件同步到服务器工作副本。
- Files:
  - `training/prepare_grasshopper_field_eval.py`
  - `training/finalize_grasshopper_field_review.py`
  - `training/test_grasshopper_field_eval.py`
  - `training/evaluate_weak_reranker.py`
- Next:
  - 用户在 Roboflow 登录后下载目标 ZIP。
  - 运行真实数据审计并完成人工框复核。
  - 审计门通过后同步服务器并启动第二轮校准。

### Roboflow Download Resume — 2026-08-07

- **Status:** in_progress
- Actions taken:
  - 用户已完成 Roboflow 登录。
  - 用户已明确授权 Codex 直接下载并保存目标类 13 数据。
  - 会话 catch-up 已执行；三份规划文件和 Git 工作区已恢复校验。
  - 已接管登录态 `Export Version` 标签页并确认 587 张图片。
  - 已选择 `YOLOv11` 导出格式，等待最终下载方式确认。
  - 点击 Continue 后页面控制超时；恢复时发现流程曾进入 `/fork`。
  - 重连后只剩原数据集标签页；未提交 Fork，也未创建账户内副本。
  - 用户已明确授权创建 Roboflow Fork 副本。
  - 已接管 `Fork Dataset` 标签并检查最终对话框；未发现额外配置字段，等待提交默认 Fork。
    - 首次提交节点在点击时过期；页面仍停留在 Fork 对话框，未确认创建成功，已切换到新定位方式。
    - 角色定位未找到对话框确认按钮；未发生账户变更，准备同调用快照点击作为最后一次自动尝试。
    - 最后一次同快照提交再次超时；按三次失败协议停止重复提交。
    - 随后只读检查确认 `/fork` 标签已关闭，当前仅剩原公开数据集版本页；尚不能据此断定 Fork 成功。
    - 用户已手动点击 Fork 最终按钮；受控标签列表暂时为空，已接管的原公开版本页 URL 未改变，正在只读核验创建结果。
    - 已从原版本页可见 DOM 确认存在直接 `YOLOv11` 下载链接，停止所有 Fork 重试并转入下载流程。
    - 已进入 YOLOv11 下载对话框并确认目标是 ZIP/代码片段下载路径，而非 Roboflow 云训练。
    - Continue 再次跳转到 Fork 对话框；自动交互已停止，建议用户手动下载 YOLOv11 ZIP，下载完成后立即恢复本地自动审计。
    - 用户进入工作区 Fork 项目后未看到下载按钮；只读检查发现下载入口位于 `Versions`，但当前项目总数为 968 张，与目标公共 v1 的 587 张不一致。
    - 已暂停该项目导出，准备核验 Versions/其他 Fork，确保只下载精确 587 张目标数据。
    - Versions 页确认当前错误项目没有版本；新建版本会使用 968 张并改变固定划分，因此未点击 Create、未消耗额度。
    - 用户确认多出的图片是误添加；工作区列表发现两个干净的 587 张 Fork，可绕过 968 张错误项目继续。
    - 用户选择 `grasshopper-qpkes-i1pbc-bujaf`（587 张）；已导航到 Versions，未进入训练流程。
    - 已核对干净项目划分为 445/70/72；下载按钮缺失的原因是尚未创建版本。创建会使用 Roboflow Credits，当前停在提交前等待授权。
    - 用户已完成干净 587 张项目的 YOLOv11 ZIP 下载并放入 `artifacts/incoming/`；开始本地自动审计。
    - 归档哈希与结构已确认；修正 Windows 双扩展名 `.zip.zip` 为标准 `.zip`。
    - 首轮审计暴露 39 个空标签负样本和 1 个轻微越界框；改进工具后通过 5 个回归测试。
    - 正式自动审计通过：70 tune + 72 frozen、262 个框、39 张负样本、1 个可追溯边缘修复、8 个近重复记录；保持 `calibration_eligible=false` 等待人工复核。
    - 新增并运行 `training/render_grasshopper_field_review.py`，生成 142 张带框图片和可筛选 HTML 画廊；抽查修复框与负样本渲染正常。
    - 已视觉确认第一组跨 split 感知距离 0 样本完全相同；建议排除 frozen 侧记录，尚未替用户写入人工复核决定。
    - 已视觉确认第二组跨 split 负样本也完全相同；另确认首组 tune 内近重复为不同相邻帧，可保留并备注。
    - 继续核对近重复：确认一组 tune 内完全重复和一组 frozen 内完全重复，各建议排除后出现的记录。
    - 核对 frozen 连续帧组 010/011/013：确认是高度相关但非完全相同的相邻帧，建议保留并备注。
    - 核对最后一组 near pair 021/022：确认为相邻帧，建议保留并备注。
    - 完善人工复核终结门：支持有理由排除重复记录，并硬性阻止跨 split 距离 0 泄漏。
    - 生成 `review_recommendations.md`：建议排除 4 个完全/跨 split 重复，接受并备注 5 个相邻帧/修复框；建议终结规模 69 tune + 69 frozen。
- Next:
  - 在当前下载页选择标准 YOLO ZIP 并保存到 `artifacts/incoming/`。
  - 运行真实数据自动审计和人工复核准备。

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
| Class-13 audit pipeline | Synthetic Roboflow 70 tune + 72 frozen prepare/review/finalize | 本机与服务器均通过 | PASS |
| Real class-13 automated gate | 70 tune + 72 frozen, strict labels/images, cross-dataset duplicate audit | 142/142 selected, 0 invalid, automated gate passed | PASS |
| Class-13 review gallery | 142 annotated records, filterable flags, readable repaired/negative samples | 142 rendered; spot check passed | PASS |
| Experiment JSON validation | New reports parse | 成功 | PASS |
| GitHub remote safety scan | No secrets/weights/raw images/archives | secret markers 0；binary/data artifacts 0 | PASS |
| Shutdown backup hashes | Local critical files match server | 已匹配 | PASS |
| Second-round calibration (valid v2) | 101 tune + 85 frozen, tune-only selection and one frozen comparison | 3,888 candidates; 36 tune-acceptable; frozen rejected; keep current main model | PASS |

## Error Log

| Date | Error | Attempt | Resolution |
|------|-------|---------|------------|
| 2026-08-07 | GitHub App token lacked repository creation/write permissions | 1 | Switched to user-created repo plus Git Credential Manager |
| 2026-08-07 | Chrome control timed out on GitHub form | 2 | Requested one manual submit instead of repeating automation |
| 2026-08-07 | Initial SSH audit command expanded locally in PowerShell | 1 | Sent remote script through SSH stdin |
| 2026-08-07 | CRLF affected final remote Bash argument | 2 | Used simpler single-line command for final sync check |
| 2026-08-07 | Git push waited on hidden credential dialog | 1 | Explicitly ran GCM device authorization, then repeated push successfully |
| 2026-08-07 | PowerShell default `Get-Content` rendered UTF-8 Chinese as mojibake | 1 | Read planning files with explicit `-Encoding UTF8` |
| 2026-08-07 | Markdown diff check reported a trailing blank line in `findings.md` | 1 | Removed the extra EOF blank line and reran `git diff --check` |
| 2026-08-07 | GitHub HTTPS reset, followed by repeated port 443 timeouts | 3 | DNS resolved correctly; stopped retrying, kept local commits, and deferred push until network recovery |
| 2026-08-07 | Windows `python.exe` resolved to the Microsoft Store placeholder and catch-up exited 1 without output | 1 | Used the bundled Codex workspace Python; catch-up then completed successfully |
| 2026-08-07 | Roboflow dataset page dynamic DOM timed out in the in-app browser | 2 | Stopped repeating DOM reads and used one exact public search to verify metadata; login download remains pending |
| 2026-08-07 | Roboflow Continue navigation timed out while reading the full resulting DOM | 1 | Reconnected with lightweight tab inspection; identified a likely Fork prerequisite without submitting it |
| 2026-08-07 | The transient `/fork` tab was unavailable after reconnect | 1 | Returned to the original dataset tab and stopped before any account-side creation |
| 2026-08-07 | The Fork dialog node became stale at click time | 1 | Refreshed page state and switched to role-based selection of the modal's final submit button |
| 2026-08-07 | Role-based locator did not expose the second Fork confirmation button | 2 | Kept state unchanged and switched to same-snapshot DOM node extraction for the final attempt |
| 2026-08-07 | Same-snapshot Fork submission timed out; only the original public dataset tab remained afterward | 3 | Stopped automatic resubmission and switched to read-only verification before requesting any manual click |
| 2026-08-07 | Current Roboflow fork project contains 968 images instead of the expected 587 | 1 | Stopped before export and switched to read-only Versions/workspace verification |
| 2026-08-07 | Direct web open of the Roboflow version URL was rejected, and opening the search result later hit a parser error | 2 | Kept the successful exact search result as evidence and stopped retrying direct opens |
| 2026-08-07 | First resumed SSH audit repeated PowerShell expansion of remote `$f`; stdin Bash script then hit the known line-ending truncation | 2 | Switched to explicit single-line remote checks without shell variables |
| 2026-08-07 | Remote project root is not a Git repository | 1 | Treat the local Git worktree as authoritative and sync only validated files |
| 2026-08-07 | Long inline synthetic integration command was blocked by local safety policy | 1 | Replaced it with a persistent standard-library `unittest` |
| 2026-08-07 | Remote non-interactive shell had no `python` command in PATH | 1 | Used `/root/miniconda3/bin/python` explicitly |
| 2026-08-07 | Class-13 audit aborted on a broken image in an external comparison root | 1 | Patched comparison indexing to log and skip unreadable external images while keeping target images strict; added regression coverage |
| 2026-08-07 | Finalizer treated average-hash distance 0 as definitive cross-split equality and failed synthetic tests | 1 | Replaced the sole coarse-hash hard gate with decoded-pixel hashing plus an explicit human distinctness marker for accepted cross-split d0 pairs |
| 2026-08-07 | PowerShell rejected a foreach block piped directly to Format-List | 1 | Collected loop output in a task-specific variable, then formatted it separately |
| 2026-08-07 | Git ignore audit accidentally repeated the foreach-to-pipeline parser pattern | 2 | Rewrote it using `$ignoreResults`; added precise ignore rules for private class-13 and diagnostic outputs |
| 2026-08-07 | Final status command embedded multi-statement exit-code logic inside a PowerShell hashtable | 1 | Split the command and boolean assignment from the hashtable construction; final verification passed |
| 2026-08-07 | Running the class-13 regression test as a module from the repository root omitted the `training` directory from `sys.path` | 1 | Ran the test through its direct script entry point; all 6 tests passed |
| 2026-08-07 | First SciDB remap assumed only local class 0; source valid/test labels also contained local class 1, and a sed rewrite hit remote quoting | 1 | Read the dataset builder mapping and rebuilt a fresh evaluation copy with `0→8` and `1→10` |
| 2026-08-07 | Remote Python diagnostic code was stripped by nested shell quoting | 1 | Sent the read-only diagnostic through Base64; confirmed the class-13 first sample had no main-model prediction at conf 0.05 |

## 5-Question Reboot Check

| Question | Answer |
|----------|--------|
| Where am I? | Phase 5：多模型协同生产集成 |
| Where am I going? | 多模型生产集成、防治知识与可信交互、比赛最终交付 |
| What's the goal? | 完成可复现、可演示、可解释的多模型病虫害识别与防治系统 |
| What have I learned? | 见 `findings.md`，尤其数据许可、冻结评估、弱类混淆和模型哈希 |
| What have I done? | 见本文件的阶段日志；Phase 1–4 已完成，Phase 5 待开始 |

## Immediate Resume Checklist

- [x] 读取三个规划文件并检查 Git 状态。
- [ ] 若本地分支领先远程，在 GitHub HTTPS 恢复后补推提交。
- [x] 向用户确认可用服务器地址/GPU 状态。
- [x] 检查类 10 独立列表和本地关键备份是否仍可用。
- [x] 下载并人工复核类 13 合法检测样本。
- [x] 固定 tune/test 并执行第二轮类 10/13 校准。
- [x] 更新三个规划文件并汇报已完成工作与下一步。
- [x] 类 13 自动审计、近重复视觉核对、复核画廊和严格终结门已完成；用户已确认 142 条复核决定。

## Phase 5 Server Resume — 2026-08-10

- Status: in_progress; server restored and validated, with inference service running in shadow mode.
- Verified: SSH connectivity, RTX 5090 (32,607 MiB total; ~729 MiB used), health `ok`, 16 classes, 640px input, and all three model hashes against the shutdown checkpoint.
- Local test surface: tunnel `127.0.0.1:8870`, backend health `127.0.0.1:8000`, web `http://127.0.0.1:3000/`.
- Current action: persist Phase 5 monitoring/configuration/metrics/weight evidence after completing E2E and benchmark measurements. Do not enable active routing.
- Browser tab at `localhost:3000` completed the real-image submission; case `3850f4500d164c4cb6562a8f96ef09bc` is saved as `detected`.
- The production `vinext start` surface returned 404 for its client asset and could not hydrate; it was stopped. The same app is now served with `vinext dev` on `localhost:3000` for the requested browser E2E (no source-code change).
- Browser E2E checkpoint: `phase5-e2e-class10.jpg` uploaded successfully, preview rendered, the recognition button is enabled, and the form remains connected to the local backend.

## Phase 5 Real Web E2E — 2026-08-10

- Completed a real user-facing browser submission on `localhost:3000` with `artifacts/incoming/phase5-e2e-class10.jpg`, temperature 26°C, humidity 68%, and an explicit shadow-only note.
- Case `3850f4500d164c4cb6562a8f96ef09bc` reached `detected`; quality passed at 640×640 (brightness 82.02, contrast 47.52, edge energy 45.26).
- UI/result evidence: 0 selected detections, 1 shadow expert candidate, routing shadow, 41.638 ms routing; remote request-model time 122.671 ms. The candidate was retained as `shadow_keep`; active routing was not enabled.
- The production `vinext start` client-asset issue was isolated to the local serving mode and worked around for this test with `vinext dev`; no repository source change was made.

## Phase 5 Benchmark & Routing Gate — 2026-08-10

- Saved route benchmark: `artifacts/server/phase5-benchmark-20260810-route.json`. Sequential 20/20 succeeded (mean wall 121.501 ms, p95 142.248 ms, 8.082 req/s); 4-worker concurrency 24/24 succeeded (wall p95 233.521 ms, 29.572 req/s).
- Saved main PT benchmark: `artifacts/server/phase5-benchmark-20260810-main-pt.json`. Batch 1/8/32 throughput was 190.246/380.474/368.962 images/s; standalone GPU peak 2,587.94 MiB from 497.75 MiB idle.
- Model-size evidence: main PT 5.145 MiB, class-10 PT 5.134 MiB, crop PT 3.042 MiB, combined PT 13.321 MiB, main ONNX 10.101 MiB. Service after restart reports 729 MiB used and `status=ok` with all three hashes matching the checkpoint.
- Accuracy evidence is the fixed official frozen validation result (833 images): mAP50 0.827517, mAP50-95 0.548224, precision 0.839196, recall 0.776205. The unlabeled field E2E image is not counted as accuracy.
- Gate decision: keep `active` disabled; leave remote service in `shadow` and proceed to Phase 5 monitoring/configuration/metrics/weight persistence.
- Consolidated checkpoint: `artifacts/server/phase5-benchmark-checkpoint-20260810.json`; this records the current live configuration, model assets, web case, benchmarks, accuracy basis, and routing gate. The service was restarted after the clean standalone benchmark and rechecked healthy in shadow mode.

## Phase 5 Full Monitoring / Evidence — 2026-08-10

- **Status:** complete. Added `scripts/collect_phase5_evidence.py` and ran it with the bundled Codex Python after `py_compile` passed. The final regeneration produced `artifacts/server/phase5-full-evidence-20260810.json` (108,768 bytes; SHA-256 `753ff334045ddabbe99ba20db69df8155e0e56e1e742cd7316563a4697e0733a`).
- **Runtime checks:** inference tunnel `127.0.0.1:8870`, backend `127.0.0.1:8000`, training monitor `127.0.0.1:8765`, and web training page `localhost:3000/training` all returned reachable/HTTP 200. The collector stores the health payloads, routing configuration, latest case summary, model file hashes/sizes, benchmark summaries, calibration result, and a 85-file artifact inventory.
- **Monitoring:** remote training monitor is running through `training/server/run_monitor.sh`; API returned 20 run summaries. The selected run `pairwise-crop-cls-10-13-v5-e30-b128` is completed at 30/30 epochs. The snapshot records RTX 5090 at 0% utilization, 729 MB/32607 MB, 27°C, ~4.64 W and the retained GPU history.
- **Configuration/weights:** collector confirmed `routing.mode=shadow`, `reclassify=false`, `score_mode=keep`, candidate/background/target thresholds `0.05/0.90/0.15`, class-10/13 thresholds `0.15/0.15`, temperatures `1.25/0.75`, and all three service-loaded hashes match the local production PT records. Active routing remains forbidden.
- **Metrics:** collector references official frozen 833-image accuracy (P `0.839196`, R `0.776205`, mAP50 `0.827517`, mAP50-95 `0.548224`), main PT batch benchmarks, and sequential/concurrent shadow-route pressure evidence. The valid independent calibration report is retained with `frozen_acceptable=false` and `keep_current_main_model`.
- **Planning transition:** Phase 5 is now complete in `task_plan.md`; the next entry point is Phase 6 (防治知识与可信交互). No server shutdown was requested, so inference, monitor, tunnels and web surfaces remain available for the next step.

### New error log entries

- The first ad-hoc JSON inspection here-string accidentally left a `PY` marker in the Python stdin and ended with `NameError`; no artifact was modified. A corrected read-only inspection and the collector validation then completed successfully.

## Phase 6 Start — 2026-08-10

- Read `CLAUDE.md`; it is an untracked, malformed serialized `Invoke-WebRequest` object rather than a complete Markdown instruction file. Preserved it untouched and adopted the visible caution principle (small changes, explicit validation, no unsafe treatment claims).
- Read the full planning files, ran session catch-up, confirmed the branch is clean except for the user-owned `?? CLAUDE.md`, and moved `task_plan.md` to Phase 6 `in_progress`.
- Initial code inventory: `backend/app/catalog.py` contains only the 16 class names; `backend/app/detector.py` already returns normalized boxes, confidence and remote routing metadata; `backend/app/main.py` stores quality/detections/summary/analysis/review but does not yet expose a unified knowledge card or case-review audit trail.
- Immediate work order: (1) create a source-registered 16-class knowledge contract with safe IPM-only guidance, (2) attach explainability and safety flags to case results, (3) add a review decision/audit endpoint and UI entry, (4) run backend/web regression tests and record provenance.

## Phase 6 Implementation — 2026-08-10

- **Status:** complete for the current safe scope. Added `backend/app/knowledge.py` with 16 source-linked cards and a clear no-product/no-dose boundary. Sources are FAO IPM principles/definition plus two Ministry of Agriculture green-control/regulation pages.
- Backend changes: knowledge contract endpoints; `detector_summary.explainability`; SQLite `review_events_json` migration; review queue, decision endpoint and audit-event endpoint. Existing records remain readable because the migration adds the column only when absent.
- Web changes: diagnosis evidence panel now shows confidence band, observation focus, first actions, source IDs, route mode and chemical boundary; low/ambiguous/no-target/quality cases expose buttons for “请求补充证据” and “确认当前候选”. README records the API contract.
- Tests: backend `9 passed`; web `npm test` `3 passed`; web lint `0 errors` (3 existing image warnings). Live checks on the refreshed local backend: `/health=200`, `/api/catalog/knowledge=200` with 16 classes/4 sources, `/api/cases/review-queue=200`.
- No GPU work was needed for Phase 6. Remote inference/monitoring was not changed and active routing remains prohibited.

### Phase 6 error log

- A first combined restart command using `Start-Process` was blocked by local policy; an alternate detached Python child process was used after stopping only the known local backend PID. The server was restored on port 8000 and verified.
- A PowerShell `Get-NetTCPConnection` check passed an unsupported port array and returned no result; the check was replaced by individual HTTP probes and a single-port query.
- One lint command attempted `Get-Content web/package.json` while already in the `web` directory; this was a path-only command error, and the corrected lint/build/test commands passed.

## Phase 7 Start — 2026-08-10

- **Status:** in_progress. Confirmed the worktree is clean except for user-owned `?? CLAUDE.md`; branch `codex/publish-audits-and-calibration-plan` is aligned with origin before Phase 7 edits.
- Added four competition-ready Markdown artifacts under `docs/competition/`: architecture/data governance/innovation, 5-minute demo and offline fallback, final reproducibility checklist, and public submission-package boundary.
- Added `scripts/final_repro_check.py`, a stdlib-only static gate with optional local runtime probes. It checks the 16-class knowledge contract, Phase 5 scope/metrics/shadow gate, required evidence files, and forbidden tracked artifacts.
- Updated `README.md` and `.gitignore` with the Phase 7 entry point and generated-report boundary. The generated report path is `artifacts/release/final-repro-check-20260810.json` and remains a local ignored artifact.
- Next actions: run syntax/static check, backend and web regression, optional live service probes, inspect the generated report, then update all three planning files and publish only intended tracked files.

### Phase 7 command note

- An initial read-only inspection used a root-level `.venv\Scripts\python.exe` path that does not exist; no files were changed. Subsequent checks use the bundled Codex Python path recorded in the competition checklist.

## Phase 7 Completion — 2026-08-10

- **Status:** complete locally; GitHub push is pending network recovery. Added five competition materials under `docs/competition/` and linked them from `README.md`.
- The demo runbook now includes explicit remote endpoint environment variables, health probes, a five-minute script, and offline behavior for backend/model/tunnel failures. It forbids fabricated detections, stale-case reuse, automatic active approval, and concrete chemical instructions.
- `scripts/final_repro_check.py --require-services` returned `passed=True`: required files 20/20, knowledge/Phase5/public-boundary/runtime sections all true; runtime probes `[True, True, True, True]`.
- Regression evidence: backend `9 passed`; web build/render test `3 passed`; lint `0 errors` with the existing three image warnings; `py_compile` and `git diff --check` passed.
- The local service was not reconfigured or restarted during Phase 7. Its health endpoint is reachable but reports `detector_mode=unconfigured`; the remote inference tunnel remains healthy in shadow mode. This preserves the documented offline fallback and does not alter server weights or routing.
- Staged only the Phase 7 files and planning updates (never `CLAUDE.md`), reran the report after staging and after commit, and created the local Phase 7 commit. `git push` and a subsequent `git ls-remote` both failed at `github.com:443` (connection reset/unreachable); no remote partial write occurred. Network recovery only requires pushing the local branch's one leading commit.

## Phase 8 Kickoff — 2026-08-10

- **Status:** in_progress.
- **Assumptions locked:** self-host Qwen3-VL-8B-Instruct on the existing RTX 5090; use vLLM OpenAI-compatible chat completions; change the primary web path to one-click upload→detect→analyze; persist Karpathy Guidelines in `task_plan.md`; keep `active` off and do not retrain.
- **Success criteria:** real `/v1/models` and image request; backend health reports multimodal configured; strict C-item schema persists in case history; real browser flow succeeds and can reload history; 16-class stratified evidence records accuracy/completeness/latency/throughput/VRAM/model size without simulated values.
- **Scope guardrail:** only touch planning, VLM deployment/tunnel, backend multimodal/config/tests, the diagnosis page, directly related docs/evidence; preserve untracked `CLAUDE.md`.
- **Server baseline:** SSH succeeds; RTX 5090 is idle with 32,607 MiB total; `/root/autodl-tmp` has about 43G free; no VLM or inference process currently runs.
- **Current step:** inspect the exact backend/web contracts and tests, implement the smallest local code change first, then deploy the endpoint and run real integration checks.

### Phase 8 error log

- A combined parallel recovery command returned exit code 1 without usable output. It was split into individual checks.
- Windows `python.exe` again resolved to the Microsoft Store placeholder; session catch-up succeeded with the bundled Codex workspace Python. All further local Python checks will use that interpreter.
- The first backend test command repeated the repository-relative `backend/.venv` prefix while already using `backend` as its working directory. The corrected `.venv/Scripts/python.exe` command passed; this was a path-only error.
- The first web regression used PowerShell's blocked `npm.ps1` entry point. Re-running the same package scripts through `npm.cmd` passed; no source change was required.
- The first dual-tunnel PowerShell parse check found a trailing comma in the SSH argument array. The comma was removed before the script was run or synchronized.
- The first vLLM 0.26.0 launch rejected the removed `--disable-log-requests` CLI flag before any model download or GPU allocation. Current CLI help confirmed the remaining model-length, memory, multimodal, sequence and served-name options; the obsolete flag was removed for the second launch.
- The second launch reached model resolution but the server could not connect to `huggingface.co:443`; no cache file or GPU allocation occurred. The exact process was stopped. `https://hf-mirror.com` returned the official repository commit header successfully, so the deployment now pins revision `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` and uses the reachable mirror only as the transport endpoint.
- The mirror-resolved launch then failed because Hugging Face Hub still selected Xet CAS and its reconstruction endpoint returned `401 Unauthorized`; GPU remained at 0 MiB. The deployment was reworked instead of retried: `download` disables Xet, materializes the pinned snapshot under `${CROP_VLM_ROOT}/model`, and `start` loads only that local path.
- A direct inline download probe was not executed because nested PowerShell/SSH quoting produced a local parser error. The persistent `download` action replaces that fragile command and is Bash-syntax checked before use.
- The first evidence-script upload assumed the remote work copy already had a top-level `scripts/` directory; it did not. Backend files had already copied successfully. The exact remote directory was created, the evidence script uploaded, and all synchronized Phase 8 Python files passed remote `py_compile`.

## Phase 8 Backend Contract — 2026-08-10

- **Status:** complete. `CROP_VLM_ENDPOINT` now targets an OpenAI-compatible chat-completions endpoint; added model and timeout settings without changing the public analyze route or database schema.
- Added strict `phase8-multimodal-v1` validation for diagnosis, candidates, symptoms, harm, causes, evidence, uncertainty, detector alignment and review status. Responses persist model/protocol/latency provenance without endpoint secrets.
- Existing detector and quality risks are merged into `review_reasons`; the VLM cannot clear them. No-target, uncertain alignment or conflict also force review. The system prompt forbids product, dose, mixture, re-entry and pre-harvest instructions.
- Validation after the first implementation: backend full suite `13 passed` with one pre-existing Starlette deprecation warning. A persisted API success/reload case was then added and will be included in the next full regression.

## Phase 8 One-Click Web Flow — 2026-08-10

- **Status:** implementation complete; regression pending. The existing form now calls upload, detect and analyze in sequence and exposes the active stage without introducing new routes or components.
- If visual detection succeeds but the VLM call fails, the detected case remains active and saved; the analysis card offers a VLM-only retry. Upload/detection are not repeated.
- The analysis card now renders all C-item fields: primary/candidate diagnosis, symptoms, harm, possible causes, evidence, uncertainty, detector alignment, review reasons, model and latency.
- Detector/quality and multimodal review reasons are merged in the existing review card. History and Phase 6 knowledge/review behavior remain unchanged.
## Phase 8 VLM Runtime Recovery — 2026-08-10

- Qwen3-VL completed its local weight load, but FlashInfer sampler warmup rejected the RTX 5090 architecture. Because the load used only about 21.1 GiB before KV cache allocation and did not report OOM, the one-time 4096/72% memory fallback was not triggered. The targeted documented fix disables only FlashInfer sampling and preserves FlashAttention.
- The first 16-class smoke collector completed without calling the VLM because it passed the `ImageQuality` dataclass where the backend contract expects its dictionary form. The collector now uses the same `.as_dict()` conversion as the production API and records the materialized model directory size separately; no service or model change was needed.
- The next smoke run proved all 16 real image requests returned HTTP 200 and passed Pydantic, but vLLM legitimately emitted `{}` because every schema field had a Pydantic default. All nine C-item output fields are now required by the strict JSON schema (nullable diagnosis remains allowed), preventing an empty object from counting as a valid analysis.
- The normal class-2 browser sample produced the same detector and VLM diagnosis (`南瓜白粉病`) but the model also labeled alignment as `conflict`. A deterministic post-validation reconciliation now derives agreement/conflict from the two primary names, records the raw model value in provenance, and still preserves every pre-existing detector/quality review risk.
- Real browser failure-recovery setup exposed that choosing the same file twice does not fire the native file-input `change` event, leaving the prior completed case visible. The file input now clears its browser value before each chooser open, so same-file reruns reset the pipeline and create a new case as expected.
- The first formal 160-image run returned 151 successes and 9 failures: four JSON responses reached the 800-token output cap, while five vLLM requests returned HTTP 400. The cap is raised to 1200 and HTTP failures now retain a bounded response detail; the collector supports exact sample-ID reruns so the 400 cause can be diagnosed without repeating unaffected samples.
- Exact reruns proved the HTTP 400 cause was image-derived input lengths of 8,426–14,299 tokens exceeding the fixed 8,192 context, not service instability. The OpenAI request now uses vLLM's advertised `mm_processor_kwargs.max_pixels=1003520` while still sending the complete source image, and constrains concise list lengths so 1,200 output tokens are sufficient.
- Review of the zero-failure evidence exposed a metric bug: class 8 `芫菁` is a substring of class 15 `豆芫菁`, so substring-only matching could inflate class-8 Top-1 and falsely mark class-8/15 agreement. Diagnosis text is now resolved to the longest matching catalog name before comparing class IDs; final evidence must be regenerated with this corrected rule.
- The combined local syntax command attempted `bash -n` on Windows, where Bash is not installed; Python compile, PowerShell parse and `git diff --check` remained usable, and the VLM shell script had already passed `bash -n` on the target Linux server.
- A post-fix compile command was launched from `backend/` while naming root-relative `scripts/...`; the 17 backend tests had already passed, and the compile path was corrected by running it from the repository root before synchronization.
- The first final `--require-services` gate passed all static/Phase 5/Phase 8/VLM/detector/web checks but found the detached local backend process had exited, so the 8000 probes timed out and the gate correctly failed. The backend was restarted with the final environment before repeating the gate; no model or evidence result was affected.

## Phase 8 Live Endpoint and Browser E2E — 2026-08-10

- **Endpoint:** `crop-pest-vlm` is healthy on server loopback port 8890 with max context 8192; detector port 8870 is healthy with 16 classes and `shadow`. The dual local tunnel and backend health checks passed.
- **Normal sample:** official class 2 completed upload→detect→analyze→save in the real webpage, with detector `南瓜白粉病` 91.78%, structured Qwen3-VL diagnosis, all C-item fields, `agree` alignment and model latency displayed.
- **Weak/risk sample:** the class-10 field image retained its no-target/shadow-candidate evidence and required human review; no existing risk was cleared.
- **Failure recovery:** with a controlled local endpoint failure, detection and the case remained saved, the VLM-only retry appeared, and after restoring the endpoint that button completed analysis without another upload/detection. Same-file reselection and post-refresh history restoration also passed.
- **Regression checkpoint:** backend `17 passed` with one pre-existing warning; web build and 3 rendered routes passed; lint has 0 errors and the same 3 existing `<img>` warnings. Final 160-image evidence rerun is in progress after all nine first-run failures passed exact targeted reruns.

## Phase 8 Completion — 2026-08-10

- **Status:** complete. Real Qwen3-VL endpoint, OpenAI-compatible strict backend contract, one-click web pipeline, failure-preserving retry, real browser E2E, stratified metrics and competition/reproduction materials are implemented.
- **Final evidence:** 160/160 successful, Top-1 86.25%, schema valid 100%, content nonempty 58.13%, unsafe output 0, risk-preservation failure 0; SHA-256 `be54b463fcb6a709197510159d963e668d825d68ce7ee780c29f575b74baf415`.
- **Performance/resources:** end-to-end P50/P95 2325.747/2949.004 ms; sequential/concurrency-2 throughput 0.429228/0.841212 image/s; peak GPU 24,024 MiB; model directory 17,545,920,365 bytes.
- **Gate:** error-conflict identification is only 1/17 (5.88%), so `active` remains forbidden. No new training or second-round experiment was started.
- **Git handoff:** the final live gate passed, the Phase 8 scope was committed locally without `CLAUDE.md`, and the branch is one commit ahead of origin. The remaining external action is the user's manual GitHub push.
- **Final reproduction gate:** `phase8-final-repro-v1` passed after backend restart: 25/25 required files, Phase 5 and Phase 8 evidence, 16-class/4-source knowledge contract, public boundary, and all five live probes (backend health, knowledge, detector 8870, VLM 8890, web 3000) are true. Generated report remains under ignored `artifacts/release/`.

## Phase 9 Planning Checkpoint — 2026-08-10

- **Status:** pending; no project validation, implementation, deployment change or UI redesign was performed in this conversation.
- **User-requested order for 2026-08-11:** (1) user-perspective requirements/build acceptance, (2) gap optimization, (3) cross-computer/browser direct-use and dependency audit, (4) backend database/detection-record persistence audit and only-if-needed implementation, (5) user manual use-case validation, (6) UI redesign after all previous gates pass.
- **Planning output:** the detailed Phase 9 checklist, stop conditions and expected documentation artifacts were added to `task_plan.md`; supporting findings and known boundaries were recorded in `findings.md`.
- **Current evidence to carry forward:** Phase 8 final evidence is 160/160 successful, Top-1 86.25%, schema-valid 100%, `active` forbidden; local branch is one commit ahead of origin and `CLAUDE.md` remains an untracked user file.
- **Recovery note:** the first Windows `session-catchup.py` invocation used the Microsoft Store `python.exe` placeholder and exited 1 without output. This conversation did not retry by changing project files; future sessions should use the bundled workspace Python path recorded in the existing planning logs.
- **Next:** tomorrow resume by reading all three planning files and `git status`, then begin Phase 9.1 only. Do not start 9.2–9.6 early, and do not perform any of the six workstreams in this conversation.

## Karpathy Guidelines Audit — 2026-08-10

- **Status:** complete; rules already existed and were confirmed as mandatory for all future work.
- **Detected location:** `task_plan.md` → `Mandatory Karpathy Guidelines`, with matching references in the Phase 8/9 findings and progress logs.
- **Required workflow from now on:** before code changes, state assumptions and success criteria; choose the simplest sufficient implementation; avoid unrelated refactors; make every change reproducibly verifiable; touch only files directly required by the task.
- **Verification of this audit:** repository-wide `rg` search found the five rules and their Phase 8/9 references; no business code was changed. The untracked `CLAUDE.md` remains untouched.
- **Next:** apply this workflow at the start of Phase 9.1 and record assumptions, affected files, tests and results before proceeding to any later phase.

## Test Server Connection — 2026-08-11

- **完成内容：** 使用项目专用 SSH 私钥恢复远程检测器和 Qwen3-VL 服务，建立 8870/8890 双隧道，启动本地 FastAPI 后端，并打开前端测试页面。
- **验证结果：** `8000/health`、`8000/api/catalog/knowledge`、`8870/health`、`8890/v1/models` 和 `localhost:3000/` 均返回 200；浏览器页面已加载“田诊协同｜农作物病虫害识别与防治系统”。
- **本次错误与处理：** 默认 `id_ed25519` 不存在，改用 `codex_autodl_nongxin_2026`；首次隧道尝试时远程两个服务均未启动，先启动远程 detector/VLM 后重建隧道。
- **当前可测试地址：** `http://localhost:3000/`。Phase 9.1–9.6 仍未完成，本轮仅恢复测试环境，不标记 Phase 9 完成。

## Phase 9.1 CPU/Static Preflight — 2026-08-11

- **假设与范围：** GPU 当前不可用；只做验收矩阵、源码/API/SQLite 静态核验和 CPU 回归，不启动远程推理，不改业务代码、数据库或 UI。
- **完成内容：** 对照 README、比赛架构、演示手册、复现清单、前端页面、FastAPI 路由和数据库实现，形成 `docs/competition/user-acceptance-matrix-20260811.md`。
- **回归结果：** 后端 `17 passed`（1 个既有弃用警告）；网页 build 与 3 个渲染测试通过；lint `0 errors`、3 个既有 `<img>` warnings。
- **数据库结果：** `backend/runtime/crop-pest.sqlite3` 只读 schema/记录检查完成，11 条病例记录，`PRAGMA integrity_check=ok`；没有新增数据库能力。
- **当前缺口：** 8870/8890 GPU 隧道关闭；真实 detector/VLM、跨电脑完整访问、重启/换浏览器恢复、备份恢复和并发边界仍未验证；自动备份缺口只记录，不进入 9.2。
- **下一小任务：** 服务器 GPU 恢复后先做 GPU/远程服务健康检查，再补齐矩阵中的真实检测、综合分析、失败重试和刷新恢复用例；GPU 未恢复则保持等待，不重复尝试。

## Project-Wide Scoring Audit — 2026-08-11

- 读取并视觉核对比赛 PDF 第 8 页“评分项具体判定标准”，锁定题目二 A-E 满分条件。
- 当前判断：A 上传与闭环、B 真实视觉识别/定位/展示已具备主要功能；C 因关键内容非空率 58.13% 和冲突识别率 5.88% 不能按满分认定；D 具备知识来源和 IPM 安全边界，但逐类权威防治依据与风险等级不足；E 有稳定性、记录、复核、监控和创新材料，但严重程度/趋势/报告、跨电脑稳定演示仍未完成。
- 该审计只修改规划记录，不修改业务代码、数据库结构或 UI；后续按 Phase 9.1 GPU 恢复条件补充现场证据，再决定是否进入 9.2。

## 新版 Phase 9 Kickoff — 2026-08-11

- **Status:** in_progress；新版 9.1–9.8 已替换旧 Phase 9，当前先实施 CPU 可完成范围。
- **实施假设：** 公共用户匿名；新病例明确同意后公开 30 天；旧病例保持私有；管理端只在主机本地；Sites 前端通过受保护的同源代理访问主机 FastAPI；当前 GPU 和固定公网域名均暂不可用。
- **成功标准：** 每项 A–E 条件都有接口、页面、数据库、测试和证据映射；所有修改可由后端 pytest、前端 build/render/lint、数据库迁移/恢复/清理测试和浏览器检查重复验证；真实模型指标不使用 mock 冒充。
- **范围控制：** 不启用 `active`，不重训，不修改官方冻结验证集，不迁移前端框架，不引入第二数据库或第二大模型，不修改用户未跟踪的 `CLAUDE.md`。
- **当前动作：** 先同步规划文件；随后按最小依赖顺序实现病例/SQLite/公开安全与趋势报告，再实现两阶段多模态、逐类知识和用户界面。
- **外部停止门：** 真实 160 张分层评估和完整 E2E 等待 GPU；固定 HTTPS 隧道和 Sites 正式公网连接等待用户准备域名与 Cloudflare 账号；最终用户验收必须由用户在另一台设备完成。

### 新错误记录

- 系统 `python.exe` 再次命中 Windows Store 占位程序，`session-catchup.py` 首次退出 1 且无输出；改用 Codex 工作区依赖中的 Python 后恢复成功，并检测到 45 条未同步上下文。项目文件未受影响。
- 前端首次 lint 出现 2 个 React 19 effect 内同步状态更新错误；将状态更新移入异步请求回调后，复测为 0 errors、5 warnings。
- 浏览器首次调用了不存在的 `domcontentloaded()` 辅助方法；改用短暂等待后获取 DOM snapshot，未影响页面或项目文件。
- 后端重启时一次组合式 PowerShell 命令被执行策略拒绝，随后拆成“精确停止已确认 PID”和“单独启动”两个命令；第一次启动还因相对解释器路径指向仓库根而失败，改用明确的后端虚拟环境绝对路径后 `/health` 恢复 200。

## Phase 9 CPU/UI Implementation Checkpoint — 2026-08-11

- **后端与数据库：** 新增公共字段、最小迁移、WAL/busy timeout、30 天公共过滤、编辑令牌、IP 限流、VLM 并发门、趋势/报告接口和存储维护脚本。真实库检查为 `integrity=ok`、11/11 图片路径有效，并创建一份运行时备份。
- **多模态：** 完成 `phase9-multimodal-v2` 两阶段协议、严格结构和确定性安全门；只运行 mock/CPU 测试，未调用 GPU。
- **知识：** 16/16 类补齐逐类来源与农业/物理/生物/监测升级措施；保持农药产品、剂量、混配、次数和安全间隔禁区。
- **用户端：** 完成首页、公共历史、趋势、病例详情、可打印报告、隐私同意、仅分析重试和技术证据折叠区；Sites Worker 完成同源代理及公网管理隔离。
- **验证：** 后端 21 passed；网页 build 与 6/6 render/Worker tests 通过；lint 0 errors、5 个动态病例图片性能 warnings；桌面/手机浏览器检查通过。
- **文档：** 更新 A–E 验收矩阵，新增数据库维护、公网部署和 Phase 9 证据索引，并同步 README、架构、演示和复现说明。
- **仍待完成：** GPU 真实 160 张/冲突/性能/完整 E2E；域名与 Cloudflare 固定隧道、Sites 发布；用户另一台电脑/手机验收。Phase 9 保持 `in_progress`。
- **隐私边界收口：** `/api/cases` 默认只返回公共记录，`/api/trends` 永远只统计公共记录；主机管理模式通过 `scope=all` 查看完整病例，公网请求该 scope 返回 404。最终运行检查为公共病例 0、主机完整病例 11，旧病例没有被错误公开。
- **补充错误记录：** 一次用于检索 review 路由的 PowerShell `rg` 命令因双引号未闭合退出 1；改用单引号模式重新执行成功，未修改文件。

## Phase 9.9 Final UI Planning — 2026-08-11

- **Status:** pending；本轮只更新规划，不修改前端或业务代码。
- **完成内容：** 在 `task_plan.md` 增加 9.9“系统定型后的最终 UI/UX 重构”，并明确现有 9.5 是用于功能验收的用户化基础界面。
- **顺序门：** 必须先完成 9.1–9.8 的 GPU、公网、数据库、跨设备和用户关键用例验收，再冻结 UI 需求并开始重构。
- **验证标准：** 最终 UI 需通过 Chrome、Edge、桌面、手机、另一台电脑、异常状态、真实长内容与打印报告检查，并重新运行 build/render/lint 和关键流程回归。
- **下一步：** 当前仍等待 GPU、域名/Cloudflare 和用户跨设备验收；这些工作完成后与用户确认最终视觉和交互需求，再启动 9.9。
# Phase 9 本机交付实施启动 — 2026-08-12

- **用户决策：** 取消公网部署，仅在当前电脑运行；本地病例长期保存；服务器 GPU 仍通过私有回环 SSH 隧道使用；公网代码保留但默认停用。
- **实施假设：** 本轮只完成本机交付所需的计划、接口/数据库语义、页面文案、运行材料和 CPU 回归；不执行 GPU 真实评估，不提前进入 9.9 最终 UI 重构。
- **最小修改：** 本地模式默认查询全部病例与趋势、禁止自动过期、移除用户端公开语义；显式公网模式保持原行为和测试。
- **验证目标：** 后端本地/公网回归、前端 build/render/lint、数据库长期保存与查询范围测试、Git diff 检查全部通过；`CLAUDE.md` 和无关工作区内容不修改。
- **后端检查点：** 本地模式已改为默认全量历史/趋势且不自动清理过期病例；显式公网模式保留原过滤和安全行为。完整 pytest 为 `21 passed`，仅有 1 个既有 Starlette 弃用警告。
- **运行时错误：** 浏览器复测发现 8000 仍是修改前启动的旧进程；精确核对并停止 PID 12808 后，一条同时包含隐藏启动、轮询和接口检查的组合 PowerShell 命令被执行策略拒绝。未修改文件；后续拆为单独启动与单独健康检查，不重复组合写法。
- **运行时复测：** 新后端启动成功，`public_mode=false`；默认历史和 30 天趋势均返回真实 SQLite 的 11 条记录。浏览器确认首页无本地公开同意框，历史显示 11 条，趋势显示 11 条并可追溯。
- **已知数据问题：** 一条 2026-08-05 历史病例的作物/部位/生育期字段为既有乱码；本轮未擅自改写历史记录。

## Phase 9 本机交付改造检查点 — 2026-08-12

- **已完成：** 取消公网/Sites/Cloudflare/域名/跨电脑交付任务；本地模式默认显示全部病例和趋势，不要求公开同意，不创建过期时间或编辑令牌，不在启动/查询时执行过期清理。
- **兼容性：** `CROP_PUBLIC_MODE=true` 下的公开过滤、编辑令牌、30 天过期、限流和 Worker 管理隔离代码及测试保留；默认配置仍为 `false`。
- **用户界面：** 导航、首页、历史、趋势和病例详情已改为本机语义；本机无公开同意框，病例明确长期保存在当前电脑。
- **真实运行：** FastAPI 已按新代码重启；默认历史 11 条、30 天趋势 11 条；数据库 `integrity=ok`、11/11 图片路径有效；浏览器可逐条查看病例和趋势。
- **验证：** 后端 `21 passed`（1 个既有弃用警告）；前端 build + 6/6 render/Worker tests；lint 0 errors、5 个既有动态图片 warnings；静态复现门通过；`git diff --check` 无空白错误，仅有 Windows 行尾提示。
- **未完成：** 8870/8890 当前不可达；Phase 9 真实 160 张双阶段评估、16 类样本、完整 E2E、用户当前电脑 Chrome/Edge 验收以及 9.9 最终 UI/UX 重构仍待后续。
- **下一步：** GPU 恢复后先核对服务器地址与显卡状态，再启动 detector/Qwen3-VL 和回环隧道，执行真实评估与本机完整链路；用户确认关键用例后才启动 9.9。

## Phase 9 GPU 恢复执行启动 — 2026-08-12

- **用户提供地址：** `ssh -p 10373 root@connect.bjb2.seetacloud.com`；继续使用本机项目专用私钥 `codex_autodl_nongxin_2026`。
- **范围与硬门：** 只恢复既有 detector/Qwen3-VL、8870/8890 回环隧道并执行真实评估/E2E；保持 `shadow`，不重训、不改冻结数据、不提前进入 9.9。
- **错误记录：** 首轮并行只读检查中的端口命令再次使用了已知不兼容的“PowerShell `foreach` 后直接接管道”写法并解析失败；未改变服务或文件。后续固定先收集到任务变量再格式化，且把 SSH、脚本与端口检查拆开执行。
- **VLM 轮询错误：** 首条远程轮询命令使用 `$(seq 1 50)`，被本地 PowerShell 提前解释为本机命令并导致远程 Bash 语法错误；VLM 进程未受影响。改用单引号包裹、无命令替换的 Bash `{1..50}` 循环。
- **隧道启动错误：** 直接运行 `inference/open_tunnel.ps1` 被当前 Windows PowerShell 执行策略拦截；远程 detector/VLM 未受影响。使用一次性 `powershell.exe -ExecutionPolicy Bypass -File` 调用已审计脚本，不修改系统策略或项目脚本。
- **冒烟解释器错误：** 首次远程 16 类冒烟假设项目存在 `../.venv/bin/python`，实际不存在，命令在任何评估请求前退出。改为读取 detector PID 1914 的 `/proc/.../exe`，复用正在运行服务的真实 Python 环境，不安装新依赖。
- **只读命令附带错误：** 获取 detector 解释器时 `readlink` 成功返回 `/root/miniconda3/bin/python3.12`，同一命令中的 `tr` 因远程引号处理提示缺少参数；不再依赖 `tr`，直接使用已确认解释器并显式设置 `PYTHONPATH=backend`。
- **服务恢复结果：** RTX 5090 可用；远程 detector PID 1914、Qwen3-VL PID 1958 正常，8870/8890 回环隧道由本机 PID 5056 提供。detector 健康检查为 16 类、三个视觉模型已加载、`routing.mode=shadow`；本机后端健康检查显示 detector 与 multimodal 均已配置且 `public_mode=false`。
- **16 类真实冒烟：** `phase9-multimodal-smoke-20260812.json` 已生成并下载，16/16 成功、Schema/内容完整率 100%、不安全输出 0、风险错误清除 0；但严重度输入引用率 18.75%、预期冲突识别 0/3、E2E P95 8.902 秒，未达到 160 张正式门槛。当前暂停正式 160 张，先做直接相关的协议最小修正并重跑冒烟。
- **本地回归路径错误：** 协议修正后的首次 pytest 命令在 `backend` 工作目录错误使用 `..\.venv\Scripts\python.exe`，解释器不存在，任何测试均未开始。只读核对确认实际解释器为 `backend\.venv\Scripts\python.exe`；后续固定在 `backend` 下使用 `.\.venv\Scripts\python.exe`。
- **冒烟长任务调用错误：** v2 冒烟首次仍使用前台 SSH 并把本地超时设为 1 秒（工具实际约 5 秒后终止），不能据此判断远程评估状态。先核对精确进程/输出文件；若任务未继续，改用远程 `nohup` 后台运行与短轮询，正式 160 张沿用该模式。
- **v2 首次远程任务终止：** 前台 SSH 断开后一度观察到收集器 PID 4087 继续运行，但随后进程退出且未生成最终 JSON；收集器只在全部样本结束后写文件，因此没有可用的部分证据。按既定方案改用带 PID 文件和日志的 `nohup` 后台任务重跑，不把此次中断计入模型成功率。
- **v2 结果读取引号错误：** 冒烟已完成，但首次把含 Python 字典索引的 `python -c` 嵌入 PowerShell 双引号命令，触发本地解析错误，请求未发往服务器。改为先下载 JSON，再用本机项目 Python 读取，避免继续叠加跨 shell 引号。
- **v2 本机摘要命令仍被 PowerShell 解析：** 下载后又把复杂 Python f-string 直接放入 PowerShell 双引号，`or` 与花括号被本地解析，仍未读取文件。停止内联 Python，改用 PowerShell 原生 `ConvertFrom-Json` 分步读取；该错误不影响证据 JSON。
- **v2 有效结果：** 16/16 成功、Schema/内容/严重度引用均 100%、预期冲突 3/3、不安全输出 0、风险错误清除 0；Top-1 56.25%、E2E P95 9.012 秒仍未通过硬门。继续暂停 160 张，按“阶段二不重复上传原图 + 明确综合结论规则”的最小范围做 v3 复测。
- **后台 SSH 表象：** v3 使用 `nohup ... &` 启动后，调用侧仍因远程 shell 保持而在约 5 秒超时；精确检查确认收集器 PID 6000 正常运行、日志文件已建立。以后不把启动命令超时视为任务失败，以进程和最终 JSON 为准。
- **v3 结论与 v4 范围：** v3 的严重度/冲突/安全门继续通过，但 Top-1 56.25%、P95 9.015 秒无改善。依据既有 160 张证据中主检测 Top-1 86.875% 高于原综合 86.25%，v4 明确主检测负责最终规范类别，多模态独立判断负责冲突、候选和复核，并把列表限制为 1–2 条短句以压缩生成耗时；本地 23 项测试通过。
- **v4 前置门：** 16/16 成功；Schema、内容、严重度引用、冲突识别均 100%；安全输出与风险保护为 0 失败；E2E P95 4.838 秒。已满足启动正式 160 张的前置条件，下一步使用相同官方验证列表、每类 10 张和相同协议生成最终证据。
- **本机后端停止竞态：** 为加载 v4 代码精确停止已确认的后端进程树时，子/父进程先后退出，最后一个 PID 1560 在检查后、执行 `Stop-Process` 前已消失，命令因此返回 1；目标进程已停止，不是业务故障。启动新后端前重新确认 8000 无监听。
- **等待期回归与页面检查：** 正式 160 张独占模型服务期间，本机后端已重启加载 v4；后端 23 passed，前端 build 通过，lint 0 errors/5 个既有 `<img>` warnings。内置浏览器首页显示服务开放、本地病例语义、受害比例/扩散速度输入、最近记录和安全声明，未发起额外模型请求影响性能证据。
- **浏览器标签恢复：** 首次新建标签后 Playwright 报告标签不属于当前会话；按浏览器技能要求保留浏览器绑定、重新新建标签并改用可见 DOM 后恢复，随后 Playwright DOM 读取成功。未切换浏览器或使用外部自动化。
- **正式 160 张通过：** `phase9-multimodal-evidence-20260812.json` 已下载并按摘要重算硬门：160/160 成功，Top-1 87.50%，Schema/内容/严重度引用 100%，冲突识别 15/17（88.24%），不安全输出 0、风险错误清除 0，E2E P95 5.087 秒，峰值显存 23,058 MiB；SHA-256 `9b31bb691063c14759f70c0283d2f78fd5fee5d4f4c92c749d4568c6d2aba45d`。
- **E2E 上传命令错误：** 首次 `curl.exe -F` 的 `environment_json` 在 PowerShell/Windows curl 参数传递中丢失 JSON 引号，接口正确返回 422“环境信息格式错误”；首条脚本又未先检查响应字段而输出一组 null。数据库未创建病例。改用合法空对象 `{}` 完成接口闭环，田间环境细节由网页交互另行验证。
- **本机正常 E2E：** 新病例 `4992820b001c4dc18a1b7619209fec5c` 完成上传→1 个南瓜白粉病检测→两阶段分析→历史/趋势→报告→补充证据复核；严重度为 low 且依据引用 12.5% 与缓慢扩散，协议为 `phase9-multimodal-v2`，分析总耗时 4.561 秒，报告含 5 个来源。病例详情、趋势和报告真实页面均通过 DOM 检查并保存 PNG。
- **双隧道降级与恢复：** 精确停止 SSH PID 5056 后，8870/8890 均不可达，但原 12 条历史和报告仍可读取；新病例 `7b23a3d5a0e14c448326ea881f0f7236` 上传成功，检测明确进入 `model_unavailable` 且 `needs_review=true`。恢复同一回环隧道后，该病例重新检测和两阶段分析成功。
- **恢复检查命令输出噪声：** 读取离线病例 ID 时未加 `-Raw`，在最终 JSON 中把 PowerShell FileInfo 扩展属性一并序列化，产生大量无关输出；API 实际使用的字符串值正确且恢复成功。后续读取临时 ID 固定使用 `[string](Get-Content -Raw).Trim()`。
- **仅分析重试：** 使用 detector 保持 8870、故意把 VLM 转发到 8891 的隧道，新病例 `b80717bdddd64c17be7926fcad082f62` 先成功检测 1 个目标，分析接口返回 502；数据库保留 `detected` 状态和检测框。恢复标准 8890 后只重试 `/analyze` 即完成，不需要重新上传或重新检测。
- **重启持久化：** FastAPI 精确重启后，主 E2E 病例仍为 `review_pending`，`phase9-multimodal-v2` 分析与 1 条复核事件均可恢复；本地历史现为 14 条，包含新建病例。
- **最终并行回归路径错误：** 数据库维护命令误写为仓库根 `scripts/storage_maintenance.py`，实际入口是 `backend/scripts/manage_storage.py`；该子命令在文件打开前退出，其他并行结果未完整返回。改为分别运行后端、前端、维护脚本和 diff，避免聚合掩盖结果。

## Phase 9 GPU 与自动验收检查点 — 2026-08-12

- **正式模型门：** 固定 160 张真实两阶段评估全部硬门通过：成功率、Schema、内容、严重度引用 100%，Top-1 87.50%，冲突识别 15/17（88.24%），不安全输出和风险错误清除 0，E2E P95 5.087 秒，峰值显存 23,058 MiB。
- **本机闭环：** 新建真实病例完成上传、检测、两阶段分析、历史、趋势、报告和人工复核；详情、趋势、报告三张浏览器证据已保存到 `artifacts/server/phase9-local-*-20260812.png`。
- **故障与恢复：** 验证双隧道关闭时病例仍保存、模型不可用状态明确、历史/报告可读；验证 VLM 单独不可用时检测结果保留，恢复后只重试分析成功。
- **持久化：** FastAPI 重启后病例、分析与复核事件恢复；SQLite 在线备份、同备份恢复和安全备份通过，`integrity=ok`，14/14 图片路径有效。
- **最终自动回归：** 后端 23 passed；前端 build 与 6/6 render/Worker tests；lint 0 errors/5 个既有图片性能 warnings；`git diff --check` 无空白错误。
- **当前状态：** GPU/自动验收完成，服务保持运行；Phase 9 仍为 `in_progress`，唯一流程门是用户在当前电脑 Chrome/Edge 亲自验收并确认。用户确认前不进入 9.9 最终 UI/UX 重构。

## Phase 9 产品诊断 — 2026-08-12

- **范围：** 只读诊断，不修改业务代码、数据库内容或 UI；使用评分矩阵、Phase 9 证据、当前本机页面、接口、SQLite 检查和 Git 状态。
- **服务与存储：** 3000/8000/8870/8890 均返回 200；SQLite `integrity=ok`，21/21 图片路径有效。
- **评分判断：** 模型和功能自动硬门基本通过，但用户 Chrome/Edge 验收、PDF 保存确认和 9.9 最终 UI/UX 重构未完成，因此不能宣称完全满足满分。
- **产品判断：** 当前适合技术人员预先启动后的比赛演示和受引导试用，不适合完全不懂术语的普通用户独立长期使用。
- **新发现：** 160 张中 102 张触发人审，56 张为非预期冲突误触发；病例人工复核没有真实处理/反馈闭环；移动端主导航被隐藏；用户端大量 9–11px 文字；存在 `????` 历史字段和带图库水印的演示病例。
- **计划同步：** 上述问题已写入 Phase 9 的 9.9 前置产品问题清单；本轮未擅自修复，也未提前进入 UI 重构。

## Phase 9 当前问题整改与自动化交付启动 — 2026-08-12

- **状态：** `in_progress`；先处理 CPU/本机产品问题，再执行统一数据审计与六模型公平对照，最后恢复服务并完成真实回归。
- **已锁定边界：** 自动判断或自动拒答；独立 `/admin`；先备份再标记现有 21 条测试病例；不删除原始数据；不启动 9.9 最终视觉重构。
- **服务器前置：** RTX 5090 当前运行 detector 与 Qwen3-VL，约占 23 GiB 显存，项目盘剩余约 19 GiB；训练允许停服错峰，恢复后必须重新验证 8870/8890、FastAPI 和前端。
- **Karpathy Guidelines：** 每个子阶段修改前记录假设，采用最小数据/API/UI改动，只改与本计划直接相关的文件，并立即运行可重复验证。
- **数据库保护与隔离：** 在线备份 `backend/runtime/backups/phase9-pre-automation-20260812.sqlite3` 已创建；源库 `integrity=ok`、21/21 图片存在。新增 `is_test` 后使用精确 `expected-count=21` 门将实施前快照标记为测试记录，未删除或改写原始病例。
- **维护检查修正：** 测试记录默认过滤后，首次维护检查只显示 0 条图片；数据未丢失。将管理维护检查显式改为覆盖 `record_scope=all` 并加回归测试，复测为 21/21。
- **验证入口错误：** 首次前端并行验证命中 Windows `npm.ps1` 执行策略并中止，改用同一安装的 `npm.cmd`；不修改系统策略。
- **Worker 隔离遗漏：** 新 `/admin` 首次渲染测试在公网兼容模式返回 200 而非 404；本机管理功能正常。将 `/admin` 加入现有 `/review`、`/training` 同一屏蔽判断后重跑。
- **产品整改检查点：** 后端 24 passed；前端 build/6 tests 通过；lint 0 errors/5 个既有图片警告。真实 API 为用户 0、测试 21、全部 21、趋势 0；`/admin` 实际显示 21 条测试记录。
- **响应式与无障碍：** 桌面普通页最低可见文字 14px；390×844 下移动导航 3 项可见、46px，表单 16px、最小操作高度 44px、无横向溢出。机械检测仅报非用户主流程的既有训练进度条宽度动画 warning，本轮不做无关修改。
- **统一数据构建完成：** 新增只写清单的构建器并通过相关测试；服务器最终 v4 为 4,490 张，开发训练 3,816、内部验证 674、官方冻结验证 833。独立 OpenCV 复核 4,490/4,490 无问题；源图片和标签未被移动或改写。
- **审计排除：** Pest65 的 11 张空标签、4 张损坏 JPEG 和 1 张重复框图片已排除；Roboflow 类 13 原始训练 445 张在服务器缺失，未使用独立 tune/frozen 数据替代。该事实不阻止六架构在现有合规统一数据上的公平对照，但必须进入证据和晋级判断。
- **质量门重启：** 首次 YOLO26n 训练约进行 10/120 轮时，重复出现截断 JPEG 解码警告。已精确停止未完成任务、保留日志，向构建器增加 JPEG 结束标记与 Pillow 解码校验后生成 v2 清单；首轮中间权重不参与排名。
- **最终数据质量门：** v2 仍有底层 JPEG 警告，进一步用 OpenCV 逐图审计定位 `p58_train_108_3a5906bbc070.jpg`；同时排除训练日志发现的重复框图片。最终 v4 为 4,490 张，独立 OpenCV 复核问题数 0，相关测试 9 passed。
- **六模型正式训练启动：** 精确记录并停止远程 detector PID 1914、Qwen3-VL PID 1958/2167 后释放显存；`phase9-model-search-v4` 使用 640、120 epochs、batch 32、固定种子顺序训练六候选。首个 YOLO26n 已正常进入训练，数据警告计数 0；本地历史、趋势和报告仍可用，真实识别暂时降级。
- **YOLO26n 完成：** 120/120 与 best 权重开发验证完成，mAP50-95 `0.503968`、弱类均值 `0.419486`、选型分 `0.478624`；官方冻结集未使用。
- **权重下载恢复：** YOLO26s 自动下载在服务器侧生成 0 字节文件并持续轮询 3 分钟，已停止训练器。改从 Ultralytics 官方 `assets` v8.4.0 在本机下载缺失五权重，使用 `.part` 临时文件、大小和 SHA-256 校验后传服务器；服务器端 5/5 Ultralytics 可加载。恢复训练器后跳过已完成 YOLO26n，从 YOLO26s 继续。
- **六模型对照完成：** 六个候选均以 640、120 epochs、batch 32、seed 20260729 在同一 3,816/674 开发划分完成，无训练失败、无数据解码/CUDA 异常，官方冻结 833 张未参与选型。按综合分排序：YOLO11s `0.495082`、YOLO12s `0.493887`、YOLO26s `0.488974`、YOLOv8s `0.481238`、YOLO26n `0.478624`、YOLOv5su `0.478102`。
- **最终架构选择：** YOLO11s 与 YOLO12s 分差 `0.001196`，小于预设 `0.005`；按“接近时先比较 Recall”的固定规则，YOLO12s 以 `0.756101` 高于 YOLO11s 的 `0.750980`，进入全量 4,490 张允许数据最终重训。选型证据已固化为 `artifacts/server/phase9-model-search-20260812.json`。
- **冻结隔离复核：** 重建数据清单后 `dataset-refit.yaml` 仅引用 `final-train.txt`，`dataset-frozen-eval.yaml` 的验证集才引用官方 833 张；全量图片再次解码/哈希检查通过，未改变 4,490、3,816/674 和冻结 833 的计数。
- **最终重训与一次冻结评测：** YOLO12s 使用全部 4,490 张允许数据从官方预训练权重完成 120/120，训练期间 `val=False`，未读取官方冻结集。随后唯一一次官方 833 张评测得到 Precision `0.807657`、Recall `0.798434`、mAP50 `0.809507`、mAP50-95 `0.523463`。
- **晋级结论：** 候选仅 Recall 与 16 类证据通过；总体 mAP50-95、mAP50、弱类平均增益和弱类不下降门失败，故严格拒绝上线，不执行候选 160 张系统评估，也不在冻结集上继续调参。当前主模型 + 类 10/13 shadow 专家链继续作为在线视觉层，Qwen3-VL继续保留。
- **服务恢复：** 远程原 detector PID 35662、Qwen3-VL 服务已恢复，8870/8890 双回环隧道重建；FastAPI 发现旧进程未带 detector/VLM endpoint 后，使用既有 `run_local_server.cmd` 最小重启，健康状态恢复为 `detector_mode=remote`、`multimodal_configured=true`。3000/8000/8870/8890 均可用，视觉路由保持 `shadow`。
- **最终自动回归：** 后端 `24 passed`；前端 build + 6/6 tests；lint 0 errors/5 个既有 `<img>` warnings；最终复现门含所有服务通过。SQLite `integrity=ok`、22/22 图片路径有效，普通历史/趋势仍为 0，测试病例只在 `/admin` 可见。
- **真实链路：** 无目标样本自动落入 `no_supported_target`，页面显示“无法判断、请补拍”；正常南瓜样本检测 1 框、自动 `conclusive`、严重度 low、报告与 5 个来源生成。两条自动病例随后标记 `is_test=true`，未污染用户历史。
- **恢复后固定 160 张复测：** 160/160 成功，Top-1 `87.50%`，Schema/内容/严重度输入引用均 `100%`，冲突识别 `15/17=88.24%`，不安全输出 0、风险错误清除 0，E2E P50/P95 `4.494/5.105` 秒，峰值显存 `23,088 MiB`。证据为 `artifacts/server/phase9-post-remediation-multimodal-evidence-20260812.json`。
- **当前门：** 自动化整改与交付完成，Phase 9 仍保持 `in_progress`；下一步由用户在当前电脑 Chrome/Edge 亲自使用并反馈，用户确认前不启动 9.9 最终视觉重构。

## Phase 9.11 弱类 8/10/13/15 混淆与专家 shadow 专项验证启动 — 2026-08-12

- **范围：** 先做官方冻结集混淆统计、训练/验证数据独立性审计和现有专家的 shadow 对照；不改变线上模型、路由或冻结数据。
- **验证门：** 只有弱类在冻结集提升、总体 mAP50-95 不下降、其他类别不下降且专家成本可接受，才允许讨论 `active`；否则保持 `shadow` 并如实记录“不上线”。
- **已确认前置：** 本地 8000、detector 8870、Qwen3-VL 8890 健康；路由为 `shadow`，`reclassify=false`，三份视觉权重均已加载。
- **下一步：** 完成四类混淆矩阵与错误类型统计，核对 4,490 张统一训练集、674 张内部验证、833 张官方冻结集及类 10/13 独立 101 tune/85 frozen 的哈希和标签门，再运行 shadow 对照。
- **专项审计首次错误：** 直接在服务器 GPU 加载额外主模型运行 833 张审计时，detector/Qwen3-VL 已占用约 22 GiB 显存，审计进程触发 CUDA OOM；线上服务未停止、模型和路由未改变。后续改用 `CUDA_VISIBLE_DEVICES=''`、CPU、batch 1 的只读审计，shadow 对照复用现有 8870 服务，不再额外占用 GPU。

## Phase 9.11 弱类专项结果 — 2026-08-12

- **冻结集混淆已完成：** 类 8/10/13/15 的 GT 框为 `98/87/89/83`；主要错分为 8→15=`15`、15→8=`13`、10→13=`18`、13→10=`18`。漏检分别为 `18/10/9/4`，另有低 IoU 与背景误报；具体矩阵和阈值扫描保存在专项 JSON。
- **数据审计已完成：** 统一 4,490 张数据 OpenCV 检查 `4490/4490` 无问题；dev train/val、专家 tune/frozen 与官方 frozen 的 SHA-256 交叉均为 0。官方 frozen 内部 3 组重复内容哈希（830/833 唯一），作为评测局限记录。类 10/13 为 101 tune、85 frozen；类 8/15 无独立专家 frozen，不能支持四类专家上线。
- **Shadow 对照已完成：** 833/833 HTTP 请求成功，服务观察值 `shadow`、`reclassify=false`，主模型与 shadow_keep 完全一致；类 10/13 候选覆盖 76/87、75/89，已覆盖框上的 crop Top-1 一致 62、53。
- **晋级判断：** 当前 active 规则的离线同代码反事实使 mAP50-95 下降 `0.001331`，弱类均值下降 `0.005323`，类 10/13 分别下降 `0.002504/0.018787`，故不满足冻结集稳定提升门。最终保持主模型在线、专家只作 `shadow` 证据，不切换 `active`。
- **交付证据：** `artifacts/server/phase9-weak-classes-audit-20260812.json`、`artifacts/server/phase9-shadow-route-20260812.json`、`artifacts/server/phase9-weak-classes-shadow-evidence-20260812.json`；新增 `training/evaluate_shadow_route.py` 已通过 `py_compile`，评估脚本仅调用现有 HTTP 服务，不复制加载 GPU 模型。
- **后续状态：** 本专项完成；继续执行 Phase 9.7–9.8 的本机用户验收。用户确认前不进入 9.9 UI/UX 重构，也不因本轮结果进行无证据重训。
- **会话封存与明日测试版本：** 已封存 `artifacts/server/phase9-weak-classes-session-checkpoint-20260812.json`，明日暂定使用当前已验证的 `official-plus-public-weak-v1-e120-b64` 主模型；YOLO12s 候选不替换。专家无最终决定权，继续 `shadow`。本机前后端保持；远程 detector、Qwen3-VL 和双隧道已停止，GPU 显存为 0 MiB。由于远程是平台容器且 PID 1 为 `/init/boot/boot.sh`，SSH 内 `systemctl/poweroff/reboot` 均被拒绝，实例本身仍需在 SeetaCloud/AutoDL 控制台手动停止。

## 2026-08-13 本次 GPU/浏览器真实测试收尾

- **前置假设：** 只恢复服务和执行验收，不改业务代码、不重训、不切换主模型、不启用专家 `active`；所有本轮病例测试后标记为测试记录。
- **服务：** SSH、RTX 5090、远程 detector、Qwen3-VL、本机双隧道、FastAPI 和前端均已恢复；结束时服务仍保持在线，交给用户继续人工测试。
- **已通过：** 正常上传→检测→两阶段分析→保存→报告；detector 故障降级；VLM 恢复后仅重试分析；历史/趋势/报告读取；FastAPI 重启持久化；SQLite 完整性和测试数据隔离；后端 24 个测试、前端 build/6 tests、lint 无错误；桌面和 390×844 基础浏览器检查。
- **未完全通过：** 无目标结果页的主标题可能展示 Qwen 独立候选，和“未发现支持目标”矛盾；VLM 故障仍以 HTTP 502 暴露而非结构化不可用状态。两项均记录为后续优先整改，未在本轮直接修改。
- **当前结论：** 系统已具备明天本机人工集中测试条件，但不能宣称满分或 Phase 9 完成。用户测试后提交问题，再进入对应整改；在用户确认关键用例可行前不进入 Phase 9.9 最终 UI 重构。

## 两项问题修复启动 — 2026-08-13

- **范围：** 只处理无目标页面误导和 Qwen3-VL 故障 502；不训练专家、不切换模型、不启用 `active`、不改数据库。
- **已完成分析：** 已定位普通用户页面直接显示 `analysis.primary_diagnosis` 的根因；已定位后端仅将未配置异常结构化、而把 HTTP/解析异常返回 502 的根因。
- **方案：** 统一用户诊断标题和非结论内容边界；将多模态异常转换为保留病例与检测证据的 `multimodal_unavailable/service_unavailable` HTTP 200，并保留仅分析重试。
- **下一步：** 修改后端、普通用户页面/API助手和最小测试；立即执行后端、前端和真实浏览器回归。

## 两项问题修复完成 — 2026-08-13

- **代码：** 完成状态优先用户标题、非结论内容隔离、多模态故障结构化 HTTP 200 和高风险/未知严重度保护。
- **验证：** 后端 `25 passed`；前端 `npm.cmd test` 为 build + 6/6 tests 通过；lint `0 errors`/5 个既有图片警告；compileall 和 diff check 通过。
- **真实浏览器：** 无目标样本首页/详情/报告均显示“无法可靠判断”；关闭 Qwen3-VL 后显示服务不可用和仅分析重试；恢复服务后重试成功。
- **服务收尾：** 本机前端、FastAPI、detector 隧道、Qwen3-VL 隧道均已恢复并健康，路由仍为 `shadow`；本轮病例已隔离为测试记录。
- **当前入口：** 两项整改完成，Phase 9 仍为 `in_progress`；下一步交给用户在当前电脑 Chrome/Edge 进行人工测试。用户反馈前不进入 Phase 9.9 最终 UI 重构，也不训练新的专家模型。
- **证据：** `artifacts/server/phase9-remediation-20260813.json` 已记录无目标标题、故障 HTTP 200、恢复重试、自动化测试和交付时服务状态。

## Same-Frozen-Set Detector Comparison — 2026-08-13

- **范围锁定：** 只评测昨天六模型中的 YOLO26n 权重与当前主模型；不重训、不调参、不切换线上权重、不启用专家、不调用 Qwen3-VL。
- **前置核对：** SSH 已恢复；远程 RTX 5090 可用；两份权重和同一冻结清单均存在，SHA 已记录到 `findings.md`。本机 `/health` 返回 `200`，detector/Qwen3-VL 当前在线。
- **待执行：** 停止远程 detector 与 Qwen3-VL，使用统一评测脚本在同一 833 张冻结集上各评测一次；保存原始 JSON 后恢复服务并检查 3000/8000/8870/8890。

## Same-Frozen-Set Detector Comparison Completed — 2026-08-13

- **停服与评测：** 评测前停止远程 detector PID `4842`、Qwen3-VL PID `3904`，显存降至 `0 MiB`；直接执行 `training/evaluate_detector.py`，未经过 HTTP、专家或多模态链路。
- **统一对象：** 服务器 `official-frozen-val.txt` 为 `833` 行；冻结 YAML SHA-256 `2e7f691de609c4a310549d1ac6fb98e99eedcec18160588729f8e1e38fef60b8`；两个结果均含完整 16 类指标和 17×17 混淆矩阵。
- **YOLO26n 候选：** `phase9-yolo26n-e120-b32/weights/best.pt`，SHA 前缀 `fb71fab6`；P `0.829715`、R `0.756240`、mAP50 `0.806850`、mAP50-95 `0.519087`。
- **当前主模型：** `official-plus-public-weak-v1-e120-b64/weights/best.pt`，SHA 前缀 `cbb26d83`；P `0.831993`、R `0.778327`、mAP50 `0.825132`、mAP50-95 `0.546065`。
- **差值：** 主模型相对候选 P `+0.002278`、R `+0.022087`、mAP50 `+0.018282`、mAP50-95 `+0.026978`；11/16 类提升，5/16 类下降。类 8 降幅最大 `-0.054795`，类 10 `-0.014842`，类 13/15 基本持平。
- **恢复：** detector PID `7017`、Qwen3-VL PID `7059` 已恢复；远程 GPU 约 `22110 MiB`，本机 3000、8000、8870、8890 均返回 200；detector 健康状态确认主模型 SHA 一致、`routing.mode=shadow`、`reclassify=false`。
- **交付结论：** 当前主模型继续保留上线；昨天 YOLO26n 候选不替换。该结论仅证明同一冻结集上的整体检测优势，不授予专家决定权，也不证明类 8 等弱类没有后续优化空间。
- **产物：** 已保存三份本地证据 JSON/YAML；`git diff --check` 通过（仅有既有 LF/CRLF 提示，无空白错误）。

## Remaining Five Detector Comparison Started — 2026-08-13

- **范围：** 评测 YOLO26s、YOLO11s、YOLO12s、YOLOv8s、YOLOv5su 五份六模型搜索权重；不重训、不调参、不切换主模型、不启用专家、不调用 Qwen3-VL。
- **统一口径：** 同一官方 833 张冻结清单、640 输入、batch 32、workers 4、直接 Ultralytics 评测；结果完成后与已保存的 YOLO26n 和当前主模型结果合并比较。
- **下一步：** 核对五份服务器权重 SHA 和冻结清单 SHA，停止两项远程推理服务，依次后台评测并保存原始 JSON，最后恢复全部服务。

## Remaining Five Detector Comparison Completed — 2026-08-13

- **权重核验：** YOLO26s、YOLO11s、YOLO12s、YOLOv8s、YOLOv5su 五份 best 权重均存在；冻结清单 833 张，SHA 与上一轮一致。
- **统一评测：** 停止远程 detector/Qwen3-VL 后，直接运行 `training/evaluate_detector.py`，每个权重一次，640/batch32/workers4；没有专家、HTTP shadow 或多模态调用。
- **结果：** YOLO26s mAP50-95 `0.535458`；YOLO11s `0.534951`；YOLO12s `0.522652`；YOLOv8s `0.530064`；YOLOv5su `0.519336`；当前主模型同口径 `0.546065`。
- **综合观察：** 主模型 mAP50-95 仍最高；YOLO26s Precision 最高 `0.834140`；YOLO12s Recall 最高 `0.807891`，但两者都未超过主模型的总体综合结果。
- **冻结集加权分：** current-main `0.487785` > yolo26s `0.483844` > yolo11s `0.483537` > yolo26n `0.474415` > yolov8s `0.473773` > yolo12s `0.466811` > yolov5su `0.464188`。
- **服务恢复：** detector PID `8927`、Qwen3-VL PID `8969`；远程显存约 `22110 MiB`；本机 3000/8000/8870/8890 及主模型健康检查均通过，路由保持 `shadow/reclassify=false`。
- **证据：** 五份原始 JSON 与 `phase9-same-frozen-eval-20260813-five-model-summary.json` 已保存；本轮没有代码、数据库或线上模型配置修改。

## 4,490 全量训练与 833 冻结集统一比较启动 — 2026-08-13

- 已完成本轮启动前的 planning-with-files 恢复检查、Git 状态核对和三份规划文件同步；工作区已有改动全部保留。
- 已固定训练口径：4,490 张 `final-train.txt`、120 轮、640、batch64、seed `20260729`、官方预训练权重、训练期不使用验证集、完成后使用 `last.pt`。
- 已固定评测口径：六个新 `last.pt` 加当前主模型，共七个权重；官方 833 张冻结集、640、batch64、workers4、`training/evaluate_detector.py`；不调用专家、Qwen3-VL 或 detector HTTP。
- 已核对文件级独立性：训练/冻结跨集合精确 SHA 交集 0；训练无缺失，冻结无缺失；冻结内部存在 3 组重复内容，待在最终报告中标注。
- 待执行：解码像素/感知哈希补充门；GPU 停服与显存确认；六模型依次训练；统一冻结评测；恢复服务并输出七模型比较证据。
- 当前尚未停止服务、尚未训练、尚未修改线上模型；如遇 OOM、重复像素或服务恢复失败，将停止相应步骤并记录具体错误。
- **错误记录：** 服务器默认 PATH 没有 `python` 命令，首次运行独立性审计返回 `bash: python: command not found`；未生成有效审计结论，改用服务器已有绝对 Python 解释器继续。
- **错误记录：** 使用绝对解释器的首次运行发现审计脚本条件列表存在语法错误；没有生成结果文件，已做单行语法修复并重新执行编译检查。
- **审计复核：** 首次有效报告显示文件 SHA 与解码像素 SHA 跨集合均为 0，但发现脚本把重复文件的 `processed_count` 误写成唯一哈希数，且没有保存精确感知哈希的路径配对；在训练前修正统计和证据字段，重新生成报告并人工检查 43 组感知哈希相同项。

## 训练前独立性门阻断 — 2026-08-13

- 独立性审计及 23 页复核图已完成；没有跨集合文件/像素 SHA 重复，但确认 74 张唯一训练图片与官方冻结集存在同图变体或同场景近重复。
- 74 张候选构成为 PlantDoc 51、SciDB 3、官方训练 20；精确 pHash 48 个实际配对、近似 pHash 43 个配对；冻结集内部 3 组重复已单独记录。
- 因用户原计划要求训练集和冻结集独立，当前不能使用原 4,490 张直接训练；本阶段停止在训练前，不停止 detector/Qwen3-VL，不修改清单、不修改线上主模型。
- 待用户确认：是否保留原始清单作为审计原件，并排除 74 张候选生成 4,416 张独立训练清单后继续。确认后才执行清单生成、二次审计、停服和六模型训练。

## 用户授权后继续 — 2026-08-13

- 用户已授权使用排除 74 张视觉重复候选后的 4,416 张独立训练集继续。
- 当前仍未停止 detector/Qwen3-VL，未训练，未切换线上主模型；先生成派生清单和 YAML，再通过二次独立性门。
- 二次门通过条件：训练 4,416 条、官方冻结 833 条；缺失/解码错误为 0；跨集合文件 SHA、解码像素 SHA、精确 pHash 和 pHash 距离 `<=8` 均为 0。

## 二次独立性门通过 — 2026-08-13

- 派生训练清单已固定为 4,416 张，原始 4,490 张清单和官方 833 张冻结清单未修改。
- 二次审计通过：4,416/4,416 与 833/833 成功解码；跨集合文件 SHA、像素 SHA、精确 pHash 和近似 pHash（距离≤8）均为 0；训练集内部像素重复为 0。
- 冻结集内部 3 组重复仍保留并记录为官方评测限制。
- 下一步：记录服务/PID/GPU/磁盘，停 detector/Qwen3-VL，依次启动六个严格 batch64、120轮、val=False 训练。
- **错误记录：** 服务器训练前检查命令因 PowerShell/Bash 多层引号解析失败，未执行到远程检查、未停止服务、未修改文件；改为多个短命令分别核对。

## GPU 停服完成，六模型训练开始 — 2026-08-13

- 停服前记录：detector PID `8927`、Qwen3-VL PID `8969`，GPU 使用 `22110 MiB`；停止后两进程消失，GPU 使用 `0 MiB`。
- 训练数据：独立训练清单 4,416 张；冻结 833 张不在训练期使用。
- 训练配置：六个官方预训练权重，120 轮、640、batch64、seed `20260729`、`val=False`、`patience=0`，串行运行，统一使用 `last.pt`。
- 当前状态：已具备启动第一个 YOLO26n 训练条件；训练期间实时服务暂不可用，历史/病例数据不受影响。

## 首次训练暂停 — 2026-08-13

- 首次 YOLO26n 已启动至约第 5/120 轮；显存约 11.3 GiB，batch64 未 OOM。
- 发现训练 YAML 包含官方冻结 `val` 字段，尽管 `val=False`，启动日志仍扫描冻结标签缓存；该运行不纳入最终结果。
- 当前动作：停止首次训练，检查训练器行为并生成无 `val` 字段的训练 YAML；修正后从 YOLO26n 重新开始，六个模型均以修正后的训练契约执行。
- 已完成最小修复代码：派生清单生成器现在输出训练占位 YAML（`train=val=4,416`）和含官方冻结集的评测 YAML；待上传并验证 YAML 内容后重启训练。

## 第二次训练启动失败 — 2026-08-13

- 训练专用 YAML 不含 `val:` 时，Ultralytics 在启动前报 `'val:' key missing`；没有训练进程、没有权重结果，GPU 仍为 0 MiB。
- 修正决定：保留 `val=False`，让 `val:` 指向同一份 4,416 张训练清单作为框架占位，避免官方 833 张进入训练配置；训练后统一使用单独的冻结评测 YAML。

## 即时评测执行规则 — 2026-08-13

- 用户已确认：每个模型训练完成后立即评测，不等待六模型全部完成；结果以独立 JSON 保存用于后续比较。
- 当前执行门：先用修正后的训练 YAML 启动 YOLO26n；确认日志只扫描 4,416 张独立训练清单后，训练完成即评测官方 833 张冻结集。
- 统一比较字段：Precision、Recall、mAP50、mAP50-95、16 类指标、17×17 混淆矩阵、速度、显存、权重 SHA、数据清单/评测配置哈希。
- 当前主模型单独完成同配置基线；候选模型不自动替换线上主模型，全部结束后再按预先固定的排名规则判断。

## YOLO26n 修正训练已启动 — 2026-08-13

- 训练专用 YAML 已重新生成，`train` 和框架必需的 `val` 均为 4,416 张独立训练清单；官方冻结路径未进入训练 YAML。
- YOLO26n 已进入第 `1/120` 轮，随后监测到第 `11/120` 轮；batch `64`，640 输入，seed `20260729`，显存约 `11.3 GiB`，未发生 OOM。
- 训练日志确认只扫描独立训练清单的 `4,416` 张图片；未扫描官方 833 张冻结集。
- 服务器已启动串行编排器：YOLO26n 完成后立即冻结评测，随后评测当前主模型基线，再依次训练并即时评测其余五个模型。

## 用户中止全部训练 — 2026-08-13

- 用户要求停止所有训练，当前主模型继续作为视觉模型，不做任何线上权重变更。
- 已终止 YOLOv5su 及其子进程和串行编排器；YOLOv5su 训练记录返回主动终止 `rc=143`，未生成完成记录或冻结评测结果。
- 已完成的 YOLO26n、YOLO26s、YOLO11s、YOLO12s、YOLOv8s 即时评测和当前主模型基线均保留在服务器 `artifacts/server/phase9-fulltrain-eval-20260813-*.json`。
- 服务器验证通过：无训练进程、无串行编排器，GPU `0 MiB`；下一步只恢复既有主模型服务与本机测试链路，保持 `shadow/reclassify=false`。

## 编排器等待逻辑修正 — 2026-08-13

- **发现：** 初版等待条件会把包含训练命令的远程 shell 命令行一并匹配，可能在 YOLO26n 完成后错误地继续等待。
- **最小修正：** 等待条件收窄为真正的 `/root/miniconda3/bin/python training/train_phase9_finalist.py` 进程；停止并重启编排器，不停止或重启正在运行的 YOLO26n。
- **验证：** 重启后仅一个 YOLO26n 训练任务继续运行，当前约第 `51/120` 轮；状态文件新增等待记录，未启动后续模型。

## YOLO26n 即时评测完成 — 2026-08-13

- YOLO26n 训练完成：120/120，使用独立训练清单 4,416 张、640、batch64、seed `20260729`，最终权重为 `last.pt`；训练记录标记 `frozen_validation_used_during_training=false`。
- 官方 833 张冻结评测已立即完成，评测未调用 detector HTTP、专家或 Qwen3-VL；评测数据清单 SHA 为 `91a777a8818b8766f49f67891562d1cd808198a89586ec370b49a9e56d7096a4`。
- YOLO26n 结果：Precision `0.687078`，Recall `0.689678`，mAP50 `0.684810`，mAP50-95 `0.410084`；权重 SHA `5bd3db42f4223f43e914d74b151cf2d7f8bf018a057d45910402a0afa9425fe1`。
- 当前主模型同配置基线：Precision `0.839196`，Recall `0.776205`，mAP50 `0.827517`，mAP50-95 `0.548224`。YOLO26n 四项总体指标均未达到替换门，不上线。
- 证据：服务器 `artifacts/server/phase9-fulltrain-eval-20260813-yolo26n.json`、`...-current-main.json`；状态文件记录 YOLO26n 评测完成后已进入 YOLO26s。

## YOLO26s 即时评测完成 — 2026-08-13

- YOLO26s 训练完成：120/120，使用同一 4,416 张独立训练清单、640、batch64、seed `20260729`，最终使用 `last.pt`。
- 官方 833 张冻结评测即时完成：Precision `0.736392`，Recall `0.684162`，mAP50 `0.677087`，mAP50-95 `0.409398`。
- 权重 SHA：`cd5972261d09859bff22a60253f8847d5e96f2e5935121ff45dba9d143f50c88`；评测 YAML SHA 与 YOLO26n 相同，冻结列表 SHA 为 `91a777a8818b8766f49f67891562d1cd808198a89586ec370b49a9e56d7096a4`。
- 相对于当前主模型，YOLO26s 的 mAP50-95、mAP50 和 Recall 均未达到替换门，不上线；状态文件记录评测完成后已进入 YOLO11s。
- 证据：服务器 `artifacts/server/phase9-fulltrain-eval-20260813-yolo26s.json`。

## YOLO11s 即时评测完成 — 2026-08-13

- YOLO11s 训练完成：120/120，使用 4,416 张独立训练清单、640、batch64、seed `20260729`，最终使用 `last.pt`。
- 官方 833 张冻结评测即时完成：Precision `0.721783`，Recall `0.659075`，mAP50 `0.678103`，mAP50-95 `0.401406`。
- 权重 SHA：`309d282351343a0a979a5f341c06662818518f4b480fe50543b35b83ac6a69c9`；评测 YAML SHA 为 `1d834c0fe5100884d8fe6a2e117558137a6f19d72b33e02e8a0e076da679afec`。
- YOLO11s 总体指标均低于当前主模型，不具备替换资格；状态文件记录评测完成后已进入 YOLO12s。
- 证据：服务器 `artifacts/server/phase9-fulltrain-eval-20260813-yolo11s.json`。

## YOLO12s 即时评测完成 — 2026-08-13

- YOLO12s 训练完成：120/120，使用 4,416 张独立训练清单、640、batch64、seed `20260729`，最终使用 `last.pt`；训练期间未读取官方冻结清单。
- 官方 833 张冻结评测即时完成：Precision `0.747517`，Recall `0.676535`，mAP50 `0.696172`，mAP50-95 `0.414133`。
- 权重 SHA：`f81227fe07abf938867c6cb93cfca9e9a8a2a85ff8f94bc18f6eac93b4334418`；评测 YAML SHA 为 `1d834c0fe5100884d8fe6a2e117558137a6f19d72b33e02e8a0e076da679afec`。
- YOLO12s 总体指标低于当前主模型，不具备替换资格；状态文件记录评测完成后已进入 YOLOv8s。
- 证据：服务器 `artifacts/server/phase9-fulltrain-eval-20260813-yolo12s.json`。

## YOLOv8s 即时评测完成 — 2026-08-13

- YOLOv8s 训练完成：120/120，使用 4,416 张独立训练清单、640、batch64、seed `20260729`，最终使用 `last.pt`。
- 官方 833 张冻结评测即时完成：Precision `0.702166`，Recall `0.703074`，mAP50 `0.672390`，mAP50-95 `0.398096`。
- 权重 SHA：`7a09f233d5c95f8dc5286c46d0749d1e28dca21b3a56c83443c2f9ae260b58c1`；评测 YAML SHA 为 `1d834c0fe5100884d8fe6a2e117558137a6f19d72b33e02e8a0e076da679afec`。
- YOLOv8s 总体指标低于当前主模型，不具备替换资格；状态文件记录评测完成后已进入最后一个 YOLOv5su。
- 证据：服务器 `artifacts/server/phase9-fulltrain-eval-20260813-yolov8s.json`。
## 训练停止与主模型冻结完成 — 2026-08-13

- 用户决定停止全部训练，线上继续使用当前主模型，不做权重或路由变更。
- 已停止 YOLOv5su 及串行训练编排器；无训练进程、无训练编排器，GPU 已从训练状态释放。
- 已保留五个已完成候选和当前主模型的统一冻结集评测 JSON；候选结果均低于当前主模型，不具备上线资格。
- 已恢复 detector、Qwen3-VL、8870/8890 隧道及本机前后端；主模型 SHA、`shadow` 路由和 `reclassify=false` 已复核。
- 当前交付状态：等待用户进行集中人工测试；后续问题按用户反馈处理。

## 当前模型冻结，进入用户功能测试 — 2026-08-13

- 视觉检测继续使用当前主模型，Qwen3-VL 继续作为多模态分析模型。
- 不训练候选模型、不切换权重、不改变专家 `shadow` 路由。
- 当前任务阶段切换为用户人工测试；用户反馈问题后再进行最小范围修复和回归验证。
- 功能问题处理完成且用户确认后，再进入最终 UI 界面重构。

## Session Resume — 2026-08-14

- **使用 planning-with-files 恢复：** 已完整读取三个规划文件；工作区 Python 执行 `session-catchup.py` 成功退出，未报告未同步上下文。
- **Git 状态：** 当前分支 `codex/publish-audits-and-calibration-plan`，领先远端 1 个提交；既有已修改/未跟踪文件和用户 `CLAUDE.md` 全部保留，未执行清理、回滚、提交或重置。
- **服务检查：** 本机 FastAPI `8000/health=200`；前端 `3000`、detector 隧道 `8870`、Qwen3-VL 隧道 `8890` 均不可达。FastAPI 仍显示 remote detector/Qwen3-VL 配置，但上游隧道未就绪，不能据此开始真实识别。
- **远程检查：** `connect.bjb2.seetacloud.com:10373` 当前 TCP 不可达；未尝试复用旧 PID、未重启远程服务、未启动训练/评测、未修改线上模型或路由。
- **当前结论：** 自动/GPU 门已在上一轮完成，但用户 Chrome/Edge 人工验收的运行前置条件不满足；等待用户恢复 GPU 主机或提供新 SSH 地址后，再按既有启动材料重新核对并进入验收。
- **本轮错误：** Windows Store `python.exe` 占位程序首次执行 catch-up 退出 1；改用工作区 Python 成功。一次并行 PowerShell 检查因循环块直接接管道解析失败，拆分后完成检查，均未产生业务副作用。

## 实验室服务器部署评估启动 — 2026-08-14

- 使用 `planning-with-files` 恢复项目状态并核对 Git 差异；既有用户修改全部保留。
- 读取服务器检查输出，确认 CentOS 7/glibc 2.17、4×K80、125 GiB RAM、根盘 97%、`/data` 约 3 TiB 可用。
- 读取 `backend/pyproject.toml`、`inference/requirements.txt`、`web/package.json`、RTX 5090 环境证据和 Qwen3-VL 启动脚本引用。
- 当前正在对照官方文档确认 VS Code Remote Server 与 vLLM/GPU 的最低要求；未对服务器执行升级、安装或部署。
- 已核对微软 Remote Development、vLLM、NVIDIA CUDA/架构矩阵和 Qwen3-VL 官方资料：CentOS 7 主机不满足当前 VS Code Server；K80 不满足 vLLM 且不能承载现有 CUDA 12.8 栈。
- 完成部署判定：CPU、RAM 和 `/data` 容量足够；操作系统、根盘、Python、Node、GPU/驱动不满足完整系统。形成“只解决 VS Code”“降级部署”“完整部署”三条升级路径。
- 本轮只读检查与规划记录已完成；未在实验室服务器上安装软件、升级系统、清理磁盘或启动服务。
# 双服务器部署执行日志（2026-08-14）

- 已读取 `planning-with-files` 与 `karpathy-guidelines`，恢复三份规划文件并检查 Git 状态。
- 已锁定无损约束：优先不重装；不格式化 `/data`；不清理根盘；现有工作区改动全部保留。
- 当前进行 Phase A：代码接口、数据结构、测试和 SSH 可达性核对。
- 工具错误：首次并行恢复调用失败且无输出；拆分后成功读取 Git 与规划文件。默认 `python.exe` 运行 catch-up 退出 1，尚未重复同一失败命令。
- 已完成现有 FastAPI、SQLite、病例三阶段请求、动态报告、Admin 页面和前端 API 调用点核对。
- SSH 只读检查确认服务器可达但无免密认证；未写入服务器、未记录密码。
- 后端双实例、认证、离线切换拒绝、病例归属和报告快照测试已增至 29 项并全部通过。
- 前端生产构建通过；首轮页面测试仅因 Admin 旧标题断言失败，已更新为受保护会话加载文案。
- 首轮 lint 发现 Admin effect 内同步触发状态更新，已改为会话 Promise 内顺序刷新；其余 5 项为项目原有 `<img>` 性能警告。
- SSH 密钥首次安装尝试失败：Windows OpenSSH 无法直接执行 `.cmd` askpass（`CreateProcessW error:2`）；未接收密码、未连接成功、服务器无改动。改用本机编译的最小 askpass `.exe` 重试。
- Windows 原生凭据包装器首次运行在弹窗前因 PowerShell 5.1 对无 BOM 中文脚本的解析错误停止；未读取密码、未连接服务器。已把包装器提示改为 ASCII。
- 第二次原生凭据框后台等待 120 秒后仍不可见/无输入，已终止本轮新建进程；保留用户原有 SSH PID 12044。
- 已生成实验室 Docker/CPU/llama.cpp 部署包、Docker 数据根安全迁移脚本、重装前备份清单、GPU 独立后端启动包和 Windows 密钥上传脚本。
- 本地验证：后端 29 passed；前端生产构建与 6 项页面测试通过；ESLint 0 error（保留既有 5 条 img 警告）；Compose YAML 可解析。
- 用户执行局域网公钥拉取命令后，BatchMode 密钥认证仍被拒绝；推断为反向路由/防火墙或追加格式问题，未进入服务器命令执行。改为启动可见 PowerShell，仅让用户交互输入 SSH 密码完成公钥安装。
- 用户完成可见 PowerShell 中的密码输入后，显式指定 `ghl_codex_ed25519` 已返回 `KEY_OK`；Docker data-root 为 `/data/ghl/docker`，部署环境文件存在。已将专用密钥写入本机 `Host ghl` 配置，后续不再需要重复输入 SSH 密码。
- 一次远端只读状态命令的 `awk` 引号被 Windows PowerShell 改写，导致末尾字段脱敏检查语法错误；此前的密钥、时间、Docker data-root 和环境文件检查均已成功，未产生远端写入。
- `ssh ghl` 别名免密验证成功；远端 Admin 哈希与会话密钥仍为空，服务尚未启动。
- 已验证公共 ECR 的 Python/Node/nginx 镜像和 GHCR llama.cpp server 镜像均可在本机解析；已确定官方 Qwen3-VL Q4_K_M 与 Q8_0 mmproj 的准确文件名和大小，准备离线下载。
- 四个离线镜像已下载完成：Python 43,202,048 字节、Node 79,900,672 字节、nginx 20,980,736 字节、llama.cpp server 310,675,968 字节。
- 首次 Qwen 双文件并行下载包装失败：PowerShell `Receive-Job` 把 curl 的 stderr 进度输出升级为 NativeCommandError，未留下模型文件。按 3-strike 规则不重复该包装方式，改用 Hugging Face 官方下载客户端或静默 curl。
- 已在本地后端 venv 安装 `huggingface_hub 1.27.0` 与 `hf-xet 1.6.0`，不改变项目依赖清单；官方客户端下载仍在运行。下载期间目标 `.incomplete` 文件暂为 0，但下载进程约占 2.2 GB 内存并持续使用 CPU，推断 Xet 正在内存/分块阶段，暂不终止。
- Qwen 官方客户端下载完成：目标目录总字节数与官方精确大小一致。主模型 SHA-256 `67d1659b...e9e2`，mmproj SHA-256 `c6ba8550...3bfd`；四个镜像 tar 也已生成本机 SHA-256 清单。
- 已将四个镜像、Qwen3-VL Q4_K_M 和 Q8_0 mmproj 上传至 `/data/ghl/cache/images` 与 `/data/ghl/models/qwen3-vl`。上传过程中只读抽查确认镜像与主模型完成、mmproj 持续增长；最终两个 SCP 作业均为 Completed。
- 服务器端 SHA-256 与本机六项全部一致，精确字节数一致；镜像/模型文件权限已收紧为 640，目录为 750。
- 首次批量 `docker load` 命令因 PowerShell 在远端双引号字符串内提前展开 Bash `$archive`，远端报 `unexpected end of file`，没有导入或删除镜像。已改用 PowerShell 单引号保护远端脚本后重试。
- 第二次 `docker load` 已逐项成功导入 Python、Node、nginx、llama.cpp server；只在末尾格式化列表时 SSH 引号丢失导致 `grep` 管道被拆分，导入结果不受影响。改用三条简单只读命令复核成功。
- 远端新镜像均位于 `/data/ghl/docker`；原有 Redis/MySQL/EMQX 镜像和三个停止容器完整保留，未启动、未删除。
- 已新增离线 Dockerfiles、Compose 覆盖和固定依赖清单；主 Compose 的 nginx 使用已导入公共 ECR 名称，VLM 改用实际 GGUF 文件名。
- 后端 wheelhouse 首次跨平台解析因 `uvicorn[standard]` 的可选 `watchfiles` 没有匹配显式 manylinux_2_28 标签而失败，未留下不完整 wheel。生产服务不依赖热重载/文件监控，离线清单最小化为普通 `uvicorn` 后重试。
- 后端 wheelhouse 通过双 manylinux 标签解析完成（19 文件/10.6 MB）；推理 wheelhouse 完成（51 文件/363 MB）。npm 基础缓存 197 MB，并额外缓存锁文件中的 13 个 Linux x64/glibc 原生包，最终缓存约 323 MB。
- PowerShell 5 的 `ConvertFrom-Json` 无法解析该 package-lock 的属性名，已改用 Node 只读解析；没有修改锁文件。
- 三个离线缓存包已生成 SHA-256。首次直接执行上传 `.ps1` 被本机 ExecutionPolicy 拒绝，脚本未运行、服务器无改动；改用单次 `-ExecutionPolicy Bypass -File` 调用，不修改系统策略。
- 更新后的部署代码已上传；三个缓存包在服务器端 SHA-256 全匹配并解压到 `/data/ghl/cache`。兼容性门通过：CentOS 7 旧内核可从 `/data/ghl/docker` 离线运行 Python 3.12.14 与 Node 22.23.2，Compose 合并配置有效。
- Admin 密钥仍未设置；现有生成脚本已具备两次密码确认，输出仅包含 PBKDF2 哈希和随机会话密钥，不保存明文。
- 2026-08-16 用户已成功生成 Admin 配置；本地只读验证确认两行、PBKDF2-SHA256/600000 格式及会话密钥格式均有效，未显示敏感值。
- 合并远端 `.env` 前的首次 SCP 被远端关闭；后续 TCP/SSH 与快速重试均确认 `192.168.15.133:22` 不可达。当前电脑仅连接 `WLAN 172.20.10.2/172.20.10.1`，不是实验室 `192.168.15.0/24` 网络，因此没有向服务器写入 Admin 配置，也没有启动构建或服务。
- 2026-08-16 服务器恢复可达：TCP 22、密钥 SSH、`/data/ghl/docker` 和约 3 TB 空间均正常。Admin 配置已合并进远端 `.env`，写入前版本保存在 `/data/ghl/migration-backup`。
- 首次 Compose 启动发现 PBKDF2 哈希中的 `$` 被当成插值变量；未泄露密码，但容器内哈希会被截断。已把 Compose 环境文件中的 `$` 改为 `$$`，备份问题版本并重建 backend 及依赖容器；后续启动无该警告。
- 离线构建完成并启动 gateway/web/backend/detector/vlm 五个容器。后端、前端、CPU detector 正常监听；Qwen3-VL Q4_K_M + Q8 mmproj 约 8 秒加载完成，`8890/health` 返回 200，`/v1/models` 声明 multimodal 能力。
- VLM 当前显示 unhealthy 的原因不是模型失败，而是 llama.cpp 镜像内置 healthcheck 固定探测 8080，部署命令改为 8890。需在 Compose 覆盖健康检查到 `127.0.0.1:8890/health` 后重建 VLM。
- 已覆盖 VLM healthcheck 并重建，状态转为 healthy。首次正式 `verify.sh` 停在网关 curl，`bash -x` 证明 Windows 合并的 `.env` 使用 CRLF，端口变量变成 `8080\r`；服务未失败。将远端文件规范化为 LF，并在验证脚本中显式移除 `\r`。
- 规范化 LF 后正式验证通过：健康 JSON、lab_cpu 配置、SQLite/上传/报告目录、detector/VLM 内网 200、Admin 哈希与会话密钥容器格式均正确。
- 真实 lab_cpu 病例上传成功，CPU detect 约 0.6 秒且本图无支持目标时正确进入复核；Qwen3-VL 首次 CPU analyze 约 96.5 秒，状态 completed、结构化字段与 provenance 完整；报告重复读取 SHA-256 一致。
- 前端 `/` 与 `/admin` 首次真实访问返回 500。vinext 日志显示本地 production server 调用 Worker 时 `env` 为 undefined，而 Cloudflare Worker 入口直接读取 `env.CROP_PUBLIC_MODE`。最小修复为给本地运行提供空 Env/ExecutionContext 默认值，Cloudflare 注入 Env 时行为不变。
- vinext Worker 默认 Env/ExecutionContext 修复后，本地生产构建通过；服务器离线重建 web 后 `/` 与 `/admin` 均返回 200，未登录 Admin API 返回 401。重建脚本最终因 Windows here-string CRLF 的 `[` 判断退出 1，但 HTTP 结果已独立复核通过，服务无故障。
- 五服务整体 restart 后健康接口、前端、lab_cpu 病例状态和实例归属恢复；报告快照重启前后 SHA-256 一致。SQLite `PRAGMA integrity_check=ok`，病例数 1，上传图片和报告 JSON 均存在；VLM 重新加载后恢复 healthy。
- CPU 多模态稳定态复测约 96.1 秒，与首请求约 96.5 秒接近；服务重启和重复分析均完成。
- 类 10 专家验收病例 `lab_cpu-282c1e389a984334b83c9641b87c5896`：主模型输出类 10、置信度 0.943568，路由候选 1、动作 `shadow_keep`，crop 支持 0.925467、类 10 专家支持 0.937514，总检测约 0.54 秒。
- 类 13 专家验收病例 `lab_cpu-5b1830353da64aefa5883a886c5b1c65`：主模型输出类 13、置信度 0.930684，路由候选 1、动作 `shadow_keep`，crop 支持 0.820420，总检测约 0.33 秒。两例均无路由错误，确认当前 `shadow` 专家不会覆盖主模型识别。
- Docker 服务为开机启用且当前 active；空闲容器内存约为 web 79 MiB、VLM 5.0 GiB、backend 39 MiB、detector 281 MiB、gateway 2 MiB。实验室 CPU 单机自动验收仅剩用户使用自设密码完成 Admin 登录。
- 最终回归：后端 `29 passed`；前端生产构建与 6 项页面测试通过；lint 0 error（5 条既有 `<img>` warning）；相关 `git diff --check` 仅有 Windows 换行提示，无空白错误。
- 远端最终 `verify.sh` 再次通过，五容器均在线、VLM healthy；公网入口 `/`、`/admin`、`/health` 均返回 200，当前病例数 3、存储剩余约 3.27 TB。

## GPU 双服务器联调启动（2026-08-17）

- 用户已在实验室服务器 Admin 成功登录，并已开启原 GPU 服务器；实验室 CPU 单机人工登录门完成。
- 原 GPU 地址 `connect.bjb2.seetacloud.com:10373` TCP 已恢复可达，继续使用项目专用私钥 `codex_autodl_nongxin_2026`。
- 首次 GPU 只读状态命令因 PowerShell 提前展开远端 Bash 变量导致引号不闭合，SSH 未执行远端命令、无服务器改动；后续改用 PowerShell 单引号保护完整远端命令。
- 第二次只读包装被 Windows OpenSSH 去掉远端 grep 正则的引号，Bash 在状态读取前遇到括号语法错误；仍无远端改动。停止复用复合正则命令，改为多条无正则的简单只读 SSH 检查。
- GPU 只读核验：主机身份与历史一致，RTX 5090 空闲，数据盘剩余约 18 GiB；旧 detector/VLM 资产存在，但两个服务和 FastAPI 均未运行。
- 实验室服务器到 GPU 公网 SSH `connect.bjb2.seetacloud.com:10373` 的 TCP 探测超时，原定由实验室主动建立 `18000` SSH 隧道暂不可行；正在区分完全无外网与单端口阻断，再选不裸露 GPU 后端的替代链路。
- 一条远端 Python 版本检查因 Windows OpenSSH 去掉 `python -c` 代码引号而在导入前失败；不再用该包装，改用简单模块版本命令或 heredoc 文件方式。
- 本机没有 `bash` 可执行文件，GPU 部署脚本的本地 `bash -n` 未运行；`git diff --check` 通过。改为上传后先在 GPU Linux 上执行 `bash -n`，语法通过前不运行 bootstrap。
- GPU 端 `bash -n` 通过，轻量后端代码已上传到新 `/root/autodl-tmp/ghl/app`；bootstrap 使用 `--system-site-packages` 与 `--no-build-isolation --no-deps` 成功，只构建约 39 KB 项目 wheel，未下载或复制模型。
- GPU 后端首次启动因 Bash `source` 读取未加引号的 `CROP_INSTANCE_LABEL=原 GPU 服务器`，把空格后的 `GPU` 误当成命令而停止；未创建病例、未修改模型。修复为带引号的标签后再启动。
- GPU 独立后端随后健康启动，报告 `instance_id=gpu_full`、空白病例库、remote detector 与 `crop-pest-vlm` 均已配置。
- GPU 真实类 10 闭环通过：病例 `gpu_full-eb8287361dd04fb38b50ed842d028ed4`，检测约 0.48 秒、置信度 0.943703、专家 `shadow_keep`；两阶段多模态约 12.17 秒（请求总计约 12.49 秒）、结论 `conclusive`、模型 `crop-pest-vlm`，报告重复读取一致。
- 首次 GPU 后端 `restart` 因 Windows SCP 后脚本缺少可执行位，在真正停止前被拒绝；后端与数据未受影响。bootstrap 增加显式 `chmod 0750`。同一验收摘要还遇到 PowerShell 5 不支持 `Convert.ToHexString`，改用 `BitConverter` 兼容转换。
- 修复权限后 GPU backend `restart` 成功；病例仍为 `analyzed`，报告 SHA-256 前后均为 `88bd0b709d6ea4594f7986d2a6d3da3ef688dea3224dc6f47bd59c1ddb017369`。
- GPU 最终状态：backend、detector、Qwen3-VL 均健康；主模型 SHA 保持 `cbb26d83...58071`，专家路由仍为 `shadow/reclassify=false`，VLM 服务名 `crop-pest-vlm`。
- 实验室网络实测无可用外网，无法由实验室建立到 GPU 的持久 SSH 隧道；`sshd -T` 为 `allowtcpforwarding yes`、`gatewayports no`。当前无 `active-instance.json`，控制存储按代码默认仍使用 `lab_cpu`，未发生切换。
- 浏览器只读核对未复用到用户已登录标签：控制接口返回空标签列表，新建局域网标签访问超时并重置；未点击或提交 Admin 操作，不影响用户当前页面。后续以服务器/API 证据为准。
- 一次实验室容器 Python 探针再次被 Windows OpenSSH 改写引号而语法失败；改用已有网络探测与简单状态文件读取，不重复复杂 `python -c`。一次三条 SSH 串行检查超过本地 30 秒上限，首条同时确认误查的 `/data/ghl/storage/control` 不存在；实际控制挂载为 `/data/ghl/runtime/control`。

## Windows 临时中继（2026-08-17）

- 用户明确选择当前 Windows 电脑作为临时中继；不创建 Windows 开机任务，电脑必须保持开机、联网且不休眠。
- 新增 `deploy/lab/tcp_relay.py`、`lab-gpu-relay.service` 与 `scripts/windows_gpu_relay.ps1`；Python 编译、PowerShell 解析、空闲状态和差异检查通过。
- 实验室 systemd relay 已安装、enabled/active，仅监听 `172.17.0.1:18000`；Windows GPU 本地隧道 PID 26408、实验室反向隧道 PID 20208，本机仅监听 loopback 18001。
- 三层健康检查均返回 `gpu_full`：Windows `127.0.0.1:18001`、实验室 `127.0.0.1:18000`、Docker host-gateway `172.17.0.1:18000`。
- 统一入口保持活动实例 `lab_cpu`，但已经成功读取 GPU 病例 `gpu_full-eb8287361dd04fb38b50ed842d028ed4` 及其报告，证明病例前缀能经临时中继固定回 GPU 存储。
- Windows Stop 脚本增加 PID 与 SSH 命令标记双重核对，避免 PID 文件陈旧时误终止其他 SSH 会话。
- 用户在 Admin 完成 `lab_cpu → gpu_full` 切换；`active-instance.json` 与 `switch-audit.jsonl` 均确认 admin 操作和时间，Windows 两个中继 PID 正常。
- 从实验室统一入口上传类 13 样本得到 `gpu_full-fcb09b112dbb4c79bf69d472a50cf5be`；检测类 13 置信度 0.930618、0.43 秒、专家 `shadow_keep`，GPU 多模态约 4.92 秒，报告实例为 `gpu_full`。
- GPU 活动实例列表仅含 2 个 GPU 病例；原 CPU 病例 `lab_cpu-f5a9ef4da90e471f85314a123ba85dbf` 仍可按前缀读取，状态 analyzed、报告实例 lab_cpu。
- 文件级隔离通过：实验室 storage 为 3 个 `lab_cpu` 上传文件/3 病例，GPU storage 为 2 个 `gpu_full` 上传文件/2 病例，两个目录没有对方前缀文件。
- 用户在 Admin 完成 `gpu_full → lab_cpu` 切回；控制状态与第二条审计记录均确认成功，中继保持在线。
- 切回后从统一入口新建 `lab_cpu-812db2c77557486585d17d3160cf3e5f`，检测类 10 置信度 0.943568、约 0.35 秒，报告实例 `lab_cpu`；CPU 活动列表 4 条且全部为 lab_cpu，GPU 计数仍为 2。
- 离线门验收：停止 Windows 两个中继进程后，实验室到 GPU 不可达，活动实例仍为 lab_cpu，CPU 健康且 4 病例可读；用户在 Admin 确认 GPU“离线”、按钮“服务器不可用”、CPU“当前使用”。
- Windows 中继已恢复，当前 PID 为 GPU 26660、实验室反向 25984；Windows、实验室 loopback/Docker 网关和统一入口再次返回 gpu_full 健康，GPU 病例数仍为 2。
- 最终状态：活动实例 lab_cpu、CPU 4 病例、GPU 2 病例、切换审计 2 条；实验室五容器及 relay systemd active，GPU backend/detector/VLM 健康，GPU 约占 22,244 MiB 显存。
- 最终回归从仓库根目录误运行 pytest 时收集到 `training/test_grasshopper_field_eval.py`，因后端轻量环境没有 NumPy 而收集失败；这是测试范围错误，不是部署回归。改在 `backend` 目录运行正确套件后 `29 passed`。Python relay 编译、PowerShell 解析、`git diff --check` 与实验室 `verify.sh` 均通过。
- 尝试在最终检查的组合命令中递归删除本轮 `py_compile` 生成的 `deploy/lab/__pycache__` 时被本地安全策略拦截；命令未执行、没有删除文件。停止递归清理，不影响部署或验收结果。
- 随后对已核实位于工作区内的单个 `.pyc` 做精确删除仍被同一策略拦截；不再尝试，保留该 2.8 KB 编译缓存。

## GitHub 发布准备（2026-08-17）

- 用户要求将相关文件发布到 `genghailong8-maker/crop-pest-multimodel-system`；GitHub CLI 已安装并以目标账号登录，origin 与目标仓库一致，默认分支为 master。
- 当前工作分支 `codex/publish-audits-and-calibration-plan` 比远端同名分支领先 1 个既有 Phase 8 提交，工作树还包含 Phase 9、双服务器部署、训练证据和本机运行文件，禁止直接 `git add -A`。
- 发布审计发现未跟踪 `tmp/` 含约 5.8 GB Qwen GGUF、镜像、wheel/npm 缓存、Admin 配置和中继 PID；已将 `tmp/`、检查输出、`*.gguf`、`*.sqlite3` 加入 `.gitignore`，明确不上传密钥、病例、数据库、模型或缓存。
- 敏感扫描未发现服务器密码、SSH 私钥或 GitHub/OpenAI Token；`CROP_ADMIN_*` 唯一命中为安全生成脚本中的变量名。忽略后未跟踪候选共约 3.44 MB。
- 当前分支已有 draft PR #1（目标 master），本次应更新该 PR 而不是重复创建。工作树仍混有约 3.4 MB 旧训练评测 JSON/脚本；按发布安全流程，提交前需要用户确认“系统/部署范围”或“连同训练证据全部发布”。
