# Findings & Decisions

## Qwen3-VL 移除与轻量证据架构审计（2026-08-24，进行中）

- 基线：`competition-dev`，HEAD `1819b2a9e7ebc4dbb7b5d8465fea31d0a6c1035b`，开始时工作区干净。
- 已确认：`backend/app/config.py` 和 `.env.example` 暴露完整 `CROP_VLM_*` 配置；`backend/app/multimodal.py` 直接调用 Qwen；`backend/app/search/normalizer.py` 的 `build_qwen_context` 仅为 Qwen 上下文预算服务；`scripts/competition.ps1`、`inference/open_tunnel.ps1` 和 `inference/run_vlm_server.sh` 都包含 8890/Qwen 逻辑。
- 已确认：`knowledge/baidu-baike-20260818` 已有 16 个 Markdown 文档和本地图片资产；当前 `knowledge_documents.py` 可安全解析并重写图片 URL、启用 Markdown table，但仅将部分段落加工为摘要字段，尚未提供结构化化学防治提示元数据。
- 待完成：逐类 Markdown 结构清单、病例持久化/路由细节、历史 Qwen 病例兼容边界、实验室 Qwen 服务/模型专属路径确认；未进行服务停止或删除。

### 审计结论（已完成）

- 分析入口为 `POST /api/cases/{id}/analyze`：当前是 YOLO 检测后再调用 `request_multimodal_analysis`，分析 JSON 与外部来源快照都已保存在同一病例记录中。报告快照在读取时优先复用；`test_evidence_persistence.py` 已覆盖“历史报告不重分析”。新实现应保留这些字段与读取行为，仅将新分析的生成者改为确定性提取器。
- 当前正常/补拍阈值仍为 `<0.45`，同时带有 Qwen 对齐/字段一致性分支；本轮应收敛为 YOLO 置信度门：`>=0.75`、`0.50–0.75`、`<0.50`。
- `knowledge_documents.py` 已有真实路径解析、图片后缀白名单与 MarkdownIt table 渲染。资产端点已拒绝 `../manifest.json`；仍需补绝对路径和根目录逃逸的显式回归。
- 当前前端只把全文 `full_html` 置于报告页，结果/病例仍主要消费静态知识卡摘要。应保留视觉骨架，补充 `requires_pesticide_warning`、完整知识文档入口及未检索状态，不能恢复 Qwen 状态/重试语义。
- 本机 8000/8870/8890/3000 均未监听；环境中仅有 Tavily/检索变量，未发现 Qwen 变量。SSH 配置有项目候选主机别名 `ghl`（主机地址未记录到日志）；尚未连接、停止或删除任何远端资源。

### 16 类 Markdown 内容清单

| ID | 类别 | 文档 | 字符 | 标题/防治层级 | 表格行 | 图片 | 化学提示 |
| --- | --- | --- | ---: | --- | ---: | ---: | --- |
| 0 | 玉米叶枯病 | `00.md` | 702 | 5 / 化学防治 | 6 | 1 | 是 |
| 1 | 番茄斑枯病 | `01.md` | 2026 | 6 / 化学防治 | 6 | 4 | 是 |
| 2 | 南瓜白粉病 | `02.md` | 1847 | 6 / 化学防治 | 6 | 4 | 是 |
| 3 | 马铃薯早疫病 | `03.md` | 1931 | 6 / 化学防治 | 6 | 4 | 是 |
| 4 | 玉米锈病 | `04.md` | 2332 | 6 / 化学防治 | 6 | 4 | 是 |
| 5 | 番茄细菌性斑点病 | `05.md` | 2354 | 6 / 化学防治 | 6 | 4 | 是 |
| 6 | 番茄晚疫病 | `06.md` | 2327 | 6 / 化学防治 | 6 | 4 | 是 |
| 7 | 马铃薯晚疫病 | `07.md` | 2798 | 6 / 化学防治 | 6 | 4 | 是 |
| 8 | 芫菁 | `08.md` | 1885 | 7 / 化学药剂防治 | 7 | 4 | 是 |
| 9 | 蚜虫 | `09.md` | 2238 | 7 / 药物防治 | 7 | 4 | 是（关键词回退） |
| 10 | 盲蝽科 | `10.md` | 1806 | 4 / 防治方法 | 7 | 4 | 是（正文关键词） |
| 11 | 蝼蛄 | `11.md` | 1991 | 6 / 防治方法 | 7 | 4 | 是（正文关键词） |
| 12 | 叶蝉科 | `12.md` | 2533 | 7 / 化学防治链接标题 | 7 | 4 | 是 |
| 13 | 蝗总科 | `13.md` | 3385 | 7 / 化学防治 | 7 | 4 | 是 |
| 14 | 蛴螬 | `14.md` | 3783 | 4 / 防治方法 | 7 | 4 | 是（正文关键词） |
| 15 | 豆芫菁 | `15.md` | 2763 | 11 / 药剂防治 | 7 | 4 | 是 |

- 以上图片均为 Markdown 相对路径，61/61 实体存在；文档 hash 与 manifest 已存在，不修改原始 Markdown。检测规则将优先解析“防治方法”下的化学子层级，再使用受控关键词回退。

### 本地实现与远端只读验证（2026-08-24）

- 已完成：删除 `backend/app/multimodal.py` 与 VLM 启动/恢复脚本；删除 `CROP_VLM_*` 配置、8890 健康、上下文预算及启动/隧道依赖。新 `EvidenceExtractor` 为纯 Python 抽取器，结论逐句来自已规范化来源正文并只绑定该来源 ID；无来源时返回 unavailable，不使用模型自身知识补写。
- YOLO 门已统一为：`>=0.75` 可参考、`0.50–0.75` 建议补拍、`<0.50` 不形成明确结论。Tavily 不可用时分析仍完成，本地知识库、防治内容和病例快照可用。
- 知识接口现在返回原始 Markdown、完整 HTML、相对图片重写后的资源 URL、化学检测来源与风险提示；病例/报告正文渲染表格、图片、链接、列表、引用和风险提示。旧病例仍只读使用既有 `analysis`/来源快照，不触发重分析。
- 本地验证：初始 backend `67 passed`（1 条第三方 TestClient deprecation warning）；`competition.tests.ps1` PASS；web ESLint PASS；web production build + 渲染 `8/8` PASS；`git diff --check` PASS。续作发现两个真实来源相关性边界后，新增回归并以 backend `69 passed` 为最终计数。活动运行代码/测试/启动脚本/隧道/环境示例内 Qwen/VLM/8890 搜索结果为零；旧状态字符串仅保留用于历史病例的只读兼容。
- GPU 只读探测：SSH 候选主机可连接；`127.0.0.1:8870` 拒绝连接，不能做新链路三病例 E2E。8890 存在 `/app/llama-server` Qwen3-VL 进程（参数指向 `/models/Qwen3VL-8B-Instruct-Q4_K_M.gguf` 与对应 mmproj），但它归入系统的 `cpolar.service` cgroup、模型目录在当前命名空间不可列出，且未发现项目部署目录。因此不能安全判定为本项目专属资源；未停止、隔离、删除服务或文件。
- 续作测试审计：基线 77 个测试定义、当前 69 个；`test_multimodal.py` 删除 20 个 Qwen/VLM 协议、图像二阶段、8890 配置与故障测试，`test_search.py` 删除 8 个仅用于 `build_qwen_context` 预算/截断的测试，`test_api.py` 删除 1 个 VLM 故障重试测试。新增 `test_analysis.py` 3 个置信度门测试、`test_evidence_extractor.py` 16 个来源逐句/来源 ID/去重/空证据/类别相关性测试，知识库新增 2 个全文与农药提示测试；其他 API、搜索 provider/normalizer、快照持久化、重启读取、知识库、公开 API、安全路径测试仍在。
- 续作正式残留审计：发现旧 `backend/run_local_server.cmd` 和两条检索连通性脚本仍含 Qwen 上下文遗留；已最小清理为 detector + provider/normalizer 语义。三份 2026-08 历史 Phase 9 文档已在顶部明确标注“历史架构记录”，不再可作为当前运行说明。
- 三病例真实验收首轮发现：蛴螬的一个泛病虫害集合页包含其他虫种段落，抽取器会错误优先其中的危害句。已收紧为“结论句或来源标题必须直接包含当前类别”；宁可不输出，也不使用同页其他类别的真实但无关句，并新增回归测试。
- 8870 恢复诊断：项目脚本默认 `connect.bjb2.seetacloud.com:10373` 的专用候选密钥在 SSH 握手阶段被拒绝；`ghl` 是另一可连接实验室。该机 `lab-detector-1` / `lab-vlm-1` 是 `/data/ghl/app/deploy/lab` Compose 内部容器，未映射 8870/8890 到宿主机；检测器容器内部和宿主到容器健康均返回 200、`class_count=16`、三份模型 loaded、shadow 路由。仅建立 `127.0.0.1:8870` 到容器 `172.18.0.4:8870` 的 SSH 转发，不重启或重配远端。
- 8890 安全：`lab-vlm-1` 仍使用 `/data/ghl/models/qwen3-vl:/models`，但项目本机没有 8890 监听；本轮未停止、删除、重启该容器或 `cpolar.service`。正式扫描仅剩三份明确标注“历史架构记录”的 Phase 9 文档；`web/package-lock.json` 的 5 条为 integrity hash 子串碰撞，不是依赖或调用。
- 三病例 E2E（当前运行后端）：蛴螬 `lab_cpu-fb47d9966b824f91ba57fa2884840c07`，0.918733、1 框、5 来源、available；马铃薯晚疫病 `lab_cpu-5edc4b9ae9094a98b03d23011f48714c`，0.913733、1 框、5 来源、available；马铃薯早疫病 `lab_cpu-a767365fb3f344a9aabfaa7345f73cf5`，0.684728、1 框、`retake_required`、0 来源。高置信度病例均使用 `deterministic_evidence_extractor`，知识库与农药风险提示均在；低置信度病例按门控跳过 Tavily/抽取而不是伪造结论。
- 重启与前端：本地 backend/frontend 已按入口 stop/start 后读取新、旧病例及报告；`updated_at` 不变，来源快照、知识库和警示可读，旧 `multimodal_unavailable` 病例也只读可开。浏览器发现生产入口的 `/assets/*.js` 返回 404，导致病例/报告页停在“正在读取病例”；SSR、API 和 8/8 render tests 虽通过，但此项阻止 UI 真实展示验收，最终状态只能 conditional PASS。
- 静态资源 404 首轮实证：`vinext build` 输出实际位于 `web/dist/client/assets`，包含 JS/CSS；当前 3000 为 `vinext start --host 127.0.0.1 --port 3000`。运行中 SSR HTML 仍引用旧 build 的 `index-CFhjZoVX.js` 等文件，而新 build 已输出 `index-DFyqv_ac.js`；无论磁盘文件是否存在，`GET /assets/*` 都返回 404。生成的 `dist/server/wrangler.json` 正确声明 `assets.directory="../client"`，因此问题不是缺少 build 产物，而是 Node 生产服务器没有将该静态目录映射到 `/assets`。

## UI Redesign V3 视觉复核（2026-08-20）

- 视觉方向按 Product Design 探索后的 Clinical Agriculture 70% + Field Intelligence 30% 落地；Scientific Minimal 只吸收报告的纸面排版语法。
- 真实核心路径已替换为 V3：`v3-app` 工作台、`ProductMark` 证据汇流标、`ImageEvidenceFrame` 图片证据舞台、`FieldFacts` 田间字段、`DiagnosisPath` 诊断路径、`DiagnosisSummary` 结论块、来源化 `ComprehensiveAnalysis` 和纵向 `KnowledgeSummary`。
- 首页截图核验：1280px 为图片/田间信息双栏，390px 为图片→田间信息→提交；服务不可用时保留警告与禁用态，不展示虚假模型结果或进度。
- 病例/报告错误态核验：报告页头部与打印按钮的类名冲突已修复；病例错误提示已从原始 `Failed to fetch` 改为普通用户可理解的服务器/病例读取提示。
- `ImageEvidenceFrame` 已把检测框绑定到实际图片舞台，避免背景留白造成坐标偏移；报告知识库图片补齐缺失 alt、lazy loading 和 async decoding。
- 浏览器 390px 未观察到横向溢出；公共导航、表单、状态和错误均有语义化 DOM。品牌首页链接从约 42px 调整到 44px 触控高度。
- Assessment B 检测器命中 `reports/[id]/page.tsx:25` 的 `<img>` 字符串替换两次；源码核验为给知识库图片补 alt/加载属性的正则字面量，不是破损图片，判定为误报。由于 Assessment A 子代理超时关闭，本轮由主上下文补充设计审阅，最终 critique 标记为 degraded。

## UI Redesign V2 发现（2026-08-20）

- 旧首页最大问题不是颜色，而是任务结构：大介绍区延迟操作、图片与字段缺少空间关系、空结果区占据第二块大卡片。
- V2 使用图片/田间信息双栏后，1280px 工作区可同时看到采样图和全部主要字段；390px 自然降为单列，无页面级横向溢出。
- 统一 `DiagnosisSummary` 能避免首页、病例和报告对同一病例采用不同阅读顺序。
- `resolution_status=conclusive` 与 `analysis=null` 可能同时出现；展示层必须将其视为“定位完成、等待综合核对”，不能提前标记为参考结果。
- 结果高风险或需人工复核时，长篇知识附录会压过风险声明，因此 V2 只在分析完成且不属于高风险/人工复核状态时展示。
- Impeccable detector 最初命中 Inter、装饰网格和侧边强调条；polish 后三项均已移除。
- 当前剩余主要债务是 V2 与历史 `globals.css` 共用少量基础类，以及精确受害比例输入对普通用户仍有估算压力；二者不阻断本轮交付。

## 公共诊断流程 P2 复审（2026-08-20）

- 报告页屏幕正文由大量 11px 提升到 14px/约 1.75 行高，打印正文统一为 11pt；病例详情建立 12px 标签、14px 正文、20px 分节标题三级层级，保留表格的高信息密度。
- Vinext 的 `next/image` 会把图片请求送到 `/_vinext/image`；病例图片来自动态、无缓存 API，且包含检测框覆盖和打印要求，机械迁移会改变真实显示链路。因此保留原生 `<img>`，补齐原始尺寸、语义化 alt、`loading`、`decoding` 和关键图片优先级，并为 ESLint 例外写明原因。
- 结果页行动顺序与视觉权重已固定为“打开诊断报告”主按钮、“查看病例详情”次级入口；移动端主按钮占满宽度，次级入口保持 44px 触控高度。
- 390px 浏览器验证：首页、病例详情和报告均无横向溢出；报告正文实测 14px/24.5px，详情正文 14px/23.8px；品牌入口和历史入口实测高度均为 44px。
- CPU 耗时提示已改为完整边框的现有 surface/border token，不再使用单侧强调线；本轮触及的报告与行动颜色均改用现有语义令牌。
- 训练进度的 `transition: width` 仅存在于 Admin/训练监控，按用户约束不修改；全局 CSS 仍有未完全令牌化的历史颜色，二者作为 P3 保留。
- 本轮没有后端代码或接口修改；动态 API 图片策略、双服务器归属和既有业务状态保持不变。

## 自建知识库接入审计（2026-08-18）

- 用户知识库包含 16 个 UTF-8 Markdown，与 `CLASS_CATALOG` 的 0–15 类按中文名一一对应。
- 文档实际引用 61 张图片，总计约 5.2 MB；图片均存在于 `E:\病图片`，但绝对 Windows 路径必须在打包副本中改为相对路径。
- 15 个文档含“特征”章节；“玉米叶枯病”缺失该章节，按需求显示“知识库暂未收录该项”，不从其他章节推断或生成。
- 当前报告是 `crop-report-json-v1` 不可变快照；升级必须新增 v2 版本文件并保留原文件，不能覆写历史版本。
- 实验室服务器五容器在线，`/data` 剩余约 3.0 TB，尚无独立知识库目录；本阶段只重建 backend/web，不修改 detector、VLM 或 GPU 主机。
- 实验室部署后 3 个已有可靠病例升级为 v2，复查为 `eligible=0/already_v2=3`；SQLite `integrity=ok`，6 个病例图片均存在。
- 叶蝉病例详情和报告实测通过：三个知识栏目正确；报告含 2 个表格、4 张已加载图片、百度百科来源，两个页面均无“查看技术证据”。

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

## Phase 5 Full Evidence — 2026-08-10

- 已新增可重复采集脚本 `scripts/collect_phase5_evidence.py`，并生成统一证据清单 `artifacts/server/phase5-full-evidence-20260810.json`。最终清单大小 108,768 bytes，SHA-256 为 `753ff334045ddabbe99ba20db69df8155e0e56e1e742cd7316563a4697e0733a`；清单同时记录采集时的 Git 分支/提交、运行环境、证据文件 inventory 和各文件 SHA-256。
- 采集时 `http://127.0.0.1:8870/health`（远程推理隧道）、`http://127.0.0.1:8000/health`（FastAPI）、`http://127.0.0.1:8765/health`（训练监控）以及 `http://localhost:3000/training`（网页训练监控入口）均可达；网页返回 HTTP 200。最新病例接口也可达，病例 `3850f4500d164c4cb6562a8f96ef09bc` 保留在清单中作为 E2E 追踪证据。
- 训练监控由远程 `training/server/run_monitor.sh` 维持运行，`/api/training/status` 返回 20 个运行摘要和完整当前运行曲线。当前选中运行 `pairwise-crop-cls-10-13-v5-e30-b128` 已完成 30/30 epoch；RTX 5090 快照为 0% 利用率、729 MB/32607 MB 显存、27°C、约 4.64 W，GPU 历史采样随清单保存。
- 生产配置已固化为 `routing.mode=shadow`、`reclassify=false`、`score_mode=keep`、候选阈值 0.05、背景阈值 0.90、目标阈值 0.15、`threshold10/13=0.15/0.15`、`temperature10/13=1.25/0.75`；三路模型均报告 `configured=true, loaded=true`。`active_routing_allowed=false`，在新的独立 frozen 门通过前不得切换。
- 保留模型角色和权重证据：官方基线 PT `0443b179564564fce071b7595e1c4a68484a339230951c5e8cefe279af066192`；生产主模型 PT `cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071`（5,394,821 B）；类 10 检测专家 `95a03f1d613681259680f7018f16cdbfef41ff99dd881fd3b9342bfbfcc00a49`（5,383,365 B）；类 10/13 crop 专家 `9804458da627e30299114f31e032ad5bcc08a7f74694f6559dcf45b27d7c242c`（3,189,762 B）；生产主模型 ONNX `048b9050caa2db6389881865fe16818968e75d3f11fd288d4fa6a88181a258e2`（10,591,452 B）。服务端 health 中的三份加载哈希与本地权重记录一致。
- 指标证据仍以官方冻结 833 张验证集为准：主模型 precision `0.839196`、recall `0.776205`、mAP50 `0.827517`、mAP50-95 `0.548224`。主模型 PT 基准（RTX 5090，预热后 10 次）为 batch 1/8/32 吞吐 `190.246/380.474/368.962 images/s`，平均延迟 `5.256/21.026/86.730 ms`，全局显存峰值 `2,587.94 MiB`；shadow 路由压测 20/20 顺序成功（均值 121.501 ms、p95 142.248 ms、8.082 req/s），24/24 并发成功（p95 233.521 ms、29.572 req/s）。
- 有效第二轮独立校准仍为拒绝：101 tune、85 frozen、3,888 个候选、36 个 tune-acceptable；选中配置在 frozen 上类 10 mAP50-95 从 `0.387952` 降至 `0.363993`，类 13 为 `0.0`，`frozen_acceptable=false`，决策 `keep_current_main_model`。因此本证据固化只记录参数，不将其晋级为 active。
- 证据清单的完整一致性校验通过：四个模型角色及 ONNX 文件存在、加载哈希匹配，四个健康/网页探测均为 reachable，训练运行数为 20，路由为 shadow，独立 frozen 门为 false；当前唯一未跟踪工作区文件 `CLAUDE.md` 未纳入清单提交范围。

## Phase 6 Start — 2026-08-10

- 当前 `CLAUDE.md` 不是可执行的纯 Markdown 准则，而是一次 `Invoke-WebRequest` 的序列化输出（正文仅残留标题、谨慎优先于速度等截断内容）；文件保持原样、不加入 Git。按可见准则执行小步修改、先验证后提交、保留证据和用户文件。
- 现有后端已有 16 类 `CLASS_CATALOG`、检测框/置信度、图像质量标记、路由和模型哈希元数据，以及预标注复核 API；但 `catalog.py` 只有类别名称，缺少来源、证据等级、非化学防治和安全边界，诊断结果也没有把知识卡片或复核审计统一关联起来。
- Phase 6 的安全决策：先登记可追溯的综合防治（IPM）和观察/隔离/清洁/栽培管理建议；在没有逐类权威标签、作物登记和当地法规核验前，不输出具体药剂、剂量、混配或安全间隔。低置信度、无目标、候选接近或质量异常一律保留人工复核入口。

### Phase 6 Source Register (initial)

- `fao-ipm-principles`: FAO, “Principles and practices”, https://www.fao.org/pest-and-pesticide-management/ipm/principles-and-practices/en/ — supports ecosystem approach, resistant varieties, rotation/intercropping, sanitation and using pesticides only when effective alternatives are unavailable.
- `fao-ipm-definition`: FAO, “Integrated Pest Management”, https://www.fao.org/pest-and-pesticide-management/ipm/integrated-pest-management/en/ — supports combining biological, physical, cultural and chemical measures while reducing pesticide risk.
- `cn-crop-pest-regulation`: Ministry of Agriculture and Rural Affairs of the PRC, “农作物病虫害防治条例”, https://fgs.moa.gov.cn/flfg/202004/t20200403_6340771.htm — supports prevention-first, integrated/green control and healthy cultivation measures such as rotation, sanitation and removal of diseased residues.
- `cn-green-control`: Ministry of Agriculture and Rural Affairs, “2013年全国农作物病虫害绿色防控示范区建设方案”, https://zzys.moa.gov.cn/gzdt/201304/t20130411_6309844.htm — supports ecological, biological, physical and scientifically supervised control as green-control categories.
- These sources are general IPM policy/principle references, not product labels. The application must show them as provenance and must not infer product, dose, mixture, re-entry or pre-harvest interval from an image.

### Phase 6 Implementation Evidence — 2026-08-10

- Added `backend/app/knowledge.py` with schema `phase6-knowledge-v1`, 16 class cards, four source records, source retrieval dates, evidence levels, observation focus, first actions, escalation conditions and explicit prohibited inference fields.
- Added `GET /api/catalog/knowledge` and `GET /api/catalog/classes/{class_id}/knowledge`. Detection responses now include `detector_summary.explainability` with normalized detection evidence, confidence band, model SHA/routing/timing evidence, knowledge card/source IDs, safety boundary and review reasons.
- Added SQLite-compatible `review_events_json` migration and `review_events` response field. `GET /api/cases/review-queue` lists low-confidence/near-candidate/quality/no-target cases; `POST /api/cases/{case_id}/review` records decision, reviewer ID, notes and an evidence snapshot; `GET /api/cases/{case_id}/review-events` exposes the audit trail.
- Updated the diagnosis page to show the knowledge card's observation/first-action guidance, source IDs, shadow route and safety boundary, and to submit “请求补充证据” or “确认当前候选” decisions. README documents the contract and endpoint boundary.
- Validation: backend `9 passed` with one pre-existing Starlette deprecation warning; web `npm test` passed (build + 3 rendered routes); web lint has `0 errors` and the same 3 existing `<img>` warnings; live 8000 `/health`, `/api/catalog/knowledge`, and `/api/cases/review-queue` returned successfully.
- This Phase 6 slice does not require GPU/server training. The remote inference service remains untouched in `shadow` mode; no active-route or weight change was made.

## Phase 7 Start — 2026-08-10

- Phase 7 已进入 `in_progress`。本阶段目标是把已验证的系统事实整理成比赛材料，固化可重复的 5 分钟演示和离线降级行为，并以标准库脚本完成最终复现/公开边界门。
- 已创建 `docs/competition/architecture-and-innovation.md`、`demo-runbook.md`、`reproducibility-checklist.md`、`submission-package.md`；材料明确官方 3,321/833 划分、独立 101/85 门控、4 个保留模型角色、主模型冻结指标和 shadow-only 决策。
- 已创建 `scripts/final_repro_check.py`。脚本不依赖第三方 Python 包，静态检查知识契约、Phase 5 全量证据、必需文件和 Git 跟踪边界；后端/推理/网页探测为可选项，`--require-services` 才会把不可达视为失败。
- Phase 7 文档与静态复现检查不需要 GPU；真实网页识别仍需要可用的推理服务或兼容远程端点。当前没有授权启动训练、切换 active 或改写服务器权重。
- 公开边界继续执行 `PUBLICATION_POLICY.md`；`CLAUDE.md` 仍是用户工作区内未跟踪文件，不修改、不加入提交包。

## Phase 7 Completion — 2026-08-10

- **Status:** complete. 比赛材料五件套已完成：架构/数据治理/创新、5 分钟演示与离线容错、最终复现清单、答辩幻灯片提纲、公开提交包边界。
- `scripts/final_repro_check.py --require-services` 通过：20 个必需文件存在；知识契约 16 类、4 来源、化学边界存在；Phase 5 证据的官方 3,321/833、独立 101/85、4 个保留模型角色和 `active_routing_allowed=false` 一致；Git 禁止跟踪文件 0；后端、知识接口、推理隧道和网页全部可达。
- 回归：backend `9 passed`（1 个既有 Starlette 弃用警告）；web `npm test` 3/3 通过；web lint 0 errors、3 个既有 `<img>` warnings；Python 编译和 `git diff --check` 通过。
- 当前本机后端健康接口显示 `detector_mode=unconfigured`，这是离线/无环境变量进程的安全降级状态；推理隧道仍报告 16 类、三模型加载、`shadow`。真实识别演示使用 `demo-runbook.md` 中的 `CROP_DETECTOR_ENDPOINT=http://127.0.0.1:8870/v1/detect` 启动方式，并以 Phase 5 已保存的真实网页 E2E 作为准确率之外的链路证据。
- 生成报告写入被忽略的 `artifacts/release/`，不进入公开提交；`CLAUDE.md` 仍保持未跟踪原样。
- Phase 7 本地提交已创建；`git push origin codex/publish-audits-and-calibration-plan` 与一次只读 `git ls-remote` 均受到当前 GitHub HTTPS 连接重置/不可达影响，停止重试，远端未发生部分写入。网络恢复后只需 fast-forward 推送本地领先的 1 个 commit。

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

## Phase 8 Start — 2026-08-10

- 用户确认采用服务器自托管 `Qwen/Qwen3-VL-8B-Instruct`、网页一键完整分析，并将 Karpathy Guidelines 只写入 `task_plan.md` 的强制规则。
- 服务器 `connect.bjb2.seetacloud.com:10373` 已使用项目专用密钥重新认证成功：RTX 5090 32,607 MiB、检查时 0 MiB/0% 使用，`/root/autodl-tmp` 剩余约 43G；当前没有 Uvicorn、vLLM 或 Ollama 进程。
- 服务器基础 Python 为 3.12.3、PyTorch `2.8.0+cu128`、CUDA 12.8、GPU capability `(12, 0)`；未安装 vLLM/Transformers/Accelerate，也没有 Docker 命令。部署必须使用 `/root/autodl-tmp` 下隔离环境和缓存，不能污染已有 Ultralytics 基础环境。
- 当前后端 `backend/app/multimodal.py` 使用自定义 JSON 直返契约，只验证响应为字典；Phase 8 将以最小改动切换为 OpenAI-compatible chat completions，并用 Pydantic 严格验证 C 项结构。SQLite 继续复用 `analysis_json`，不做迁移。
- 当前网页上传后会自动检测，但多模态分析仍需单独点击且只显示少量字段；Phase 8 将串联上传→检测→分析，并在多模态失败时保留病例/检测结果和仅分析重试入口。
- 安全边界不变：多模态只能补充解释，不能降低检测链已有人工复核风险；无目标、低置信度、低质量、候选冲突或视觉/多模态冲突必须复核；不输出药剂剂量、混配、采收间隔等处方。
- 本阶段不切换 detector active 路由、不启动重训，也不把第二轮 rejected calibration 配置晋级。
- 2026-08-10 官方 Qwen3-VL 模型卡明确给出 `pip install vllm`、`vllm serve Qwen/Qwen3-VL-8B-Instruct` 和 OpenAI-compatible 图文 chat-completions 示例；因此不需要自建推理 API 包装器。官方模型卡：https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct 。
- 服务器 Python 3.12 的包索引可用且当前提供 vLLM `0.26.0`；为保证复现，Phase 8 部署脚本固定该版本，而不是每次安装不确定的最新版。
## Phase 8 VLM Runtime Finding — 2026-08-10

- Qwen3-VL weights loaded successfully on the RTX 5090 (16.65 GiB of weight memory). Startup then failed only during optional FlashInfer sampler warmup because FlashInfer 0.6.14 misidentified the Blackwell architecture; this was not an out-of-memory event. vLLM's documented `VLLM_USE_FLASHINFER_SAMPLER=0` fallback is therefore used while keeping the working FlashAttention backend.

## Phase 8 Live Endpoint and Browser Findings — 2026-08-10

- The pinned Qwen3-VL snapshot is served as `crop-pest-vlm` from `/root/autodl-tmp/crop-pest-vlm/model`; `/v1/models` reports max context 8192. The service uses `vllm==0.26.0`, listens only on server `127.0.0.1:8890`, uses 65% configured GPU memory and measured about 21,156 MiB idle after load.
- The detector service is separately healthy on `127.0.0.1:8870`, covers all 16 classes and remains `routing.mode=shadow`; all three detector-side weights retain their saved hashes. The local tunnel forwards both private endpoints, and backend `/health` reports `detector_mode=remote`, `multimodal_configured=true`, `multimodal_model=crop-pest-vlm`.
- Real browser weak/no-target sample: the existing class-10 field image retained the saved detector result (0 selected detections, 1 shadow candidate), produced a strict no-primary VLM result, and forced human review. Real normal sample: official class 2 detected `南瓜白粉病` at 91.78%, Qwen3-VL returned the same primary diagnosis with complete C-item fields; deterministic alignment reconciliation changed the model's contradictory raw `conflict` to `agree` and recorded the raw value in provenance.
- A controlled local VLM endpoint outage proved the web keeps the newly created case, image quality, 91.78% detection and shadow evidence, exposes `仅重试综合分析`, and succeeds after endpoint recovery without re-uploading or re-detecting. Reloading the page restored the persisted case and analysis from history.
- Exact failure reruns established that large-image HTTP 400 responses were context-length violations, not random endpoint failures. Per-request `mm_processor_kwargs.max_pixels=1003520` keeps the complete image content while bounding vision tokens; all nine previously failed samples then succeeded with schema/content completeness 100% and no unsafe output.

## Phase 8 Final Evidence — 2026-08-10

- Final evidence `artifacts/server/phase8-multimodal-evidence-20260810.json` is 16-class stratified at 10 images/class (160 total), SHA-256 `be54b463fcb6a709197510159d963e668d825d68ce7ee780c29f575b74baf415`. All 160 succeeded; failure rate 0, Top-1 0.8625, schema-valid rate 1.0, content-nonempty rate 0.58125, unsafe outputs 0 and risk-preservation failures 0.
- Per-class Top-1: 0/2/3/4/11/14 = 1.0; class 5/7/9 = 0.9; class 6/10/12/15 = 0.8; class 8/13 = 0.7; class 1 = 0.5. The longest-catalog-name rule prevents class 15 `豆芫菁` from being counted as class 8 `芫菁`.
- Conflict evaluation: 17 cases had a detector primary outside ground truth, but the VLM/final alignment identified only 1 (5.8824%); 132/160 results requested human review. This is a measured limitation, not a reason to enable active.
- VLM mean/P50/P95 latency is 2221.518/2238.267/2756.890 ms; end-to-end P50/P95 is 2325.747/2949.004 ms. Sequential throughput is 0.429228 image/s; 8 requests with concurrency 2 all succeeded in 9.510 s, 0.841212 image/s.
- Peak GPU memory is 24,024 MiB. The materialized model directory is 17,545,920,365 bytes (about 16.34 GiB), isolated runtime venv 8,319,801,095 bytes, and complete VLM root 25,888,950,823 bytes.

## Phase 9 Planning Checkpoint — 2026-08-10

- 用户要求将以下工作安排到 2026-08-11，本次对话不执行：从用户角度核验题目要求和完整构建；识别未满足项并优化；验证其他电脑/浏览器直接打开与依赖；核验后端数据库检测记录存储并在确有缺口时实现；由用户亲自验证用例；全部完成后再做前端 UI 重设计。
- 当前已知基线：Phase 8 的真实多模态端点、后端严格结构校验、一键上传→检测→分析、失败保留/仅分析重试、真实浏览器 E2E、16 类证据和最终复现门已完成；`active` 仍禁止。
- 明天必须先把“已有自动化证据”与“用户可完成的人工验收”分开，不能仅因 `phase8-final-repro-v1` 通过就推断另一台电脑可直接打开，也不能仅因已有 SQLite/病例 API 就推断跨设备集中存储已满足。
- 跨电脑检查的重点是实际架构边界：网页、FastAPI、127.0.0.1 端口转发、远程 detector/VLM、训练监控、CORS/防火墙/HTTPS、依赖和数据目录是否需要同时存在；结论必须给出用户可执行的下载/安装/启动清单。
- 数据库检查的重点是持久化字段、重启/刷新恢复、数据库路径与备份恢复、并发与隐私边界；只有验收发现真实缺口并获得实现授权时才扩展数据库，不预设必须更换 SQLite。

## Karpathy Guidelines Audit — 2026-08-10

- **结果：已使用。** `task_plan.md` 已有 `Mandatory Karpathy Guidelines`，明确覆盖“修改代码前分析假设、优先简单实现、避免无关重构、所有修改必须可验证、修改范围必须与任务直接相关”五项用户要求。
- `findings.md` 与 `progress.md` 的历史记录已将该规则用于 Phase 8 的范围控制、最小实现、验证和 `CLAUDE.md` 保留边界；Phase 9 计划也要求发现问题后先列出假设和最小修复范围。
- **持续执行决定：** 从后续每一项代码、配置、测试、部署和 UI 任务开始，必须先写明假设与成功标准，再实施最小直接相关改动，并立即运行可重复验证；不做未授权的相邻重构。
- **审计边界：** 现有日志能证明规则已经写入并被引用，不能反向证明历史每一行改动都完成了逐项合规审计；后续阶段以规划文件、变更差异、验证结果和错误记录作为证据。

## Test Server Connection — 2026-08-11

- 本机默认 `~/.ssh/id_ed25519` 不存在；使用项目已有私钥 `~/.ssh/codex_autodl_nongxin_2026` 可成功认证 `connect.bjb2.seetacloud.com:10373`。
- 远程检测服务和 Qwen3-VL 服务初始均已停止；按仓库既定脚本启动后，检测器 `127.0.0.1:8870` 与模型服务 `127.0.0.1:8890` 均已就绪。模型服务返回 `crop-pest-vlm`，最大上下文 8192。
- 本机双 SSH 隧道已建立：检测器 `127.0.0.1:8870`、VLM `127.0.0.1:8890`；本地 FastAPI 后端运行在 `127.0.0.1:8000`，网页运行在 `localhost:3000`。
- 连通性验证：后端 `/health`、知识库接口、检测器 `/health`、VLM `/v1/models` 和网页首页均返回 200。后端报告 `detector_mode=remote` 且多模态服务已配置。
- 本次只恢复测试运行链路，没有修改业务代码、数据库结构、模型权重或 Phase 9 计划状态。

## Phase 9.1 CPU/Static Preflight — 2026-08-11

- 按 GPU 等待边界完成 CPU/静态前置核验；没有启动远程 detector、Qwen3-VL、SSH 隧道或 GPU 请求。
- 后端回归 `17 passed`，网页 `npm.cmd test` 的构建与 3 个路由渲染测试通过；lint 为 0 errors、3 个既有 `<img>` warnings。
- SQLite 默认路径为 `backend/runtime/crop-pest.sqlite3`；只读检查显示 11 条病例记录（analyzed 7、detected 3、model_unavailable 1），`PRAGMA integrity_check` 为 `ok`。
- `diagnosis_cases` 已覆盖环境、质量、检测框、detector summary、分析、复核和复核事件 JSON 字段；当前未发现需要立即扩展数据库的证据。
- 发现的非阻塞边界：没有自动备份/恢复脚本；图片路径依赖 `runtime/uploads`；SQLite 并发写入和跨浏览器重启恢复尚未运行时验证；GPU 相关完整链路继续等待。
- 详细矩阵已写入 `docs/competition/user-acceptance-matrix-20260811.md`。本阶段不修复问题、不进入 9.2–9.6。

## 题目二评分细则审计 — 2026-08-11

- **评分依据：** 用户目录微信文件中的《2026第三届“农信杯”编程大赛》PDF 第 8 页“评分项具体判定标准”；题目二满分项为 A 图片上传与基础流程 15 分、B 视觉识别/定位与展示 25 分、C 多模型协同综合分析 25 分、D 知识库与防治建议 20 分、E 系统质量/创新/答辩 15 分。
- **A：** 代码、后端测试和 Phase 8 真实网页证据覆盖上传、作物/部位/生育期、检测、分析、保存、历史查看；按功能证据接近/达到满分。仍需在服务器恢复后现场再次演示，确认不是仅依赖已保存证据。
- **B：** 实际 YOLO 主检测器覆盖 16 类，输出框、类别、置信度，并对多目标、无目标、低质量进入人工复核；按细则功能已基本达到满分条件。当前 `shadow` 专家只补充证据，不覆盖主模型结论，不能把专家路由描述成已经提升主模型。
- **C：** Qwen3-VL 已接入并收到原图、视觉结果、作物/部位/生育期/环境等字段，输出结构化诊断、症状、危害、诱因、依据、候选、置信度和复核信息；但 160 张正式分层样本的关键内容非空率只有 58.13%，17 个预期冲突只识别 1 个（5.88%），因此按满分标准的“处理相近类别、低置信度和模型冲突”仍只能判为部分达标。
- **D：** 已有 16 类知识卡片、4 个来源 ID、农业/物理/生物/IPM 方向和农药标签安全边界；但来源主要是原则/法规级来源，尚不是逐病虫害的当地标签或权威药剂登记库，也没有结构化风险等级与严重度映射，因此现场评分存在从满分降为部分分的风险。
- **E：** 已有网页、FastAPI、SQLite 病例/复核审计、训练监控、复现材料、shadow 安全边界和模型/数据说明；但题目二满分项要求的完整识别记录、严重程度、趋势或报告能力尚未形成独立功能，跨电脑稳定运行与现场答辩仍未验证，故 E 不能无条件视为满分。
- **当前明确未满足或证据不足的满分点：** C 的多模态内容完整性与冲突识别；D 的逐类权威来源/风险分级/针对性防治证据；E 的严重程度/趋势/报告和跨环境稳定演示；A/B/E 的“现场稳定演示”尚受 GPU、隧道和部署环境约束。
- **评分结论边界：** 不把 PPT、自动化报告或历史成功日志单独当作现场功能验收；正式评分仍需服务器恢复后用项目样本完成真实演示，并记录截图、接口响应、日志和用户操作结果。

## 新版 Phase 9 实施基线 — 2026-08-11

- 用户已明确授权以新版 9.1–9.8 替换旧 Phase 9 顺序，把 A–E 评分缺口与验收、数据库、公网、用户测试和 UI 改造统一实施；UI 不再等待旧 9.5 用户验收后才开始，而是在 CPU 可完成阶段与后端契约同步实现。
- **公开模式决定：** 匿名用户可上传；明确同意后病例进入共享公共历史并保留 30 天；旧病例默认私有。匿名用户只可用一次性病例编辑令牌修改自己的病例。
- **部署决定：** Sites 提供公网前端；当前主机继续承担 FastAPI、SQLite、上传图片和 SSH 模型隧道。浏览器只访问同源 `/api/*`，Sites Worker 注入 origin secret；detector 和 Qwen3-VL 不直接暴露公网。
- **严重度决定：** `diagnostic_risk` 表示系统诊断可靠性风险，`field_severity` 表示结合用户受害比例、扩散速度和图片的田间辅助判断；缺少受害比例或扩散速度时后者必须为“无法判断”。现有人工复核 `severity` 字段继续使用。
- **模型决定：** 在线链路保持 3 个视觉模型加 1 个 Qwen3-VL；专家只提供 `shadow` 第二意见。多模态升级为两阶段，先独立看图，再与 YOLO/专家/质量证据比对；不新增第二个大模型，不启用 active，不自动重训。
- **GPU/公网阻塞：** 当前 GPU 不可用，不执行真实 160 张评估、性能或完整 E2E。用户尚无域名和 Cloudflare 账号，固定公网地址必须等人工准备完成；这两个阻塞不妨碍数据库、协议 mock、知识、UI 和本地构建测试。
- **最小修改范围：** 只修改 Phase 9 直接相关的规划、FastAPI/SQLite、多模态协议、知识卡片、网页与部署文档/测试；保留用户未跟踪 `CLAUDE.md` 和既有训练/模型证据。

## Phase 9 CPU 实施发现 — 2026-08-11

- 病例主表已用兼容迁移补入受害比例、扩散速度、公开同意、过期时间、诊断风险、田间严重度和编辑令牌哈希；旧病例仍为私有。SQLite 启用 WAL、busy timeout、完整性检查，并提供备份、恢复、过期删除和图片路径检查。
- `phase9-multimodal-v2` 已实现两个独立请求：阶段一 prompt 不包含 YOLO 类别；阶段二才比较独立判断、主检测、质量风险和 shadow 专家。确定性门覆盖冲突、无目标、低置信度、质量异常、字段矛盾与“风险不可降低”。
- 16/16 类现均有至少一个逐类权威来源；报告 API 展开来源标题、机构、URL 和检索日期，不再要求普通用户理解内部 source ID。
- 新用户端已形成首页、公共历史、趋势、病例详情和打印报告；浏览器检查覆盖 1280×720 与 390×844，无横向溢出。技术参数继续收在折叠区。
- Sites Worker 已完成同源 API 代理、origin secret 注入、公共模式管理页 404 和主机不可达 503；但固定 API 域名、Cloudflare tunnel 和 Sites 正式发布仍缺用户人工前置。
- 公开趋势严格描述为“系统收到的公共上传记录”，不等同真实地区疫情；SQLite 仍只定位单主机演示和小规模公开测试。
- 生成的 `web/public/phase9-social-preview.png` 仅作网页分享预览，不作为项目样本、检测结果或评分证据。

## Phase 9 最终 UI 顺序决定 — 2026-08-11

- 用户新增要求：系统设置和功能验收完成后，按照最终确认的需求再次重构 UI 界面。
- 当前 9.5 已完成的是支撑普通用户功能验收的基础界面，不应被描述为最终视觉定稿；新增 9.9 专门承担系统定型后的最终 UI/UX 重构。
- 9.9 的硬入口是 9.1–9.8 全部完成，包括 GPU 真实链路、公网固定地址、数据库/安全边界、跨电脑与手机测试以及用户关键用例确认。底层接口或流程仍可能变化时不得提前重构。
- 最终 UI 重构只基于用户确认的真实反馈和定型数据契约，优先信息架构、操作路径、响应式、可访问性和各种状态；继续使用现有前端技术栈，不顺带修改模型、数据库或后端业务。
# Phase 9 本机交付范围变更 — 2026-08-12

- 用户明确取消公网部署、Sites、Cloudflare、域名、固定 HTTPS 隧道和另一台电脑访问要求；最终系统仅在当前电脑运行。
- 运行拓扑锁定为：前端 `localhost:3000`、FastAPI `127.0.0.1:8000`、SQLite/图片/报告本机保存；detector 8870 与 Qwen3-VL 8890 继续通过仅监听回环地址的私有 SSH 隧道使用服务器 GPU。
- 本地病例选择长期保存：不要求公共展示同意、不执行 30 天自动过期；历史和趋势默认使用 SQLite 全部病例。现有 11 条旧病例多数 `public_consent=false`，若沿用公共默认范围会错误隐藏，因此必须按 `settings.public_mode` 选择查询范围。
- 公网 Worker、`CROP_PUBLIC_MODE`、公开同意、过期时间、编辑令牌、origin secret 和限流代码保留但默认停用；这是比删除整套已测试实现更小、更安全的修改。
- Phase 9.9 最终 UI 重构入口改为：GPU 真实链路、数据库持久化、本机 Chrome/Edge 和用户关键用例通过；不再等待公网或跨设备验收。
- 新后端进程的真实接口确认：`public_mode=false`，默认 `/api/cases` 返回 11 条，`/api/trends?days=30` 统计 11 条；浏览器历史和趋势页面均能逐条追溯。
- 浏览器检查发现病例 `2ae2e30d46004bf4bcc162fcb8eb2e1a` 的作物/部位/生育期为既有乱码（显示为 `???? · ?? · ??`）。这是历史数据本身的问题，不属于本次本机交付语义修改；为避免未经授权改写病例，本轮只记录。
- 数据库维护检查为 `integrity=ok`、11/11 图片路径存在；重启生命周期测试证明带旧 `expires_at` 的本地病例不会在启动时被清理。
- 当前本机 FastAPI 与网页可用，但 detector 8870、Qwen3-VL 8890 不可达，因此不能执行或宣称 Phase 9 GPU 真实评估和完整 E2E 已完成。

## Phase 9 GPU 真实冒烟发现 — 2026-08-12

- 服务器 RTX 5090 已恢复；远程 detector 与 Qwen3-VL、8870/8890 本机回环隧道均已启动。健康检查确认主检测器覆盖 16 类、两个专家模型已加载、路由保持 `shadow`；本机 FastAPI 已按真实模型配置重启且 `public_mode=false`。
- Phase 9 两阶段 16 类冒烟使用官方冻结验证列表每类 1 张，共 16/16 请求成功，Schema 与内容字段完整率均为 100%，不安全农药输出 0，已有风险错误清除 0，证明真实两阶段协议可运行。
- 冒烟未通过正式评估前置门：田间严重度依据仅 3/16 同时明确引用“受害比例 12.5%”与“扩散速度缓慢”；3 个主检测类别错误样本中显式冲突识别为 0；端到端 P95 为 8.902 秒，高于 7 秒目标。16 张 Top-1 为 50%，仅作逐类冒烟，不能代替 160 张正式分层指标。
- 根因假设：严重度引用目前只依赖模型遵循提示，没有确定性后处理；冲突校验错误地使用已看到 YOLO 证据的第二阶段最终诊断，而非第一阶段独立判断，且输出未被约束到 16 个规范类名或“无法判断”；两阶段均固定 `max_tokens=1200`，未针对阶段内容长度设置上限。
- 最小修正范围锁定为 `backend/app/multimodal.py`、对应测试和 Phase 9 证据收集字段：强制保留用户田间输入引用、用独立判断执行确定性一致性校验、限制规范诊断名称、记录两阶段诊断/耗时，并在 16 类复测通过后才启动 160 张正式评估。不修改检测器权重、路由、冻结数据或 UI。
- v2 同样本复测为 16/16 成功、Schema/内容完整率 100%、严重度输入引用 16/16、预期冲突识别 3/3、不安全输出与风险错误清除均为 0，说明确定性协议修正有效。
- v2 仍未放行正式评估：Top-1 为 56.25%，第二阶段在主检测正确时仍多次机械沿用错误的独立判断；E2E P95 为 9.012 秒。两阶段耗时显示阶段二重复携带原图后常占 3–7 秒，而其职责是比较阶段一图像摘要、YOLO、shadow、质量和田间字段，不需要再次编码同一原图。
- 下一最小假设：阶段一保持真正多模态独立看图；阶段二改为仅接收结构化文本证据，并明确 `primary_diagnosis` 是综合结论、`detector_alignment` 是独立判断与 YOLO 的一致性，两者不能混为一谈。这样不改变模型数量和安全门，预期同时降低重复图像开销与独立判断锚定。
- v3 证明取消第二阶段重复图片没有显著降低生成耗时：16/16 成功，E2E P95 仍为 9.015 秒；最终 Top-1 仍为 56.25%。问题不是重复视觉编码本身，而是完整结构输出长度和综合类别职责不清。
- 既有同一 160 张 Phase 8 证据重新计算显示：主检测器 Top-1 为 139/160（86.875%），原多模态综合为 138/160（86.25%）。因此 Phase 9 最终类别采用主检测器规范主候选，多模态独立判断保留为候选/冲突/人工复核证据；这与既定“专家和多模态不覆盖主模型、风险只升级”边界一致。无检测框时仍保留多模态的“无法判断/候选”结论。
- v4 前置门通过：16/16 成功，Schema/内容/严重度引用均 100%，预期冲突 3/3，不安全输出 0，风险错误清除 0；E2E P50/P95 为 4.420/4.838 秒。Top-1 13/16（81.25%）等于该小样本的主检测正确数，仅用于逐类冒烟；正式门仍由固定 10 张/类的 160 张结果决定。
- Phase 9 固定 160 张正式真实评估全部硬门通过：160/160 成功，Top-1 87.50%，Schema/内容/严重度输入引用均 100%；17 个主检测错误样本中独立判断识别出 15 个冲突（88.24%）；不安全输出 0、已有风险错误清除 0。端到端 P50/P95 为 4.444/5.087 秒，并发 2 成功 2/2，峰值显存 23,058 MiB。证据文件为 `artifacts/server/phase9-multimodal-evidence-20260812.json`，SHA-256 `9b31bb691063c14759f70c0283d2f78fd5fee5d4f4c92c749d4568c6d2aba45d`。
- 本机真实 E2E 证明新协议并非只在批处理脚本中可用：病例 `4992820b001c4dc18a1b7619209fec5c` 的主检测为南瓜白粉病 0.917845，路由 `shadow`，Qwen 独立判断一致，田间严重度 low，严重度依据包含受害比例 12.5% 和缓慢扩散，分析总耗时 4.561 秒；报告含 5 个权威/原则来源。
- 本机故障边界已实测：detector/VLM 双隧道关闭时上传仍持久化且检测返回 `model_unavailable`；仅 VLM 不可用时病例保留 `detected` 状态和检测框，恢复后仅调用分析接口即可完成。历史、趋势与报告不依赖 GPU 在线。
- SQLite 在线备份、恢复与 FastAPI 重启均通过，当前 14 条病例、14/14 图片路径有效，主 E2E 病例的分析和复核事件可恢复。剩余的 Phase 9 门不是技术实现，而是用户亲自在当前电脑 Chrome/Edge 完成关键用例并确认；该确认前不得进入最终 UI 重构。

## Phase 9 满分与普通用户产品诊断 — 2026-08-12

- **结论：不能宣称完全满足满分。** A–E 的主要功能和既定自动硬门已大部分满足，但用户 Chrome/Edge 亲自验收、PDF 保存确认和最终 UI/UX 重构仍未完成；评分最终还取决于现场演示和评委判定。
- **模型硬门已通过：** 固定 160 张为 160/160 成功、Top-1 87.50%、Schema/内容/严重度引用 100%、冲突识别 15/17（88.24%）、不安全输出和风险错误清除均为 0、E2E P95 5.087 秒。
- **安全与可用性的张力：** 102/160（63.75%）触发人工复核；71 张被判独立判断与视觉候选冲突，其中 56 张不是预期 detector 错误样本。硬门达标不等于复核成本可接受，当前会造成普通用户频繁看到“待复核”。
- **人工复核尚未形成产品闭环：** 病例页会写入 `review_pending`，但普通用户端没有责任人、处理时限或反馈机制；现有 `/review` 页面读取的是预标注队列，不是 `/api/cases/review-queue` 的病例队列。
- **普通用户判断：** 在技术人员先启动 3000/8000/8870/8890 且有人讲解时，普通用户可以完成上传和查看结果；但系统还不适合“完全不懂术语、无人指导、独立长期使用”的用户。
- **主要 UX 缺口：** 移动端隐藏主导航且没有替代入口；受害比例、生育阶段、诊断风险、田间严重度、视觉候选和独立多模态判断仍需解释；大量用户端辅助文字为 9–11px；触控目标、键盘焦点、200% 缩放和屏幕阅读器尚未正式验收。
- **数据与演示可信度：** 本机 21 条病例中有 1 条 `crop/part/growth_stage` 为 `????/??/??`，趋势页也显示 `????`；真实 E2E 病例使用了带 Alamy 水印的图库样本。数据库完整性和 21/21 图片路径正常，但这些内容不宜直接用于正式演示。
- **正面结果：** 首页主流程清晰，默认隐藏 SHA/阈值/JSON，服务不可用时不伪造结果，病例历史、趋势、报告、备份恢复和模型故障重试均已有真实证据；前端产品语言已明显优于开发者界面。
- **技术 UI 审计：** Implementation Integrity 3/4、Accessibility 2/4、Performance 3/4、Theming 3/4、Responsive 2/4，总计 13/20（Acceptable）。静态 detector 只报 1 个非主用户流程的宽度动画 warning；主要风险来自人工复核闭环、移动导航、可读性和术语，不是框架或性能崩坏。

## Phase 9 当前问题整改启动 — 2026-08-12

- 用户确认普通用户端采用“自动判断或自动拒答”，不再依赖人工复核队列；证据不足必须诚实提示补拍或无法判断，不能强制猜测。
- 用户确认本机管理区采用独立 `/admin`，普通导航不展示管理功能且本机模式不设置口令。
- 用户确认数据库先备份，再将实施开始前的 21 条开发/评测记录全部标记为测试；普通历史与趋势隐藏，管理区保留可追溯查看。
- 用户要求统一治理可用检测数据，并公平对照 YOLO26n、YOLO26s、YOLO11s、YOLO12s、YOLOv8s、YOLOv5su；允许训练期间暂停 detector 与 Qwen3-VL。
- 只读服务器检查确认 RTX 5090 32,607 MiB，当前 detector 约占 746 MiB、Qwen3-VL 约占 22,298 MiB；项目盘剩余约 19 GiB。训练必须先停推理释放显存，并控制中间产物占用。
- 当前计划明确：单一主模型只替代视觉检测层；Qwen3-VL继续负责独立看图、证据比对、风险解释和防治建议。
- 数据隔离已落地：源库备份后，实施前 21 条均以 `is_test=true` 可逆标记；普通 API 0 条、管理测试范围 21 条、全部范围 21 条、普通趋势 0 条，21/21 图片仍存在。
- 自动结果采用派生而非重复存储：服务不可用、无支持目标、图片硬质量风险、主候选低于 0.45、明确模型冲突分别映射为四种用户状态；纯模型“建议复核”不再阻塞普通用户，但技术证据和管理接口继续保留。
- `/admin` 已独立显示 21 条测试病例，普通用户导航不含管理入口；公网兼容 Worker 对 `/admin`、`/review`、`/training` 均返回 404。
- 桌面/390×844 浏览器检查：普通页可见文字最低 14px，输入 16px，最小操作高度 44px，移动导航 3 项均为 46px，无横向溢出。Impeccable detector 仅报非普通流程训练进度条的既有 `transition: width` 警告，按避免无关重构保留。
- 统一数据完整质量审计最终得到 4,490 张合格图片：官方 3,321、PlantDoc 303、ScienceDB 555、Pest65 311；固定种子划分为开发训练 3,816、内部验证 674。官方冻结 833 张清单 SHA-256 为 `91a777a8818b8766f49f67891562d1cd808198a89586ec370b49a9e56d7096a4`，未用于架构选型；独立 OpenCV 复核 4,490/4,490 无解码警告。
- Pest65 审核清单中 11 张图片标签为空、4 张 JPEG 损坏、1 张包含重复框，已按 `invalid_label`、`invalid_image` 排除，且没有伪造框或修补原图；计划中的 Roboflow 类 13 原始训练 445 张在服务器不存在，记为 `excluded_missing_source`，没有使用既有 tune/frozen 集替代。
- 六模型统一开发集结果表明，没有候选在该内部验证划分上同时显著领先：YOLO11s 综合分最高 `0.495082`，YOLO12s 为 `0.493887`，差值仅 `0.001196`；YOLO12s 的整体 mAP50-95 更高（`0.529228` 对 `0.525417`）且 Recall 更高（`0.756101` 对 `0.750980`），但弱类均值更低（`0.411423` 对 `0.424303`）。因此严格按事先冻结的“分差不超过 0.005 时先看 Recall”规则选 YOLO12s，而不是事后更改权重。
- 六模型完整排序证据为 `artifacts/server/phase9-model-search-20260812.json`；资产 SHA 证据为 `artifacts/server/phase9-model-assets-20260812.json`，统一数据与 OpenCV 审计证据分别为 `phase9-unified-dataset-manifest-20260812.json`、`phase9-opencv-audit-20260812.json`。
- YOLO12s 全量重训后的官方冻结结果没有超过当前线上基线：mAP50-95 `0.523463`（基线 `0.548224`）、mAP50 `0.809507`（基线 `0.827517`）；Recall 虽从 `0.776205` 提升到 `0.798434`，但弱类均值只有 `0.328963`，且类 13/15 相对基线下降超过 0.02。按预设硬门必须拒绝晋级，不能用单一新模型替换当前 shadow 链。
- 冻结评测与门判定证据为 `artifacts/server/phase9-yolo12s-frozen-metrics-20260812.json`、`phase9-yolo12s-detector-gate-20260812.json`；训练记录为 `phase9-yolo12s-final-training-20260812.json`。由于 detector 门已失败，继续为该候选运行 160 张多模态评估不会改变晋级结论，属于不必要 GPU 消耗，故按计划停止候选验证并恢复原服务。
- 原模型链恢复后固定 160 张复测与整改前指标一致且满足既有硬门：160/160 成功、Top-1 87.50%、Schema/内容/田间输入引用 100%、冲突 15/17、E2E P95 5.105 秒、峰值显存 23,088 MiB；说明产品整改、数据隔离和六模型实验没有破坏当前线上模型协议。
- 普通用户状态已由真实浏览器确认：无目标病例显示“无法判断 / 请补拍”，正常南瓜白粉病病例显示“已有可参考结果”、92% 模型匹配程度、较低严重度和田间依据；普通历史为空，管理页可追溯全部测试记录。技术上仍保留 `needs_human_review` 供审计，但用户决策不再依赖无人处理的等待队列。

## Phase 9.11 弱类混淆与专家 shadow 专项验证启动 — 2026-08-12

- **用户要求：** 先统计类 8/10/13/15 的具体混淆关系，检查训练/验证数据是否足够干净独立，以 `shadow` 方式验证现有专家是否改善，只有冻结集稳定提升且其他类别不下降才考虑上线。
- **实施边界：** 复用现有主模型、类 10 检测专家和类 10/13 crop 专家；不改线上主模型、不启用 `active`、不重划官方 833 张冻结集、不删除或改写原始数据。
- **验证门：** 混淆必须区分漏检/低 IoU 与错分类；数据必须记录来源、数量、标签质量、哈希去重和冻结隔离；专家结论必须同时比较弱类、总体和全 16 类非回归。
- **当前状态：** 服务器 8870/8890 和本地 8000 已健康，detector `routing.mode=shadow`、`reclassify=false`，三份视觉权重已加载；专项评测尚未形成新的最终证据，下一步先完成冻结集混淆与数据清单核验。

## Phase 9.11 弱类专项结果 — 2026-08-12

- **四类混淆：** 官方冻结集 833 张上，类 8 共 98 个 GT 框，正确 62，错为类 15 共 15，错为类 13 共 2，漏检 18；类 10 共 87 个 GT 框，正确 67，错为类 13 共 6、类 8 共 4，漏检 10；类 13 共 89 个 GT 框，正确 54，错为类 10 共 18、类 8 共 5、类 9 共 3，漏检 9；类 15 共 83 个 GT 框，正确 66，错为类 8 共 13，漏检 4。预测视角下最主要的对称关系是 8↔15 和 10↔13，不能只靠提高置信度解决，因为同时存在漏检和已定位后的错分类。
- **数据充分性与独立性：** 统一允许数据 4,490 张，开发训练 3,816、内部验证 674，四类框数 8/10/13/15=`498/800/352/322`；4,490/4,490 OpenCV 解码检查无问题。训练/内部验证、专家 tune/frozen、官方 frozen 的 SHA-256 交叉均为 0；但官方 frozen 内部有 3 组重复内容哈希（833 文件、830 唯一 SHA），已作为指标局限保留。类 10/13 独立校准为 101 tune、85 frozen；类 8/15 没有独立专家 frozen，现阶段不足以支持四类专家上线声明。Roboflow 类 13 原始训练 445 张因服务器缺失被排除，未用 tune/frozen 伪装替代。
- **Shadow 实测：** 复用现有 8870 服务完成 833/833 请求，观察到 `routing=shadow`、`reclassify=false`；shadow_keep 与主模型输出完全相同。类 10/13 候选覆盖分别为 76/87、75/89，crop 专家在已覆盖框上的 Top-1 一致分别为 62、53，这说明专家产生了证据，但不能等同于净收益。
- **Active 反事实：** 使用当前服务返回的专家支持和线上校准规则做同一数据集离线对照，结果 mAP50-95 `0.505247→0.503916`（下降 `0.001331`），弱类均值 `0.309752→0.304430`（下降 `0.005323`），类 10 下降 `0.002504`、类 13 下降 `0.018787`；因此总体和目标弱类均未满足非下降门，不能启用 active。该脚本 mAP 只用于同代码相对比较，不替代官方 Ultralytics 冻结基线 `0.548224`。
- **最终决策：** 当前主模型继续在线；类 10 检测专家和类 10/13 crop 专家继续只提供 shadow 第二意见，不参与最终检测类别决策；类 8/15 当前没有专家路由。专项证据为 `artifacts/server/phase9-weak-classes-audit-20260812.json`、`artifacts/server/phase9-shadow-route-20260812.json`、`artifacts/server/phase9-weak-classes-shadow-evidence-20260812.json`。
- **会话结束状态：** 已封存 `artifacts/server/phase9-weak-classes-session-checkpoint-20260812.json`；远程 detector、Qwen3-VL 和本机 8870/8890 隧道已停止，远程 GPU 显存为 0 MiB。远程是平台容器，PID 1 为 `/init/boot/boot.sh`，`systemctl/poweroff/reboot` 均被拒绝，实例本身仍需在 SeetaCloud/AutoDL 控制台停止；未将未完成的实例级关机伪报为成功。

## 2026-08-13 本机 GPU 真实测试发现

- **运行环境：** SSH `root@connect.bjb2.seetacloud.com:10373` 可用；远程 GPU 为 RTX 5090（32,607 MiB），检测器和 Qwen3-VL 已恢复。本机 `3000/8000/8870/8890` 全部健康，线上路由仍为 `shadow`。
- **正常链路通过：** 现有类 10 样本完成上传、检测、两阶段分析、保存、历史/报告读取；检测置信度 `0.9437`，状态 `conclusive`，Qwen3-VL 协议 `phase9-multimodal-v2`，完整分析约 `4.53s`，报告来源数 5。
- **无目标链路部分通过：** 后端状态、风险和补拍动作正确，但详情页标题仍可能展示 Qwen3-VL 的独立候选类别。这会让普通用户误以为系统已经确认了一个系统不支持的类别，属于需要优先修复的 P1 产品/安全问题。
- **服务故障链路部分通过：** detector 关闭时能保留病例并返回 `service_unavailable`；Qwen3-VL 关闭时病例和检测证据保留，接口返回 HTTP `502`，恢复后“仅重试分析”成功，但还需要把该 502 收敛为结构化用户态不可用结果。
- **持久化与数据隔离通过：** FastAPI 重启后健康、病例详情、报告和趋势可读；SQLite 完整性检查为 `ok`。当前 29 条记录全部为测试记录，普通历史/趋势不显示，管理区可追溯。
- **浏览器检查：** 普通导航未暴露管理功能；首页上传入口、桌面 DOM、390×844 响应式视口和键盘焦点检查通过。Chrome/Edge 的真实人工关键用例仍是未完成验收项。
- **模型结论保持不变：** 当前线上主模型官方冻结集基线为 Precision `0.839196`、Recall `0.776205`、mAP50 `0.827517`、mAP50-95 `0.548224`。六候选中 YOLO11s 仅在开发集综合分暂列第一，YOLO12s 最终冻结门失败（mAP50-95 `0.523463`），因此没有切换。类 10/13 专家产生证据但冻结集 active 反事实下降，继续 shadow；类 8/15 没有独立专家冻结数据，当前没有训练并上线专家模型的必要性证据。
- **证据文件：** `artifacts/server/phase9-real-test-20260813.json`、`artifacts/server/phase9-detector-smoke-20260813.json`、`artifacts/server/phase9-detector-failure-20260813.json`、`artifacts/server/phase9-failure-recovery-v3-20260813.json`；自动化回归为后端 `24 passed`、前端 6 tests/build 通过、lint 0 errors/5 warnings。

## 两项问题修复前分析 — 2026-08-13

- 无目标页面问题的根因已确认：`web/app/cases/[id]/page.tsx`、首页和报告标题直接优先读取 `analysis.primary_diagnosis`，没有先判断 `resolution_status`；因此独立多模态候选可能被普通用户理解为最终诊断。
- 同一问题还影响普通用户的内容边界：详情页症状/危害/可能原因和报告防治方向没有统一受 `conclusive` 限制；修复后非 `conclusive` 只显示状态、补拍/恢复提示和不确定性，不展示疾病特定建议。
- 多模态故障问题的根因已确认：`backend/app/main.py` 只把 `MultimodalUnavailable` 转为病例状态，`httpx.HTTPError` 和 `ValueError` 直接转 HTTP 502；修复后所有已知上游/协议故障统一为结构化 HTTP 200。
- 产品决策：不训练新专家模型，不改变 `shadow`；采用本机用户优先的结构化 200，而不是让前端解析 HTTP 错误后再找回病例。

## 两项问题修复结果 — 2026-08-13

- 新增 `userDiagnosisTitle`/`isConclusive` 用户展示边界；首页、历史、病例详情和报告统一使用状态优先标题，管理端仍保留原始候选供审计。
- 无目标真实病例 `9607fad8942747a18736cff5b1ac006c` 已验证：首页、详情和报告主标题均为“无法可靠判断”；详情显示“暂不形成具体诊断”，报告不展示疾病特定防治方向；最后已标记测试记录。
- 多模态故障统一为 `multimodal_unavailable` + `service_unavailable` + HTTP 200；用户提示为“图片识别结果已经保存，但综合分析暂时不可用”，分析按钮为“仅重试综合分析”。底层异常只记录日志，不直接返回。
- 故障状态会强制 `diagnostic_risk=high`、`field_severity=unknown`，防止旧的成功分析结果在服务不可用时继续显示为可靠结论。
- 实测关闭 8890 后 `/analyze` 返回 HTTP 200；恢复 8890 后对已有有目标测试病例仅重试分析成功，状态 `analyzed`、`conclusive`，无需重新上传或检测。
- 未训练新专家、未切换主模型、未启用 `active`、未修改数据库结构；线上仍为主模型 + 类 10/13 shadow + Qwen3-VL。
- 本轮修复汇总证据已保存为 `artifacts/server/phase9-remediation-20260813.json`。

## Same-Frozen-Set Detector Comparison — 2026-08-13

- 本次严格比较两个不同权重：昨天六模型实验中的 `phase9-yolo26n-e120-b32/weights/best.pt`，以及当前线上 `official-plus-public-weak-v1-e120-b64/weights/best.pt`。
- 两者均使用服务器同一份 `phase9-unified-v4/dataset-frozen-eval.yaml`（官方 833 张冻结验证集）、640 输入和同一 `training/evaluate_detector.py` 评测逻辑；不调用专家、不调用 Qwen3-VL。
- 评测前已核对权重 SHA：YOLO26n 候选 `fb71fab6c063be002ce9bc114235b5c9023635ec13b280661733e2ce9eb82f31`；当前主模型 `cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071`。冻结清单 SHA 为 `2e7f691de609c4a310549d1ac6fb98e99eedcec18160588729f8e1e38fef60b8`。
- 服务器检查时 detector 与 Qwen3-VL 正在运行、显存约 22.2 GiB；正式评测前必须停止二者，完成后恢复并再次健康检查。

### Same-Frozen-Set Results

- 冻结清单实际为 833 行；两次直接 Ultralytics 评测均使用同一 `dataset-frozen-eval.yaml`、`imgsz=640`、`batch=32`、`workers=4`，不经过 8870 HTTP、不加载专家路由、不调用 Qwen3-VL。
- 昨天六模型中的 YOLO26n 权重 SHA `fb71fab6c063be002ce9bc114235b5c9023635ec13b280661733e2ce9eb82f31`：Precision `0.829715`、Recall `0.756240`、mAP50 `0.806850`、mAP50-95 `0.519087`。
- 当前线上主模型权重 SHA `cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071`：Precision `0.831993`、Recall `0.778327`、mAP50 `0.825132`、mAP50-95 `0.546065`。
- 当前主模型相对 YOLO26n 的整体增益为 Precision `+0.002278`、Recall `+0.022087`、mAP50 `+0.018282`、mAP50-95 `+0.026978`。逐类 mAP50-95 有 11 类提升、5 类下降；类 8 `-0.054795`、类 10 `-0.014842`、类 13 `-0.003090`、类 15 `-0.000805`。
- 这次同口径结果确认“当前主模型整体更好”，但不意味着每一类都更好；类 8 是最明显的回归，需要在后续弱类数据和专家决策中单独关注。由于专家和多模态未参与，本结论只针对视觉主检测权重。
- 当前主模型本次同集 mAP50-95 `0.546065` 与历史官方报告 `0.548224` 有约 `0.002159` 差异；本次使用统一 v4 冻结清单、batch 32、workers 4 复测，历史报告使用旧数据 YAML/配置。两次数值不应混为同一运行记录，但两模型本次比较使用完全相同口径。
- 评测证据文件：`artifacts/server/phase9-same-frozen-eval-20260813-yolo26n.json`、`artifacts/server/phase9-same-frozen-eval-20260813-current-main.json`、`artifacts/server/phase9-same-frozen-eval-20260813-dataset-frozen-eval.yaml`。

## Remaining Five Detector Comparison — 2026-08-13

- 本轮将评测六模型搜索中除 YOLO26n 外的五个候选：`yolo26s`、`yolo11s`、`yolo12s`、`yolov8s`、`yolov5su`。
- 统一对象仍为官方 833 张冻结验证集；统一评测逻辑为 `training/evaluate_detector.py`，不调用专家、不调用 Qwen3-VL。
- 结果必须与上一轮 YOLO26n/当前主模型对照保持同一数据清单、输入尺寸和 batch，才能放入同一张比较表。

### Same-Frozen-Set Results

- 五个候选均使用同一 `phase9-unified-v4/dataset-frozen-eval.yaml`、官方冻结 833 张、640 输入、batch 32、workers 4；每份结果包含 16 类指标和 17×17 混淆矩阵。
- 总体结果：YOLO26s `P=0.834140/R=0.772209/mAP50=0.820916/mAP50-95=0.535458`；YOLO11s `0.811513/0.781263/0.822261/0.534951`；YOLO12s `0.805109/0.807891/0.822365/0.522652`；YOLOv8s `0.824542/0.795836/0.818483/0.530064`；YOLOv5su `0.807224/0.769482/0.810575/0.519336`。
- 当前主模型在相同冻结集为 `P=0.831993/R=0.778327/mAP50=0.825132/mAP50-95=0.546065`，因此总体 mAP50-95 仍高于五个候选；YOLO26s 仅 Precision 高于主模型，YOLO12s 仅 Recall 高于主模型。
- 按弱类加权对照分排序为：当前主模型 `0.487785`、YOLO26s `0.483844`、YOLO11s `0.483537`、YOLO26n `0.474415`、YOLOv8s `0.473773`、YOLO12s `0.466811`、YOLOv5su `0.464188`。这是同冻结集的补充排名，不替换原来基于开发集的架构搜索结果。
- 与当前主模型相比，五候选的 mAP50-95 分别低 `0.010607`（YOLO26s）、`0.011114`（YOLO11s）、`0.023413`（YOLO12s）、`0.016001`（YOLOv8s）、`0.026730`（YOLOv5su）。因此没有候选满足“整体检测优于当前主模型”的替换理由。
- 五个候选权重 SHA：YOLO26s `b7d328a47b594733289640a6d78b1a84449a1560ae33ff9e06e1749d7e0a5934`；YOLO11s `60e9a4c517c02abc19a36953a8aa6343280fb0a39856b4f2b8fb54814f314093`；YOLO12s `2da1dfa03b09a2631789eb71382b2b0f3fb807da55fa28551cfd4dccf1ff6adc`；YOLOv8s `6dd7416957d60fcc1ce380d1616ba8f86d66d419818a9d9db484997eb96e63b6`；YOLOv5su `ef7539200c552e9bcbd4f4db13af18663daae9c5acfa3d24383a80f7f95a88dd`。
- 结论：当前主模型继续在线；五个候选全部保留为离线实验/答辩证据，不切换线上权重。该结论只涉及视觉主检测器，专家继续 `shadow`，Qwen3-VL 未参与本轮评测。

## 4,490 全量训练与 833 冻结集统一比较前置记录 — 2026-08-13

- 用户要求重新训练六个候选：YOLO26n、YOLO26s、YOLO11s、YOLO12s、YOLOv8s、YOLOv5su。统一训练数据为 `phase9-unified-v4/final-train.txt` 的 4,490 张，统一 120 epochs、640、batch 64、seed `20260729`、官方预训练权重。
- 用户已确认训练期间不使用官方 833 张冻结集，也不使用任何验证集进行逐 epoch 选择；因此本轮不使用 `best.pt`，统一使用训练完成后的 `last.pt`，官方 833 张只在训练完成后各评测一次。
- 当前主模型也要用同一冻结集、同一评测脚本、640/batch64/workers4 重新评测，作为七模型对照基线。专家和 Qwen3-VL 完全不参与。
- 已有文件 SHA 检查结果：`final-train.txt` 4,490 条、路径和文件 SHA 均唯一、无缺失；`official-frozen-val.txt` 833 条、路径唯一、830 个唯一文件 SHA、无缺失；跨集合文件 SHA 交集为 0。冻结集内部 3 组重复内容需要如实保留为评测限制。
- 文件 SHA 不能覆盖不同编码但相同图像内容，因此正式训练前仍需计算解码像素 SHA-256 和 16×16 感知哈希。跨集合像素完全相同将阻止训练；近似感知哈希只记录并人工审查。
- 当前线上主模型不自动替换。候选排名只依据本轮同口径冻结评测；即使候选最高，也必须通过既有总体指标、弱类非回退、160 张系统评估、协议安全、P95 和显存等晋级门，并经用户确认后才可讨论上线。
- 首次远程运行审计时服务器默认 PATH 未提供 `python` 命令；这是 shell 入口问题，未改变数据、模型或服务状态。后续使用已确认的服务器绝对解释器路径，不重复该命令。
- 随后发现新增审计脚本的条件列表展开语法错误；属于本地脚本缺陷，未生成错误审计结论，已最小修正后再运行。
- 首次完整审计的有效事实：训练 4,490 条、冻结清单 833 条均无解码错误；跨集合文件 SHA 和解码像素 SHA 均为 0；冻结集内部 3 组像素重复。脚本统计将冻结实际处理数显示为 830，原因是按唯一哈希计数，不能直接作为处理数使用；同时发现 43 组跨集合精确 pHash 与 43 组近似 pHash，需要保存完整路径并人工审查后才决定是否训练。

## 全量训练前 pHash 人工复核结论 — 2026-08-13

- 复核产物：`artifacts/server/phase9-fulltrain-independence-20260813.json`、`artifacts/server/phase9-fulltrain-phash-review-20260813/`、`artifacts/server/phase9-fulltrain-phash-review-all-20260813/`。
- 硬检查结果：训练清单 4,490 条、冻结清单 833 条；两侧无缺失或解码错误；文件 SHA 跨集合交集 0；解码像素 SHA 跨集合交集 0；冻结集内部 3 组像素重复。
- 人工复核结果：精确 pHash 实际配对 48 个、近似 pHash 配对 43 个；对应 74 张唯一训练图片。图像表现为同一叶片、虫体、场景的重新编码、轻微裁剪或同源变体，足以影响冻结评测独立性。
- 受影响训练来源：PlantDoc 51 张、SciDB 3 张、官方训练集 20 张。若从训练清单排除这些唯一训练图，预计剩余 4,416 张；原始 4,490 清单保持不变作为审计原件。
- 结论：不能在原 4,490 张清单上直接启动六模型训练，否则“官方 833 张冻结集一次评测”不再是严格独立测试。需要用户确认是否接受 4,416 张独立训练清单；在确认前不停止线上服务、不训练、不生成排名。

## 用户授权后的独立训练清单 — 2026-08-13

- 用户已授权：从原始 4,490 张训练清单中排除已人工确认的 74 张跨集合视觉重复候选，使用预计 4,416 张独立训练图片继续训练六个模型。
- 原始 `final-train.txt`、官方 833 张冻结清单、原始图片和标签均保持不变；只新增派生清单和审计证据。
- 继续执行前置门：生成清单时核对排除路径全部属于原训练清单；核对剩余图片/标签存在；重新运行文件 SHA、解码像素 SHA 和 pHash 审计；若任何跨集合 pHash 距离 `<=8` 的配对仍存在，停止训练并记录。
- 用户授权不等于允许自动上线：六个新模型只作为离线候选，与当前主模型统一冻结评测后形成建议；不自动替换线上权重，专家和 Qwen3-VL不参与模型评测。

## 4,416 独立训练清单二次审计通过 — 2026-08-13

- 二次审计结果：训练 4,416/4,416 成功处理，冻结 833/833 成功处理；双方无解码错误。
- 文件 SHA 跨集合交集 0；解码像素 SHA 跨集合交集 0；精确 pHash 交集 0；pHash 汉明距离 `<=8` 的近似配对 0；训练集内部像素重复 0。
- 官方冻结集内部仍有 3 组像素重复（833 条中 830 个唯一像素哈希），作为评测集自身限制记录，不改变冻结清单。
- 训练前数据独立性 gate 通过，可以按用户授权的 4,416 张训练集继续。证据：`artifacts/server/phase9-independent-v1-audit-20260813.json`。
- 训练前服务器检查的第一条复合 SSH 命令因引号嵌套失败，未产生远程副作用；后续改用短命令，避免重复该错误。

## 六模型训练启动状态 — 2026-08-13

- 训练数据契约：`data/experiments/phase9-independent-v1/dataset-independent-frozen-eval.yaml`，训练列表 4,416 张；官方冻结列表仍为 `phase9-unified-v4/official-frozen-val.txt`，833 张，仅用于训练后一次评测。
- 六个官方预训练权重均存在：`yolo26n.pt`、`yolo26s.pt`、`yolo11s.pt`、`yolo12s.pt`、`yolov8s.pt`、`yolov5su.pt`。
- 停服前 RTX 5090 使用 22,110 MiB；停止远程 detector PID `8927` 和 Qwen3-VL PID `8969` 后显存为 0 MiB，满足 batch64 训练前置。
- 本轮训练不使用 `best.pt`，不执行验证集早停；训练 120 轮完成后只采用 `last.pt`。训练期间禁止调用专家、Qwen3-VL、detector HTTP 和官方冻结评测。

## 首次训练配置偏差 — 2026-08-13

- 首次 YOLO26n 命令使用了同时含 `train=4,416` 与 `val=official-frozen-833` 的 YAML，并传入 `val=False`。日志确认 Ultralytics 仍在启动阶段扫描官方冻结集标签缓存；目前未看到验证指标计算，但严格来说不满足训练期间不读取验证集的要求。
- 首次运行约到第 5/120 轮，未完成、未评测、权重不纳入最终结果；停止后保留其运行目录和日志，不删除用户证据。
- 最小修复：新增仅含 `train` 与 16 类 `names` 的训练专用 YAML；官方冻结集 YAML 只用于训练完成后的统一评测。重新启动时必须检查日志不出现 `val: Scanning ... official/labels`。
- 已在派生清单生成器中增加训练专用 YAML 输出；因 Ultralytics 强制要求 `val:`，该字段与 `train:` 同指 4,416 张训练清单作为占位，训练日志只允许出现独立训练路径，不允许出现官方冻结路径。

## Ultralytics 训练 YAML 兼容性修正 — 2026-08-13

- 仅含 `train` 与 `names` 的 YAML 无法启动：Ultralytics 在 `check_det_dataset` 阶段强制要求 `val:`，返回 `'val:' key missing`；该次没有训练进程和权重产物，GPU 保持 0 MiB。
- 采用最小兼容方式：训练 YAML 的 `val:` 与 `train:` 指向同一份 4,416 张独立训练清单，仅作为框架占位；训练参数仍为 `val=False`，不运行验证、不读取官方 833 张冻结集。
- 训练 YAML 与冻结评测 YAML 分离；任何训练日志出现 `official-frozen-val` 或官方冻结标签扫描都视为配置失败并停止。

## 逐模型训练后即时评测 — 2026-08-13

- 用户确认采用流水线方式：一个模型完成训练后立即在官方 833 张冻结集上评测并保存结果，不等待其余模型。
- 每个候选模型使用独立运行目录和独立评测 JSON，保证中途即可与当前主模型比较，也便于单个模型失败后保留其余证据。
- 评测严格不启用专家、Qwen3-VL 或 detector HTTP；统一使用 `last.pt`、640、batch64 和同一评测脚本。
- 当前主模型需先/并行完成一次相同配置的冻结集基线评测；候选模型仅作为比较证据，不自动上线。

## 用户停止剩余训练 — 2026-08-13

- 用户明确要求停止全部训练，并继续使用当前主模型作为线上视觉模型，不进行候选权重替换。
- 已停止最后的 YOLOv5su 训练和串行编排器；YOLOv5su 训练返回 `rc=143`，表示被主动终止，不作为完成或评测结果。
- 已完成并保存的即时评测：YOLO26n、YOLO26s、YOLO11s、YOLO12s、YOLOv8s，以及当前主模型基线；这些证据不改变线上模型。
- 服务器核验：训练进程为空、编排器为空、GPU 使用 `0 MiB`。后续只恢复既有主模型 detector/Qwen3-VL 服务，不加载新候选权重。
## 最终收尾与线上模型冻结 — 2026-08-13

- 用户明确要求停止所有训练，并以当前主模型作为视觉模型，不做权重切换。
- 远端训练进程和串行编排器已确认不存在；YOLOv5su 的 `rc=143` 是本次主动停止造成的中止，不是可比较的完整结果。
- 统一冻结集比较中，当前主模型仍明显优于已完成的五个候选：当前主模型 `mAP50-95=0.548224`；YOLO26n `0.410084`、YOLO26s `0.409398`、YOLO11s `0.401406`、YOLO12s `0.414133`、YOLOv8s `0.398096`。因此没有任何候选具备替换资格。
- 当前线上 detector 与本机健康检查均返回主模型 SHA `cbb26d83e47df06b6ae135d8adebd89453cb496d99d00242dfa92d8ea3f58071`、16 类、`routing.mode=shadow`、`reclassify=false`。
- 远端 detector 和 Qwen3-VL 已恢复；本机 3000、8000、8870、8890 均监听并可用。GPU 当前占用属于恢复后的在线推理服务，不是训练任务。
- 评测原始证据已保存到 `artifacts/server/phase9-fulltrain-eval-20260813-*.json`，供后续人工测试和答辩追溯。

## 用户确认模型暂定与后续测试顺序 — 2026-08-13

- 用户确认当前视觉主模型和 Qwen3-VL 暂不更换，后续以现有系统作为人工功能测试版本。
- 当前没有新的模型训练、权重替换或多模态协议变更授权；候选模型不进入线上链路。
- 后续优先处理用户实际测试发现的功能、结果展示、异常恢复和易用性问题。
- UI 重构属于后置工作，须在功能问题整改并由用户确认测试结果后再开始。

## Resume Check — 2026-08-14

- 使用工作区依赖 Python 执行 `planning-with-files` 会话恢复脚本，退出码为 0，未返回未同步上下文。
- 三个规划文件已按 UTF-8 完整读取。Git 当前位于 `codex/publish-audits-and-calibration-plan`，领先远端 1 个提交；工作区包含大量既有 Phase 9 改动，以及用户未跟踪的 `CLAUDE.md`，均不得清理、回滚或擅自提交。
- 只读运行检查显示 FastAPI `127.0.0.1:8000/health` 返回 200，且仍配置为 remote detector/Qwen3-VL；但本机前端 `127.0.0.1:3000`、detector 隧道 `127.0.0.1:8870`、Qwen3-VL 隧道 `127.0.0.1:8890` 不可达。
- 远程地址 `connect.bjb2.seetacloud.com` 解析到 `106.38.204.136`，但 TCP `10373` 当前失败。旧服务器不可达时不能默认沿用旧 PID、模型状态或隧道；需用户在平台恢复实例或提供新 SSH 地址后重新做只读核验。
- 当前没有新的业务代码问题证据，也没有授权进行训练、模型切换或最终 UI 重构；本轮暂停在用户本机 Chrome/Edge 验收前置条件。

## 实验室服务器初步部署审计 — 2026-08-14

- 服务器为 CentOS 7、kernel 3.10、glibc 2.17；CPU 24 核/48 线程、RAM 125 GiB；4×Tesla K80（每卡约 11 GiB），驱动 470.161.03，`nvidia-smi` 报告 CUDA 11.4。
- 根分区 414 GiB 已用 97%，只剩约 16 GiB；`/data` 3.6 TiB，仅用 17%。任何新环境、模型和容器必须放到 `/data`，不能继续占用根分区。
- 项目后端声明 Python `>=3.11,<3.14`，服务器现有 Anaconda Python 3.9.13 不满足；前端声明 Node `>=22.13.0`，服务器当前没有 Node/npm。
- 已验证的原运行环境为 Ubuntu/glibc 2.35、Python 3.12.3、PyTorch 2.8.0+cu128、CUDA 12.8、RTX 5090 32 GiB；与 K80/CUDA 11.4 存在根本代际差异。
- 多模态启动脚本固定安装 vLLM 0.26.0 并加载 Qwen3-VL-8B；是否能在 K80 上运行需继续对照 vLLM/NVIDIA 官方硬件要求。
- 本轮一次 `rg` 聚合命令因前置文件匹配返回 1 导致整体退出 1，但关键依赖输出已取得；后续改用直接读取依赖文件，不重复该失败方式。
- 微软当前 Remote Development 基线为 kernel >=4.18、glibc >=2.28、libstdc++ >=3.4.25、binutils >=2.29；CentOS 7 被官方明确列为不支持。当前 kernel 3.10 与 glibc 2.17 同时不达标，不能靠补一个 RPM 正常解决。
- VS Code 1.99 起预编译 Server 以 glibc 2.28 为最低线；官方提供自建 sysroot/patchelf 的临时技术方案，但明确不是受支持场景，而且本机 kernel 3.10 仍低于当前基线，故不作为正式部署方案。
- vLLM 官方 NVIDIA GPU 基线为 compute capability >=7.0；Tesla K80 为 Kepler compute capability 3.7，不能运行当前 vLLM/Qwen3-VL 服务。
- NVIDIA 官方矩阵说明 Kepler 3.7 的最后 CUDA Toolkit 支持为 CUDA 11.x、最后驱动分支为 R470；当前项目 PyTorch 2.8.0+cu128/CUDA 12.8 环境无法迁移到 K80。
- Qwen3-VL-8B 官方权重仓库约 17.5 GB；本项目原来在 RTX 5090 32 GiB 上验证 detector 与 Qwen3-VL 共存。K80 单卡 11 GiB 且无当前 vLLM 支持，因此不能保持现有多模态链路。
- 若保持现有 CUDA 12.8 软件栈，NVIDIA 官方要求 Linux 驱动至少 570.26（GA）；服务器 R470 既无法满足，也因 K80 架构不能通过简单升级驱动跨到 CUDA 12.8。
- 当前 detector/专家权重只有约 3–10 MiB，历史 PT 推理峰值约 4.2 GiB；它们可在新系统上考虑 CPU 推理，或另建兼容旧 CUDA 的实验环境，但这不解决 Qwen3-VL。
- 当前多模态整链路历史峰值约 22.5–24.0 GiB；24 GiB 显卡几乎没有余量。保持当前模型、8192 上下文和 detector 共存时，建议单卡 >=32 GiB，或使用 40/48 GiB 数据中心卡。
- 推荐部署路径：重装为满足 VS Code 条件的现代 x86_64 Linux；将项目、Conda、Docker data-root、Hugging Face 缓存和模型全部放到 `/data`；安装 Python 3.11/3.12、Node >=22.13；若保持现有 `torch 2.8.0+cu128`，更换现代 GPU 并使用 >=570.26 驱动。
- 若暂不换 GPU，可部署前端、FastAPI、SQLite 和 CPU detector/shadow 专家，但必须关闭或替换 Qwen3-VL；这属于降级版，不是当前完整系统。
- 第二次组合读取因末尾 `rg` 无完整匹配而退出 1，但前置脚本、模型与显存证据均已成功读取；未产生任何服务器副作用。
# 双服务器部署实现发现（2026-08-14）

- 实验室服务器为 CentOS 7、glibc 2.17、kernel 3.10；根盘 97%，独立 `/data` 约 3 TiB 可用。
- CPU 为双路 Xeon E5-2650 v4，支持 AVX2；4×Tesla K80 不满足当前 vLLM GPU 要求，因此本机多模态采用 llama.cpp CPU/GGUF。
- 工作区已有大量用户修改和证据文件，本任务必须采用最小增量修改。
- 当前阶段 GPU 服务器不在线；远端部署与双机联调必须在本地 CPU 全链路通过后进行。
- 现有病例流程是上传、检测、分析三个请求；使用带实例前缀的病例 ID，并在前端同时发送 `X-Crop-Instance`，可避免切换发生在流程中间时串库。
- 最小网关方案是在实验室 FastAPI 增加中间件：Admin/控制接口始终本地，病例列表/新建按活动实例，带实例前缀的病例请求按归属实例；GPU 后端运行相同代码但关闭网关模式。
- 当前 SSH 别名 `ghl` 可达，但仅密码认证，非交互 BatchMode 被拒绝；实际部署前需要用户交互输入一次密码并配置专用密钥。
- 前端要求 Node >=22.13；需先在旧 kernel 的容器内通过兼容门，失败时改为在本地构建产物后上传。
- 后台执行环境无法把 SSH/Windows 凭据对话框可靠显示到用户桌面；两种内存凭据方案均在未认证前超时，服务器无改动。
- 用户已有一个从 2026-08-14 15:43 建立且仍为 Established 的交互式 SSH 进程；最短解锁路径是在该窗口从临时局域网地址追加专用公钥。
- 用户完成交互式安装后，服务器已接受专用 Ed25519 公钥；先前 `ssh ghl` 失败只是本机 SSH config 未声明该 IdentityFile，并非服务器丢失密钥。显式 `-i` 已验证成功，本机别名现已固定使用该专用密钥。
- 公共 ECR 的 Docker 官方镜像镜像源可从本机访问，Python 3.12 slim、Node 22 bookworm slim、nginx 1.27 alpine 均已成功解析 digest，可绕过被污染/超时的 Docker Hub 路径。
- 本机可访问 `ghcr.io/ggml-org/llama.cpp:server`，digest 为 `sha256:c88223e4...966ff`，可下载为离线镜像后导入实验室服务器。
- Qwen 官方 GGUF 仓库中的目标文件已确认：`Qwen3VL-8B-Instruct-Q4_K_M.gguf` 为 5,027,784,800 字节，`mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf` 为 752,289,728 字节；两者合计约 5.78 GB。
- Crane 离线 tar 导入后保留了完整仓库名：`public.ecr.aws/docker/library/python:3.12-slim`、`.../node:22-bookworm-slim`、`.../nginx:1.27-alpine` 与 `ghcr.io/ggml-org/llama.cpp:server`。离线 Dockerfile/Compose 必须引用这些已导入名称，不能继续使用 Docker Hub 短名称，否则会再次尝试联网拉取。
- 当前在线 Dockerfiles 仍含 Docker Hub `FROM`、apt-get、pip/npm 联网安装；实验室服务器外网 HTTPS 不可用，因此需新增离线构建覆盖：基础镜像改用已导入完整名称，Python wheelhouse 与 npm cache 由本机下载后放入 `/data/ghl/cache`。
- Docker Compose 会对 `--env-file` 中 PBKDF2 哈希的 `$` 做变量插值；Admin 哈希写入 Compose 环境文件时必须转义为 `$$`，容器接收到的值才是原始单 `$` 哈希。
- `ghcr.io/ggml-org/llama.cpp:server` 镜像自带探针访问 localhost:8080；本部署使用 8890，因此必须显式覆盖 healthcheck。模型实际在 8890 正常服务，健康接口和模型列表均已验证。
- 本地已具备主检测器、类 10 检测专家和 10/13 作物分类专家权重；Qwen3-VL GGUF 与 mmproj 仍需下载/放置。
- 实验室五个容器已稳定运行；Docker 服务为 `enabled/active`，容器采用 `unless-stopped`。空闲总内存约 5.4 GiB，其中 Qwen3-VL 约 5.0 GiB、detector 约 281 MiB。
- CPU 多模态首次分析约 96.5 秒，紧接的稳定态复测约 96.1 秒，说明主要耗时是 CPU 生成而非首次模型加载。
- 已知类 10/13 样本在实验室 CPU detector 上分别约 0.54/0.33 秒；主模型置信度约 0.9436/0.9307。两者专家候选均成功路由且动作均为 `shadow_keep`，专家只写入反事实证据，不覆盖主模型输出。
- 2026-08-17 原 GPU 主机 `connect.bjb2.seetacloud.com:10373` 恢复，主机身份仍为 `autodl-container-4129428075-000fbcc8`；RTX 5090 32,607 MiB、驱动 580.105.08，检查时 0 MiB/0% 使用。
- GPU 数据盘 `/root/autodl-tmp` 为 50 GiB，剩余约 18 GiB；旧 `/root/autodl-tmp/crop-pest-system` 与 `/root/autodl-tmp/crop-pest-vlm` 完整保留，新 `/root/autodl-tmp/ghl` 尚不存在。
- GPU 开机后 detector、Qwen3-VL、FastAPI 均未启动。为避免 18 GiB 空间再次复制约 16 GiB 模型，联调应复用旧模型/虚拟环境，只新增轻量后端代码与独立业务存储。
- GPU 独立后端现已部署到 `/root/autodl-tmp/ghl`，复用旧 detector/VLM，不复制模型；健康接口报告 `gpu_full`，独立存储初始 0 病例。
- GPU 类 10 真实闭环：检测 0.48 秒、主模型置信度 0.943703、专家 `shadow_keep`；Qwen3-VL 两阶段总延迟约 12.17 秒、`conclusive`，报告快照重启前后稳定。GPU 当前独立病例数 1。
- 实验室服务器虽有默认路由，但 DNS、百度 HTTPS、AutoDL HTTPS、`1.1.1.1:443` 和 GPU `10373` 均超时，属于无可用出站网络；不是单一 AutoDL 端口故障。
- 实验室 SSH `AllowTcpForwarding=yes` 但 `GatewayPorts=no`。Windows 可做临时双 SSH 中继，但现有 backend 容器无法直接访问只绑定实验室 loopback 的反向端口；永久采用该方案还需增加受限桥接代理，并依赖 Windows 持续在线。
- 用户选择 Windows 临时中继。实验室 backend 的 `host.docker.internal` 实际解析为 `172.17.0.1`；受限 Python relay 只绑定该地址的 18000，并转发到实验室 loopback SSH 18000，因此不开放 LAN 监听。
- Windows 双 SSH 链路已建立：PID 26408 将本机 `127.0.0.1:18001` 转到 GPU `127.0.0.1:8000`；PID 20208 将实验室 `127.0.0.1:18000` 反向转到 Windows 18001。两者都启用 BatchMode、ExitOnForwardFailure 和 keepalive。
- 统一入口已经能按 `gpu_full-...` 病例 ID 读取 GPU 病例和报告；实验室健康仍为 `lab_cpu`，说明前缀归属路由与当前活动实例互不混淆。
- 用户从 Admin 成功切换 `lab_cpu → gpu_full`，控制状态和审计日志均已持久化。经实验室统一入口新建的类 13 病例为 `gpu_full-fcb09b112dbb4c79bf69d472a50cf5be`，检测 0.43 秒、多模态请求 4.92 秒、报告实例均为 GPU。
- GPU 活动时 `/api/cases` 只列出 2 个 `gpu_full` 病例；按 ID 读取原 CPU 病例仍返回 `lab_cpu` 及原 CPU 报告。实验室上传目录只有 3 个 `lab_cpu` 文件，GPU 上传目录只有 2 个 `gpu_full` 文件，实际文件未交叉。
- 用户切回 `lab_cpu` 后，统一入口新建病例 `lab_cpu-812db2c77557486585d17d3160cf3e5f`；检测类 10 约 0.35 秒，报告归属 CPU。活动列表变为 4 个且全部为 `lab_cpu`，GPU 仍保持 2 个病例，切换没有复制或移动数据。
- 停止 Windows 中继后，Admin 实测 GPU 显示离线、按钮为“服务器不可用”，CPU 仍为“当前使用”；控制文件保持 `lab_cpu`，CPU 4 个病例正常。目标离线拒绝切换门通过。
- 中继恢复后 GPU 再次在线，统一入口仍以 `lab_cpu` 为活动实例，并可按 GPU 病例前缀读取已分析病例。最终 Windows 隧道 PID 为 26660/25984，GPU 显存约 22,244 MiB、空闲利用率 0%。
# 2026-08-18 Knowledge summary vertical layout

- The case-detail knowledge block reuses `.public-three`, whose desktop rule creates three columns.
- The scoped `.knowledge-summary` class is already present, so a one-rule override can create a single-column reading order without affecting other three-column surfaces or the report page.
# 2026-08-19 自动元数据与表单精简

- 当前上传API和SQLite要求 `crop/part/growth_stage` 非空；无需改表，可用“系统未判断”作为新病例占位并在检测/分析后覆盖。
- 当前Qwen独立阶段同时收到作物、部位、阶段、环境、说明、比例和扩散速度；最新蛴螬病例因此被“玉米/叶片/苗期/30%”诱导为玉米叶枯病。
- 16类目录已有稳定的 `class_id -> crop` 映射；部位和生育期没有可靠目录映射，必须由图片推断并允许“系统未判断”。
- “现在建议你”是首页 `.public-next` 区块；技术证据中的“需要补拍”和拒答状态提示是独立安全信息，按用户选择保留。
- 实验室CPU当前在线；Windows到GPU的 `127.0.0.1:18001` 中继离线，GPU部署需在CPU验收后通知用户开启。
- 实验室真实蛴螬回归：仅上传图片及比例/扩散速度即可建例；创建时三项元数据均为“系统未判断”，YOLO 类别 14 检测后关联作物自动更新为“玉米”。
- Qwen3-VL 纯图片第一阶段对该图返回“无法判断”，部位和阶段规范为“系统未判断”；最终主类别固定为 YOLO 的“蛴螬”，旧默认“叶片/苗期”已不再参与识别。
- 部署后健康状态为 `ok`、活动实例仍为 `lab_cpu`、普通病例数保持 22；SQLite `PRAGMA quick_check` 返回 `ok`，detector/VLM 容器未重建。
- Phase 9.12 已确认：作物选项为玉米/番茄/南瓜/马铃薯/昆虫；非昆虫必须选择部位与阶段，昆虫保存“不适用”；所有田间字段初始为空并由前后端共同校验。
- 人工字段不覆盖 YOLO 最终类别；作物冲突只进入一致性风险。第一阶段仍只看原图，第二阶段重新接收原图、YOLO、shadow 与人工字段。
- 新综合分析必须使用带明确关联的结构化输出，每条危害/诱因绑定 `image|yolo|field_input` 依据；证据不足返回“无法判断”，百度百科不得作为该阶段依据。
- 主页采用上下两步，内嵌综合分析与知识摘要；仅删除成功绿色提示和可靠性卡，错误/冲突/补拍提示继续保留。
- 真实 CPU 验收发现仅做字段/来源白名单仍不足：Qwen 曾把“啃食根系导致萎蔫”作为图片危害依据，并在第一阶段全为“无法判断”时于第二阶段补写“根部蛀食痕迹”。因此增加保守语义门：禁止产量、传播、病原和因果后果推断；第二阶段正向图片依据必须通过第一阶段可见证据门，否则整条危害/诱因固定降为“无法判断”。
- 第二阶段田间依据若未引用本次请求的真实字段值会被过滤；无剩余充分依据时不再把整例标记为服务失败，而是生成明确的“无法判断”及缺失证据说明。

# 2026-08-20 Impeccable 设计文档与 UI 审查

- 项目根目录当前没有 `DESIGN.md`、`PRODUCT.md` 或 Impeccable surface brief；现有前端代码和已部署页面足以使用 Scan mode 提取设计系统。
- `impeccable document` 要求同时生成规范化 `DESIGN.md` 与 `.impeccable/design.json` sidecar；令牌必须来自真实复用值，不能发明不存在的视觉系统。
- `impeccable critique` 要求设计审查与机械/浏览器证据两项评估相互隔离；当前没有子代理工具，因此必须顺序执行并显式标注 degraded。
- 当前工作树有 18 个既有修改文件和 2 个未跟踪前端组件；这些都是上轮功能实现资产，本轮不得覆盖或回滚。
- `DESIGN.md` 已按现有 CSS 提取 13 个颜色令牌、5 级文字角色、5 级圆角、7 级间距和 6 个组件令牌；sidecar 提供 7 个可渲染组件、阴影、动效与 620/900px 断点。

## Critique Assessment A — 独立设计审查（检测器运行前）

- **设计特异性：** 绿色农业语义、田间拍照、检测框、证据绑定、知识库与拒答边界形成了可信的产品特征；但整体仍是常见的“浅色大圆角卡片 + 绿色 SaaS 工作台”结构，缺少把田间采样、证据强弱和病例归属做成独特视觉语法的进一步表达。
- **主要优点：** 单一深绿主色和风险色语义稳定；上传→结果→证据→知识顺序符合任务；全局 `:focus-visible`、44px 交互高度、移动底栏和拒答文本构成良好可访问性基础。
- **P1 数据归属语义不准确：** 历史、趋势和页脚反复写“当前电脑”，但双服务器系统实际按当前活动实例隔离数据；公共页又不显示当前实例，切换后病例列表变化容易被误解为数据丢失。
- **P1 必填状态不可诊断：** 首页最多要求上传图片并完成 6 个田间决策；主按钮在缺项时直接禁用，没有缺失项汇总或逐字段提示，首次用户只能反复查找原因。
- **P1 长耗时缺少预期管理：** CPU 多模态历史稳定耗时约 96 秒；界面只显示阶段名，没有预计时长、继续等待说明、离开页面影响或恢复入口。
- **P2 技术术语进入主路径：** “YOLO 决定最终类别”“第二阶段证据”“技术证据/provenance”面向普通用户缺少解释；折叠技术区虽降低影响，但步骤说明仍承担翻译成本。
- **P2 层级过度与纵向负担：** 空结果区桌面最小高 610px、移动端 420px；结果形成后又连续展示摘要、综合分析、知识、两个 22px 链接和技术区，主结果与后续动作的优先级变得模糊。
- **P2 导航缺少当前位置：** 公共页头没有 active class 或 `aria-current`；历史和趋势页只能靠大标题判断所在位置。
- **认知负荷：** 8 项清单中“≤4 个可见决策”和“一次只做一件事”失败，属于 2 项失败的中等负荷；植物病例会同时呈现 6 个字段选择/输入加图片上传。
- **初步 Nielsen 评分：** 3/2/2/3/3/3/1/3/3/2，总计 25/40（Acceptable）。机械检测尚未运行，评分将在综合报告中复核。
- **相关角色：** Jordan 会被禁用按钮和 YOLO 术语阻塞；Sam 会受缺失 `aria-current` 与非 live 的进度/服务状态影响；Casey 会受表单不保存、约 96 秒等待和长页面影响。

## Critique Assessment B — 机械检测与浏览器证据

- 审查目标解析为 `web-app`；`.impeccable/critique/ignore.md` 不存在，没有静默忽略项。
- `detect.mjs --json web/app` 返回 1 条 `layout-transition` warning：`web/app/globals.css:280` 的训练进度条使用 `transition: width .4s ease`。这是有效的 P3 性能/动效问题，但位于训练监控，不影响公共诊断主任务。
- 主要文本组合对比度：muted/surface 4.84、green/green-soft 5.77、white/green 6.50、amber-text/amber-soft 7.20、red/red-soft 5.32、nav/paper 6.35，均达到普通文本 AA 的 4.5:1。
- 浏览器自动化成功打开 `http://192.168.15.133:8080/` 并读取正确标题；桌面/响应式截图与样式采样两次超时并重置。Codex Browser 的 evaluate 为只读且没有可用的 DOM 脚本注入能力，因此没有可靠的人类可见 overlay；回退证据为成功 URL/标题导航、源码结构、CSS 响应式规则和 CLI 检测。
- Assessment A 在检测器之前完成并持久化；B 未改变 A 的判断，只补充了进度条动画与色彩对比证据。
- 用户选择“昆虫”时部位/阶段在真实病例中均保存为“不适用”；人工字段与目录冲突只把 `field_input_consistency` 升为 `conflict`，YOLO 最终类别不会被覆盖。
# 2026-08-20 三个 P1 实施发现

- 当前三个 P1 的基准分来自既有 Impeccable critique：Design Health Score 为 25/40。
- 公共页头已被首页、历史、趋势、病例详情和报告复用，适合集中增加当前服务器标签和当前导航状态，无需重写各页。
- 双服务器路由只代理 `/api/cases`、病例子路由和 `/api/trends`；普通 `/health` 是实验室本地健康，不足以单独代表当前活动实例，需要继续核对是否已有公开活动实例字段或最小只读接口。
- 病例目前只有 `created`、`detected`、`analyzed` 等持久状态，分析请求完成前没有明确的 `analyzing/queued` 持久状态；在未证明可安全恢复前，不实现虚假进度或自动重放。
- `/health` 当前只返回本地 `instance_id/instance_label`，而活动实例由 `ControlStore.active_instance()` 决定；因此切换到 GPU 后直接展示现有 health 标签会错误地显示 CPU。
- 采用最小的后端加法修改：在原 `/health` 响应增加 `active_instance_id`、`active_instance_label` 和 `active_instance_mode`。不更改现有字段、路由规则或鉴权接口，也不暴露 IP/端口。
- 首页创建病例后已经立即执行 `setRecord(created)`，可直接复用这一时点显示病例编号；无需等待目标定位或综合分析完成。
- Admin 现有确认框只说明“新病例保存在目标服务器”，还需明确补充“病例历史列表会变化，切回后仍可查看”，以避免被理解为数据丢失。
- 本地桌面验收使用独立的 3002/8002 实例，避免覆盖用户已有的 3000/8000 开发进程。1280×720 下无水平溢出。
- 桌面动态证据：页头显示“当前识别服务器：实验室 CPU”；桌面与移动导航的“开始诊断”均带 `aria-current="page"`；缺项提示完整；CPU 1–2 分钟说明可见；提交按钮仍由原有验证禁用。
- 整个结果卡片已不再设置 `aria-live`，仅服务器状态、缺项状态和运行阶段使用窄范围 polite live region，降低重复播报风险。
- 首轮 390×844 验收发现既有 `backdrop-filter` 会让页头内的 fixed 手机导航以 sticky header 为定位容器，导航跑到顶部并遮住品牌/服务器标签。该问题直接影响本轮服务器归属可见性，已在 <=900px 关闭页头 backdrop-filter，待复测。
- 移动复测通过：390×844 下底部导航位于 y=774–832，服务器标签位于页头 y=15–48，二者不重叠；页面无水平溢出，提交按钮最小高度 44px。
- 缺项交互复测通过：选择“玉米”后动态增加“植物部位、生长阶段”；切换为“昆虫”后两项控件与缺项文字同时移除，其余缺项继续保留。
- Impeccable 源码 detector 报告 2 个 warning：旧训练进度条的 `transition: width`，以及本轮 CPU 耗时提示的单侧 3px 琥珀边框。前者是既有性能 P3；后者需在 audit 中判断为状态提示的低影响 P3 或设计反模式。
- Impeccable URL detector 因本机未安装 Puppeteer 无法运行；不为审计临时引入依赖，改用已完成的真实浏览器桌面/移动证据，并在报告中明确降级。
- 修改前 critique 的 10 项分数为 `3,2,2,3,3,3,1,3,3,2`，总分 25/40；本轮可直接改善系统状态可见性、真实世界匹配、一致性、错误预防、识别优于回忆、错误恢复和帮助说明。
- 审计静态扫描确认仍有 5 个 ESLint `<img>` 性能警告、报告正文 11px、结果区两个 22px 同权入口、较多未令牌化硬编码颜色；这些不属于本轮三个 P1，作为 P2/P3 保留。
- 移动可访问性抽检：5/5 当前表单控件均有关联标签，图片无缺失 alt，标题层级为 H1→H2/H3，polite live region 仅 2 个；品牌链接高 40px、历史预览文字链接高 42px，低于 44px，作为 P3 记录。
- 本轮 audit 预计无 P0/P1；剩余问题集中在报告小字号、结果行动层级、图片优化，以及设计令牌/孤立动画/小触控目标等 P2/P3。
# 2026-08-20 第三阶段视觉辨识度发现

- 上一轮审计已关闭全部 P0/P1/P2；本轮不是修复轮，而是从“通用暖白绿色农业工作台”提升为“证据驱动诊断工具”。
- 可保留资产：暖白纸张底色、深绿色主色、“田”字品牌标、克制圆角、现有 PublicHeader、ComprehensiveAnalysis、KnowledgeSummary、结果主次行动与打印报告层级。
- 主要缺口：缺少贯穿页面的真实诊断路径；证据来源虽有数据结构但视觉语义不统一；病例归属和知识参考仍像普通元数据，尚未形成产品识别符号。
- 建议视觉母题：以“田”字方格和细线轨迹表达田间采样与证据流；来源使用单字方形标记（图、田、定、核、知、报）和统一排版，不增加彩虹标签。
- 当前 `ComprehensiveAnalysis` 在普通可见区域把 `yolo` 标为“YOLO”，应改为“目标定位”；原始技术术语仅保留在折叠技术详情中。
- 当前工作树包含用户此前多个阶段的未提交修改；本轮必须做叠加式局部修改，不回滚、不格式化无关文件。
- 恢复记录时系统 `python` 别名和 `py` 不可用；已改用 `backend/.venv/Scripts/python.exe` 成功运行 planning-with-files session catch-up。第一次并行恢复无有效输出，未影响文件。
- 桌面 1280×900 实测：诊断路径为六个横向节点，当前步骤仅“田间采样”；页面 `scrollWidth == clientWidth`，主按钮 44px。首版标题三行过重，已收敛到 54px、两行。
- 390×844 实测：诊断路径自然转为六个纵向节点，底部导航触控高度 46px，主按钮 44px，`scrollWidth == clientWidth`。
- 病例详情实测发现旧后端 `resolution_reasons` 会把 502 URL 暴露在普通路径；已在前端过滤 URL/server error/traceback/bad gateway，原始内容移入折叠技术详情。
- 报告实测：病例归属显示“实验室 CPU”，路径当前节点为“诊断报告”，桌面与 390px 均无横向溢出。
- 第一次 production QA 服务只返回 HTML、静态 CSS 404；改用构建产物自带的 Wrangler assets 配置后完成视觉检查。重建时临时 QA 进程锁定 `dist/server/.wrangler`，停止本轮启动的 4173/4174/4175 进程后构建恢复通过。
- Impeccable critique 的 Assessment B 独立完成；两次 Assessment A 子代理均未在等待与中断后返回，因此 critique 按规则标注单上下文降级，不把未返回结果冒充双代理共识。
- Critique 发现失败病例会把未执行阶段标成完成；polish 后按 `resolution_status`、检测结果和分析状态停在真实的“目标定位”或“信息核对”，同时显示“在此停止”并设置 `aria-current="step"`。
- 旧 health 响应缺少实例 label 时，页头在线状态现在回退到 id/mode 映射或“当前实例”，避免“服务开放”与“正在读取”长期并存。
- 最终 390px 抽检：报告来源链接 49px、移动导航 46px、主按钮 44px、上传区 250px；首页、病例、报告 `scrollWidth == clientWidth`。
- 最终 detector 仅报告 `web/app/globals.css:284` 的训练监控 `transition: width`；该项为用户明确排除范围的 P3。公共状态仍有少量硬编码警告色，为渐进令牌化 P3。
- 最终评分：Design Health 36/40，Impeccable Audit 18/20；P0/P1/P2 为 0。
# 2026-08-20 第四阶段比赛展示页最终发现

- 最终视觉方向采用“田间证据图谱”：不是通用 SaaS 卡片堆叠，而是以证据节点、细线轨迹与诊断路径串联图片、定位、田间信息、知识参考和报告。
- 首屏在 10 秒信息范围内同时给出项目定义、真实诊断入口和三项创新；指标区给出技术数值及普通语言解释，避免评委必须理解 mAP 才能判断价值。
- 页面真实数据为 16 类、4,164 张审计训练图、5,920 个目标框、833 张冻结评测图、mAP50-95 0.5482，以及 160/160 固定重测成功、Top-1 87.50%、内容完整率 100%、冲突识别 15/17。
- 页面使用真实实验室诊断界面截图；未生成假系统 UI，未编造用户数、满意度或准确率。
- 本地 Vinext 生产启动没有正确提供 CSS 静态资源，浏览器验收改用构建产物只读静态服务；这属于本地 QA 运行路径问题，不应为消除现象而更改业务或迁移技术栈。
- Next 图片优化在当前构建运行时无法稳定取图，最终采用带 width/height、alt、decoding 和 eager/lazy 策略的静态 `<img>`；detector 返回空结果，ESLint 通过。
- 最终 Audit 为 18/20：A11y 4、Performance 3、Responsive 4、Theming 3、Implementation Integrity 4；P0/P1/P2 为 0，P3 为首屏图片体积与局部展示色令牌化。

# 2026-08-20 UI Redesign V2 初始约束

- 用户明确撤销“保留当前设计”约束；旧 JSX、文案、CSS、卡片、布局和视觉层级都不是权威，只保留产品功能与数据契约。
- 重点页面为智能诊断首页、诊断结果状态、病例详情和诊断报告；Admin、训练监控、showcase 和后端不在范围。
- 桌面目标拓扑为图片与田间信息左右工作区；移动端为图片、田间信息、提交的自然纵向流。
- 结果首屏必须先回答问题名称、风险、下一步行动，再展示综合分析、证据、知识和技术详情。
- 病例详情按诊断档案组织；报告依靠 Typography、分隔线和留白而非连续卡片。
- 1440px 现有首页截图显示：首屏被 54px 大标题和独立三步提示占据，真正的上传工作区落到视口下半部；用户的第一任务是拍照，但视觉第一焦点却是宣传式标题。
- 当前首页上传与田间字段仍在一个纵向大卡片中，图片区只有约 250px 高，桌面没有形成“图片主区域 + 田间信息侧栏”的操作工作区。
- 大量圆角边框、浅绿表面、状态胶囊和说明文本叠加，使页面更像精致后台表单，而不是面向田间任务的图像诊断工具。
# 2026-08-20 UI Redesign V3 initial inspection

- User explicitly allows replacing the current JSX layout, copy, CSS and visual system while preserving every existing function, API, database field, model path, dual-server behavior, case ownership and recovery state.
- Product Design context preflight returned no saved user context; current project context comes from `PRODUCT.md`, `DESIGN.md`, source code and the local runtime.
- Impeccable context identifies the target as an existing web app with no surface brief. The current `DESIGN.md` is an older visual baseline, not a constraint for this replacement-world redesign.
- The local preview at `http://localhost:3101/` is reachable in the Codex in-app browser. The current home visibly shows the established green header, a large `智能诊断` title, a top service-unavailable warning, a large rounded workbench, an upload zone, and a two-column field area. The current service is unavailable, so no result record can be created during this read-only inspection.
- Current empty state is truthful: the action is disabled and the missing-items status lists image, object, environment, affected ratio and spread speed. The new V3 must preserve this state logic while making the workbench more decisive and less card-like.
- Design direction decision for V3: a light clinical-agriculture workspace with a deep agricultural green as the only brand accent, warm neutral surfaces, evidence/source marks, a slim instance status, and a record-like result/report language. Use a 70% Clinical Agriculture / 30% Field Intelligence blend; avoid landing-page hero treatment, gradients, glass, neon and invented metrics.
- Browser inspection limitation: the first auto-selected browser binding produced empty DOM/screenshot responses; the Codex in-app binding worked after creating a fresh tab. No upload or form submission was performed, so no user file was transmitted and no backend state was changed.

# 2026-08-20 参考图驱动诊断工作台改造初始发现

- 用户选择的参考图是一个“诊断记录工作台”，核心构成为深绿色左侧工作区、顶部病例标识与服务器归属、六步诊断路径、中间图片证据/来源栏和右侧结论/风险/行动栏。
- 参考图中的日期、姓名、地块、示例病例和额外导航属于示例内容，不应写入真实业务，也不应因此创建新业务路由。
- 当前公共首页已经有真实上传、田间字段、状态提示和 API 数据链路；当前病例详情已有 `DiagnosisSummary`、`DiagnosisPath`、`ImageEvidenceFrame`、`ComprehensiveAnalysis` 和 `FieldFacts`，可直接重排为目标三栏结构。
- 当前 `/history` 和 `/trends` 使用旧的 `public-*` 视觉体系，与 V3 核心页不同；这是既有 Impeccable audit 记录的第一个 P2。
- 实验室入口 `http://192.168.15.133:8080/health` 当前返回 `ok`、`instance_id=lab_cpu`、`detector_mode=remote`、`multimodal_configured=true`，可用于真实成功态验收。
- 本轮只应更新实验室 `web`；API 契约、SQLite、上传图片、报告、detector、Qwen3-VL、GPU 服务器及 Windows 中继均保持不变。

# 2026-08-20 参考图驱动诊断工作台验收发现

- 参考图的有效结构是“左侧工作区 + 顶部真实路径 + 图片证据/来源/结论三栏”，而不是复制日期、姓名、地块等示例数据；实现仅复用了结构和视觉关系。
- 首页、病例详情、报告已共用 `workspace-v4-shell`；历史和趋势不再使用独立旧页头，统一显示当前识别服务器、切换后列表/统计会变化的说明和相同的标题层级。
- 左侧归属栏在历史、趋势、病例详情和报告页会单独读取 `/health`，因此不会停留在“按病例固定”；首页继续复用已有 health 请求，避免改变后端接口。
- 图片证据区仍使用原始图片 API 与现有检测框坐标；`EvidenceRail` 只显示实际病例字段、检测结果、grounded evidence 和知识来源，不生成参考图中的虚构病例信息。
- 本地 390px 检查 `body.scrollWidth == clientWidth`；工作台导航、提交按钮、返回和报告动作均保持可用触控高度。
- 全量 Impeccable detector 的两个报告图片 warning 命中的是 `normalizeKnowledgeHtml` 里的 HTML 清洗正则/模板字符串，不是页面发出的空 `src`；已核验为误报，不改动安全清洗逻辑。
- 全量 detector 仍报告 `web/app/globals.css:284` 的训练监控 `transition: width`；该项在 Admin/训练监控范围外，本轮不修改。
- 实验室健康与容器状态：`lab-backend-1`、`lab-detector-1`、`lab-vlm-1`、`lab-gateway-1` 保持原运行；仅 `lab-web-1` 在部署时重建。SQLite 文件仍位于 `/data/ghl/storage/crop-pest.sqlite3`。

# 2026-08-20 公共诊断界面恢复旧版：实施前发现

- 首次 Impeccable 改造前的公共页面基线为 Git `HEAD`（`7f24239`），目标页面的旧版 JSX 可直接读取，不应使用中间 V2/V3 版本作为回滚目标。
- 当前 `globals.css` 仍包含旧版 `public-*` 样式；V4 样式主要通过 `.workspace-v4-page` 和 `.workspace-v4-*` 选择器覆盖，因此可用独立 legacy 覆盖层隔离恢复，不必替换整个全局 CSS。
- `WorkspaceShell` 当前同时负责侧边栏、Logo、服务器状态和主内容；旧版模式应只替换主内容顶部 Header/容器，不修改侧边栏 DOM、导航和 `ProductMark`。
- 当前后端白名单为作物 `玉米/番茄/南瓜/马铃薯/昆虫`、环境 `露地/温室/大棚/室内样本/未知`、部位 `叶片/茎秆/果实/根部/整株`、阶段 `苗期/营养生长期/开花期/结果期/成熟期`；受害比例和扩散速度必填。旧版数组包含已失效作物和“未知”部位/阶段，必须使用当前值替换。
- 当前首页的 API 请求链和病例字段已经可靠，视觉恢复不应重新设计 `/api/cases`、`detect`、`analyze`、`report` 或 `/api/trends`。
- 用户已明确选择：旧版外观，但历史/趋势保留“当前识别服务器/实验室 CPU/原 GPU”等准确归属文案。

# 2026-08-20 公共诊断界面恢复旧版：验收发现

- 公共页面已通过 `visualMode="legacy"` 使用独立旧版承载模式；默认 `WorkspaceShell` 仍是当前工作台模式，因此 Admin、训练和审核页未被切换。
- 1280px 下侧边工作栏和当前 `ProductMark` 保留，首页恢复旧版 Hero、两栏诊断区、结果卡片、病例历史预览；390px 下工作栏按原响应式行为隐藏，顶部页头与底部移动导航可用。
- 第一版移动导航在 in-app browser 中因 `position: fixed` 的静态定位产生顶部偏移；改为显式 `top: calc(100vh - 70px)` 后，390px 视口稳定落在底部且无横向溢出。
- Impeccable detector 对报告页 `normalizeKnowledgeHtml` 中生成 `<img>` 的正则/模板字符串给出 broken-image warning；实际图片仍来自 `apiUrl(record.image_url)` 或知识库安全 HTML，未发现空 `src`。

# 2026-08-20 旧版公共界面双服务器部署发现

- 实验室服务器是统一 Web 入口；GPU 服务器只运行独立 backend、detector 和 VLM，不直接提供 Web 页面。因此本次“部署到两端”采用实验室更新 `web`、GPU 同步 backend/deploy 并重启 backend 的架构正确实现。
- 部署后实验室入口所有公共路由均为 200，`/health` 为 `lab_cpu`，活动路由为 `gpu_full`；GPU `/health` 为 `gpu_full`，两端病例数均为 0。
- 使用旧版公共页面的 SSR 标记、当前侧边工作栏和 `ProductMark` 作为发布验收信号；模型、知识库、SQLite、上传图片和报告目录未被发布过程修改。

# 2026-08-20 GPU 同步部署发现

- GPU 服务器不是 Docker 部署：独立后端位于 `/root/autodl-tmp/ghl/app/backend`，由 `/root/autodl-tmp/ghl/app/deploy/gpu/run_backend.sh` 管理；独立存储位于 `/root/autodl-tmp/ghl/storage`。
- 原检测器启动脚本位于 `/root/autodl-tmp/crop-pest-system/inference/run_server.sh`，默认 `127.0.0.1:8870`；Qwen3-VL 启动脚本位于 `/root/autodl-tmp/crop-pest-system/inference/run_vlm_server.sh`，默认 `127.0.0.1:8890`。
- 当前端口 8000、8870、8890 均未监听；“GPU 服务器可用”目前表示 SSH/GPU 可用，不等于三个推理服务已启动。
- GPU 端已有模型资产：RTX 5090、多个 detector `best.pt`、Qwen3-VL 8B 权重目录；本轮不重新上传或重建模型资产。
- 部署前 SQLite `PRAGMA integrity_check` 返回 `ok`，已做应用/存储/日志归档备份。

# 2026-08-20 GPU 切换后公共页面仍显示 CPU 的诊断

- 实验室控制文件 `/data/control/active-instance.json` 已记录 `active_instance=gpu_full`，后台 `/api/admin/instances/activate` 日志返回 `200 OK`，说明切换动作实际写入成功。
- Windows 两段中继在线，GPU 端 `/health` 返回 `gpu_full / 原 GPU 服务器 / ok`；远端 backend、detector、VLM 均可访问。
- 实验室 `http://192.168.15.133:8080/health` 仍只返回 `instance_id=lab_cpu` 和 `instance_label=实验室 CPU`，缺少 `active_instance_id`、`active_instance_label`、`active_instance_mode`。
- 由于本轮 GPU 发布时只重建了 GPU backend，实验室 `lab-backend-1` 未随最新双服务器 health 契约更新；公共 `PublicHeader`、`WorkspaceShell` 和首页会按 `health.instance_label` 回退为 CPU，因此截图中的两个 CPU 标签都属于同一后端版本不一致问题。
- 正确修复方向是备份后仅更新/重建实验室 `backend`，不动 SQLite、病例图片、报告、detector、VLM 和 gateway；重启后重新验证控制文件、`/health` 和公共页面。

# 2026-08-21 GitHub 项目同步：待检查

- 目标仓库为 `LingmaFuture/plant-health-ai`；用户授权本轮提交并 push，但不创建 Pull Request。
- 需要先确认本地当前 remote 是否已指向目标仓库；如果不是，只添加/更新明确的目标 remote，不覆盖原有 remote 信息。
- 需要区分“源码/配置模板/部署脚本”与“运行数据/模型权重/缓存”；后者必须按大小、敏感性和可复现性单独处理。
- `best_model.pth` 的上传方式必须以实际字节大小和仓库限制为依据，不能仅按扩展名判断。
- `Image Data base/` 不应上传完整训练集；需要保留能说明类别、目录结构、数量、训练代码路径和获取方式的文档或清单。

# 2026-08-21 GitHub 项目同步：基线审计结果

- 本地当前分支为 `codex/publish-audits-and-calibration-plan`，HEAD 为 `7f24239 feat: add curated Baidu knowledge reports`；工作树存在既有修改和多个最新 UI/设计文档未跟踪目录，不能重置或覆盖。
- 本地 `origin` 指向 `genghailong8-maker/crop-pest-multimodel-system`，不是本次目标；目标 `LingmaFuture/plant-health-ai` 当前只存在 `main`，HEAD 为 `2dfd6d0 Update README.md`，包含 13 个旧版 Gradio 项目文件。
- 本地已跟踪约 2705 个文件，内容明显比目标 `main` 完整；相对目标 `main` 存在大量新增项目源码/文档/部署/知识库文件，同时目标旧版 `app.py`、`main.py`、`requirements.txt`、`best_model.pth` 等不在当前本地树中。
- 本地根目录不存在 `best_model.pth`、`Image Data base/`、`example/`、`app.py`、`main.py` 或根 `requirements.txt`；不能把目标仓库旧模型或旧示例误报为当前系统资产，也不应恢复/复制旧文件覆盖当前架构。
- 当前 `.gitignore` 已排除 `.env`、运行时、虚拟环境、`node_modules`、缓存、模型格式和大部分数据/训练图片；需要补充的重点是文档化当前数据集与模型资产，而不是放宽这些忽略规则。
- 工作区存在约 5.0 GB Qwen GGUF、近 1 GB PlantDoc 压缩包、离线镜像/wheel/npm 缓存和实验归档等大型运行资产，均不应进入普通 Git 分支；应保留现有忽略规则并在资产说明中记录提供方式。
- 提交前第一次从项目根目录运行 `pytest` 会收集训练测试，并因后端虚拟环境没有 `numpy` 在训练测试收集阶段失败；后端 API 测试应按项目边界从 `backend/tests` 单独运行，训练依赖不应为 GitHub 同步强行装入后端环境。
- 本地提交 `4c8fa20` 已包含 64 个确认文件；`git push -u target competition-dev` 返回 HTTP 403，GitHub 连接器确认当前账号 `genghailong8-maker` 对目标仓库权限为 `push: false`。
# 2026-08-21 外部证据增强诊断：初始发现

# 2026-08-21 Gemini Grounding provider 调整：官方接口核对

- 官方当前文档推荐 Gemini API 的 `google_search` 工具；REST 使用 `POST https://generativelanguage.googleapis.com/v1beta/interactions`、`x-goog-api-key`、`model`、`input` 和 `tools: [{"type":"google_search"}]`。
- Interactions 响应通过 `steps[].type=model_output` 的文本块 `annotations[].type=url_citation` 返回 URL、标题及引用文本区间；旧 Generate Content 响应通过 `candidates[].groundingMetadata.groundingChunks` 和 `groundingSupports` 返回来源与关联关系。
- Grounding 返回的是 Gemini 的搜索整合文本和引用，而本项目不能把 Gemini 文本直接当作最终危害/可能诱因。因此 provider 只提取 citation 元数据，再抓取引用 URL 的原始网页正文；只有抓到可核验原文的来源才能进入 Qwen 外部证据上下文。
- 为避免新增 SDK 依赖，采用现有 `httpx` 调用官方 REST；配置 `GEMINI_API_KEY`、`CROP_GEMINI_MODEL`、`CROP_GEMINI_ENDPOINT`。真实密钥不写入源码、测试、日志或 Git。
- Custom Search JSON API 保留为 `legacy` provider，仅为已有资格用户兼容；`CROP_SEARCH_PROVIDER=google_grounding` 才启用当前推荐实现，默认仍为 `disabled`。

# 2026-08-21 Gemini Grounding 真实 E2E：环境阻塞

- 当前分支为 `competition-dev`，HEAD 为 `f53ed24`；工作区已有未提交改动，未触碰 master/main。
- 当前工具进程中 `CROP_SEARCH_PROVIDER`、`GEMINI_API_KEY`、`CROP_GEMINI_MODEL`、`CROP_GEMINI_ENDPOINT`、搜索超时和来源上限变量均缺失；没有本地 `.env` 文件，只有 `.env.example`。
- 本地 backend `127.0.0.1:8000/health` 返回正常，但 detector `127.0.0.1:8870` 与 VLM `127.0.0.1:8890` 不可访问，因此无法完成 YOLO→Grounding→Qwen 的真实闭环。
- 本轮不发送、打印或落盘 API key；不使用 mock/历史结果代替真实验收。需用户在本机安全设置变量并恢复两个推理服务后继续。

- 为支持独立连通性验收，新增测试入口 `backend/scripts/test_gemini_grounding_connectivity.py`；它只调用当前 `GeminiGoogleGroundingProvider`，不会启动或依赖 8870/8890。

# 2026-08-21 Gemini Grounding 独立真实连通性结果

- 真实临时环境变量已加载，Provider 为 `google_grounding`，模型为 `gemini-3.7-flash`，endpoint 为配置的 `https://generativelanguage.googleapis.com/v1beta/interactions`；8870/8890 均未启动。
- “蛴螬 危害 危害症状 农业”和“蛴螬 发生条件 发病条件 发生原因 农业”均收到 HTTP 403，错误 `permission_denied`，消息为 `Your project has been denied access. Please contact support.`。
- 这是 Gemini 项目访问权限拒绝；endpoint 可达且请求进入 Google API，但 Grounding 未实际执行，citation 数量为 0，原始网页抓取数量为 0，Normalizer 最终 0 来源、状态 `unavailable`。
- 未打印或保存 GEMINI_API_KEY；未调用 YOLO/Qwen；未创建病例；未修改 master/main；未 commit/push。

# 2026-08-21 Tavily SearchProvider 调整：接口核对

- 当前 SearchProvider 尚未注册 `tavily`，因此仅设置 `CROP_SEARCH_PROVIDER=tavily` 会回退到 disabled；需要做最小 provider 接入后才能执行真实连通性测试。
- Tavily 官方 Search API 当前使用 `POST https://api.tavily.com/search`、`Authorization: Bearer <TAVILY_API_KEY>`；请求支持 `query`、`search_depth`、`max_results`、`include_answer` 和 `include_raw_content`。
- 本项目将 `include_answer=false`，只把每个 result 的 `raw_content`（优先）或 `content` 转成 SearchSource.content；不把 Tavily LLM answer 传给 Qwen或用户结论。

# 2026-08-21 Tavily 独立真实连通性结果

- 真实环境变量已加载，使用类别“蛴螬”；未启动 8870/8890，未调用 Qwen，未创建病例。
- 危害查询和可能诱因查询均调用 `https://api.tavily.com/search` 成功返回 HTTP 200，各返回 5 条结果；请求包含 `include_answer=false`、`include_raw_content=text`、`max_results=5`。
- 两次结果均包含可用 `content` 或 `raw_content`；provider 转成 SearchSource 后，EvidenceNormalizer 各保留 5 个来源并生成连续 `source-1`…`source-5`；Tavily answer 未进入 evidence/Qwen context。
- 真实来源中出现 `zhuanlan.zhihu.com`、`m.3456.tv`、`jin-cang.com` 等低质量信号，但当前 `is_obviously_low_quality` 未过滤，两个查询均过滤 0 条；这是本次整体 FAIL 的唯一验收缺口，暂不在本阶段修复。

- 当前工作树干净，分支为 `competition-dev`，与 `origin/competition-dev` 对齐；未修改 `master/main`。
- 后端依赖已有 `httpx`，没有独立搜索目录；`backend/app/multimodal.py` 当前协议版本为 `phase9-multimodal-v3`，`grounded_assessment` 的危害/诱因依据只允许 image、yolo、field。
- 现有多模态输出字段包含 `possible_causes` 和 `grounded_assessment.causes`，用户可见首页仍存在“诱因”字样和技术详情，需统一为“可能诱因”但保留旧字段兼容。
- `knowledge.py` 已有逐类知识卡片及来源；`knowledge_documents.py` 已有版本化 Markdown 知识文档接口。防治措施应继续复用它们，不能从外部检索填充。
- `database.py` 以 `analysis_json`（数据库列名 `analysis`）保存分析 JSON，未发现独立 JSON 列；可以在现有 analysis / report snapshot 中增量保存新结构，不迁移表。
- 当前首页 `web/app/page.tsx` 直接读取 `record.analysis`，病例/报告组件需继续检查；前端无独立 API client 类型文件，类型主要集中在 `web/app/lib/api.ts`。
- 粘贴方案要求真实 Google/Gemini 没有密钥时只实现 provider 接口、disabled/mock 和测试；不可伪造真实请求成功。

## 2026-08-21 实施结果

- 新增 `backend/app/search/`：`SearchProvider` 协议、Google Custom Search JSON provider、disabled/mock provider、来源模型和 EvidenceNormalizer。
- Legacy Google Custom Search provider 只在显式选择 `CROP_SEARCH_PROVIDER=google_legacy`（兼容别名 `google`）且存在 `GOOGLE_API_KEY`/`GOOGLE_SEARCH_ENGINE_ID` 时工作；会尝试抓取原始 HTML 正文，只有抓到原文的来源才能作为 Qwen 的结论依据。前端永远看不到密钥或原始 API 请求。
- 新病例分析协议升级为 `phase9-multimodal-v4-external-evidence`；`evidence_analysis.harms` 与 `evidence_analysis.possible_causes` 的每条结论都必须绑定有效 `source_ids`。没有有效原文来源时强制返回 `status=unavailable` 和空列表。
- `present_case` 增加 `evidence_analysis`、外部 `sources` 和 `treatment`；`treatment.source` 固定为 `local_knowledge_base`。报告保留原有知识库 `sources`，另增 `external_sources`，避免两类来源混淆。
- 首页、病例详情、报告新增“危害 / 可能诱因 / 参考来源 / 防治措施”展示；防治说明明确来自本地审核知识库；外部链接使用新标签页和 `noopener noreferrer`。
- 当前本地配置默认 `CROP_SEARCH_PROVIDER=disabled`，实测 `collect_external_evidence("蛴螬")` 返回 `unavailable`，没有伪造真实搜索结果。
- `npx tsc --noEmit` 仍报告 `web/app/review/page.tsx`、`web/db/index.ts`、`web/worker/index.ts` 的既有工程错误；本轮未修改这些文件。Vinext production build、ESLint 和页面测试均通过。
- 最终回归新增明显低质量论坛/商城 URL 过滤测试后，backend 测试为 `52 passed`。

# 2026-08-21 Tavily 来源质量过滤修复与真实验收

- `EvidenceNormalizer` 新增基于主域名/子域名的黑名单：知乎、贴吧、百度知道、3456.tv、jin-cang.com；并补充问答、论坛、自媒体、商城、农资销售、营销软文、内容农场和明显 SEO 信号过滤。
- 来源排序使用可解释分数：政府农业部门 100、农业科研院所 80、高校/农技推广/植保机构 70、权威农业数据库及其他农业专业来源 60、普通网页 0；黑名单来源直接过滤。
- 最大来源数仍是上限而非填充目标，Normalizer 最多保留 5 条，且同一主域名最多保留 2 条；空结果返回 `unavailable`。
- 真实 Tavily 两次查询均 HTTP 200。危害查询过滤知乎与 3456.tv 各 1 条，保留 3 条陕西/上海/怀化农业农村部门来源；可能诱因查询过滤 jin-cang.com 与知乎各 1 条，保留 2 条农业农村部门来源和 1 条农业研究数字图书馆来源。两次 source IDs 均从 `source-1` 连续生成，Tavily answer 未进入 evidence。
- 自动化 SearchProvider 测试 22 passed；将外部 provider 在进程级设为 disabled 后 backend 全量测试 66 passed。后者是为避免真实 Tavily 临时环境污染旧多模态测试，不是生产配置变更。

# 2026-08-21 完整真实验收：启动前配置核对

- 用户授权在不 commit/push、不修改 master/main、不暴露 secret 的前提下，由本地负责启动 YOLO/Qwen、建立隧道并完成三病例真实闭环。
- 项目文档确认 YOLO 使用 `inference/run_server.sh`，默认监听远端 `127.0.0.1:8870`；Qwen 使用 `inference/run_vlm_server.sh`，默认监听远端 `127.0.0.1:8890`；本地通过 `inference/open_tunnel.ps1` 转发两个端口。
- 当前分支为 `competition-dev`，HEAD 为 `f53ed24`，工作区存在既有未提交改动，不能使用 reset/clean/checkout 覆盖。
- 当前进程安全检查只显示 `CROP_SEARCH_PROVIDER=tavily`、`TAVILY_API_KEY=set`；未输出 key 值。detector/VLM endpoint 未在当前进程变量中出现，需根据运行方式和项目 `.env`/部署配置继续确认。

# 2026-08-21 完整验收：Qwen 上下文预算问题

- 三个真实上传均完成 YOLO：蛴螬 class 14（0.918622）、番茄样本被识别为马铃薯晚疫病 class 7（0.915291）、马铃薯早疫病 class 3（0.663122）。
- 番茄样本首次完成 Tavily→EvidenceNormalizer→Qwen→报告快照；其余两例因 Qwen 结构化请求超过 8192 上下文或输出 JSON 截断而降级，未伪造结论。
- Qwen 日志显示旧请求为 7293+900、重试后为 7493+700；分别触发 8192 超限和不完整 JSON。已将 Qwen 外部原文上下文单来源上限从 6000 调到 4000 字符，并保留 700 输出上限，待重启后复验。

# 2026-08-21 完整真实验收：最终结果

- 远端 RTX 5090 上的 YOLO 8870 与 Qwen3-VL 8890 已真实启动并通过健康检查；本地 SSH 隧道、backend 8000 和 frontend 3103 均可用。
- 为适配 Qwen 8192 上下文，`build_qwen_context` 仅将每个外部来源的 1600 字符摘录送入第二阶段；完整网页正文仍保留在 SearchSource/病例快照中。第二阶段 `max_tokens=700`，没有改变证据协议或业务字段。
- 三个真实病例均完成 YOLO→Tavily→EvidenceNormalizer→Qwen→knowledge/treatment→病例 API→前端/报告闭环：蛴螬 class 14（0.918622）、马铃薯晚疫病 class 7（0.915291）、马铃薯早疫病 class 3（0.663122）。
- 每例均有 5 个真实来源、1 条危害、1 条可能诱因；所有 `source_ids` 都存在于该例 sources，且 `treatment.source` 均为 `local_knowledge_base`。人工番茄字段与 YOLO class 7 的冲突被保留并记录，未覆盖 YOLO 结果。
- 浏览器真实页面确认首页/病例详情/报告可访问；详情和报告显示危害、可能诱因、参考来源、检索时间、防治措施与完整知识库内容。外部链接为新标签并带 `noopener noreferrer`。
- 独立隔离降级测试中，YOLO 仍成功，分析 API 为 200，外部 evidence 为 unavailable，危害/可能诱因为空，知识库防治措施仍可用。
- 自动化：backend `66 passed`（1 条既有弃用警告）；frontend `8 passed`；ESLint、production build、`git diff --check` 均通过。未 commit/push，未输出密钥。
- 结论：本轮真实 Tavily 外部证据闭环 PASS。当前仅保留一个本轮隔离降级用的未跟踪 `backend/runtime-fallback` 测试目录，删除操作被本机安全策略拒绝；它不属于业务数据，也未进入 Git。

# 2026-08-21 最终提交准备

- `backend/runtime-fallback` 已确认仅为本轮隔离测试数据，并已安全删除；没有未跟踪运行数据残留。
- 29 个确认文件已通过 staged diff 检查并创建本地 commit `5bad8b0`（`feat: add evidence-grounded diagnosis with Tavily sources`）。
- 暂不 push；用户将手动执行 `git push origin competition-dev`。

# 2026-08-21 P0-1 初始定位

- Work 报告干净 clone 在 `vite.config.ts` 找不到 `web/build/sites-vite-plugin`；本地开发环境曾能 build，说明需要区分本地生成物与仓库源码。
- 当前开始前工作区干净，分支为 `competition-dev`；本轮基线为 `eb7ba9480b5df65a84f1e6f182d0ee62dec27a4d`，不修改 master/main。
- 需要先读取 `web/vite.config.ts`、`web/build/`、两处 `.gitignore`、package/lock 文件，并执行 `git status --ignored`、`git check-ignore -v web/build/sites-vite-plugin`、`git ls-files web/build`，再决定 A/B/C。

# 2026-08-21 P0-1 根因确认

- `web/build/sites-vite-plugin.ts` 是项目自己的必要源码，不是 dist/cache，也不是第三方依赖复制物；它导出 `sites()` Vite plugin，在 build closeBundle 时复制 `.openai/hosting.json` 与 `drizzle/` 到 `dist/.openai`。
- 当前根 `.gitignore` 第 28 行 `web/build/` 忽略整个目录；`git check-ignore -v` 命中该规则，`git ls-files web/build` 无输出；`web/vite.config.ts` 第 4 行静态引用该文件。
- package-lock 存在且项目依赖已锁定；该插件只使用 Node 内置模块和已存在的 Vite 类型，不需新增依赖。
- 最小修复：在根 `.gitignore` 紧邻 `web/build/` 后加入 `!web/build/` 和 `!web/build/sites-vite-plugin.ts`，只纳入这一个必要源码文件。

# 2026-08-21 P0-1 干净环境基线复现

- 基于当前 HEAD `eb7ba94` 创建的独立 worktree 未包含 ignored 的 `web/build`；`npm ci` 成功，`npm run build` 真实失败，错误为 `UNRESOLVED_IMPORT: Could not resolve './build/sites-vite-plugin'`。
- 第一次修复后 worktree 夹具复制文件时目标目录尚未创建，导致复制动作失败，随后 build/render 均失败；该错误仅属于测试夹具，下一次验证会先创建目标目录并重新执行。

# 2026-08-21 P0-1 修复后验证

- 在独立 detached worktree 中创建 `web/build` 后只复制候选 `sites-vite-plugin.ts` 和 `.gitignore`，没有复制当前工作区 `node_modules`、dist 或其他 ignored 文件。
- `npm ci` 安装锁定依赖成功；production build 成功；render tests 8/8 通过。
- 本地工作区 frontend tests 8/8、ESLint、production build 和 render tests 均通过；插件源码没有新增依赖，也未触及外部证据、模型或知识库。

# 2026-08-21 P0-1 最终审计

- 当前未跟踪目录 `web/build/` 仅包含 `sites-vite-plugin.ts`（1299 字节）；没有其他 build 输出。
- `.gitignore` 的最小例外使该源码不再被忽略，同时继续忽略该目录中未来可能产生的其他文件。
- 当前 `git status` 无 runtime 测试目录；ignored 的模型、数据集、缓存和 node_modules 未进入候选范围。
- 本地与修复后独立 worktree 的前端测试、Lint、build、render tests 均通过；结论 PASS。

- 本轮已获得用户授权创建独立 P0-1 原子提交；提交范围严格限定为 `.gitignore`、`web/build/sites-vite-plugin.ts`、`task_plan.md`、`findings.md`、`progress.md`。

# 2026-08-21 P0-2 审计

- `SearchSource.content` 在搜索抓取和 Normalizer 后仍存在，Qwen 只使用其 1600 字符摘录；`public_metadata()` 明确排除 `content`，多模态输出的 `analysis.sources` 因此只有公开元数据。
- `diagnosis_cases.analysis_json` 保存完整分析 JSON blob，现有 SQLite 无需新增列；报告由 `build_case_report()` 生成并由 `reports.save_snapshot()` 保存为独立 JSON。
- 列表和上传/检测/分析接口均通过 `present_case()` 返回轻量数据；病例详情可增加按需正文快照，报告可在根部保存快照，避免列表 API 携带长正文。

# 2026-08-21 P0-2 实现与验收

- 新增 `persisted_evidence_snapshots()`，只复制 Normalizer 最终接受且有正文的来源字段：`source_id/title/site_name/url/retrieved_at/reliability_level/content`；不复制 provider headers、密钥、cookie 或被过滤来源。
- `analysis_json` 保存快照；`GET /api/cases/{id}` 按需返回快照，`GET /api/cases` 继续只返回公开来源元数据；报告 v2 根节点同步保存快照。
- 不需要 SQLite schema migration；旧病例/旧报告缺少快照时返回空列表并继续读取既有 sources、harms、possible_causes。
- 真实隔离病例 `lab_cpu-da980cfd48b54d4c9f775897ee560d73`：YOLO 识别蛴螬；5 个来源、5 个正文快照（单份约 349–3826 字符）；危害和可能诱因各 1 条，source_id 均有效；treatment 为 `local_knowledge_base`。
- 停止并重新启动隔离后端后，病例详情和 report 仍恢复 5 份正文；重复 GET report 文件未更新，证明历史读取不重新调用 Tavily。
- 完整 backend pytest 在临时 disabled provider 下为 70 passed；前端 8/8、Lint、Build、diff-check 通过；工作区仍未提交。

# 2026-08-21 P0-3 启动链审计

- `inference/open_tunnel.ps1` 已是现有 GPU 隧道入口，默认转发本地 `8870/8890` 到远端同端口；本轮仅补充可选 PID 文件记录和安全回收，不重写隧道逻辑。
- Backend 健康端点为 `/health`，Detector 使用 `/health` 并要求 `status=ok`、`class_count=16`、主模型 loaded，Qwen 使用 `/v1/models` 并要求 `crop-pest-vlm`，Frontend 通过根路径 HTTP 检查。
- 生产前端 API 在未设置 `NEXT_PUBLIC_API_BASE_URL` 时开发环境默认 8000；统一入口启动 build/start 前显式注入本机 backend 地址，避免把本地开发地址带入比赛构建。
- Tavily 属于外部证据增强项：配置存在性检查失败为 `DEGRADED`，核心 Backend/Detector/Qwen/Frontend 失败为 `FAILED`；status 不输出 key 值。
- `.gitignore` 已忽略 `tmp/`、backend runtime、node_modules、.venv 等运行产物；统一入口 PID/log 固定写入 `tmp/competition`。

# 2026-08-21 P0-3 实现与验收

- 新增 `scripts/competition.ps1`：`start` 进行 Python/venv/Node/npm/node_modules/ssh/身份文件预检，按需复用 `open_tunnel.ps1`，启动 Backend 8000 和生产 Frontend 3000；`status` 只检查；`smoke` 额外做一次 Tavily 网络检查；`stop` 只回收脚本自有本地进程。
- 状态策略为核心 Backend/Detector/Qwen/Frontend 任一非 READY 即 `FAILED`；Tavily、Knowledge、Storage 不可用时为 `DEGRADED`，不阻断核心诊断。状态输出只显示 key 是否 configured/missing，不显示值。
- `inference/open_tunnel.ps1` 增加可选 `PidFile`，保留原有 SSH 参数、健康等待和远端服务行为。Frontend stop 增加项目 `vinext` + 端口的孤儿进程精确清理；不使用全量 Python/Node 杀进程。
- 新增 `scripts/competition.tests.ps1`，分类、降级策略和 PID 误匹配保护通过；真实 start/status/smoke/stop 与临时 3110 production start/stop 通过。
- 真实 API 链路中，默认 5 来源样本复现既有 Qwen 8192 上下文超限，系统返回 `multimodal_unavailable` 而未伪造结论；临时单来源配置下上传、YOLO、Qwen、详情、报告均返回成功，treatment 仍为 `local_knowledge_base`。这属于既有证据上下文容量问题，不在本轮修复范围。
- 本轮候选文件未包含 API key、密码、token 值、私钥、模型、数据集、runtime、tmp、dist、node_modules 或 `.venv`；未 commit/push。

# 2026-08-21 P0-4 初始审计

## P1 比赛配置与启动路径收口：初始审计（2026-08-21）

- 当前正式基准为 `a37ac675d56cf87476392779b29942a3fff4e95d`，分支为 `competition-dev`，工作区初始干净。
- `backend/.env.example` 的实际值已是 `CROP_SEARCH_PROVIDER=tavily`，但注释仍写“当前推荐：google_grounding”，且 Tavily 仍被描述为可替代 provider；README/runbook 只强调 Tavily 增强能力，缺少三种 provider 的统一定位。
- `backend/app/config.py` 将非绝对 `CROP_STORAGE_DIR` 解析为 `backend/` 下路径，将非绝对 `CROP_KNOWLEDGE_DIR` 解析为 `backend/` 下路径；因此 `.env.example` 的 `runtime` 应为 `backend/runtime`，`../knowledge/...` 应为仓库根目录 `knowledge/...`。
- `scripts/competition.ps1` 已正确使用 `$PSScriptRoot` 推导仓库根和 `backend/`，但 `Get-StorageStatus` 直接使用配置字符串，导致从仓库外 cwd 调用时相对 storage/knowledge 路径可能被错误解释并产生假性 DEGRADED。
- 本轮将新增基于脚本目录的统一路径解析函数，不改变调用者 cwd；测试覆盖 root、外部 cwd、绝对路径、中文空格和真实不存在目录。

## P1 比赛配置与启动路径收口：验收（2026-08-21）

- `backend/.env.example`、README 和 `docs/competition/demo-runbook.md` 已统一说明 `CROP_SEARCH_PROVIDER=tavily`；Tavily 是比赛默认外部证据 provider，Google Grounding 是 optional/compatible，Google Custom Search 是 legacy；API Key 示例均为空。
- `scripts/competition.ps1` 新增 `Resolve-BackendPath`：相对路径以 `backend/` 为基准，绝对路径原样规范化为 full path；未使用 `Set-Location` 修复，也未改变启动、PID 或远程停止逻辑。
- `scripts/competition.tests.ps1` 新增 root、外部 cwd、绝对 storage、绝对 knowledge、中文/空格路径和真实缺失 knowledge 的测试；PowerShell tests PASS。
- 项目根目录和 `C:\Windows\Temp` 外部 cwd 的 `status`、`smoke` 均 READY，二者 Knowledge/Storage 路径一致，不再出现假性 DEGRADED。
- Backend pytest 77 passed（1 条既有弃用警告）；frontend/render 8 passed；ESLint、production build、`git diff --check` 均通过。
- 本轮只改文档、启动脚本、PowerShell 测试和规划记录；未修改核心诊断、搜索算法、YOLO/Qwen/Tavily provider、UI 或远程服务。

## 跨对话交接摘要（2026-08-23）

- 当前正式基线是 `competition-dev` / `8807b90aa135d97549d463c37807f81de7300daa`，远端已同步；交接后仅三份规划文件有未提交记录改动。
- P0-1～P0-4 与 P1 均已独立提交并通过验收；不要在新对话中重复实现或回滚这些阶段。
- 当前最重要的运行事实：Backend、Frontend、Knowledge、Storage 正常；Detector 8870 与 Qwen 8890 当前未运行，因此 `competition.ps1 status` 的 Overall 为 FAILED，这是服务状态而非代码状态。
- 继续工作前应先阅读 `task_plan.md` 的“跨对话工作交接记录”、本文件和 `progress.md`，再检查分支与工作区。
- 任何新功能或部署动作都需要用户明确范围；当前没有授权自动开始 P2/P3、部署、commit 或 push。

- 当前 `SearchEvidence.sources` 最多 5 个，Normalizer 已按可靠性排序并重编号为 `source-1...source-5`；`persisted_evidence_snapshots()` 保存这些最终来源的完整正文，不能削减搜索或持久化数量。
- 当前 `build_qwen_context()` 会把所有有正文来源送入第二阶段，每个正文固定取前 1600 字符；这与 Qwen 的 system prompt、字段/YOLO JSON、第一阶段结果和图片 token 叠加，默认 5 来源可能达到 8192 上限。
- 第二阶段固定 `max_tokens=700`；第一阶段固定 `max_tokens=500`。图片通过 `data:image/...` 发送，不能把 base64 文本按普通字符计入 evidence 预算，但必须为视觉 token 预留安全空间。
- 当前 Qwen 服务不提供可复用 tokenizer 接口；本轮采用保守估算器，不引入 Transformers 或模型权重依赖。估算只用于证据 excerpt 选择，不宣称精确 tokenizer 计数。
- 当前已知真实失败：默认 5 来源下 Qwen 返回 `maximum context length is 8192`；将搜索最大来源数改为 1 能绕过但违反业务约束，因此必须在 Qwen 输入层解决。

# UI / 比赛展示优化第一阶段：当前视觉审计（2026-08-23）

- 本轮仅做只读审计与视觉方案探索，不修改 `web` 源码、不提交、不推送。
- 当前前端可访问：`http://localhost:3000/`；真实审计截图保存于 `tmp/ui-audit-round1/`：`01-home-current.png`、`02-case-current.png`、`03-report-current.png`。
- 首页现状：深绿色左侧导航、米白背景、双栏上传/结果工作区；品牌识别清晰，但 Hero 文案较长，上传表单字段与说明连续堆叠，空结果面板占据大面积，评委第一眼难以看到“识别结果/证据链”。
- 病例详情现状：真实图片与检测框很突出，状态横幅清楚；随后依次出现综合分析、外部资料、5 条来源、防治措施、知识库长文，证据与知识内容重复呈现，信息节奏偏平。
- 报告现状：报告头、图片、指标网格和打印入口成立；后半段包含逐条分析、外部来源、本地防治、综合信息、百科长文、来源与边界，报告感有但过长，不利于比赛现场快速讲解。
- 真实业务不可丢失：结果必须突出病虫害名称、置信度、检测图、危害、可能诱因、防治措施、来源证据；`treatment.source=local_knowledge_base` 与外部来源边界需保留。
- 方案探索应优先解决：一屏一个主结论、证据层级分组、长知识内容折叠/摘要、异常状态短文案、首页上传与结果的视觉比例。
- 浏览器审计首次尝试使用错误插件路径失败，随后改用浏览器插件根目录成功；未影响项目文件。

## UI / 比赛展示优化第一阶段：参考研究（2026-08-23）

- Apple HIG 的可迁移原则：用字体大小、字重和颜色建立少量明确层级；避免轻字重与过多字体；长内容与大字体应能自然换行，不依赖截断。[Apple Typography](https://developer.apple.com/design/human-interface-guidelines/typography)
- Material Cards 的可迁移原则：卡片适合承载不同类型内容、可变高度或操作入口；同质、快速扫描的内容应使用列表而不是大量卡片；卡片内应先放主内容，避免塞入无关操作；长内容可以展开而不是在首页全部展开。[Material Cards](https://m1.material.io/components/cards.html)
- Google Gemini 的产品方向：入口简洁、结果更易读、更短；图片/视频/报告等生成结果进入独立的资料空间；复杂任务用可探索的模块化结果承载，而不是一段长文本。[Google Gemini redesign](https://blog.google/products-and-platforms/products/gemini/gemini-3-gemini-app/)
- Linear 的近期设计复盘：导航和辅助结构应退后；减少图标和不必要的装饰；结构应“被感知而不是被看见”；软化边界、减少分隔线，让工作内容优先。[Linear interface refresh](https://linear.app/now/behind-the-latest-design-refresh)
- Ada 的数字健康产品启发：评估结果应提供面向用户的摘要、下一步和可分享/可打印报告；“不确定”也要导向下一步，而不是堆叠免责声明。[Ada enterprise assessment](https://about.ada.com/enterprise/)
- 方案原则：本项目应把“诊断结论”设为第一视觉层，把“证据依据”设为第二视觉层，把“完整知识库”设为可展开的第三层；搜索来源与本地防治必须使用不同视觉标签，避免评委误以为外部网页生成了防治建议。

# 2026-08-21 P0-4 实现决策

## P0-4 最终验收（2026-08-21）

- 三条默认最多 5 来源的真实病例均返回 `analyzed`：蛴螬 class 14（0.918622）、马铃薯晚疫病 class 7（0.915291）、马铃薯早疫病 class 3（0.663122）。每条病例 API 与报告 API 均为 HTTP 200；原始来源数组和正文快照均为 5 条。
- 三条病例的 provenance 均记录 `evidence_sources_total=5`、`evidence_sources_selected=2`、`selected_source_ids=[source-1, source-2]`，估算值分别为 1600、1600、1599，未超过 1600 证据预算。病例中的危害/可能诱因引用均通过 source ID 存在性校验。
- 蛴螬病例重复分析两次均完成，未再出现 Qwen 8192 context overflow。后端重启后详情和报告读取恢复 5 个来源、5 份正文快照，读取过程未触发重新检测或重新分析。
- 三例的防治措施均来自 `local_knowledge_base`；外部网页正文仅进入证据快照和 Qwen 证据摘录，未替换本地知识库防治内容。
- `backend` 测试 77 passed（1 条既有 Starlette/httpx 弃用警告）；前端 tests/render 8 passed；ESLint、production build、`git diff --check` 均通过。根目录 pytest 的训练评测收集因环境缺少 NumPy 报错，按项目实际 `backend` 测试目录复跑通过，未修改训练代码。
- 本轮改动 9 个文件；精确安全扫描确认没有真实 API key、私钥、运行时目录、模型、数据集或依赖目录进入改动范围。测试中的 `test-*` 凭据仅为 mock 字符串，未使用真实密钥。

- 新增 `CROP_VLM_CONTEXT_WINDOW`、`CROP_VLM_OUTPUT_TOKENS`、`CROP_VLM_RESERVED_INPUT_TOKENS`、`CROP_VLM_EVIDENCE_TOKEN_BUDGET`、`CROP_VLM_MAX_EVIDENCE_SOURCES` 和 `CROP_VLM_EVIDENCE_EXCERPT_MAX_CHARS`；默认 8192 / 700 / 5892 / 1600 / 2 / 900。
- 1600 证据预算是 `8192 - 700 output - 5892 system/field/YOLO/image/safety reserve` 的保守残余；估算器使用字符上界，不宣称等同 Qwen tokenizer，也不引入大模型 tokenizer 依赖。
- 选择按 Normalizer 已有来源顺序进行，先尝试 2 个来源并公平分配 excerpt；若两条无法放入预算，再退到 1 条。excerpt 保留前缀和“危害/为害/症状/发生/原因/条件/幼虫/根部/传播/防治”附近窗口，原始正文不变。
- Qwen prompt 内保留原始 source ID；技术 provenance 记录总来源数、选中数、选中 ID、估算 token、预算和估算方法；日志不记录正文或密钥。
- 首轮公平分配修正后，蛴螬、马铃薯晚疫病、马铃薯早疫病默认搜索最多 5 个来源均完成 Qwen 分析；每例保留 5 个来源，Qwen 使用 2 个来源，treatment 仍为 `local_knowledge_base`。

## UI 最终视觉方案前端落地：验收事实（2026-08-24）

- 可参考的既有蛴螬病例为 `lab_cpu-4361d9fada86434ba588b5031e3a8961`：`analyzed` / `conclusive` / 92% / 5 条来源 / `local_knowledge_base` 防治内容；只读 GET 即可复现结果、病例和报告。
- `lab_cpu-11b0747fc0b04e429f4942be15d067af` 提供现成的“来源不可用 / 需要补拍”降级验收数据，不需要触发模型推理。
- 新视觉以低密度暖白、深绿标题、细分割线和三段语义色条组织内容；不展示 YOLO、Qwen、Tavily 或 `source-1` 等技术链路。
- 首页没有本地样例图片时保留真实上传入口的空态；上传后仍直接使用用户本地预览，病例/报告仍直接读取真实 API 图片。GPU 真实 E2E 按用户限制未执行，待可用后以一条蛴螬病例复验。

## 生产前端静态资源 404 解阻：根因与浏览器实证（2026-08-24）

- 最新 `vinext start` 在 Windows 仍将实际存在的 `/assets/*` 返回 404：`StaticFileCache` 以 `path.relative()` 的反斜杠 key（如 `/assets\\index-…js`）索引，但浏览器请求为 `/assets/index-…js`，缓存查找失败。
- `wrangler dev --config dist/server/wrangler.json --local` 使用同一份 Vinext 产物的 worker 与 `assets.directory: ../client`，首页、结果页、报告页引用的全部 CSS/JS 均为 HTTP 200。
- 最小修复只调整 `web/package.json` 的生产启动命令和 `scripts/competition.ps1` 的 `--ip`/wrangler 清理标记；不改后端、诊断、知识库、GPU、Qwen 或 UI。浏览器已水合蛴螬 92% 结果、展开 5 条来源并渲染报告检测图片与摘要。

- 最终验收：前端 render tests 8/8、ESLint、backend 69 passed（仅既有 Starlette 弃用警告）、PowerShell 入口测试、带比赛 API 基址的 production build、资源映射及浏览器验收均通过。`competition.ps1 status` 为 Overall READY；本轮没有创建或提交任何新病例、没有触发 GPU E2E、没有 commit/push。

- 为满足报告知识库图片的真实展示，补齐 local Worker 的已有 API proxy bindings：无 bindings 时 `/api/catalog/knowledge/assets/...` 在 3000 返回 503，而 backend 直连为 200；正式比赛入口注入后该 URL 在 3000 返回 image/jpeg 200。该变更仍限于 web build/server routing 与 `competition.ps1` runtime 配置，没有修改 UI 或诊断业务。
