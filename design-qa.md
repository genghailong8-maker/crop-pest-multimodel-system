# 最终 UI 视觉落地 Design QA

Reference images:

- `C:\Users\GENGHA~1\AppData\Local\Temp\codex-clipboard-2d97e465-6b9e-46cb-83ee-09041c82ef68.png`（首页）
- `C:\Users\GENGHA~1\AppData\Local\Temp\codex-clipboard-f48634b0-11f1-468d-b50a-544a8f65640f.png`（结果）
- `C:\Users\GENGHA~1\AppData\Local\Temp\codex-clipboard-f267b008-58e7-4c6d-b082-9b4e52bf5126.png`（报告）

Captured local verification screenshots:

- `C:\Users\genghailong\AppData\Local\Temp\crop-pest-ui-final-20260824\01-home.png`
- `C:\Users\genghailong\AppData\Local\Temp\crop-pest-ui-final-20260824\02-result-grub.png`
- `C:\Users\genghailong\AppData\Local\Temp\crop-pest-ui-final-20260824\03-report-grub.png`
- `C:\Users\genghailong\AppData\Local\Temp\crop-pest-ui-final-20260824\04-evidence-unavailable.png`

## Result

**Final result: passed**

## Compared and checked

- 首页：保留居中标题、服务状态、双栏真实上传/田间表单和弱化结果预览；没有加入静态伪图片或虚构指标。
- 结果：用既有蛴螬病例 `lab_cpu-4361d9fada86434ba588b5031e3a8961` 的真实 92% 定位图、5 条来源和本地知识库防治内容对照。图片、名称与置信度优先，危害/诱因/防治使用克制的细语义色条，来源原生展开。
- 病例与报告：元数据、图片和诊断摘要在首屏；知识库、来源边界和技术详情折叠为次级信息；打印样式隐藏导航、操作和技术详情。
- 降级：用既有来源不可用病例验证“需要补拍”与“暂未检索到可靠资料”不会生成补写结论。
- 响应式：1100px、820px、560px 三个布局断点使导航、双栏、字段、来源行、知识库和报告纸面自然转为单列；没有针对移动端另写业务逻辑。
- 功能：上传、FormData、检测框、GET 病例/报告、外部来源链接、`local_knowledge_base`、重试、知识库与 `window.print()` 均保留。`?case=<id>` 只读加载已有病例，用于视觉复现，不触发诊断。
- 验证：`npm test` 8/8 passed，`npm run lint` passed，`npm run build` passed，`git diff --check` passed。

真实 GPU 单例 E2E 未执行：本轮按用户要求不主动调用 GPU/SSH；待 GPU 可用后再以一条蛴螬病例复验前端 → Backend → YOLO → Qwen3-VL → Tavily。
