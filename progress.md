# Progress Log

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
