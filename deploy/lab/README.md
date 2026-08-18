# 实验室服务器无损部署

目标主机是 CentOS 7，所有新增文件位于 `/data/ghl`。脚本不会格式化、重新分区或删除 `/data` 中的既有文件。

## 顺序

1. 上传代码到 `/data/ghl/app`，使用 `bash deploy/lab/bootstrap-layout.sh` 创建目录。
2. 使用 `bash deploy/lab/prepare-docker-data-root.sh` 检查。若 Docker 不在 `/data/ghl/docker` 且没有运行容器，再显式追加 `--apply`；旧 Docker 目录保留。
3. 将 `.env.example` 复制为 `.env`，通过 `backend/scripts/generate_admin_secrets.py --compose` 交互生成密码哈希和会话密钥。`--compose` 会转义哈希中的 `$`，不得保存明文密码。
4. 放置三个视觉权重：`models/detector/main.pt`、`models/experts/class10.pt`、`models/experts/crop-classifier.pt`。
5. 放置 Qwen3-VL GGUF 为 `models/qwen3-vl/Qwen3VL-8B-Instruct-Q4_K_M.gguf` 和 `mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf`。
6. 离线镜像放入 `cache/images`，Python wheelhouse 放入 `cache/wheels/backend`、`cache/wheels/inference`，npm 缓存放入 `cache/npm`。服务器使用 `docker-compose.offline.yml`，不访问外网构建。
7. 运行 `compatibility-check.sh`；通过后运行 `deploy.sh`，最后运行 `verify.sh`。

默认从 `http://服务器IP:8080` 访问。GPU 服务器尚未开启时，Admin 会将其显示为离线并拒绝切换。实验室 CPU 全链路通过后，再建立 `127.0.0.1:18000 → GPU服务器:8000` 的持久 SSH 隧道并进行双机联调。

## Windows 临时 GPU 中继

实验室服务器没有出站网络时，可由当前 Windows 电脑同时连接 GPU 与实验室服务器。先在实验室安装并启动 `lab-gpu-relay.service`；该服务仅监听 Docker host-gateway，不开放新的局域网或公网端口。然后在项目根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\windows_gpu_relay.ps1 -Action Start
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\windows_gpu_relay.ps1 -Action Status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\windows_gpu_relay.ps1 -Action Stop
```

中继 PID 写入 `tmp/gpu-relay`。Windows 必须保持开机、联网且禁止休眠；中继断开时 Admin 会把 GPU 显示为离线，CPU 实例和两端既有病例不受影响。该临时方案不创建开机启动任务。

## 重装保护

`backup-before-reinstall.sh` 默认只打印范围。只有明确使用 `--apply` 才会把 `/root`、`/home`、`/etc`、MySQL 导出和不位于 `/data` 的 Docker 数据复制到 `/data/ghl/migration-backup/<UTC时间>`，并生成磁盘清单和 SHA-256。重装前还必须停相关服务、做最终增量同步和抽样恢复；Ubuntu 安装界面中禁止格式化 `/data`。
