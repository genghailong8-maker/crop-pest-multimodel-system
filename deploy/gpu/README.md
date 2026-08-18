# 原 GPU 服务器独立后端

GPU 服务器继续运行现有 detector `127.0.0.1:8870` 和 Qwen3-VL/vLLM `127.0.0.1:8890`，新增独立 FastAPI 后端及 `/root/autodl-tmp/ghl/storage`。该目录保存自己的 SQLite、上传图片和 JSON 报告快照，不与实验室服务器同步。

GPU 开机后：

1. 上传项目到 `/root/autodl-tmp/ghl/app`。
2. 复制 `.env.example` 为 `.env`，核对两个模型服务地址。
3. 运行 `bash deploy/gpu/bootstrap.sh` 和 `bash deploy/gpu/run_backend.sh start`。
4. 确认 `curl http://127.0.0.1:8000/health` 返回 `instance_id=gpu_full`。
5. 从实验室服务器建立持久 SSH 隧道：本机 `127.0.0.1:18000` 转发到 GPU 服务器 `127.0.0.1:8000`。Admin 健康检查通过后才允许切换。
