# 比赛演示流程与离线容错

## 1. 演示目标

用一张真实田间图片在 5 分钟内展示完整证据链：上传与质检、16 类主模型、专家 `shadow` 证据、知识来源与安全边界、人工复核审计，以及训练监控。演示只展示已经固化的事实，不现场切换 `active`、不现场重训、不把无标签图片当成准确率样本。

## 2. 演示前检查

### 需要服务器的部分

完整识别 E2E 需要 RTX 5090 上的检测服务和 Qwen3-VL 多模态服务；检测端应报告 `status=ok`、`class_count=16`、三份模型 `loaded=true`、`routing.mode=shadow`，多模态 `/v1/models` 应列出 `crop-pest-vlm`。训练监控页不是识别链路的硬依赖。

### 不需要服务器的部分

架构讲解、数据治理、知识卡片、安全边界、公开仓库审计和静态复现检查均可离线完成。没有 GPU 时不要把 CPU 结果写成正式性能数据。

### 本机启动

```powershell
# 终端 1：后端
cd backend
$env:CROP_DETECTOR_ENDPOINT = "http://127.0.0.1:8870/v1/detect"
$env:CROP_DETECTOR_TIMEOUT_SECONDS = "30"
$env:CROP_VLM_ENDPOINT = "http://127.0.0.1:8890/v1/chat/completions"
$env:CROP_VLM_MODEL = "crop-pest-vlm"
$env:CROP_VLM_TIMEOUT_SECONDS = "120"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 终端 2：网页
cd web
npm.cmd run dev
```

服务器推理服务和 SSH 隧道按 `inference/README.md` 的既定流程启动；启动后先执行健康检查，再打开网页。
如果只做离线降级演示，省略两行 `CROP_DETECTOR_*` 环境变量即可；如果要做真实识别，确认 endpoint 末尾没有空格，并在后端进程启动前设置它。

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object -ExpandProperty Content
Invoke-WebRequest http://127.0.0.1:8870/health | Select-Object -ExpandProperty Content
Invoke-WebRequest http://127.0.0.1:8890/v1/models | Select-Object -ExpandProperty Content
Invoke-WebRequest http://localhost:3000/ | Select-Object -ExpandProperty StatusCode
```

## 3. 5 分钟讲解脚本

| 时间 | 操作 | 要讲的证据 |
| ---: | --- | --- |
| 0:00–0:30 | 打开首页，指向 4,164/5,920/16 数据概览 | 类别空间与数据治理，不是写死的演示结论 |
| 0:30–1:20 | 上传一张清晰图片，填写作物、部位、生育期和环境 | 图片先经过分辨率、亮度、对比度、清晰度检查 |
| 1:20–2:10 | 点击“开始完整分析”，观察上传、检测、分析三段状态 | 主模型负责定位；专家结果显示为 `shadow`，不覆盖主结果 |
| 2:10–2:50 | 展示多模态字段和“可信边界” | 主/候选诊断、症状、危害、原因、证据、不确定性、一致性、模型溯源及来源 ID |
| 2:50–3:35 | 点击“请求补充证据”，填写拍摄建议并保存 | `review_pending`、reviewer ID、证据快照与审计事件 |
| 3:35–4:10 | 打开历史记录或复核页 | 可追溯病例、复核队列和人工决定 |
| 4:10–4:40 | 打开 `/training` | 训练运行、完成 epoch、GPU 快照和监控证据 |
| 4:40–5:00 | 指向 shadow-only 门和独立 frozen 结论 | 解释为什么当前不批准 active：安全性与证据优先 |

## 4. 离线/故障演示

故意停止后端、隧道或模型服务时，按下面顺序展示，不要刷新到看似成功的旧页面：

1. 后端不可达：网页顶部变为“本地服务未启动”，保留上传界面但不提交虚假结果。
2. 后端可达、模型不可用：上传仍会保存图片；检测状态为 `model_unavailable`，摘要包含原因、`needs_review=true` 和可解释边界。
3. 远程推理超时：后端保留病例和图像质量检查，返回“服务器视觉识别调用失败”，人工复核入口仍可用。
4. 知识服务可用：`GET /api/catalog/knowledge` 和类别卡片不依赖模型权重，可继续展示安全的 IPM 方向。
5. 服务恢复：重新执行健康检查，刷新历史记录；只有新的真实检测完成后才展示新的模型证据。

离线模式绝不执行的动作：伪造检测框、把上一病例套到新图片、自动批准 active、把低置信度结果写成确定诊断、给出具体药剂/剂量/混配建议。

## 5. 现场应急检查表

- [ ] 网页 `http://localhost:3000/` 返回 200。
- [ ] 后端 `/health` 返回 `status=ok`。
- [ ] 推理 `/health` 返回 16 类、三份模型已加载、`routing.mode=shadow`。
- [ ] 多模态 `/v1/models` 返回 `crop-pest-vlm`，后端 `/health` 返回 `multimodal_configured=true`。

- [ ] 有一张本地演示图片；图片无标签时只作为 E2E 证据。
- [ ] 能打开知识卡片来源和安全边界。
- [ ] 能保存一次 `needs_more_evidence` 复核事件。
- [ ] 备好离线截图/录屏；断服时展示降级行为而不是重试到超时。

## 6. Phase 9 本机用户演示顺序

1. 在当前电脑的 Chrome 或 Edge 打开 `http://localhost:3000/`，说明病例和图片保存在本机。
2. 拍照/选图，填写作物、部位、生育期、环境、受害比例和扩散速度。
3. 展示检测框、类别和置信度，再展示两阶段综合分析、诊断风险和田间严重度。
4. 若结论冲突、图片质量异常、无目标或低置信度，指出人工复核原因；不要把候选说成确诊。
5. 打开病例详情、病例历史、7/30 天记录趋势和可打印报告。
6. 展开“查看技术证据”说明主模型、shadow 专家、协议版本和权威来源。
7. 故障演示时关闭模型隧道，确认本机页面显示“识别服务暂时未开放”且不展示伪造结果；历史、详情和报告仍可读取。

本机运行固定使用 `CROP_PUBLIC_MODE=false`，后端和两个模型隧道只监听 `127.0.0.1`。Phase 9 GPU 真实门已经通过：160/160 成功、Top-1 87.50%、内容与严重度引用 100%、冲突识别 15/17、E2E P95 5.087 秒；现场仍应把冲突与复核显示为辅助证据，不把它包装成自动确诊。
