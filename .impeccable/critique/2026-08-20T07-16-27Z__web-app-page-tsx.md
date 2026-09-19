---
target: 第三阶段公共诊断流程视觉辨识度强化
total_score: 35
max_score: 40
na_heuristics:
p0_count: 0
p1_count: 0
timestamp: 2026-08-20T07-16-27Z
slug: web-app-page-tsx
---
⚠️ DEGRADED: single-context (two authorized Assessment A sub-agents remained running without returning; both were closed, while Assessment B completed independently)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | 真实诊断路径清楚，但失败病例仍可能把后续节点标成已完成；旧 health 响应下服务器名称会停在“正在读取”。 |
| 2 | Match System / Real World | 4 | 使用田间采样、目标定位、信息核对和补拍等普通用户可理解的语言。 |
| 3 | User Control and Freedom | 3 | 历史、详情、报告和重试入口清楚；长任务仍不能取消，但用户可离页后从历史查看。 |
| 4 | Consistency and Standards | 4 | 首页、病例和报告共享诊断路径、归属和证据来源语义。 |
| 5 | Error Prevention | 4 | 条件必填、动态缺项、证据不足拒答和无假百分比形成完整防线。 |
| 6 | Recognition Rather Than Recall | 4 | 当前步骤、病例归属、证据来源和下一步都在当前上下文可见。 |
| 7 | Flexibility and Efficiency | 2 | 核心流程有历史入口，但没有面向植保人员的批量或快捷处理能力。 |
| 8 | Aesthetic and Minimalist Design | 4 | 视觉层级克制，项目特征来自结构与语义，不依赖装饰。 |
| 9 | Error Recovery | 4 | 错误使用普通语言，提供补拍、重试或稍后查看，并把内部 URL 收入技术详情。 |
| 10 | Help and Documentation | 3 | 田间拍摄和字段说明就地可见，但缺少更系统的任务帮助入口。 |
| **Total** | | **35/40** | **Good，已接近比赛展示状态** |

## Design Specificity Verdict

界面已经不再像可替换品牌名的通用农业管理系统。六段诊断路径把真实推理流程变成稳定视觉骨架，证据来源标签让“为什么得到这个结论”成为产品语言，病例归属把双服务器架构转化为用户可理解的状态。这三者共同形成了田诊协同的专属识别。

仍有一层通用表单产品的底色：上传与田间字段位于常规白色大容器内，历史卡片仍较标准化。但它们服务于效率，没有盖过诊断路径和证据系统，不需要为追求独特而重做。

自动检测对 `web/app/page.tsx` 返回 0 项发现；桌面与 390px 三个代表页面均无横向溢出。没有可靠的浏览器 overlay，因为浏览器 evaluate 是只读能力；使用截图、DOM 尺寸、CSSOM 和源码检查作为替代证据。

## Overall Impression

第一眼已经是“按证据工作的诊断工具”，而不是“农业数据后台”。最大的剩余机会不是增加视觉效果，而是让诊断路径在失败、拒答和服务不可用状态下同样保持事实准确。

## What's Working

- 六段路径使用真实节点和状态，不显示虚构百分比；桌面横向、移动纵向的转化自然。
- 综合分析把图片观察、目标定位、田间信息和综合核对统一成可扫描来源，知识参考保持独立。
- 诊断名称、证据状态、严重度和当前行动形成明确主次；报告与病例沿用同一语言。

## Priority Issues

### [P2] 失败病例的路径会把未执行阶段标成完成

**Why it matters**：服务不可用病例在第 2 步失败，但病例页显示前四步已完成，报告页甚至显示六步完成，违背“不制造假进度”。

**Fix**：为诊断路径增加“在此停止”状态；根据真实 `resolution_status`、检测结果和分析是否存在，决定停止于目标定位、信息核对或诊断结果。

**Suggested command**：`$impeccable polish`

### [P3] 旧版 health 响应下服务器名称长期显示“正在读取”

**Why it matters**：状态同时显示“服务开放”，会让用户误以为页面仍在加载。

**Fix**：优先显示 label/mode/id 映射；在线但没有名称时使用明确的兼容性占位“当前实例”，避免持续时态。

**Suggested command**：`$impeccable clarify`

### [P3] 报告来源链接在 390px 下为 43.5px

**Why it matters**：只差极小距离但仍低于本项目 44px 触控基线。

**Fix**：让来源链接使用 `inline-flex`、`min-height: 44px` 并垂直居中，不改变打印布局。

**Suggested command**：`$impeccable polish`

## Cognitive Load

- 8 项检查中 1 项轻微失败：植物病例的田间信息组最多同时出现 6 个字段，虽已分组，但桌面端仍是一段较长输入区。
- 没有决策点要求用户同时从超过 4 个操作中选择；诊断路径的 6 个节点是只读序列，不属于 6 个竞争操作。
- 技术详情、知识内容和逐条依据采用渐进披露，整体认知负担低。

## Emotional Journey

- 开始：标题直接回应“是什么、风险、怎么做”，降低首次使用焦虑。
- 等待：真实路径与 CPU 耗时说明提供控制感，不用假进度安抚。
- 结果：诊断结论和当前行动形成情绪峰值，证据摘要提供可信支撑。
- 失败：普通错误文案和补拍/重试路径较稳健；路径错误完成态是唯一破坏信任的低谷。
- 结束：报告将病例归属、证据和知识边界保留下来，结束感完整。

## Persona Red Flags

**Jordan（首次使用者）**：上传和田间信息说明足够明确；风险是植物病例一次出现 6 个字段，需要依赖动态缺项来确认完成顺序。

**Sam（依赖无障碍）**：路径有 `aria-current="step"`、主导航有 `aria-current="page"`、触控和焦点基线清楚；但“在此停止”若只使用琥珀色会失败，必须同时有文本和 ARIA 状态。

**Casey（移动田间用户）**：390px 无溢出、底部导航 46px、上传区足够大；六段纵向路径占用一定首屏高度，但它提供任务方向而非装饰。报告来源链接需要补足到 44px。

## Minor Observations

- 首页服务不可用提醒会把首屏向下推，但这是有价值的真实状态，不建议折叠。
- 报告中的路径在打印时仍清楚，但失败报告必须避免暗示完整诊断已经完成。
- 当前单一绿色强调和暖白表面已足够，不需要继续增加证据颜色。

## Questions to Consider

- 是否应把“诊断路径”视为一条事实记录，而不是普通步骤条，并让失败节点永久保留“在此停止”？
- 比赛展示时，是否更应展示一条成功病例和一条拒答案例，以证明证据系统不仅会给答案，也会克制地不回答？
- 如果未来只增强一处品牌记忆，是否应继续深化“田”字与证据轨迹，而不是增加新的装饰图形？
