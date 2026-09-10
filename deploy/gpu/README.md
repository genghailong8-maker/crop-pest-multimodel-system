# 原 GPU 服务器独立后端

GPU 服务器继续运行 detector `127.0.0.1:8870`，新增独立 FastAPI 后端及 `/root/autodl-tmp/ghl/storage`。该目录保存自己的 SQLite、上传图片和 JSON 报告快照，不与实验室服务器同步。外部资料由 CPU 后端的 Tavily、EvidenceNormalizer、EvidenceExtractor 与本地知识库处理；GPU 只承载 YOLO detector。

GPU 开机后：

1. 上传项目到 `/root/autodl-tmp/ghl/app`。
2. 复制 `.env.example` 为 `.env`，核对 detector 服务地址。
3. 运行 `bash deploy/gpu/bootstrap.sh` 和 `bash deploy/gpu/run_backend.sh start`。
4. 确认 `curl http://127.0.0.1:8000/health` 返回 `instance_id=gpu_full`。
5. 从实验室服务器建立持久 SSH 隧道：本机 `127.0.0.1:18000` 转发到 GPU 服务器 `127.0.0.1:8000`。Admin 健康检查通过后才允许切换。
