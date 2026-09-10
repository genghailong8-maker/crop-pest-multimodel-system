# 田诊协同——农作物病虫害识别与防治系统

本项目面向第三届“农信杯”编程大赛题目二，采用“视觉模型定位 + 多模态综合分析 + 可追溯知识来源 + 自动判断或拒答”的证据化诊断流程；人工复核仅保留为本机管理审计能力，不阻塞普通用户。

## 已确定的技术路线

- 产品形态：响应式网页系统，适合电脑答辩、手机拍照上传和快速迭代。
- 本机职责：开发网页、后端业务、数据管理和接口联调。
- 服务器职责：视觉模型训练、验证、导出，以及 YOLO 检测服务。
- 模型接入：网页通过后端调用服务器推理接口，本机不承担正式训练负载。

## 当前进度

- 已审计官方训练集：4,164 张图片、5,920 个目标框、16 个类别。
- 已生成按重复图分组的 80/20 训练与验证划分。
- 已隔离 10 张“图片完全相同但标签互相冲突”的样本，未修改官方文件。
- 已建立上传、图像质检、模型适配、记录保存、历史查询和多模态服务适配接口。
- YOLO26n 基线在第 105 轮正常早停；独立验证 mAP50 为 0.7050、mAP50-95 为 0.4253。
- 最佳权重已接入服务器推理服务，网页后端通过 SSH 私有隧道获取真实检测框。
- 已准备服务器环境自检、只读数据挂载、训练、推理和实时监控脚本。
- 界面会明确区分“可参考结论、请补拍、未发现支持目标、服务不可用”，不使用写死的识别结论，也不让普通用户等待不存在处理人的复核队列。
- Phase 6 知识契约位于 `backend/app/knowledge.py`：`GET /api/catalog/knowledge` 返回 16 类知识卡片、来源和安全边界；病例结果中的 `detector_summary.explainability` 保存检测框、置信度、模型/路由证据、来源和人工复核触发原因。
- `POST /api/cases/{case_id}/review` 会记录 `accepted`、`needs_more_evidence` 或 `rejected` 决策及证据快照；`GET /api/cases/review-queue` 和 `GET /api/cases/{case_id}/review-events` 用于复核队列与审计追溯。知识卡片只提供综合防治方向，不生成具体药剂、剂量、混配或安全间隔。
- 当前分析链路为“上传→目标检测→确定性证据整理→保存→查看”：病虫害结论由 YOLO 置信度门控制，Tavily 仅提供可追溯的危害/可能诱因来源，本地 Markdown 知识库提供防治内容。
- Phase 9.9 已接入版本化自建知识库：识别成功后按 16 类 `class_id` 展示症状、特征和防治建议；完整报告保留知识库表格与图片，并将来源标注为百度百科。

## 目录

- `backend/`：API、SQLite 记录、图片存储、视觉模型和多模态服务适配器。
- `web/`：诊断工作台网页。
- `data/official/`：官方数据的只读映射以及本地划分文件。
- `DATASET.md`：官方数据目录、16 类清单、划分数量和外部数据获取说明；完整图片/标签不提交。
- `PROJECT_ASSETS.md`：`best_model.pth`、YOLO 权重和真实运行所需外部资产说明。
- `tools/`：数据审计、划分和服务器数据视图工具。
- `training/`：视觉模型训练与服务器运行脚本。
- `inference/`：服务器 GPU 推理服务、启动脚本和本机 SSH 隧道。
- `knowledge/`：16 类版本化 Markdown 知识文档、相对路径图片与完整性清单。
- `artifacts/dataset-audit/`：数据质量审计结果。
- `docs/competition/`：比赛架构、数据治理、演示、复现和提交包材料。

## 本机运行

比赛现场推荐使用统一入口：

```powershell
cd "C:\Users\genghailong\Documents\编程大赛"
.\scripts\competition.ps1 start
.\scripts\competition.ps1 status
.\scripts\competition.ps1 smoke
```

默认访问 `http://localhost:3000/`。入口会预检 Python、Node、依赖和 SSH，复用或建立 8870 私有隧道，启动后端和生产前端，并输出状态与访问地址。`stop` 只停止入口记录的本机进程和 SSH 隧道，不停止远程 detector：

```powershell
.\scripts\competition.ps1 stop
```

GPU 私钥路径通过 `CROP_GPU_SSH_IDENTITY_FILE` 传入；它必须是 GPU/AutoDL 专用私钥，不要把 GitHub SSH key 当作 GPU key。比赛默认外部证据 provider 为 Tavily（`CROP_SEARCH_PROVIDER=tavily`），缺少密钥或网络失败时状态为 `DEGRADED`，核心诊断仍可用。Google Grounding 是可选兼容 provider（`google_grounding`）；Google Custom Search 仅作为 legacy provider，适用于已有 Custom Search JSON API 资格的用户。入口不会打印密钥。

后端：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

网页：

```powershell
cd web
npm.cmd run dev
```

默认访问 `http://localhost:3000`。模型权重和多模态服务地址通过 `backend/.env.example` 中的变量配置。

如果统一入口无法使用，可按 `docs/competition/demo-runbook.md` 的人工恢复流程分别启动隧道、后端和网页。

## 自建知识库

当前知识库版本为 `baidu-baike-20260818`，内容来源于百度百科并由项目组整理。后端通过 `GET /api/catalog/classes/{class_id}/knowledge-document` 提供详情页三段内容和报告完整内容，图片只允许从版本化知识目录读取。

重新打包时使用 `scripts/package_baike_knowledge.py --source <Markdown目录>`；脚本要求 16 个类别文档完整对应、61 个图片引用存在，并拒绝在输出中保留 Windows 绝对路径。

服务器推理服务与私有隧道说明见 `inference/README.md`。服务器有卡模式可用后，将推理设备设置为 `0` 并重启服务；无卡模式仅用于部署和 CPU 链路验证，不作为正式性能数据。

## 服务器训练

服务器侧操作说明见 `training/server/README.md`。标准顺序为：

1. 检查 NVIDIA 驱动与 GPU。
2. 安装与服务器驱动匹配的 PyTorch CUDA 环境。
3. 上传官方数据并创建只读数据视图。
4. 先运行 5 轮冒烟训练，确认数据、显存和指标链路。
5. 再运行正式训练并保存权重、指标、曲线和环境报告。

## 数据与诊断边界

官方原始数据保持只读。`data/official/splits/quarantine-conflicting-labels.txt` 只记录冲突文件，不会删除或改写数据。

知识契约已登记 16 类卡片和原则级 IPM/绿色防控来源，但不会从图像结果生成具体药剂名称、剂量、混配或安全间隔；这些信息必须来自当地现行标签和植保人员。官方病害样本中的目标框多为病叶范围，也不会直接把框面积等同于病斑严重度。

## Phase 7 比赛交付

- 比赛材料：`docs/competition/architecture-and-innovation.md`、`demo-runbook.md`、`reproducibility-checklist.md`、`presentation-outline.md`、`submission-package.md`。
- 最终复现与公开边界审计：

  ```powershell
  python scripts\final_repro_check.py --output artifacts/release/final-repro-check-20260810.json
  ```

  默认只做静态门并可离线运行；需要强制检查本机后端、推理隧道和网页时追加 `--require-services`。正式性能仍以服务器证据清单为准，当前路由保持 `shadow`。

## Phase 9 面向普通用户版本

Phase 9 已完成自动与 GPU 可实施部分：病例增加受害比例、扩散速度、诊断风险和田间严重度；SQLite 增加 WAL、完整性检查、备份恢复和测试记录隔离；16/16 类补齐逐类权威来源；用户端增加自动判断/拒答、病例历史、趋势、病例详情和可打印报告，管理功能集中在本机 `/admin`。

六个视觉候选 YOLO26n、YOLO26s、YOLO11s、YOLO12s、YOLOv8s、YOLOv5su 已在同一 4,490 张合规统一数据和固定开发划分上完成 120 轮对照。按预设规则选择 YOLO12s 全量重训后，它在官方 833 张冻结集的 mAP50-95 为 0.523463，低于现有主模型 0.548224，因此拒绝晋级；线上继续使用现有主模型与类 10/13 `shadow` 专家证据，并以确定性提取器整理来源证据。

系统最终只在当前电脑运行：前端 `http://localhost:3000/`、FastAPI `http://127.0.0.1:8000/`、SQLite/图片/报告本地长期保存；detector 8870 通过仅监听 `127.0.0.1` 的私有 SSH 隧道使用服务器 GPU。数据库维护见 `docs/competition/database-and-records-20260811.md`，本机启动与健康检查见 `docs/competition/demo-runbook.md`，A–E 当前验收结果见 `docs/competition/user-acceptance-matrix-20260811.md`。

Phase 9 尚未完成的流程门只剩用户在当前电脑的 Chrome/Edge 亲自完成关键用例验收；用户确认后再进入最终 UI/UX 重构。公网部署、域名、Cloudflare、Sites 和跨电脑访问已取消，不再是交付条件。
