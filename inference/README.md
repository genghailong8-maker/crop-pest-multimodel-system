# GPU 推理服务

该服务负责加载服务器上的主检测器，并可选接入类 10 检测专家和类 10/13 crop 分类专家，返回归一化检测框及路由审计信息。病例存储、图片质检、类别中文映射、诊断摘要和人工复核仍由 `backend/` 负责。

服务器端默认加载当前生产候选主模型；若该权重不存在则回退到官方基线：

```text
runs/detect/official-plus-public-weak-v1-e120-b64/weights/best.pt
```

当两份专家权重存在时，路由默认为 `shadow`：会运行专家并在响应 `routing` 字段中记录候选、置信度和耗时，但保持主模型检测结果不变。第二轮独立校准的配置未通过 frozen 门，因此不能默认进入 active 生产结果。需要明确验证后才可临时启用：

```bash
export CROP_INFERENCE_ROUTING_MODE=active
```

可通过环境变量调整逐类阈值和路由策略：

```text
CROP_INFERENCE_CLASS10_EXPERT_PATH=runs/detect/weak-expert-v2-full-public10-ft-freeze10-lr1e4-e18-b64/weights/best.pt
CROP_INFERENCE_CROP_EXPERT_PATH=runs/detect/pairwise-crop-cls-10-13-v5-e30-b128/weights/best.pt
CROP_INFERENCE_EXPERT_CANDIDATE_CONFIDENCE=0.05
CROP_INFERENCE_BACKGROUND_THRESHOLD=0.90
CROP_INFERENCE_THRESHOLD10=0.15
CROP_INFERENCE_THRESHOLD13=0.15
CROP_INFERENCE_TEMPERATURE10=1.25
CROP_INFERENCE_TEMPERATURE13=0.75
CROP_INFERENCE_SCORE_MODE=keep
```

`/health` 会返回三份权重的加载状态和 SHA-256；`/v1/detect` 的 `routing` 会返回本次 shadow/active 路由的候选数、决策和专家耗时。专家加载或调用失败时，服务继续返回主模型结果。

部署与启动：

```bash
cd /root/autodl-tmp/crop-pest-system
python -m pip install -r inference/requirements.txt
chmod +x inference/run_server.sh
inference/run_server.sh start
```

服务默认仅监听 `127.0.0.1:8870`。本机运行 `inference/open_tunnel.ps1 -IdentityFile "$env:USERPROFILE\.ssh\<私钥文件名>"` 后，把后端配置为；私钥路径只在本机传入，不写入仓库：

```text
CROP_DETECTOR_ENDPOINT=http://127.0.0.1:8870/v1/detect
```

如设置 `CROP_INFERENCE_API_KEY`，本机后端还需设置同值的 `CROP_DETECTOR_API_KEY`。
