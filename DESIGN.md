---
name: "田诊协同"
description: "面向田间图片辅助识别、证据核对与可追溯报告的临床型农业诊断工作台"
colors:
  ink: "#17231d"
  ink-soft: "#3f5148"
  muted: "#718078"
  line: "#d7e0da"
  line-strong: "#bdcbc2"
  paper: "#f7f9f5"
  surface: "#ffffff"
  surface-soft: "#eef4ef"
  green: "#176b47"
  green-dark: "#0f4d34"
  green-soft: "#e4f0e8"
  lime: "#d1e84f"
  amber: "#8b5d16"
  amber-soft: "#fff5df"
  red: "#a5443f"
  red-soft: "#fff0ee"
typography:
  display: "clamp(42px, 5vw, 62px)"
  page-title: "32–38px"
  section-title: "20–27px"
  body: "14–16px"
  supporting: "12–13px"
  technical: "11–12px"
rounded:
  workbench: "16px"
  section: "12px"
  control: "8–10px"
  label: "5px"
spacing:
  base: "4px"
  compact: "8–18px"
  section: "26–56px"
---

# Design System: 田诊协同 V3

## Overview

**Creative North Star: “临床田间证据台”**

田诊协同不是一个通用后台，而是一张把田间采样、图像定位、信息核对、证据综合和报告输出串起来的诊断工作台。V3 以农业植保的真实判断顺序为结构，用现代临床影像工具的克制感来表达“看见什么、依据什么、下一步做什么”。

视觉语言保持农业绿，但取消大面积装饰性绿色和营销式 Hero。图片是主要证据对象；田间信息是并列输入；结论、风险、行动和依据按用户需要逐层展开。实验室 CPU / 原 GPU 作为低干扰的实例状态持续可见，病例归属不被隐藏在技术页面里。

### Product-specific signatures

- **证据汇流标：** 深绿几何框、叶片形态和三点证据节点组成产品标记，表达图像、田间信息和模型定位汇入一个结论。
- **诊断路径：** 田间采样 → 目标定位 → 信息核对 → 证据综合 → 诊断结果 → 诊断报告，以状态节点和完成/当前/阻断语义表达真实流程，不制造假进度。
- **证据语言：** 图片观察、目标定位、田间信息和综合核对使用来源标签、边界线和证据台账；技术术语只在技术详情或管理员区域出现。

## Colors

深叶绿是唯一品牌主声，暖纸白和墨叶色承担阅读；浅黄绿只标检测框，琥珀只标证据不足/服务不可用，红色只标错误或高风险。公共诊断流程的颜色集中在 `.v3-app` 的 `--v3-*` 变量，避免页面之间形成多个竞争性绿色。

### Named rules

- **One Green Voice:** `green` 负责主操作、品牌和可信状态；`green-dark` 负责强对比行动。
- **Risk Carries Meaning:** 颜色必须与文字状态共同出现，不能单独依靠绿/黄/红传递风险。
- **Evidence Has a Source:** 每条综合分析证据必须能看到它来自图片、目标定位或田间信息。

## Typography

采用系统中文无衬线回退栈：`Avenir Next`、`PingFang SC`、`Microsoft YaHei`、`Noto Sans CJK SC`、Arial。通过字号、字重、行高和负字距建立层级，不使用 AI 风格渐变或装饰字体。

- **Display:** 42–62px，首页“智能诊断”，只承担页面命题。
- **Page title:** 32–38px，病例与报告标题。
- **Section title:** 20–27px，工作台、证据、知识和报告区块。
- **Body:** 14–16px，用户说明、结论和证据正文；知识文档保持 15px 左右、宽度受控。
- **Supporting:** 12–13px，来源、时间、服务器状态和边界文字。
- **Technical:** 11–12px，折叠后的 JSON、模型与 provenance，不能进入普通主阅读路径。

**The Evidence Must Stay Readable:** 面向用户的字段、结论、证据和报告正文保持至少 14px；小字号只用于元数据和技术详情。

## Layout

公共页面最大宽度约 1320px，报告使用约 1040px 的独立纸面。首页先给出紧凑标题和识别服务状态，再进入“田间图片 + 田间信息”的双栏工作台；完成诊断后按“诊断路径 → 核心结论 → 图片证据 → 综合分析 → 知识参考 → 技术详情”阅读。

桌面端图片是左侧主对象，田间字段在右侧；980px 以下降为自然纵向顺序，640px 以下导航、字段、证据和报告全部适配单列。移动端所有主按钮、导航和返回路径保持至少 44px 触控高度，页面禁止横向溢出。

报告是可打印的专业记录：屏幕上保留页头和打印按钮，打印时去除导航、按钮、技术详情和阴影，保留结论、图像、田间信息、证据、知识内容、来源和使用边界。

## Elevation and shape

系统以平面和边界为主，顶层工作台使用轻微阴影，内部信息依靠分隔线和表面色阶。工作台圆角 16px，区块/上传区约 10–12px，按钮和输入框约 8–10px，来源标签约 5px；检测框保持清晰直角边线，避免与普通内容容器混淆。

不把每个字段或证据做成独立 Card，也不使用玻璃拟态、霓虹、紫蓝渐变、无意义仪表盘或大型动画。

## Components

### ProductMark / PublicHeader

`ProductMark` 使用证据汇流标；`PublicHeader` 同时承载品牌、当前导航和“当前识别服务器”。导航使用 `aria-current="page"`，服务器状态使用低干扰 `aria-live="polite"`，不在普通路径展示 IP/端口。

### FieldIntake / ImageEvidenceFrame

`FieldIntake` 以“田间图片”和“田间信息”两个语义组组织表单，保留现有字段名、验证和 FormData。`ImageEvidenceFrame` 统一病例、结果和报告的图片呈现：保留原图比例、明确 alt、提供尺寸、对检测框使用同一坐标语义，不裁剪诊断证据。

### DiagnosisPath

六个真实阶段使用 `done`、`current`、`blocked` 和待处理状态。节点是导航式状态提示，不是估算进度；刷新、失败或服务不可用时只呈现真实状态。

### ConclusionBlock / EvidenceLedger

`DiagnosisSummary` 先回答“可能是什么、风险如何、现在做什么”；“打开诊断报告”是主行动，“查看病例详情”是次级行动。`ComprehensiveAnalysis` 将危害、诱因与逐条证据并列呈现，来源标签帮助普通用户理解依据，技术细节保持折叠。

### KnowledgeSummary / FieldFacts / ReportMasthead

知识库参考与病例证据严格分层；症状、特征、防治建议按纵向阅读。病例字段使用 `FieldFacts` 统一呈现。报告使用独立纸面结构、元数据行、分隔线和打印规则，不把诊断结果伪装成营销页。

## Interaction and motion

动效强度低：按钮 hover/press、状态节点和区域颜色变化只使用短时过渡；不使用滚动劫持、视差、GSAP 或假进度。`prefers-reduced-motion: reduce` 下取消过渡和动画，但保留布局、文本和状态本身。

## Accessibility and truthfulness

- 表单控件保持原生 label/fieldset/legend 和条件必填逻辑。
- 加载、服务离线、错误、拒答和病例创建使用状态语义与清晰文本，不用百分比伪造模型进度。
- 颜色之外同时使用文字、标签、边框和节点传达状态。
- 图片 alt 描述其在当前流程中的证据角色；技术模型名只在折叠区出现。
- 图片辅助判断不替代现场植保诊断、实验室检测或当地经济阈值。

## Do / Don't

### Do

- 保持“田间采样 → 目标定位 → 信息核对 → 证据综合 → 诊断结果 → 报告”的真实阅读顺序。
- 用图片、田间信息、模型定位、知识参考和服务器归属构成产品专属语言。
- 让主结论和下一步行动优先于模型术语，允许用户逐层展开依据。
- 让病例明确属于创建它的识别服务器。

### Don't

- 不把 V3 变成通用 SaaS Landing Page 或后端监控面板。
- 不添加虚假模型指标、用户数量、速度或进度。
- 不裁剪原始上传图、不修改病例/报告数据逻辑，不以知识库内容冒充病例证据。
- 不用多套品牌色、过量卡片、玻璃拟态或炫技动画制造层级。

## V4 Workbench Overlay（2026-08-20）

参考图驱动的公共诊断流程采用“病例工作台”布局：桌面端左侧是深绿工作区导航，顶部持续显示当前识别服务器，内容区先展示真实六步诊断路径，再按“图片证据｜证据与来源｜诊断结论”组织核心病例。历史、趋势、病例详情和报告共享同一工作台外壳；移动端将侧栏转为顶部导航并自然纵向阅读。

V4 新增的产品识别不是装饰，而是三个可复核关系：病例属于哪个识别实例、结论由哪些来源支持、诊断处于哪一个真实阶段。`WorkspaceShell`、`WorkspaceRecordHeader` 和 `EvidenceRail` 是公共壳层组件；具体病例、图片、检测框、知识参考和报告仍由既有 API 与快照提供。

参考图中的日期、姓名、地块、示例病例和额外菜单不属于产品数据，不能复制到页面或由此扩展业务路由。
