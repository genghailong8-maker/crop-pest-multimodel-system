# 项目模型与大型资产说明

本文件记录当前项目中没有提交到普通 Git 分支的模型、数据和运行资产，供 Work 在 clone 后判断哪些内容需要额外提供。

## `best_model.pth`

- 当前项目相对路径：不存在。
- 当前本地检查结果：未找到 `best_model.pth`。
- 目标仓库 `main` 中虽然存在一个约 565,218 字节的同名文件，但它属于目标仓库原有的旧版 Gradio 分类项目，不是当前 16 类 YOLO + 多模态系统的生产权重，因此没有复制或上传。
- 结论：本次不上传 `best_model.pth`，也不从目标 `main` 恢复它。

## 当前检测模型

当前生产检测器是服务器侧的 YOLO 权重，不随普通 Git 分支提交。服务通过环境变量提供模型路径，默认候选路径和专家路径见 `inference/README.md`：

```text
runs/detect/official-plus-public-weak-v1-e120-b64/weights/best.pt
runs/detect/weak-expert-v2-full-public10-ft-freeze10-lr1e4-e18-b64/weights/best.pt
runs/detect/pairwise-crop-cls-10-13-v5-e30-b128/weights/best.pt
```

实际权重通常位于 GPU/实验室服务器或被 `.gitignore` 排除的训练产物目录。`CROP_INFERENCE_MODEL_PATH`、`CROP_INFERENCE_CLASS10_EXPERT_PATH` 和 `CROP_INFERENCE_CROP_EXPERT_PATH` 可在运行环境中提供它们。

## Qwen3-VL / GGUF

- 本地离线缓存中的 `tmp/offline/qwen3-vl/Qwen3VL-8B-Instruct-Q4_K_M.gguf` 约 5,027,784,800 字节；不提交。
- 配套 `tmp/offline/qwen3-vl/mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf` 约 752,289,728 字节；不提交。
- 该缓存目录还包含离线镜像、Python wheel、npm cache 等运行资产，全部不提交。
- GPU 端可按 `inference/run_vlm_server.sh` 和 `inference/README.md` 使用固定 Qwen3-VL 版本；实验室 CPU 端按 `deploy/lab/README.md` 提供 GGUF 和 `llama.cpp` 运行环境。

## 数据和示例

- 完整官方训练图片、YOLO 标签和 `Image Data base/` 不在当前工作区，未上传；目录和划分说明见 `DATASET.md`。
- 当前工作区根目录不存在 `example/`、根 `app.py`、根 `main.py` 或根 `requirements.txt`；这些是目标仓库旧版项目的文件名，不代表当前系统入口。
- 当前系统入口分别为 `backend/app/main.py`、`web/app/`、`inference/service.py` 和 `training/`，依赖文件为 `backend/pyproject.toml`、`backend/.env.example`、`inference/requirements.txt` 与 `web/package.json`/`web/package-lock.json`。

## Work 的运行边界

仅依赖本仓库即可完成：

1. 项目结构、前后端接口、页面组件、知识库和部署脚本分析；
2. 后端测试与前端静态构建；
3. 不连接真实模型服务的接口/降级路径验收。

要完成真实检测和多模态端到端验收，还需要在运行环境中额外提供检测权重、Qwen3-VL 模型和对应的 8870/8890 服务，或配置可访问的推理端点。不要把 API key、SSH 私钥、管理员密码、SQLite、病例图片或服务器运行目录上传到 GitHub。
