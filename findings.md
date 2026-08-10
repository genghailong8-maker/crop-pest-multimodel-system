# Findings & Decisions

## Requirements

- 题目：第三届“农信杯”题目二《基于多模型协同的农作物病虫害识别与防治系统开发》。
- 所有训练使用 GPU 服务器；新增公开数据必须确实有助于训练。
- 公开数据必须有明确类别映射、检测框、许可证和低重复率。
- 先做小规模试训/校准，再决定是否从头训练。
- 官方验证集永久冻结，所有实验保留复现配置、指标和权重。
- 系统需覆盖真实识别、多模型协同、防治知识、可解释性、人工复核和比赛材料。
- 完成本轮工作后的总结性回复必须包含：此次任务完成了什么，以及针对最终项目目标下一步应该做什么；中间进度更新不必重复这两个部分。
- 默认任务结束报告只说明当前小任务完成内容和下一个小任务；当上下文接近上限、即将压缩或用户明确要求时，升级为项目全局报告。全局报告必须涵盖计划/目标进度、已完成优化、当前步骤及目的、后续优化、当前阶段、训练实验数量与保留模型角色数量、最佳模型，以及按训练/官方验证/独立 tune/独立 frozen/test/仅审计未采用划分的数据集构成；报告结尾提醒用户开启新对话。
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
- 2026-08-07 再次通过公开搜索核对：该候选仍为 587 张、1 个 `grasshopper` 类、Object Detection、CC BY 4.0；公开项目页为 `https://universe.roboflow.com/amiruls-workspace-wyolc/grasshopper-qpkes-i1pbc`。
- 本机尚无该候选的图片或标注副本；内置浏览器能打开目标版本页，但动态 DOM 读取超时，尚未完成登录下载。
- 2026-08-07 用户已在 Roboflow 登录成功，并明确授权 Codex 直接下载、保存所需数据；当前浏览器位于数据集版本 1 的下载页。
- 登录态下载页再次确认版本 1 含 587 张图片；可选格式包括 YOLO26/12/11/9/8/5/7、COCO、VOC 等。已选择与源模型和现有解析器匹配的 `YOLOv11`。
- 选择 `YOLOv11` 并 Continue 后，页面短暂进入项目 `/fork` 路径；这表明公开数据集下载可能要求先 Fork 到用户工作区。Fork 会创建新的 Roboflow 数据集副本，需在提交前获得明确授权。
- 2026-08-07 用户已明确允许将该公开数据集 Fork 到其 Roboflow 工作区，以完成 YOLOv11 ZIP 下载。
- 授权后的 Fork 对话框仅提供 Cancel 与 `Fork Dataset` 最终提交按钮，未显示需用户选择的其他配置字段；可按默认工作区创建副本。
- 最后一次自动提交在同一快照内点击时再次超时；随后只读检查发现 `/fork` 标签已关闭，但唯一剩余标签仍是原公开数据集版本 URL。该状态不足以证明 Fork 已创建，必须检查页面可见状态或用户工作区后才能继续下载。
- 用户随后在 `/fork` 页面手动点击了最终按钮。点击后的自动检查中，未接管标签列表为空；先前已接管的公开数据集页仍位于原版本 URL，因此还需用页面可见内容或工作区项目状态确认 Fork 结果。
- 原公开版本页的可见 DOM 已恢复，并明确提供 `/dataset/1/download/yolov11` 下载链接；后续可沿该页面现有链接继续，不需要重复 Fork，也不需要依赖对账户副本状态的推测。
- 已进入 YOLOv11 下载对话框；可见选项明确为 `Download dataset — Get a code snippet or ZIP file`，与本项目所需离线审计流程匹配，不需要启动 Roboflow 云训练或消耗训练额度。
- 在下载对话框点击 Continue 后仍被重定向到 `/fork`；Fork 对话框同时提示，如使用该数据集的预设导出设置，应从可用 Downloads 下载。由于动态 Fork/下载对话框已多次导致自动控制超时，用户手动完成 YOLOv11 ZIP 下载是当前更快、更可靠的路径。
- 用户工作区内当前项目 `grasshopper-qpkes-i1pbc-0o9g2` 的 Dataset 页显示 968 张图片，并提供 `Versions` 导航；该数量与目标公共 v1 的 587 张不一致，不能直接作为独立评估集下载。可能存在重复 Fork、合并或错误项目，必须先在 Versions/项目列表中定位精确 587 张版本。
- `grasshopper-qpkes-i1pbc-0o9g2` 的 Versions 页显示 `No versions created yet`；创建页将基于 968 张源图生成 734 train / 120 valid / 114 test，并会使用额度。该项目不满足目标固定 445/70/72，禁止创建或导出其版本。
- 用户确认 968 张是误添加图片所致。工作区项目列表显示三个同名 `grasshopper` 项目：一个 968 张、两个各 587 张；因此无需修改或删除错误项目，可直接选择一个未改动的 587 张 Fork。
- 用户已选择干净项目 `grasshopper-qpkes-i1pbc-bujaf`；其导航栏 Dataset 数量为 587。已从 Train 页切换到该项目的 Versions 页，未启动训练。
- 干净项目 Versions 页确认源图 587，固定划分 445 train / 70 valid / 72 test，与公共 v1 完全匹配；当前 `No versions created yet`，因此尚无 Download。页面底部 `Create` 会生成版本且标注 `Uses Credits`，需用户明确授权后才能提交。
- 已下载归档 `grasshopper-qpkes-i1pbc-v1.zip`，大小 37,042,590 字节，SHA-256 `958bd065e5197ec144603e62967044b793a1175b3bc56a526bba6a7deea8eaf8`，ZIP 共 1,179 个条目。
- 完整自动审计通过：tune 70（102 框）、frozen 72（160 框）、无排除、无目标无效记录、39 张合法负样本、1 个小于 0.002 归一化容差的边缘框已裁剪并留痕。
- 跨库比较成功解码 13,347 张历史图片，另有 407 张外部坏图被记录并跳过（394 张来自 Pest65、13 张来自本地新增图片）；目标 ZIP 仍保持严格解码失败即拒绝。
- 发现 8 个感知近重复记录，其中 2 个 frozen 负样本分别与 tune 样本的感知距离为 0，另有若干同 split 连续帧；在人工确认这些跨 split 近重复前，`calibration_eligible=false`。
- 已生成 142 张带框离线复核画廊，可筛选 flagged/negative/near/repaired/tune/frozen。视觉抽查 `frozen-000015` 的右边界修复框与昆虫位置吻合；`frozen-000070` 为空场景负样本，画廊正确显示 boxes=0。
- 跨 split 对比确认 `tune-000065` 与 `frozen-000070` 为同一张空场景图片，并非感知哈希误报；`frozen-000070` 应在人工复核中拒绝/排除，防止 tune→frozen 泄漏。
- 第二组跨 split 对比同样确认 `tune-000069` 与 `frozen-000071` 为完全相同空场景，建议排除 frozen 侧记录。
- tune 内 `tune-000002` / `tune-000003` 是同一机位的相邻帧，昆虫与框位置有轻微变化，并非同一像素内容；可保留但人工复核备注其相关性。
- `tune-000029` / `tune-000030` 视觉内容与框完全相同，建议排除后者，避免调参集重复计权。
- `frozen-000008` / `frozen-000009` 视觉内容完全相同，仅框行顺序不同，建议排除后者，避免冻结指标重复计权。
- `frozen-000010` / `frozen-000011` 以及 `frozen-000011` / `frozen-000013` 为同场景相邻帧，机位或昆虫位置存在细微变化；建议保留并在人工备注中说明相关性，而非按完全重复删除。
- `frozen-000021` / `frozen-000022` 同样为细微变化的相邻帧，建议保留并备注。
- 终结门调整为允许带理由的 `rejected` 决定，同时强制所有记录有 accepted/rejected、拒绝项有备注、近重复/修复框接受项有备注，并禁止感知距离 0 的跨 tune/frozen 重复仍同时被接受。
- 已新增 `training/prepare_grasshopper_field_eval.py`：严格要求单一 `grasshopper` 类，保留 valid→tune 70 张、test→frozen 72 张，校验 YOLO 框，映射到官方类 13，执行 SHA-256/16×16 感知哈希并生成 `review.csv`。
- 已新增 `training/finalize_grasshopper_field_review.py`：只有自动门通过、142 条人工复核全部填写 accepted/rejected、拒绝项与近重复/修复框接受项均有必要备注时，才生成正式 `tune.txt`/`frozen.txt` 并设置 `calibration_eligible=true`。
- `training/evaluate_weak_reranker.py` 已支持相对于清单文件解析图片路径，使本机复核结果同步服务器后仍可直接使用；旧绝对路径清单保持兼容。
- 用户确认采用复核建议后，`review.csv` 已写入 138 条 `accepted`、4 条 `rejected` 和 9 条必要备注；严格终结器成功生成 69 tune + 69 frozen，`human_review_status=accepted_with_exclusions`、`calibration_eligible=true`。
- 终结后独立一致性检查确认：manifest 接受 138、复核 142、拒绝 4；两份清单均为 69 行，文件缺失 0，tune/frozen 路径重叠 0；6 项类 13 回归测试通过。
- 用户重新开机后，旧地址已恢复：SSH `connect.bjb2.seetacloud.com:10373` 成功登录，主机 `autodl-container-4129428075-000fbcc8`；RTX 5090（32,607 MiB）空闲，项目盘剩余 43G，远程项目目录存在。
- 服务器只读核验通过：类 10 SciDB 清单为 32 tune + 16 frozen；主模型 SHA-256 `cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071`，类 10/13 crop 专家 SHA-256 `9804458da627e30299114f31e032ad5bcc08a7f74694f6559dcf45b27d7c242c`，均与本地记录一致。
- 已将类 13 最终 `tune.txt`/`frozen.txt`、图片、标签、manifest、review.csv 和六个工具同步到服务器；六个工具 SHA-256 均与本地一致。服务器合并清单实际为 101 tune（32 个类 10 + 69 个类 13）和 85 frozen（16 个类 10 + 69 个类 13）。
- 远程核对时一次未引用的 `grep` 管道留下孤立子进程；已按精确 PID 清理，复核 GPU 为 0 MiB/0% 利用率，未启动任何校准任务。
- 首次第二轮校准已完成但不能作为有效结论：报告计数为 101 tune/85 frozen，然而所有 baseline mAP/F1 为 0。诊断确认类 10 SciDB 标签文件使用本地类别 `0`（应映射官方类 `10`）；类 13 首张样本标注为类 13，但主模型在置信度 0.05 下没有预测框。该报告保留为诊断记录，不能据此决定模型。
- 进一步读取 `training/build_weak_expert_dataset.py` 确认专家类别映射为 `TARGET_TO_EXPERT={8:0, 10:1}`；类 10 独立列表对应的 SciDB labels 中 valid/test 共 0 类 6 框、1 类 27 框，test 共 0 类 3 框、1 类 13 框。有效评测副本按 `0→8、1→10` 重映射，原始符号链接和标签保持不变。
- 有效第二轮校准（101 tune、85 frozen）结果：tune baseline 类 10 mAP50-95 `0.448475`、F1 `0.830189`（TP 22/FP 4/FN 5）；类 13 mAP50-95 `0`、F1 `0`（TP 0/FP 14/FN 100）。tune 网格 3,888 个候选，36 个满足 tune 门；选中温度 10/13=`1.25/0.75`、阈值 10/13=`0.15/0.15`、背景阈值 `0.9`、`keep` 模式。frozen baseline 类 10 mAP50-95 `0.387952`、F1 `0.72`，选中配置为 `0.363993`，类 13 仍为 `0`，未通过 frozen 门。结论：第二轮配置不进入生产，继续保留当前主模型；类 13 独立数据暴露的是检测召回/域差问题，当前 crop 重排无法恢复缺失候选框，因此不因该结果自动重训。

### 当前数据资产与用途口径（2026-08-07）

- 官方比赛数据：4,164 张、5,920 框、16 类；固定 3,321 张训练和 833 张冻结验证，另隔离 10 个冲突重复样本。
- PlantDoc 弱类补充：CC BY 4.0，映射官方类 3/5/7；审计后保留 303 张训练图、785 框，另有 21 张测试图、34 框用于公开数据侧评估。
- ScienceDB/Pests102 弱类子集：训练侧包含类 8 的 105 张和类 10 的 450 张；类 10 另固定 32 张 tune、16 张 frozen，后 48 张不参与 pairwise v5 训练。
- Pest65 蚜虫补充：人工复核后训练侧保留 327 张、1,168 框，曾用于两次类 9 蚜虫增强主模型实验；它不是当前最佳 `official-plus-public-weak-v1` 主模型名称所指的数据源。
- 类 10/13 hard-crop 专家集：从官方训练图的 GT crop、主模型困难候选和背景 crop 派生；v5 共选择 4,690 个 crop，仅来自官方训练划分，官方 833 张验证集未进入。
- Roboflow 类 13 独立数据：源数据 587 张（445 train/70 valid/72 test，CC BY 4.0）；当前只把 valid/test 作为候选 tune/frozen，445 张 train 尚未纳入训练。人工采纳 4 个建议排除项后预计为 69 tune + 69 frozen。
- GreenFlyDB：已完成来源和质量审计，但因含 `greenfly/notgreenfly` 二分类、7 个无效标签文件且需要人工确认到官方类 9 的映射，当前未自动合并训练。
- 本地新增图片与未采用公开候选仍保留在审计资产中；“已下载/已审计”不等于“已用于当前最佳模型训练”。

## Model Findings

### 当前模型库存口径（2026-08-07）

- 本地指标与权重记录能够确认 12 次不同配置的训练运行：官方基线 1 次、Pest65 主模型实验 2 次、公开弱类主模型 smoke/pilot/full 3 次、弱类检测专家 3 次、crop 分类专家 3 次。
- 当前项目保留 4 个不重复的模型角色：官方 16 类基线、公开弱类增强的 16 类生产候选、类 10 弱类检测专家、类 10/13 crop 分类专家。PT/ONNX 导出以及 best/last 权重均不另算模型。
- 当前最佳单一主检测模型为 `official-plus-public-weak-v1-e120-b64/best.pt`；在固定官方验证集上 mAP50 为 `0.827517`、mAP50-95 为 `0.548224`、Precision 为 `0.839196`、Recall 为 `0.776205`，优于官方基线的 `0.705030`、`0.425336`、`0.733906`、`0.683310`。
- 当前最佳专项模型为类 10/13 pairwise crop 专家 v5；最终协同系统仍未冻结，需完成第二轮独立校准和生产路由后才能称为项目最终最佳模型。

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
- 类 10 弱类检测专家 SHA-256：`95a03f1d613681259680f7018f16cdbfef41ff99dd881fd3b9342bfbfcc00a49`。
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
- 2026-08-07 Phase 5 启动：先在本机审查现有推理契约并实现可回退、配置驱动的类 10/13 路由；只有真实权重加载、服务器推理链回归和延迟/显存测量才使用 RTX 5090。第二轮独立校准被 frozen 门拒绝，不能直接晋级其阈值配置。
- Phase 5 服务器链已接入当前生产候选主模型、类 10 检测专家和类 10/13 crop 分类专家；默认 `shadow` 保留主模型输出，`active` 仅显式开启。远程 `/health` 已确认三份权重加载成功，主模型 SHA-256 `cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071`、类 10 检测专家 SHA-256 `95a03f1d613681259680f7018f16cdbfef41ff99dd881fd3b9342bfbfcc00a49`、crop 专家 SHA-256 `9804458da627e30299114f31e032ad5bcc08a7f74694f6559dcf45b27d7c242c`。
- 路由配置已包含 `threshold10`/`threshold13`、`temperature10`/`temperature13`、背景阈值、候选阈值和 score mode；第二轮校准虽作为 shadow 诊断参数记录，但未被晋级为生产 active 配置。真实类 10 图片请求已返回专家支持与耗时，backend 会将这些字段写入 `detector_summary.inference`。
- 本机 SSH 隧道→FastAPI 上传→远程 GPU 推理→病例检测端到端通过；真实响应在 shadow 下保留主模型结果并记录约 35–43 ms 路由耗时。active 隔离冒烟显示该样本会因 crop 专家背景分数 `0.988147` 被丢弃，进一步证明不能在 frozen 门未通过时默认 active。
- 2026-08-07 Phase 5 暂停检查点：服务器推理服务仍由 `/root/miniconda3/bin/python -m uvicorn inference.service:app --host 127.0.0.1 --port 8870` 运行，`/health` 返回 `status=ok`、`class_count=16`、`routing.mode=shadow`；RTX 5090 为 0% 利用率、约 731 MiB/32607 MiB 显存。三份权重均存在且哈希保持不变：主模型 `cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071`（5,394,821 B）、类 10 检测专家 `95a03f1d613681259680f7018f16cdbfef41ff99dd881fd3b9342bfbfcc00a49`（5,383,365 B）、crop 专家 `9804458da627e30299114f31e032ad5bcc08a7f74694f6559dcf45b27d7c242c`（3,189,762 B）。远端检查点已 `sync` 并回拷本地：`artifacts/server/phase5-live-checkpoint-20260807.json`，本地/远端 SHA-256 均为 `9097ca3b9af70403902ee99d42d05e5ea77e5eaaa9cd3f33678e7e99e1961c30`。
- 本机网页已启动在 `http://127.0.0.1:3000/`（备用 `http://localhost:3000/`），FastAPI 在 `127.0.0.1:8000`，SSH 隧道将 `127.0.0.1:8870` 转到服务器；本轮只完成页面可见性和真实图片上传流程的准备，网页识别按钮的最终点击与指标基准尚未完成。下次应从现有浏览器页/本地服务状态继续，不重复服务器链路回归。
- 当前决策保持：`active` 路由不允许；必须先完成网页真实验证和可复现指标，再以 frozen 门结果、误报/漏报和部署成本重新评估。
- 服务器关机检查点：`artifacts/server/phase5-shutdown-task-nodes-20260807.json` 已在远端 `sync` 后回拷本地，远端/本地 SHA-256 为 `7095770760ea9f8007b4cc0bc376152cf0137b9c632db0631344479387b871e8`。检查点记录 5 个任务节点：服务器推理链完成、网页端到端待做、指标基准待做、active 不允许、服务器关机完成。推理进程停止后 GPU 为 0 MiB/0%，随后执行 `shutdown -h now`；复核 SSH 端口拒绝连接，确认服务器已关闭。
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
- 2026-08-07 Phase 5 集成已在本地提交为 `530b29f`（22 个文件，包含推理链、后端/网页传播、测试、校准报告、规划文件和服务器检查点；未包含权重、图片、压缩包或密钥）。首次推送因 `github.com:443` 网络不可达失败；本地提交与工作区内容完整保留，网络恢复后需补推该分支。
- GitHub 连接器只读仓库与分支查询成功，但尝试用 `create_blob` 发布同一提交时返回 `403 Resource not accessible by integration`，未发生远端部分写入；因此当前 GitHub 远端仍停留在 `9cf96fe`，本地最新提交为 `530b29f`、`93e1d1a`，待网络或写权限恢复后按 fast-forward 补推。

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
| Roboflow Fork 项目显示 968 张而非目标 587 张 | 暂停导出，先只读核验 Versions 和工作区中的其他 Fork 项目，防止污染冻结评估集 |
| 外部对比库含 407 张不可完整解码图片 | 将路径与异常写入 manifest 后跳过；目标候选图仍使用严格校验，不降低自动门标准 |

## Resume Findings — 2026-08-07

- 本次恢复重新以 UTF-8 完整读取三个规划文件并检查实际 Git 状态：当前分支仍领先远端 3 个提交，工作树包含类 13 审计工具、规划文件及 `.gitignore` 的未提交修改；这些既有改动必须保留。
- 当前 `Next Step` 不需要服务器：填写 `review.csv` 和运行 `finalize_grasshopper_field_review.py` 均可在本机完成；终结后的类 10/13 第二轮批量推理与校准才需要 GPU 服务器。
- `class13-grasshopper-v1/review.csv` 现有 142 条记录，`review_decision` 和 `review_notes` 全部为空。建议清单给出 4 条拒绝、5 条接受并备注，但剩余 133 条仍须人工确认，不能自动视为已接受。
- 用户随后明确确认拒绝建议的 4 条、接受其余 138 条并写入 5 条指定接受备注；该人工门已完成，不再是当前阻塞。
- 类 13 终结完成后再次探测服务器：`connect.bjb2.seetacloud.com` 仍可解析到 `106.38.204.136`，但 `10373` TCP 不可达；因此尚未同步终结数据、核验远程 GPU/模型/类 10 清单，也未运行 frozen test。
- 已按 UTF-8 完整恢复三个规划文件；当前仍处于 Phase 4，下一步是类 13 独立现场样本复核及类 10/13 第二轮冻结校准。
- 当前分支 `codex/publish-audits-and-calibration-plan` 比远程领先 3 个提交，工作树无已显示的未提交改动。
- 旧服务器关机检查点只证明关机前状态安全，不证明旧 SSH 地址当前仍在线；继续远程工作前必须重新探测地址和 GPU 状态。
- 数据候选下载、许可证留档和人工框质量复核可在本机进行；涉及现有 PyTorch 专家模型的批量推理、第二轮校准或后续训练，应按项目约束使用 GPU 服务器。
- 旧地址 `connect.bjb2.seetacloud.com:10373` 当前 DNS 可解析，但 TCP 端口关闭，旧 AutoDL 实例不可连接。
- 第二轮脚本 `training/calibrate_pairwise_thresholds.py` 会加载 Ultralytics 主检测器与 crop 分类专家，并默认使用 `--device 0` 执行 tune/eval 批量推理；因此正式运行明确需要可用 GPU 服务器。
- 类 10 的 32/16 图片清单记录为服务器相对路径；若新服务器不保留旧项目卷，需要从备份或 ScienceDB 源重新恢复这些数据与清单。
- 本机检查确认类 10 的 `scidb_valid_eval.txt`、`scidb_test_eval.txt` 及 `artifacts/public/scidb-pests102` 均不存在；只有主模型和 crop 专家权重的本地备份。
- 本机有 GTX 1660 SUPER 6GB 且 C 盘约 156 GiB 可用，理论上可做小批量推理，但这不能替代项目既定 GPU 服务器流程，也不能弥补缺失的类 10 数据。
- 用户重新开机后，项目专用 SSH 密钥可登录原 AutoDL 实例；GPU 为 RTX 5090 32GB，检查时利用率 0%、显存 0 MiB，`/root/autodl-tmp` 剩余 43G。
- 远程类 10 清单仍完整：`scidb_valid_eval.txt` 32 行、`scidb_test_eval.txt` 16 行。
- 远程 `/root/autodl-tmp/crop-pest-system` 是工作副本而非 Git 仓库；后续同步必须以本地 Git 工作树为代码真源。
- 服务器类 10 独立集逐项核对结果：48/48 图片存在，48/48 对应标签存在。
- 服务器主模型 `runs/detect/official-plus-public-weak-v1-e120-b64/weights/best.pt` SHA-256 为 `cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071`；crop 专家 `runs/detect/pairwise-crop-cls-10-13-v5-e30-b128/weights/best.pt` 为 `9804458da627e30299114f31e032ad5bcc08a7f74694f6559dcf45b27d7c242c`，均与本地记录一致。

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

## Phase 5 Live Resume — 2026-08-10

- Server `connect.bjb2.seetacloud.com:10373` is reachable again. RTX 5090 reports 32,607 MiB total and about 729 MiB used while the inference service is idle.
- Remote `/health` is `status=ok`, `class_count=16`, `image_size=640`, `routing.mode=shadow`; main, class-10 detector, and crop classifier are all loaded. Their SHA-256 values match the saved shutdown checkpoint (`cbb26d83…`, `95a03f1d…`, `9804458d…`).
- The local tunnel, FastAPI backend, and web server are running for the real-image browser E2E. Active routing remains disallowed until the requested measurements are completed and reviewed.
- Real browser E2E succeeded through the user-facing form using `artifacts/incoming/phase5-e2e-class10.jpg` (640×640). The UI reported acceptable quality, `0` selected detections, `1` shadow expert candidate, and `42 ms` routing time; the case was saved as `3850f4500d164c4cb6562a8f96ef09bc` with status `detected`.
- The saved case records remote request-model time `122.671 ms`, routing `41.638 ms`, crop-expert `23.156 ms`, class-10 detector `15.741 ms`; shadow decision preserved the main model result. The routed candidate had crop support background `0.988147` and class-10 support `8:0.421973`, so active routing must remain disabled.
- Benchmark evidence is saved as `artifacts/server/phase5-benchmark-20260810-route.json` and `artifacts/server/phase5-benchmark-20260810-main-pt.json`. The production shadow route completed 20/20 sequential requests (mean wall 121.501 ms, p95 142.248 ms, 8.082 req/s) and 24/24 requests with 4 workers (wall p95 233.521 ms, 29.572 req/s); all responses remained `routing.mode=shadow`.
- Standalone main PT benchmark on RTX 5090 (10 iterations after 3 warmups) measured batch-1 mean 5.256 ms / 190.246 images/s, batch-8 21.026 ms / 380.474 images/s, and batch-32 86.730 ms / 368.962 images/s. GPU idle was 497.75 MiB and benchmark global peak was 2,587.94 MiB (delta 2,090.19 MiB).
- Current three-model service idle memory is 729 MiB on the 32,607 MiB RTX 5090. Model sizes: main PT 5,394,821 bytes (5.145 MiB), class-10 PT 5,383,365 bytes (5.134 MiB), crop PT 3,189,762 bytes (3.042 MiB), combined PT 13.321 MiB; main ONNX 10,591,452 bytes (10.101 MiB).
- Accuracy remains the fixed official 833-image frozen validation result for the main model: precision 0.839196, recall 0.776205, mAP50 0.827517, mAP50-95 0.548224. The single real field image has no ground-truth annotation, so it is an E2E/latency sample rather than an accuracy estimate. Active routing remains disallowed because the independent frozen calibration gate was rejected (`frozen_acceptable=false`) and the observed candidate's background support was 0.988147.
- A consolidated Phase 5 checkpoint is saved at `artifacts/server/phase5-benchmark-checkpoint-20260810.json`, including server health, routing configuration, model hashes/sizes, web case evidence, benchmark summaries, and evidence SHA-256 values. The remaining Phase 5 item is full experiment monitoring/configuration persistence; no active-route switch is authorized.
