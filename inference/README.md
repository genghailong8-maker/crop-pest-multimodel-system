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

## Qwen3-VL 多模态服务

服务器首次安装与启动：

```bash
chmod +x inference/run_vlm_server.sh
inference/run_vlm_server.sh install
inference/run_vlm_server.sh download
inference/run_vlm_server.sh start
inference/run_vlm_server.sh status
```

服务固定名称为 `crop-pest-vlm`，默认只监听 `127.0.0.1:8890`，模型与隔离环境保存在 `/root/autodl-tmp/crop-pest-vlm`。`open_tunnel.ps1` 会同时建立检测端口 8870 和多模态端口 8890 的私有转发。后端使用：

部署固定 Qwen3-VL revision `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`；AutoDL 无法直接访问 Hugging Face 时默认从 `https://hf-mirror.com` 获取同一官方仓库内容，可通过 `CROP_VLM_HF_ENDPOINT` 覆盖。下载阶段禁用 Xet/CAS，将完整固定快照写入 `${CROP_VLM_ROOT}/model`；服务只加载该本地目录，避免启动时再次访问外部网络。

```text
CROP_VLM_ENDPOINT=http://127.0.0.1:8890/v1/chat/completions
CROP_VLM_MODEL=crop-pest-vlm
CROP_VLM_TIMEOUT_SECONDS=120
```

默认最大上下文为 8192、单请求最多一张图片、GPU 内存利用上限为 0.65。后端在每次请求中传入 `mm_processor_kwargs.max_pixels=1003520`，保留完整画面但约束视觉 token，避免大图超过 8192 上下文。若首次加载因显存不足失败，只允许一次受控重试：设置 `CROP_VLM_MAX_MODEL_LEN=4096` 和 `CROP_VLM_GPU_MEMORY_UTILIZATION=0.72` 后重启；不得静默更换模型。

如设置 `CROP_INFERENCE_API_KEY`，本机后端还需设置同值的 `CROP_DETECTOR_API_KEY`。
